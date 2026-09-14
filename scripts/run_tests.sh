#!/usr/bin/env bash
# =============================================================================
# The Lenny Growth Assistant -- Consolidated Test Runner (Bash)
# Runs both Backend Pytest and Frontend Vitest suites with summary reporting.
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

echo "============================================================"
echo "  The Lenny Growth Assistant -- Consolidated Test Runner"
echo "============================================================"
echo ""

START_TIME=$(date +%s)
BACKEND_STATUS=0
FRONTEND_STATUS=0

# ---------------------------------------------------------------------------
# 1. Backend Pytest Suite
# ---------------------------------------------------------------------------
echo "[1/2] Running Backend Pytest Suite..."
if [ -f "$REPO_ROOT/.venv/bin/pytest" ]; then
    PYTEST_CMD="$REPO_ROOT/.venv/bin/pytest"
elif [ -f "$REPO_ROOT/.venv/Scripts/pytest.exe" ]; then
    PYTEST_CMD="$REPO_ROOT/.venv/Scripts/pytest.exe"
else
    PYTEST_CMD="pytest"
fi

if $PYTEST_CMD -v; then
    echo "  --> Backend tests PASSED."
else
    echo "  --> Backend tests FAILED."
    BACKEND_STATUS=1
fi

echo ""

# ---------------------------------------------------------------------------
# 2. Frontend Vitest / RTL Suite
# ---------------------------------------------------------------------------
echo "[2/2] Running Frontend Vitest / RTL Suite..."
cd "$REPO_ROOT/frontend"

if npm test -- --run; then
    echo "  --> Frontend tests PASSED."
else
    echo "  --> Frontend tests FAILED."
    FRONTEND_STATUS=1
fi

cd "$REPO_ROOT"
echo ""

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# ---------------------------------------------------------------------------
# Summary Report
# ---------------------------------------------------------------------------
echo "============================================================"
echo "                    TEST EXECUTION SUMMARY"
echo "============================================================"
if [ $BACKEND_STATUS -eq 0 ]; then
    echo "  Backend Suite (Pytest)     : PASSED"
else
    echo "  Backend Suite (Pytest)     : FAILED"
fi

if [ $FRONTEND_STATUS -eq 0 ]; then
    echo "  Frontend Suite (Vitest/RTL): PASSED"
else
    echo "  Frontend Suite (Vitest/RTL): FAILED"
fi
echo "  Total Duration             : ${DURATION}s"
echo "============================================================"

if [ $BACKEND_STATUS -eq 0 ] && [ $FRONTEND_STATUS -eq 0 ]; then
    echo "SUCCESS: All test suites passed cleanly with 0 errors."
    exit 0
else
    echo "FAILURE: One or more test suites failed."
    exit 1
fi
