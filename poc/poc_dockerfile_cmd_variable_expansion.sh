#!/bin/bash
#
# PoC: Docker CMD exec-form does not expand shell variables
#
# BUG (before fix):
#   CMD ["gunicorn", ..., "--workers", "${GUNICORN_WORKERS:-4}", ...]
#
#   Docker's exec form (JSON array) does NOT invoke a shell, so environment
#   variable references like ${GUNICORN_WORKERS:-4} are passed as literal
#   strings to the entrypoint. Gunicorn receives the literal string
#   "${GUNICORN_WORKERS:-4}" instead of the number "4", causing a startup
#   failure or unexpected behavior.
#
# FIX:
#   CMD ["sh", "-c", "exec gunicorn ... --workers ${GUNICORN_WORKERS:-4} ..."]
#
#   Using shell form via "sh -c" ensures the shell expands the variable.
#   The `exec` replaces the shell process so gunicorn receives signals directly.
#
# This script demonstrates the bug by comparing exec-form vs shell-form
# variable expansion behavior.

set -e

echo "=== PoC: Docker CMD exec-form shell variable expansion bug ==="
echo ""

# Simulate the BUGGY exec-form behavior
# In Docker exec-form, arguments are NOT processed by a shell
echo "--- BUGGY (exec-form): No shell expansion ---"
# This simulates what Docker does with exec form - passes literal strings
BUGGY_ARG='${GUNICORN_WORKERS:-4}'
echo "  Argument passed to gunicorn --workers: $BUGGY_ARG"
echo "  (literal string, NOT expanded)"
echo ""

# Verify it's literally the unexpanded variable reference
if [ "$BUGGY_ARG" = '${GUNICORN_WORKERS:-4}' ]; then
    echo "  ✗ BUG CONFIRMED: Variable was NOT expanded (literal string passed)"
else
    echo "  ✓ Variable was expanded (this shouldn't happen in exec form)"
fi
echo ""

# Simulate the FIXED shell-form behavior
echo "--- FIXED (shell form via sh -c): Shell expansion works ---"

# Test 1: Without GUNICORN_WORKERS set (should use default 4)
unset GUNICORN_WORKERS
FIXED_ARG=$(sh -c 'echo ${GUNICORN_WORKERS:-4}')
echo "  Without GUNICORN_WORKERS env var:"
echo "  Argument passed to gunicorn --workers: $FIXED_ARG"
if [ "$FIXED_ARG" = "4" ]; then
    echo "  ✓ FIX VERIFIED: Default value 4 correctly applied"
else
    echo "  ✗ FAILED: Expected 4, got $FIXED_ARG"
fi
echo ""

# Test 2: With GUNICORN_WORKERS set to a custom value
export GUNICORN_WORKERS=8
FIXED_ARG=$(sh -c 'echo ${GUNICORN_WORKERS:-4}')
echo "  With GUNICORN_WORKERS=8:"
echo "  Argument passed to gunicorn --workers: $FIXED_ARG"
if [ "$FIXED_ARG" = "8" ]; then
    echo "  ✓ FIX VERIFIED: Custom value 8 correctly applied"
else
    echo "  ✗ FAILED: Expected 8, got $FIXED_ARG"
fi
echo ""

# Verify the Dockerfile-mozcloud has the fix
echo "--- Verifying Dockerfile-mozcloud ---"
DOCKERFILE="docker/Dockerfile-mozcloud"
if [ -f "$DOCKERFILE" ]; then
    if grep -q 'CMD \["sh", "-c"' "$DOCKERFILE"; then
        echo "  ✓ Dockerfile-mozcloud uses shell-form CMD (fix is in place)"
    elif grep -q 'CMD \["gunicorn"' "$DOCKERFILE"; then
        echo "  ✗ BUG: Dockerfile-mozcloud still uses exec-form CMD"
        echo "    Shell variables like \${GUNICORN_WORKERS:-4} will NOT be expanded"
    else
        echo "  ? Could not determine CMD form"
    fi

    # Check that exec is used for signal forwarding
    if grep -q 'exec gunicorn' "$DOCKERFILE"; then
        echo "  ✓ Uses 'exec' for proper signal forwarding"
    else
        echo "  ⚠ Missing 'exec' — gunicorn won't receive SIGTERM directly"
    fi
fi

echo ""
echo "=== PoC Complete ==="
