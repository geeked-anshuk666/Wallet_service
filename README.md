# Wallet Service

A closed-loop virtual currency wallet service built with Django and PostgreSQL.

## Quick Start (Docker)

Requirements: Docker, Docker Compose

```bash
git clone <repo-url>
cd wallet-service
docker-compose up --build
```

The app will be available at http://localhost:8080.
This automatically runs all migrations and seeds the database on first startup.

## Running Without Docker

Requirements: Python 3.12+, PostgreSQL

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your local DATABASE_URL
python manage.py migrate
gunicorn wallet_service.wsgi:application --bind 0.0.0.0:8080
```

## Running the Seed Script Manually

```bash
python manage.py migrate wallets 0001
psql $DATABASE_URL -f seed.sql
```

## Database Schema

```bash
cat schema.sql
```

## Tech Choices

**Django** — built-in ORM with `select_for_update()` for row-level locking and `transaction.atomic()` for atomicity. Migrations handle schema and seed data in one place.

**PostgreSQL** — chosen for `SELECT ... FOR UPDATE` row-level locking, `CHECK` constraints, and full ACID compliance.

**Django REST Framework** — JSON parsing and response formatting. Transaction endpoints use custom `APIView` logic.

**django-ratelimit** — per-IP rate limiting on all endpoints to prevent abuse and audit log flooding. Uses Django's cache backend so it adds no DB overhead.

## Concurrency Strategy

When a spend or top-up request comes in, the service locks the relevant wallet rows using `select_for_update()` before reading any balances. This translates to `SELECT ... FOR UPDATE` in PostgreSQL — any other request trying to modify the same wallets has to wait. Two simultaneous spends on the same wallet run one after the other, never in parallel.

**Deadlock prevention:** always lock wallet rows in ascending UUID order. Since every transaction acquires locks in the same order, no circular wait can form.

```python
wallet_ids = sorted([source_id, dest_id])
wallets = Wallet.objects.select_for_update().filter(id__in=wallet_ids).order_by('id')
```

## Rate Limiting

All endpoints are rate limited per IP address:
- Mutation endpoints (topup, bonus, spend): 60 requests per minute
- Read endpoints (balance, transaction history): 200 requests per minute

Exceeding the limit returns HTTP 429. Every rate-limited request is recorded in the audit log.

This protects against audit log flooding — an attacker hammering the API is capped at 60 write attempts per minute per IP, keeping log growth bounded.

## Audit Logging

Every API request — successful or not, including rate-limited hits — is recorded in `wallets_auditlog`. Each entry captures: action, wallet ID, status, request payload, HTTP response code, client IP, and error message if applicable.

Audit log writes happen outside the main database transaction so that rolled-back transactions (e.g. failed spends) still produce a log entry. A failed audit log write never affects the client response.

## API Reference

All endpoints return JSON. Mutation endpoints require an `Idempotency-Key` header.

**Seeded wallet IDs for testing:**
- Alice's Gold Coins wallet: `44444444-4444-4444-4444-444444444444`
- Bob's Gold Coins wallet:   `55555555-5555-5555-5555-555555555555`
- Gold Coins asset type ID:  `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa`

### Top-up
```bash
curl -X POST http://localhost:8080/api/v1/wallets/44444444-4444-4444-4444-444444444444/topup \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: pay-ref-001" \
  -d '{"amount": 100, "asset_type_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}'
```

### Bonus
```bash
curl -X POST http://localhost:8080/api/v1/wallets/44444444-4444-4444-4444-444444444444/bonus \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: bonus-ref-001" \
  -d '{"amount": 50, "asset_type_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}'
```

### Spend
```bash
curl -X POST http://localhost:8080/api/v1/wallets/44444444-4444-4444-4444-444444444444/spend \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: spend-ref-001" \
  -d '{"amount": 30, "asset_type_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"}'
```

### Check Balance
```bash
curl http://localhost:8080/api/v1/wallets/44444444-4444-4444-4444-444444444444/balance
```

### Transaction History
```bash
curl "http://localhost:8080/api/v1/wallets/44444444-4444-4444-4444-444444444444/transactions?page=1&per_page=20"
```

## Running Tests

```bash
pytest
```

## Deployment (Render)

### Step 1 — Push to GitHub
```bash
git remote add origin https://github.com/<your-username>/wallet-service.git
git push -u origin main
```

### Step 2 — Create PostgreSQL on Render
1. Render dashboard → **New** → **PostgreSQL**
2. Name it `wallet-db`, free tier → **Create Database**
3. Copy the **Internal Database URL**

### Step 3 — Create Web Service
1. Render dashboard → **New** → **Web Service**
2. Connect your GitHub repo, then set:
   - **Runtime:** Docker
   - **Branch:** `main`
   - **Region:** same as your DB
   - **Instance Type:** Free

### Step 4 — Set Environment Variables

| Key | Value |
|-----|-------|
| `SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DEBUG` | `False` |
| `DATABASE_URL` | paste Internal Database URL from Step 2 |

### Step 5 — Deploy
Click **Create Web Service**. Render builds the image and runs:
```
python manage.py migrate && gunicorn wallet_service.wsgi:application --bind 0.0.0.0:8080 --workers 4
```

## Live URL

https://<your-service-name>.onrender.com

> Note: Render's free tier spins down after 15 minutes of inactivity. The first request after a sleep takes ~30 seconds to respond — this is expected.
