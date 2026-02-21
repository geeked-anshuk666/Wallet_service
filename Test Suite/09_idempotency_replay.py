"""Test 09: Idempotency Replay — same Idempotency-Key should return 200 with replayed: true"""
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import BASE_URL, ALICE_WALLET_ID, GOLD_ASSET_TYPE_ID

url = f"{BASE_URL}/api/v1/wallets/{ALICE_WALLET_ID}/topup"

headers = {
    "Idempotency-Key": "test-suite-topup-001",  # same key as test 04
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

assert r.status_code == 200
data = r.json()
assert data["replayed"] is True
print("PASSED: Duplicate Idempotency-Key returns 200 with replayed: true")
