"""Test 06: Spend — POST /spend should debit 30 GLD from Alice"""
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import BASE_URL, ALICE_WALLET_ID, GOLD_ASSET_TYPE_ID

url = f"{BASE_URL}/api/v1/wallets/{ALICE_WALLET_ID}/spend"

headers = {
    "Idempotency-Key": "test-suite-spend-001",
}

json = {
    "amount": 30,
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
assert data["amount"] == 30
assert data["direction"] == "DEBIT"
assert data["new_balance"] == 570
print("PASSED: Spend 30 GLD debited from Alice, new balance = 570")
