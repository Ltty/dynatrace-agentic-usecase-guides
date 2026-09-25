#!/usr/bin/env bash
# post-create.sh
# Runs once when the Codespace provisions.
# Installs dtctl, creates the playground context, installs Python deps,
# and installs the Claude Code plugin.
# The user still needs to run `dtctl auth login` (one browser round-trip).

set -euo pipefail

echo ""
echo "=== Dynatrace Agentic Guides setup ==="
echo ""

# 1. Install dtctl (downloads binary from GitHub releases, no curl | bash)
DTCTL_INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$DTCTL_INSTALL_DIR"

DTCTL_VERSION=$(curl -fsSL https://api.github.com/repos/dynatrace-oss/dtctl/releases/latest \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['tag_name'].lstrip('v'))")
DTCTL_URL="https://github.com/dynatrace-oss/dtctl/releases/download/v${DTCTL_VERSION}/dtctl_${DTCTL_VERSION}_linux_amd64.tar.gz"

echo "Downloading dtctl ${DTCTL_VERSION}..."
curl -fsSL "${DTCTL_URL}" -o /tmp/dtctl.tar.gz
tar -xzf /tmp/dtctl.tar.gz -C /tmp
mv /tmp/dtctl "${DTCTL_INSTALL_DIR}/dtctl"
chmod +x "${DTCTL_INSTALL_DIR}/dtctl"
rm /tmp/dtctl.tar.gz
export PATH="$DTCTL_INSTALL_DIR:$PATH"
echo "dtctl $(dtctl version | head -1) installed"

# 2. Configure playground context (no auth yet)
echo ""
echo "Configuring dtctl playground context..."
dtctl config set-context playground \
  --environment https://playground.apps.dynatrace.com \
  --safety-level readonly 2>/dev/null || true
dtctl config use-context playground
echo "Context: playground | safety-level: readonly"

# 3. Python dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install --quiet pyyaml jsonschema

# 4. Install Claude Code plugin
if command -v claude &>/dev/null; then
  echo ""
  echo "Installing Claude Code plugin..."
  claude plugin install . --local 2>/dev/null \
    || echo "  (Plugin install skipped — run manually: claude plugin install . --local)"
fi

echo ""
echo "================================================================"
echo ""
echo "  Setup complete. One step remaining:"
echo ""
echo "  dtctl auth login --context playground \\"
echo "    --environment https://playground.apps.dynatrace.com"
echo ""
echo "  A browser tab will open for Dynatrace SSO."
echo "  No account yet? Sign up free: https://www.dynatrace.com/signup/playground/"
echo ""
echo "  Then run in Claude Code:"
echo "    /demo-doctor   (verify everything is wired)"
echo "    /demo          (start an incident investigation)"
echo ""
echo "================================================================"
echo ""
