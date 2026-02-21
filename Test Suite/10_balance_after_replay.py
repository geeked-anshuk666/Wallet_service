"""Test 10: Balance After Replay — verify balance NOT double-credited after replay"""
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
assert data["balance"] == 570
print("PASSED: Balance still 570 — replay did NOT double-credit")
