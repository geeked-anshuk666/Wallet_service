"""Test 13: Missing Idempotency-Key — POST without header should return 400"""
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import BASE_URL, ALICE_WALLET_ID, GOLD_ASSET_TYPE_ID

url = f"{BASE_URL}/api/v1/wallets/{ALICE_WALLET_ID}/topup"

json = {
    "amount": 100,
    "asset_type_id": GOLD_ASSET_TYPE_ID,
}

# Intentionally NO Idempotency-Key header
r = requests.post(
    url=url,
    json=json,
)

print(r.text)
print(f"Status Code: {r.status_code}")

assert r.status_code == 400
data = r.json()
assert "Idempotency-Key" in data["error"]
print("PASSED: Missing Idempotency-Key correctly rejected with 400")
