#!/bin/bash
# ==============================================================================
# Phase 1 Unified Test Harness & Evaluation Runner
# Executes all primary Phase 1 verification suites sequentially
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================================================"
echo "    COMPUTER NETWORKS CAPSTONE: PHASE 1 COMPREHENSIVE VERIFICATION"
echo "========================================================================"
echo

PASSED=0
TOTAL=4

echo "------------------------------------------------------------------------"
echo "TEST 1: Domain Name Resolution (DNS Task B)"
echo "------------------------------------------------------------------------"
if bash "$DIR/dns-test.sh"; then
    echo ">> TEST 1 PASSED"
    PASSED=$((PASSED + 1))
else
    echo ">> TEST 1 FAILED"
fi
echo

echo "------------------------------------------------------------------------"
echo "TEST 2: HTTPS / TLS Certificate Validation (Task E)"
echo "------------------------------------------------------------------------"
if bash "$DIR/https-test.sh"; then
    echo ">> TEST 2 PASSED"
    PASSED=$((PASSED + 1))
else
    echo ">> TEST 2 FAILED"
fi
echo

echo "------------------------------------------------------------------------"
echo "TEST 3: Round-Robin Load Balancing Distribution (Task D)"
echo "------------------------------------------------------------------------"
if bash "$DIR/load-balancing-test.sh"; then
    echo ">> TEST 3 PASSED"
    PASSED=$((PASSED + 1))
else
    echo ">> TEST 3 FAILED"
fi
echo

echo "------------------------------------------------------------------------"
echo "TEST 4: HTTP Caching & 304 Revalidation (Task F)"
echo "------------------------------------------------------------------------"
if bash "$DIR/caching-test.sh"; then
    echo ">> TEST 4 PASSED"
    PASSED=$((PASSED + 1))
else
    echo ">> TEST 4 FAILED"
fi
echo

echo "========================================================================"
echo "SUMMARY: $PASSED / $TOTAL Tests Passed"
echo "========================================================================"
if [ "$PASSED" -eq "$TOTAL" ]; then
    echo "STATUS: ALL PHASE 1 SYSTEM TESTS PASSED SUCCESSFULLY!"
    exit 0
else
    echo "STATUS: SOME TESTS FAILED. PLEASE REVIEW INDIVIDUAL TEST OUTPUTS."
    exit 1
fi
