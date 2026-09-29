#!/usr/bin/env bash
# login-in-container.sh
#
# Run this from a terminal inside the noVNC desktop (port 6080), NOT from
# VS Code's integrated terminal. VS Code overrides BROWSER in its own terminal
# sessions to forward browser opens to your local machine; this script bypasses
# that by explicitly setting BROWSER to the in-container Chromium before
# invoking the login wizards.
#
# Usage (from the noVNC desktop terminal):
#   bash tools/login-in-container.sh

set -euo pipefail

# Find the in-container Chromium
CHROMIUM=$(command -v chromium-browser 2>/dev/null \
  || command -v chromium 2>/dev/null \
  || command -v google-chrome 2>/dev/null \
  || true)

if [ -z "$CHROMIUM" ]; then
  echo "ERROR: No Chromium/Chrome found in PATH."
  echo "The devcontainer should have installed it. Check /tmp/chromium-install.log"
  exit 1
fi

export BROWSER="$CHROMIUM"
echo "Using browser: $BROWSER"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Step 1: dtctl / Dynatrace Playground
echo "=== Step 1: Dynatrace Playground ==="
echo ""
cd "$REPO_ROOT"
python tools/preflight.py login
echo ""

# Step 2: Claude Code
echo "=== Step 2: Claude Code ==="
echo ""
if command -v claude &>/dev/null; then
  claude login
else
  echo "claude CLI not found. Sign in via the Claude Code extension panel in VS Code instead."
fi
