"""
Test Suite Configuration
========================
All test files in this suite hit a live wallet service instance.

Default base URL: http://localhost:8080
Override with environment variable: WALLET_SERVICE_URL

Usage:
    python -m pytest "Test Suite" -v
    # or run individual files:
    python "Test Suite/01_health_check.py"
"""

import os

BASE_URL = os.environ.get("WALLET_SERVICE_URL", "http://localhost:8080")
ALICE_WALLET_ID = "44444444-4444-4444-4444-444444444444"
BOB_WALLET_ID = "55555555-5555-5555-5555-555555555555"
GOLD_ASSET_TYPE_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
