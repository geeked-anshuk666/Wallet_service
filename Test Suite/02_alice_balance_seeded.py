"""Test 02: Alice Balance (seeded) — GET /balance should return 500 GLD"""
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import BASE_URL, ALICE_WALLET_ID

url = f"{BASE_URL}/api/v1/wallets/{ALICE_WALLET_ID}/balance"

r = requests.get(url=url)

print(r.text)
print(f"Status Code: {r.status_code}")

assert r.status_code == 200
data = r.json()
assert data["wallet_id"] == ALICE_WALLET_ID
assert data["user"] == "alice"
assert data["asset_type"] == "Gold Coins"
assert data["symbol"] == "GLD"
assert data["balance"] == 500
print("PASSED: Alice balance is 500 GLD as seeded")
