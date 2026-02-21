"""Test 04: Topup — POST /topup should credit 100 GLD to Alice"""
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import BASE_URL, ALICE_WALLET_ID, GOLD_ASSET_TYPE_ID

url = f"{BASE_URL}/api/v1/wallets/{ALICE_WALLET_ID}/topup"

headers = {
    "Idempotency-Key": "test-suite-topup-001",
}

json = {
    "amount": 100,
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
assert data["amount"] == 100
assert data["direction"] == "CREDIT"
assert data["new_balance"] == 600
print("PASSED: Topup 100 GLD credited to Alice, new balance = 600")
