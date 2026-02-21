"""Smoke test for the wallet service — run against a live instance."""
import json
import requests

BASE = "http://localhost:8080"
ALICE = "44444444-4444-4444-4444-444444444444"
BOB = "55555555-5555-5555-5555-555555555555"
GOLD = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

passed = 0
failed = 0


def test(name, response, expected_status, checks=None):
    global passed, failed
    ok = response.status_code == expected_status
    data = None
    try:
        data = response.json()
    except Exception:
        pass

    if ok and checks:
        for key, val in checks.items():
            if data.get(key) != val:
                ok = False
                break

    status = "PASS" if ok else "FAIL"
    marker = "[+]" if ok else "[X]"
    if ok:
        passed += 1
    else:
        failed += 1
    print(f"  {marker} {status}  {name}")
    print(f"         HTTP {response.status_code} → {json.dumps(data, indent=None)[:120]}")
    if not ok:
        print(f"         Expected HTTP {expected_status}")
    print()


print("=" * 60)
print("  WALLET SERVICE SMOKE TEST")
print("=" * 60)
print()

# 1. Health check
print("--- Health ---")
test("Health check", requests.get(f"{BASE}/health"), 200, {"status": "healthy"})

# 2. Alice balance (seeded at 500)
print("--- Balance (seeded) ---")
test("Alice balance = 500", requests.get(f"{BASE}/api/v1/wallets/{ALICE}/balance"), 200, {"balance": 500})
test("Bob balance = 200", requests.get(f"{BASE}/api/v1/wallets/{BOB}/balance"), 200, {"balance": 200})

# 3. Topup
print("--- Topup ---")
r = requests.post(f"{BASE}/api/v1/wallets/{ALICE}/topup",
                   json={"amount": 100, "asset_type_id": GOLD},
                   headers={"Idempotency-Key": "smoke-topup-001"})
test("Topup Alice +100 → 201", r, 201, {"new_balance": 600})

# 4. Balance after topup
r = requests.get(f"{BASE}/api/v1/wallets/{ALICE}/balance")
test("Alice balance = 600", r, 200, {"balance": 600})

# 5. Spend
print("--- Spend ---")
r = requests.post(f"{BASE}/api/v1/wallets/{ALICE}/spend",
                   json={"amount": 30, "asset_type_id": GOLD},
                   headers={"Idempotency-Key": "smoke-spend-001"})
test("Spend Alice -30 → 201", r, 201, {"new_balance": 570})

# 6. Overspend
print("--- Overspend ---")
r = requests.post(f"{BASE}/api/v1/wallets/{ALICE}/spend",
                   json={"amount": 999999, "asset_type_id": GOLD},
                   headers={"Idempotency-Key": "smoke-overspend-001"})
test("Overspend → 422", r, 422, {"error": "INSUFFICIENT_BALANCE"})

# 7. Balance unchanged after overspend
r = requests.get(f"{BASE}/api/v1/wallets/{ALICE}/balance")
test("Alice balance still 570", r, 200, {"balance": 570})

# 8. Idempotency replay
print("--- Idempotency ---")
r = requests.post(f"{BASE}/api/v1/wallets/{ALICE}/topup",
                   json={"amount": 100, "asset_type_id": GOLD},
                   headers={"Idempotency-Key": "smoke-topup-001"})
test("Replay topup → 200 + replayed:true", r, 200, {"replayed": True})

# Balance should NOT have changed from the replay
r = requests.get(f"{BASE}/api/v1/wallets/{ALICE}/balance")
test("Balance unchanged after replay = 570", r, 200, {"balance": 570})

# 9. Bonus
print("--- Bonus ---")
r = requests.post(f"{BASE}/api/v1/wallets/{ALICE}/bonus",
                   json={"amount": 50, "asset_type_id": GOLD},
                   headers={"Idempotency-Key": "smoke-bonus-001"})
test("Bonus Alice +50 → 201", r, 201, {"new_balance": 620})

# 10. Transaction history
print("--- Transaction History ---")
r = requests.get(f"{BASE}/api/v1/wallets/{ALICE}/transactions", params={"page": 1, "per_page": 5})
test("Transaction history → 200", r, 200)

# 11. Missing idempotency key
print("--- Validation Errors ---")
r = requests.post(f"{BASE}/api/v1/wallets/{ALICE}/topup",
                   json={"amount": 100, "asset_type_id": GOLD})
test("Missing Idempotency-Key → 400", r, 400)

# 12. Invalid amount
r = requests.post(f"{BASE}/api/v1/wallets/{ALICE}/spend",
                   json={"amount": -5, "asset_type_id": GOLD},
                   headers={"Idempotency-Key": "smoke-negative-001"})
test("Negative amount → 400", r, 400)

# Final summary
print("=" * 60)
print(f"  RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)
