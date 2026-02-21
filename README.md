# Wallet Service

A production-ready, closed-loop virtual currency wallet built with **Django**, **PostgreSQL**, and **Django REST Framework**. It supports real-time top-ups, bonuses, and spending - all backed by a **double-entry ledger**, **idempotent mutations**, and **row-level concurrency control**.

> **Live URL:** [`https://wallet-service-0tjx.onrender.com/docs`](https://wallet-service-0tjx.onrender.com/docs)

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture Overview](#architecture-overview)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Run with Docker (Recommended)](#run-with-docker-recommended)
  - [Run without Docker](#run-without-docker)
- [API Documentation](#api-documentation)
  - [Interactive Docs (Swagger)](#interactive-docs-swagger)
  - [Endpoints](#endpoints)
  - [Seeded Test Data](#seeded-test-data)
  - [Idempotency](#idempotency)
  - [Error Codes](#error-codes)
- [Testing](#testing)
  - [Unit Tests (pytest)](#unit-tests-pytest)
  - [Integration Test Suite](#integration-test-suite)
- [Database Schema](#database-schema)
- [Design Decisions](#design-decisions)
  - [Concurrency & Locking](#concurrency--locking)
  - [Double-Entry Ledger](#double-entry-ledger)
  - [Rate Limiting](#rate-limiting)
  - [Audit Logging](#audit-logging)
- [Deployment (Render)](#deployment-render)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [License](#license)

---

## Features

| Feature | Description |
|---------|-------------|
| **Multi-wallet support** | Each user can hold wallets for different asset types |
| **Idempotent mutations** | Every top-up, bonus, and spend requires an `Idempotency-Key` header - replay the same request safely |
| **Double-entry ledger** | Every transaction produces balanced debit + credit entries. Your books always add up to zero |
| **Row-level locking** | `SELECT ... FOR UPDATE` with ascending UUID ordering prevents race conditions *and* deadlocks |
| **Per-IP rate limiting** | 60 req/min for mutations, 200 req/min for reads - abuse is capped, audit log growth is bounded |
| **Full audit trail** | Every request (success, failure, rate-limited) is recorded with IP, payload, and response code |
| **Swagger UI** | Interactive API docs available at `/docs` out of the box |
| **One-command Docker setup** | `docker compose up` - that's it. Migrations, seed data, and the server all start automatically |

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Framework** | Django 5.0 | Battle-tested ORM, `select_for_update()`, `transaction.atomic()`, and built-in migration system |
| **API** | Django REST Framework 3.15 | Clean `APIView` pattern, content negotiation, and a mature ecosystem |
| **Database** | PostgreSQL 16 | Full ACID, `SELECT ... FOR UPDATE` row locking, `CHECK` constraints |
| **Rate Limiting** | django-ratelimit 4.1 | Per-IP limiting using Django's in-memory cache - zero DB overhead |
| **API Docs** | drf-spectacular 0.29 | Auto-generated OpenAPI 3.0 schema with Swagger UI and ReDoc |
| **Static Files** | whitenoise 6.7 | Serves static assets directly from the app process - no nginx required on Render |
| **Server** | Gunicorn 22 | Pre-fork worker model, 4 workers by default |
| **Containerization** | Docker + Docker Compose | Reproducible builds, single-command local dev |

---

## Architecture Overview

```
Client Request
      │
      ▼
┌─────────────────────┐
│    Rate Limiter      │  ← 60/min mutations, 200/min reads
│  (django-ratelimit)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    API View Layer    │  ← Validates input, checks Idempotency-Key
│  (DRF APIView)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    Service Layer     │  ← Atomic transaction + SELECT FOR UPDATE
│  (services.py)      │  ← Idempotency via get_or_create
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Double-Entry       │
│   Ledger Engine      │  ← Every mutation = 1 debit + 1 credit
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Audit Log Writer    │  ← Runs OUTSIDE the main transaction
│  (append-only)       │  ← Never fails the client request
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │  PostgreSQL   │
    └──────────────┘
```

---

## Getting Started

### Prerequisites

- **Docker** + **Docker Compose** (recommended), _or_
- **Python 3.12+** and **PostgreSQL 14+** for local development

### Run with Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/geeked-anshuk666/Dummy_wallet_service_test.git
cd Dummy_wallet_service_test

# Start everything - DB, migrations, seed data, server
docker compose up --build
```

That's it. The app runs at **http://localhost:8080** with pre-seeded wallets ready to use.

To stop and start fresh:

```bash
docker compose down -v          # removes volumes (resets DB)
docker compose up --build -d    # rebuild and start in background
```

### Run without Docker

```bash
# 1. Create a virtual environment
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment variables (create a .env file or export them)
# SECRET_KEY=your-secret-key
# DEBUG=True
# DATABASE_URL=postgresql://wallet_user:wallet_pass@localhost:5432/wallet_db

# 4. Ensure PostgreSQL is running and the database exists
createdb wallet_db  # or use pgAdmin/your preferred method

# 5. Run migrations (includes seed data)
python manage.py migrate

# 6. Start the server
python manage.py runserver 8080
# or with Gunicorn:
gunicorn wallet_service.wsgi:application --bind 0.0.0.0:8080 --workers 4
```

---

## API Documentation

### Interactive Docs (Swagger)

Once the service is running, open your browser:

| URL | What it is |
|-----|-----------|
| [`/docs`](http://localhost:8080/docs) | **Swagger UI** - interactive playground where you can try every endpoint |
| [`/redoc`](http://localhost:8080/redoc) | **ReDoc** - clean, read-only reference documentation |
| [`/schema`](http://localhost:8080/schema) | Raw **OpenAPI 3.0** JSON schema (useful for code generation) |

### Endpoints

All endpoints return JSON. Mutation endpoints require an `Idempotency-Key` header.

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|-----------|
| `GET` | `/api/v1/wallets` | **List all wallets** (start here!) | 200/min |
| `POST` | `/api/v1/wallets/{wallet_id}/topup` | Credit wallet from treasury | 60/min |
| `POST` | `/api/v1/wallets/{wallet_id}/bonus` | Credit wallet from bonus pool | 60/min |
| `POST` | `/api/v1/wallets/{wallet_id}/spend` | Debit wallet, credit revenue | 60/min |
| `GET` | `/api/v1/wallets/{wallet_id}/balance` | Current balance | 200/min |
| `GET` | `/api/v1/wallets/{wallet_id}/transactions` | Paginated transaction history | 200/min |
| `GET` | `/health` | Health check | - |

#### Example - Top up Alice's wallet with 100 Gold Coins

```bash
curl -X POST http://localhost:8080/api/v1/wallets/44444444-4444-4444-4444-444444444444/topup \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: my-unique-key-001" \
  -d '{"amount": 100, "asset_type_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}'
```

**Response (201 Created):**

```json
{
  "transaction_id": "d7a1f2c3-...",
  "wallet_id": "44444444-4444-4444-4444-444444444444",
  "asset_type": "Gold Coins",
  "amount": 100,
  "direction": "CREDIT",
  "new_balance": 600,
  "created_at": "2026-02-22T10:30:00.000000Z"
}
```

#### Example - Check balance

```bash
curl http://localhost:8080/api/v1/wallets/44444444-4444-4444-4444-444444444444/balance
```

**Response (200 OK):**

```json
{
  "wallet_id": "44444444-4444-4444-4444-444444444444",
  "user": "alice",
  "asset_type": "Gold Coins",
  "symbol": "GLD",
  "balance": 600
}
```

#### Example - Spend (insufficient balance)

```bash
curl -X POST http://localhost:8080/api/v1/wallets/44444444-4444-4444-4444-444444444444/spend \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: overspend-001" \
  -d '{"amount": 999999, "asset_type_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}'
```

**Response (422 Unprocessable Entity):**

```json
{
  "error": "INSUFFICIENT_BALANCE",
  "message": "wallet balance 600 is less than spend amount 999999"
}
```

#### Example - Transaction History (paginated)

```bash
curl "http://localhost:8080/api/v1/wallets/44444444-4444-4444-4444-444444444444/transactions?page=1&per_page=5"
```

### Seeded Test Data

The database comes pre-loaded with wallets you can use immediately:

| Owner | Wallet ID | Asset | Balance |
|-------|-----------|-------|---------|
| Alice | `44444444-4444-4444-4444-444444444444` | Gold Coins (GLD) | 500 |
| Bob | `55555555-5555-5555-5555-555555555555` | Gold Coins (GLD) | 200 |

**Asset Type ID:** `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa` (Gold Coins)

System wallets (treasury, bonus pool, revenue) are also seeded and managed internally by the service.

### Idempotency

Every mutation endpoint (`topup`, `bonus`, `spend`) requires an `Idempotency-Key` header.

- **First request** -> processes normally, returns `201 Created`
- **Replay with the same key** -> returns the original result with `200 OK` and `"replayed": true`
- **No header** -> rejected with `400 Bad Request`

This means you can safely retry failed network requests without worrying about duplicate charges or double-credits.

### Error Codes

| HTTP Code | Error Key | When |
|-----------|----------|------|
| `400` | - | Missing `Idempotency-Key`, missing `amount`/`asset_type_id`, or non-positive amount |
| `404` | `wallet not found` | Wallet UUID doesn't exist (read endpoints) |
| `422` | `INSUFFICIENT_BALANCE` | Spend amount exceeds current balance |
| `422` | `WALLET_NOT_FOUND` | Wallet UUID doesn't exist (mutation endpoints) |
| `429` | `RATE_LIMIT_EXCEEDED` | Too many requests from your IP |
| `500` | `INTERNAL_ERROR` | Unexpected server error |

---

## Testing

### Unit Tests (pytest)

The project includes 7 test files covering all core functionality:

```bash
# Run all tests
pytest -v

# Run inside Docker
docker compose exec app pytest -v
```

**Test coverage includes:**
- Top-up, bonus, and spend operations
- Balance updates and ledger integrity
- Idempotency (replay detection, no double-processing)
- Concurrency (multi-threaded `select_for_update` behavior)
- Rate limiting (429 responses, audit log entries)
- Audit logging (success, failure, and rate-limited events)

### Integration Test Suite

A standalone test suite lives in the `Test Suite/` directory. These are separate Python scripts that hit the live API using the `requests` library - no Django test client involved.

```bash
# Run the full suite against localhost
python "Test Suite/run_all.py"

# Run against a deployed instance
set WALLET_SERVICE_URL=https://wallet-service-0tjx.onrender.com
python "Test Suite/run_all.py"

# Run a single test
python "Test Suite/04_topup.py"
```

**14 test cases covering:**

| # | Test | Validates |
|---|------|-----------|
| 01 | Health check | Service is alive |
| 02 | Alice balance (seeded) | Seed migration ran correctly |
| 03 | Bob balance (seeded) | Multi-wallet seed data |
| 04 | Topup +100 | CREDIT mutation works |
| 05 | Balance after topup | State persisted correctly |
| 06 | Spend -30 | DEBIT mutation works |
| 07 | Overspend 999999 | Rejected with 422 |
| 08 | Balance after overspend | Unchanged after rejection |
| 09 | Idempotency replay | Same key -> `replayed: true` |
| 10 | Balance after replay | No double-credit |
| 11 | Bonus +50 | Bonus pool -> user wallet |
| 12 | Transaction history | Paginated ledger entries |
| 13 | Missing Idempotency-Key | 400 rejection |
| 14 | Negative amount | 400 validation |

> **Note:** Tests 02–12 are sequential and depend on the DB state from earlier tests. Reset the database before re-running: `docker compose down -v && docker compose up -d`

---

## Database Schema

Five core tables power the service:

```
┌──────────────┐     ┌──────────────────────┐     ┌───────────────┐
│  AssetType   │     │   WalletTransaction  │     │   AuditLog    │
│              │     │                      │     │               │
│  id (UUID)   │     │  id (UUID)           │     │  id (UUID)    │
│  name        │◄────│  idempotency_key     │     │  action       │
│  symbol      │     │  type (TOPUP/BONUS/  │     │  wallet_id    │
│  description │     │        SPEND)        │     │  status       │
└──────┬───────┘     │  amount              │     │  request_body │
       │             │  created_at          │     │  ip_address   │
       │             └──────────┬───────────┘     │  error_message│
       │                        │                 │  created_at   │
       ▼                        ▼                 └───────────────┘
┌──────────────┐     ┌──────────────────────┐
│    Wallet    │     │     LedgerEntry      │
│              │     │                      │
│  id (UUID)   │◄────│  id (UUID)           │
│  user (FK)   │     │  wallet (FK)         │
│  asset_type  │     │  transaction (FK)    │
│  balance     │     │  asset_type (FK)     │
│  is_system   │     │  direction (CR/DR)   │
│  created_at  │     │  amount              │
│  updated_at  │     │  created_at          │
└──────────────┘     └──────────────────────┘
```

The full SQL schema is available in [`schema.sql`](schema.sql) and seed data in [`seed.sql`](seed.sql).

---

## Design Decisions

### Concurrency & Locking

When a mutation request comes in, the service acquires **row-level locks** on the involved wallets using PostgreSQL's `SELECT ... FOR UPDATE`:

```python
wallet_ids = sorted([source_id, dest_id])
wallets = Wallet.objects.select_for_update().filter(id__in=wallet_ids).order_by('id')
```

**Why sort by UUID?** If two transactions try to lock Wallet A then Wallet B, while another tries B then A - you get a **deadlock**. By always locking in ascending UUID order, every transaction acquires locks in the same sequence, making circular waits impossible.

The entire mutation runs inside `transaction.atomic()`. If anything fails, the database rolls back to a consistent state. No partial updates - ever.

### Double-Entry Ledger

Every transaction creates **exactly two** `LedgerEntry` records:

- A `DEBIT` on the source wallet (e.g., treasury)
- A `CREDIT` on the destination wallet (e.g., Alice)

The sum of all ledger entries across all wallets is always **zero**. This isn't just a nice property - it's an invariant that makes it trivial to detect bugs. If debits ≠ credits, something went wrong, and you can pinpoint exactly where.

### Rate Limiting

| Endpoint Type | Limit | Group |
|--------------|-------|-------|
| Mutations (topup, bonus, spend) | 60 requests/min per IP | Separate groups per endpoint |
| Reads (balance, transactions) | 200 requests/min per IP | Separate groups per endpoint |

Rate limiting uses Django's in-memory cache (`LocMemCache`), so it adds **zero database queries**. If you're running multiple Gunicorn workers, each worker has its own counter - this is an acceptable trade-off for local development. For production with stricter requirements, swap to Redis.

Rate-limited requests return HTTP `429` and are still **recorded in the audit log** so you can track abuse attempts.

### Audit Logging

The `AuditLog` table is **append-only** and captures:
- What action was attempted
- Which wallet was involved
- Whether it succeeded or failed
- The request payload and IP address
- The HTTP status code returned

Key design choices:
1. **Audit writes happen OUTSIDE the main transaction** - if a spend fails and rolls back, the audit log entry **still persists**. You want to know about failed attempts.
2. **Audit failures are silently swallowed** - if the audit log write itself fails (disk full, etc.), the client's actual request is never affected. The service logs the error to stderr and moves on.

---

## Deployment (Render)

### Step 1 - Push to GitHub

```bash
git remote add origin https://github.com/<your-username>/wallet-service.git
git push -u origin main
```

### Step 2 - Create a PostgreSQL Database

1. Go to the [Render Dashboard](https://dashboard.render.com) -> **New** -> **PostgreSQL**
2. Name: `wallet-db`, plan: **Free** -> **Create Database**
3. Copy the **Internal Database URL** (starts with `postgresql://...`)

### Step 3 - Create a Web Service

1. Render Dashboard -> **New** -> **Web Service**
2. Connect your GitHub repository
3. Configure:
   - **Runtime:** Docker
   - **Branch:** `main`
   - **Region:** Same as your database
   - **Instance Type:** Free

### Step 4 - Set Environment Variables

In the Render web service settings, add:

| Variable | Value |
|----------|-------|
| `SECRET_KEY` | Generate one: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | `False` |
| `DATABASE_URL` | Paste the Internal Database URL from Step 2 |
| `ALLOWED_HOSTS` | `<YOUR_RENDER_DOMAIN>.onrender.com` |

### Step 5 - Deploy

Click **Create Web Service**. Render will:
1. Build the Docker image
2. Run `python manage.py migrate` (creates tables + seeds data)
3. Run `python manage.py collectstatic --noinput`
4. Start Gunicorn on the port Render assigns

Your service will be live at:

```
https://<YOUR_RENDER_DOMAIN>.onrender.com
```

**Useful endpoints after deployment:**

| URL | Purpose |
|-----|---------|
| [`/health`](https://wallet-service-0tjx.onrender.com/health) | Verify the service is running |
| [`/docs`](https://wallet-service-0tjx.onrender.com/docs) | Swagger UI |
| [`/redoc`](https://wallet-service-0tjx.onrender.com/redoc) | ReDoc |

> 💡 **Note:** Render's free tier spins down after 15 minutes of inactivity. The first request after a cold start takes ~30–50 seconds - this is expected and normal for the free plan.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes (prod) | `django-insecure-dev-only-...` | Django secret key. **Must** be changed in production. |
| `DEBUG` | No | `True` | Set to `False` in production. |
| `DATABASE_URL` | Yes (prod) | `postgresql://wallet_user:wallet_pass@localhost:5432/wallet_db` | PostgreSQL connection string. |
| `ALLOWED_HOSTS` | No | `*` | Comma-separated list of allowed hostnames. Set to your Render domain in production. |

---

## Project Structure

```
wallet_service/
├── .dockerignore              # Excludes venv, .git, test files from Docker builds
├── Dockerfile                 # Python 3.12-slim, runs migrate + collectstatic + gunicorn
├── docker-compose.yml         # PostgreSQL 16 + app service with healthcheck
├── requirements.txt           # Pinned dependencies
├── manage.py                  # Django management script
├── pytest.ini                 # pytest -> Django settings binding
├── schema.sql                 # Human-readable SQL schema reference
├── seed.sql                   # Standalone SQL seed data
│
├── wallet_service/            # Django project config
│   ├── settings.py            # DB, cache, DRF, drf-spectacular, whitenoise
│   ├── urls.py                # Root routing: /api/v1/, /health, /docs, /schema
│   └── wsgi.py                # WSGI entry point for Gunicorn
│
├── wallets/                   # Core app
│   ├── models.py              # AssetType, Wallet, WalletTransaction, LedgerEntry, AuditLog
│   ├── services.py            # Business logic: topup(), bonus(), spend(), _execute_transfer()
│   ├── views.py               # 6 API views with @extend_schema annotations
│   ├── urls.py                # /wallets/<uuid>/topup|bonus|spend|balance|transactions
│   ├── audit.py               # Resilient audit log writer
│   ├── exceptions.py          # InsufficientBalanceError, WalletNotFoundError
│   ├── migrations/
│   │   ├── 0001_initial.py    # Schema creation
│   │   └── 0002_seed.py       # Seed data (asset types, users, wallets, balances)
│   └── tests/                 # 7 test files
│       ├── conftest.py        # Shared fixtures
│       ├── test_topup.py
│       ├── test_bonus.py
│       ├── test_spend.py
│       ├── test_idempotency.py
│       ├── test_concurrency.py
│       ├── test_rate_limit.py
│       └── test_audit_log.py
│
└── Test Suite/                # Standalone integration tests (requests library)
    ├── config.py              # Base URL + wallet IDs (env var configurable)
    ├── run_all.py             # Runs all 14 tests in order
    ├── 01_health_check.py
    ├── 02_alice_balance_seeded.py
    ├── ...
    └── 14_negative_amount.py
```

---

## License

This project is for educational and demonstration purposes. Feel free to use it as a reference for building your own wallet services.

---

_Built with Django, PostgreSQL, and a healthy respect for ACID transactions._
