"""Test 12: Transaction History — GET /transactions should return paginated entries"""
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import BASE_URL, ALICE_WALLET_ID

url = f"{BASE_URL}/api/v1/wallets/{ALICE_WALLET_ID}/transactions"

params = {
    "page": 1,
    "per_page": 5,
}

r = requests.get(
    url=url,
    params=params,
)

print(r.text)
print(f"Status Code: {r.status_code}")

assert r.status_code == 200
data = r.json()
assert data["wallet_id"] == ALICE_WALLET_ID
assert "transactions" in data
assert "page" in data
assert "total_pages" in data
assert "total_count" in data
assert len(data["transactions"]) > 0
print(f"PASSED: Transaction history returned {len(data['transactions'])} entries on page {data['page']}/{data['total_pages']}")
