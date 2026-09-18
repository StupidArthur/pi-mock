#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8080}"
PI="$BASE/piwebapi"
MOCK="$BASE/mock"

pass() { echo "[PASS] $1"; }
fail() { echo "[FAIL] $1"; exit 1; }

echo "== Mock PI Server smoke test =="
echo "BASE=$BASE"

curl -fsS "$BASE/health" | grep -q '"status":"ok"' && pass "health" || fail "health"

curl -fsS "$PI/dataservers" | grep -q 'SERVER_TEST_PI' && pass "dataserver" || fail "dataserver"

curl -fsS "$PI/points?path=%5C%5CTEST-PI%5Ctemperature" | grep -q '"Name":"temperature"' \
  && pass "point" || fail "point"

WEBID=$(curl -fsS "$PI/points?path=%5C%5CTEST-PI%5Ctemperature" | python -c "import sys,json;print(json.load(sys.stdin)['WebId'])")

curl -fsS "$PI/streams/$WEBID/value" | grep -q '"Value"' && pass "current value" || fail "current value"

curl -fsS "$MOCK/data/generate" -H 'Content-Type: application/json' \
  -d '{"tag":"temperature","start":"2026-01-01T00:00:00Z","count":60,"interval_ms":60000,"generator":"sin"}' \
  | grep -q '"Generated"' && pass "generate" || fail "generate"

curl -fsS "$PI/streams/$WEBID/recorded?maxCount=10" | grep -q '"Items"' \
  && pass "history" || fail "history"

curl -fsS -o /dev/null -w '%{http_code}' -X POST "$PI/streams/$WEBID/value" \
  -H 'Content-Type: application/json' -d '{"Timestamp":"2026-09-18T11:00:00Z","Value":66.6}' | grep -q '202' \
  && pass "write" || fail "write"

curl -fsS "$PI/streams/$WEBID/value" | grep -q '66.6' && pass "read-after-write" || fail "read-after-write"

curl -fsS -X POST "$MOCK/config" -H 'Content-Type: application/json' \
  -d '{"force_status":500}' >/dev/null
STATUS=$(curl -s -o /dev/null -w '%{http_code}' "$PI/dataservers")
MOCK_STATUS=$(curl -s -o /dev/null -w '%{http_code}' "$MOCK/config")
[ "$STATUS" = "500" ] && pass "fault force_status" || fail "fault force_status ($STATUS)"
[ "$MOCK_STATUS" = "200" ] && pass "mock isolation" || fail "mock isolation ($MOCK_STATUS)"

curl -fsS -X POST "$MOCK/reset" >/dev/null && pass "reset" || fail "reset"

STATUS=$(curl -s -o /dev/null -w '%{http_code}' "$PI/dataservers")
[ "$STATUS" = "200" ] && pass "post-reset" || fail "post-reset ($STATUS)"

echo "Mock PI Server smoke test PASSED"
