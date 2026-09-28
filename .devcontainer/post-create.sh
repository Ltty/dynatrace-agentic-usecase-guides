#!/usr/bin/env bash
# post-create.sh
# Runs once when the Codespace/dev container provisions.
# Installs the Claude Code CLI, dtctl, creates the playground context, and installs
# Python deps. The user still needs two interactive steps afterward:
#   1. `claude login` (or open the Claude Code panel and sign in) — browser auth
#   2. `dtctl auth login --context playground` — browser OAuth; port 3232 is public so the
#      callback works in both VS Code desktop and browser-based Codespaces

set -uo pipefail  # deliberately not -e: one failed component shouldn't abort the rest;
                  # each step reports its own status and the summary at the end shows what's missing

echo ""
echo "=== Dynatrace Agentic Guides — dev container setup ==="
echo ""

STATUS_CLAUDE="not installed"
STATUS_DTCTL="not installed"
STATUS_PY="not installed"

# 1. Install the Claude Code CLI.
# The VS Code extension (declared in devcontainer.json) installs itself when VS Code
# attaches to this container — that part is standard Dev Containers behavior and doesn't
# need anything here. This step is belt-and-suspenders: it makes `claude` runnable directly
# from any terminal in the container (useful for testing, and in case the extension expects
# a CLI already on PATH rather than being fully self-contained).
echo "[1/4] Installing Claude Code CLI..."
if command -v npm &>/dev/null; then
  if npm install -g @anthropic-ai/claude-code 2>/tmp/claude-install.log; then
    if command -v claude &>/dev/null; then
      STATUS_CLAUDE="OK ($(claude --version 2>/dev/null | head -1))"
    else
      STATUS_CLAUDE="installed but not on PATH — check npm's global bin dir"
    fi
  else
    STATUS_CLAUDE="FAILED — see /tmp/claude-install.log. Package name may have changed; check https://docs.claude.com/en/docs/claude-code for the current install command."
  fi
else
  STATUS_CLAUDE="SKIPPED — npm not found (check the node feature in devcontainer.json)"
fi
echo "      $STATUS_CLAUDE"

# 2. Install dtctl (downloads binary from GitHub releases, no curl | bash)
echo ""
echo "[2/4] Installing dtctl..."
DTCTL_INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$DTCTL_INSTALL_DIR"

if DTCTL_VERSION=$(curl -fsSL https://api.github.com/repos/dynatrace-oss/dtctl/releases/latest \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['tag_name'].lstrip('v'))" 2>/tmp/dtctl-install.log); then
  DTCTL_URL="https://github.com/dynatrace-oss/dtctl/releases/download/v${DTCTL_VERSION}/dtctl_${DTCTL_VERSION}_linux_amd64.tar.gz"
  if curl -fsSL "${DTCTL_URL}" -o /tmp/dtctl.tar.gz 2>>/tmp/dtctl-install.log \
      && tar -xzf /tmp/dtctl.tar.gz -C /tmp \
      && mv /tmp/dtctl "${DTCTL_INSTALL_DIR}/dtctl" \
      && chmod +x "${DTCTL_INSTALL_DIR}/dtctl"; then
    rm -f /tmp/dtctl.tar.gz
    export PATH="$DTCTL_INSTALL_DIR:$PATH"
    STATUS_DTCTL="OK ($("${DTCTL_INSTALL_DIR}/dtctl" version 2>/dev/null | head -1))"

    echo ""
    echo "      Configuring playground context..."
    "${DTCTL_INSTALL_DIR}/dtctl" config set-context playground \
      --environment https://playground.apps.dynatrace.com \
      --safety-level readonly 2>/dev/null || true
    "${DTCTL_INSTALL_DIR}/dtctl" config use-context playground 2>/dev/null || true
  else
    STATUS_DTCTL="FAILED — download/extract failed, see /tmp/dtctl-install.log"
  fi
else
  STATUS_DTCTL="FAILED — could not resolve latest release, see /tmp/dtctl-install.log"
fi
echo "      $STATUS_DTCTL"

# 3. Python dependencies (validator, preflight, fixture capture)
echo ""
echo "[3/4] Installing Python dependencies..."
if pip3 install --quiet pyyaml jsonschema 2>/tmp/pip-install.log; then
  STATUS_PY="OK"
else
  STATUS_PY="FAILED — see /tmp/pip-install.log"
fi
echo "      $STATUS_PY"

# 4. Nothing to install for the plugin itself.
# .claude/commands/*.md, skills/*/SKILL.md and .claude/settings.json are picked up by
# Claude Code just by being present in the project directory — no `claude plugin install`
# step needed. Verified empirically: /demo and /demo-doctor work the moment Claude Code
# opens this folder, before any plugin-install command has ever been run.
echo ""
echo "[4/4] Plugin files (.claude/commands, skills/) — no install step needed, auto-discovered."

echo ""
echo "================================================================"
echo "  Setup summary:"
echo "    Claude Code CLI : $STATUS_CLAUDE"
echo "    dtctl           : $STATUS_DTCTL"
echo "    Python deps     : $STATUS_PY"
echo "================================================================"
echo ""
echo "  Two manual steps remain:"
echo ""
echo "  1. Sign in to Claude — click 'Sign in' in the Claude Code extension panel (sidebar)."
echo "     Do NOT run 'claude login' from the terminal — that OAuth callback can't reach"
echo "     the container. Use the extension's built-in sign-in instead."
echo ""
echo "  2. Authenticate against the Dynatrace Playground (two steps — dtctl's OAuth"
echo "     callback goes to 127.0.0.1:3232 on your LOCAL machine, so tunnel it first):"
echo ""
echo "     Step A: in a LOCAL terminal (not this one):"
echo "       gh codespace ssh -- -NL 3232:localhost:3232"
echo "     Leave that running."
echo ""
echo "     Step B: back here:"
echo "       dtctl auth login --context playground \\"
echo "         --environment https://playground.apps.dynatrace.com"
echo "     Log in, callback completes, then close the tunnel terminal."
echo "     No account yet? Free signup: https://www.dynatrace.com/signup/playground/"
echo ""
echo "  Then, in Claude Code:"
echo "    /demo-doctor   (verify everything is wired)"
echo "    /demo          (start an incident investigation)"
echo ""
echo "================================================================"
echo ""
