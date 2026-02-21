"""Test 01: Health Check — GET /health should return 200 with status: healthy"""
import requests
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from config import BASE_URL

url = f"{BASE_URL}/health"

r = requests.get(url=url)

print(r.text)
print(f"Status Code: {r.status_code}")

assert r.status_code == 200
assert r.json()["status"] == "healthy"
print("PASSED: Health check returned 200 with status: healthy")
