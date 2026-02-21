#!/bin/bash
BASE_URL="http://localhost:8080"
ALICE="44444444-4444-4444-4444-444444444444"
GOLD="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

echo "=== 1. TOPUP ==="
curl -s -w "\nHTTP %{http_code}\n" -X POST "$BASE_URL/api/v1/wallets/$ALICE/topup" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: smoke-topup-001" \
  -d "{\"amount\": 100, \"asset_type_id\": \"$GOLD\"}"

echo ""
echo "=== 2. BALANCE (after topup) ==="
curl -s -w "\nHTTP %{http_code}\n" "$BASE_URL/api/v1/wallets/$ALICE/balance"

echo ""
echo "=== 3. SPEND ==="
curl -s -w "\nHTTP %{http_code}\n" -X POST "$BASE_URL/api/v1/wallets/$ALICE/spend" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: smoke-spend-001" \
  -d "{\"amount\": 30, \"asset_type_id\": \"$GOLD\"}"

echo ""
echo "=== 4. OVERSPEND (should 422) ==="
curl -s -w "\nHTTP %{http_code}\n" -X POST "$BASE_URL/api/v1/wallets/$ALICE/spend" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: smoke-overspend-001" \
  -d "{\"amount\": 999999, \"asset_type_id\": \"$GOLD\"}"

echo ""
echo "=== 5. IDEMPOTENCY REPLAY (same topup key, should 200) ==="
curl -s -w "\nHTTP %{http_code}\n" -X POST "$BASE_URL/api/v1/wallets/$ALICE/topup" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: smoke-topup-001" \
  -d "{\"amount\": 100, \"asset_type_id\": \"$GOLD\"}"

echo ""
echo "=== 6. BONUS ==="
curl -s -w "\nHTTP %{http_code}\n" -X POST "$BASE_URL/api/v1/wallets/$ALICE/bonus" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: smoke-bonus-001" \
  -d "{\"amount\": 50, \"asset_type_id\": \"$GOLD\"}"

echo ""
echo "=== 7. TRANSACTION HISTORY ==="
curl -s -w "\nHTTP %{http_code}\n" "$BASE_URL/api/v1/wallets/$ALICE/transactions?page=1&per_page=5"

echo ""
echo "=== 8. FINAL BALANCE ==="
curl -s -w "\nHTTP %{http_code}\n" "$BASE_URL/api/v1/wallets/$ALICE/balance"
