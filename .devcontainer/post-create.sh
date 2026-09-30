#!/usr/bin/env bash
# post-create.sh
# Runs once when the Codespace/dev container provisions.
# Installs the Claude Code CLI, dtctl, and Python deps.

set -uo pipefail  # deliberately not -e: one failed component shouldn't abort the rest;
                  # each step reports its own status and the summary at the end shows what's missing

echo ""
echo "=== Dynatrace Agentic Guides — dev container setup ==="
echo ""

STATUS_CLAUDE="not installed"
STATUS_OPENCODE="not installed"
STATUS_DTCTL="not installed"
STATUS_PY="not installed"

# 1. Install the Claude Code CLI.
# The VS Code extension (declared in devcontainer.json) installs itself when VS Code
# attaches to this container — that part is standard Dev Containers behavior and doesn't
# need anything here. This step makes `claude` runnable directly from any terminal.
echo "[1/5] Installing Claude Code CLI..."
if command -v npm &>/dev/null; then
  if npm install -g @anthropic-ai/claude-code 2>/tmp/claude-install.log; then
    if command -v claude &>/dev/null; then
      STATUS_CLAUDE="OK ($(claude --version 2>/dev/null | head -1))"
    else
      STATUS_CLAUDE="installed but not on PATH — check npm's global bin dir"
    fi
  else
    STATUS_CLAUDE="FAILED — see /tmp/claude-install.log. Check https://docs.claude.com/en/docs/claude-code for the current install command."
  fi
else
  STATUS_CLAUDE="SKIPPED — npm not found (check the node feature in devcontainer.json)"
fi
echo "      $STATUS_CLAUDE"

# 2. Install OpenCode (free-tier alternative harness) and configure global model
echo ""
echo "[2/5] Installing OpenCode..."
if command -v npm &>/dev/null; then
  if npm install -g opencode-ai 2>/tmp/opencode-install.log; then
    if command -v opencode &>/dev/null; then
      STATUS_OPENCODE="OK ($(opencode --version 2>/dev/null | head -1))"
      # Write global config with the free bundled model.
      # Project-level opencode.json handles instructions and permissions;
      # the model must live in the global config at ~/.config/opencode/opencode.json.
      mkdir -p "$HOME/.config/opencode"
      cat > "$HOME/.config/opencode/opencode.json" <<'EOCONFIG'
{
  "$schema": "https://opencode.ai/config.json",
  "model": "opencode/nemotron-3-ultra-free"
}
EOCONFIG
    else
      STATUS_OPENCODE="installed but not on PATH — check npm's global bin dir"
    fi
  else
    STATUS_OPENCODE="FAILED — see /tmp/opencode-install.log"
  fi
else
  STATUS_OPENCODE="SKIPPED — npm not found"
fi
echo "      $STATUS_OPENCODE"

# 4. Install dtctl (downloads binary from GitHub releases, no curl | bash)
echo ""
echo "[3/5] Installing dtctl..."
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
    # Persist to profile so Claude Code's Bash tool picks it up in new sessions.
    # Guard against duplicates on repeated rebuilds against the same home volume.
    if ! grep -qF "/.local/bin" ~/.bashrc 2>/dev/null; then
      echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
    fi
    if ! grep -qF "/.local/bin" ~/.profile 2>/dev/null; then
      echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.profile
    fi
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
echo "[4/5] Installing Python dependencies..."
if pip3 install --quiet pyyaml jsonschema 2>/tmp/pip-install.log; then
  STATUS_PY="OK"
else
  STATUS_PY="FAILED — see /tmp/pip-install.log"
fi
echo "      $STATUS_PY"

# 4. Plugin files are auto-discovered — no install step needed.
# .claude/commands/*.md, skills/*/SKILL.md and .claude/settings.json are picked up by
# Claude Code just by being present in the project directory.
echo ""
echo "[5/5] Plugin files (.claude/commands, .opencode/, skills/) — auto-discovered, no install needed."

echo ""
echo "================================================================"
echo "  Setup summary:"
echo "    Claude Code CLI : $STATUS_CLAUDE"
echo "    OpenCode        : $STATUS_OPENCODE"
echo "    dtctl           : $STATUS_DTCTL"
echo "    Python deps     : $STATUS_PY"
echo "================================================================"
echo ""
echo "  Two sign-in steps remain:"
echo ""
echo "    1. Sign in to Claude — click Sign in in the Claude Code sidebar panel."
echo ""
echo "    2. Sign in to the Dynatrace Playground:"
echo "         python tools/preflight.py login"
echo "       A browser sign-in page opens. After signing in, the browser shows a"
echo "       'can't connect' page — copy that URL and paste it into the terminal prompt."
echo ""
echo "  Then in Claude Code:"
echo "    /demo-doctor   (verify everything is wired)"
echo "    /demo          (start an incident investigation)"
echo ""
echo "================================================================"
echo ""
