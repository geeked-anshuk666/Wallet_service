"""Test 07: Overspend — POST /spend with amount > balance should return 422"""
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import BASE_URL, ALICE_WALLET_ID, GOLD_ASSET_TYPE_ID

url = f"{BASE_URL}/api/v1/wallets/{ALICE_WALLET_ID}/spend"

headers = {
    "Idempotency-Key": "test-suite-overspend-001",
}

json = {
    "amount": 999999,
    "asset_type_id": GOLD_ASSET_TYPE_ID,
}

r = requests.post(
    url=url,
    headers=headers,
    json=json,
)

print(r.text)
print(f"Status Code: {r.status_code}")

assert r.status_code == 422
data = r.json()
assert data["error"] == "INSUFFICIENT_BALANCE"
print("PASSED: Overspend correctly rejected with 422 INSUFFICIENT_BALANCE")
