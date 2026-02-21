"""Test 11: Bonus — POST /bonus should credit 50 GLD from bonus pool to Alice"""
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import BASE_URL, ALICE_WALLET_ID, GOLD_ASSET_TYPE_ID

url = f"{BASE_URL}/api/v1/wallets/{ALICE_WALLET_ID}/bonus"

headers = {
    "Idempotency-Key": "test-suite-bonus-001",
}

json = {
    "amount": 50,
    "asset_type_id": GOLD_ASSET_TYPE_ID,
}

r = requests.post(
    url=url,
    headers=headers,
    json=json,
)

print(r.text)
print(f"Status Code: {r.status_code}")

assert r.status_code == 201
data = r.json()
assert data["amount"] == 50
assert data["direction"] == "CREDIT"
assert data["new_balance"] == 620
print("PASSED: Bonus 50 GLD credited to Alice from bonus pool, new balance = 620")
