"""Test 05: Balance After Topup — verify Alice balance updated to 600 after topup"""
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
assert data["balance"] == 600
print("PASSED: Alice balance is 600 after topup of 100")
