"""
Run All Test Suite Files (in order)
====================================
Usage:
    python "Test Suite/run_all.py"

Set WALLET_SERVICE_URL env var to test against a different host:
    set WALLET_SERVICE_URL=https://your-app.onrender.com
    python "Test Suite/run_all.py"
"""
import subprocess
import sys
import os
import glob

suite_dir = os.path.dirname(os.path.abspath(__file__))
test_files = sorted(glob.glob(os.path.join(suite_dir, "[0-9]*.py")))

passed = 0
failed = 0

print("=" * 60)
print("  WALLET SERVICE TEST SUITE")
print(f"  Target: {os.environ.get('WALLET_SERVICE_URL', 'http://localhost:8080')}")
print("=" * 60)
print()

for test_file in test_files:
    name = os.path.basename(test_file)
    result = subprocess.run(
        [sys.executable, test_file],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        passed += 1
        last_line = result.stdout.strip().split("\n")[-1]
        print(f"  [+] {name}: {last_line}")
    else:
        failed += 1
        error = result.stderr.strip().split("\n")[-1] if result.stderr else result.stdout.strip().split("\n")[-1]
        print(f"  [X] {name}: FAILED")
        print(f"      {error}")
    print()

print("=" * 60)
print(f"  RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)

sys.exit(1 if failed > 0 else 0)
