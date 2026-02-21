"""Test 03: Bob Balance (seeded) — GET /balance should return 200 GLD"""
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import BASE_URL, BOB_WALLET_ID

url = f"{BASE_URL}/api/v1/wallets/{BOB_WALLET_ID}/balance"

r = requests.get(url=url)

print(r.text)
print(f"Status Code: {r.status_code}")

assert r.status_code == 200
data = r.json()
assert data["wallet_id"] == BOB_WALLET_ID
assert data["user"] == "bob"
assert data["balance"] == 200
print("PASSED: Bob balance is 200 GLD as seeded")
