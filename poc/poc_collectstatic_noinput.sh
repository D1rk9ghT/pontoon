#!/bin/bash
#
# PoC: Missing --noinput flag on Django collectstatic
#
# BUG (before fix):
#   RUN python manage.py collectstatic          # in docker/Dockerfile
#   - run: python manage.py collectstatic       # in .github/workflows/backend.yml
#
#   Without --noinput, Django's collectstatic command prompts the user for
#   confirmation when files would be overwritten. In non-interactive contexts
#   (Docker builds, CI pipelines), stdin is not a TTY, which can cause:
#   - The command to hang indefinitely waiting for input
#   - The command to fail with an error about missing TTY
#   - Unpredictable behavior depending on the Django version and stdin state
#
# FIX:
#   RUN python manage.py collectstatic --noinput
#   - run: python manage.py collectstatic --noinput
#
#   The --noinput flag tells Django to skip all confirmation prompts and
#   proceed with overwriting files automatically.
#
# This script demonstrates and validates the fix.

set -e

echo "=== PoC: Missing --noinput flag on collectstatic ==="
echo ""

# Check docker/Dockerfile
echo "--- Checking docker/Dockerfile ---"
DOCKERFILE="docker/Dockerfile"
if [ -f "$DOCKERFILE" ]; then
    COLLECTSTATIC_LINE=$(grep 'collectstatic' "$DOCKERFILE" || true)
    if [ -n "$COLLECTSTATIC_LINE" ]; then
        echo "  Found: $COLLECTSTATIC_LINE"
        if echo "$COLLECTSTATIC_LINE" | grep -q '\-\-noinput'; then
            echo "  ✓ FIX VERIFIED: --noinput flag is present"
        else
            echo "  ✗ BUG: --noinput flag is MISSING"
            echo "    Docker build may hang waiting for user input"
        fi
    else
        echo "  No collectstatic command found"
    fi
fi
echo ""

# Check .github/workflows/backend.yml
echo "--- Checking .github/workflows/backend.yml ---"
WORKFLOW="/.github/workflows/backend.yml"
# Use full path since we're in the repo root
WORKFLOW=".github/workflows/backend.yml"
if [ -f "$WORKFLOW" ]; then
    COLLECTSTATIC_LINE=$(grep 'collectstatic' "$WORKFLOW" || true)
    if [ -n "$COLLECTSTATIC_LINE" ]; then
        echo "  Found:$COLLECTSTATIC_LINE"
        if echo "$COLLECTSTATIC_LINE" | grep -q '\-\-noinput'; then
            echo "  ✓ FIX VERIFIED: --noinput flag is present"
        else
            echo "  ✗ BUG: --noinput flag is MISSING"
            echo "    CI workflow may hang waiting for user input"
        fi
    else
        echo "  No collectstatic command found"
    fi
fi
echo ""

# Check docker/Dockerfile-mozcloud (was already correct)
echo "--- Checking docker/Dockerfile-mozcloud ---"
DOCKERFILE_MC="docker/Dockerfile-mozcloud"
if [ -f "$DOCKERFILE_MC" ]; then
    COLLECTSTATIC_LINE=$(grep 'collectstatic' "$DOCKERFILE_MC" || true)
    if [ -n "$COLLECTSTATIC_LINE" ]; then
        echo "  Found: $COLLECTSTATIC_LINE"
        if echo "$COLLECTSTATIC_LINE" | grep -q '\-\-noinput'; then
            echo "  ✓ --noinput flag is present (was already correct)"
        else
            echo "  ✗ BUG: --noinput flag is MISSING"
        fi
    else
        echo "  No collectstatic command found"
    fi
fi
echo ""

# Demonstrate why this matters
echo "--- Why --noinput is critical in non-interactive contexts ---"
echo ""
echo "  Django collectstatic behavior WITHOUT --noinput:"
echo "    - Checks if static files already exist in the destination"
echo "    - If yes, prompts: 'You have requested to collect static files at the'"
echo "      'destination location ... This will overwrite existing files!'"
echo "      'Are you sure you want to do this? Type \"yes\" to continue:'"
echo "    - In Docker/CI with no TTY: hangs or errors"
echo ""
echo "  Django collectstatic behavior WITH --noinput:"
echo "    - Skips all confirmation prompts"
echo "    - Automatically overwrites existing files"
echo "    - Safe for automated/non-interactive environments"
echo ""

echo "=== PoC Complete ==="
