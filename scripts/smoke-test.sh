#!/bin/bash
set -e
echo "=== Bryton AI CV App - Smoke Test ==="

BASE_URL="${1:-http://localhost:80}"

echo "1. Testing liveness..."
curl -sf "$BASE_URL/health" | jq -e '.status == "ok"'
echo "   PASS: Liveness OK"

echo "2. Testing readiness..."
curl -sf "$BASE_URL/health/ready" | jq -e '.status == "ready"'
echo "   PASS: Readiness OK"

echo "3. Testing SFIA levels..."
COUNT=$(curl -sf "$BASE_URL/api/reference/sfia-levels" | jq length)
[ "$COUNT" -eq 7 ] || (echo "FAIL: Expected 7 SFIA levels, got $COUNT" && exit 1)
echo "   PASS: 7 SFIA levels returned"

echo "4. Testing frontend..."
curl -sf "$BASE_URL/" | grep -q "Bryton" || (echo "FAIL: Frontend not serving" && exit 1)
echo "   PASS: Frontend serving"

echo "5. Testing SPA fallback..."
curl -sf "$BASE_URL/dashboard" | grep -q "Bryton" || (echo "FAIL: SPA fallback broken" && exit 1)
echo "   PASS: SPA fallback working"

echo ""
echo "=== All smoke tests passed ==="
