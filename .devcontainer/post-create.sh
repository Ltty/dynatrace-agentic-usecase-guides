#!/usr/bin/env bash
# post-create.sh
# Runs once when the Codespace/dev container provisions.
# Installs the Claude Code CLI, dtctl, Chromium (for in-container OAuth), and
# Python deps. One interactive step remains:
#   python tools/preflight.py login  — sign in via the browser opened inside the container

set -uo pipefail  # deliberately not -e: one failed component shouldn't abort the rest;
                  # each step reports its own status and the summary at the end shows what's missing

echo ""
echo "=== Dynatrace Agentic Guides — dev container setup ==="
echo ""

STATUS_CLAUDE="not installed"
STATUS_DTCTL="not installed"
STATUS_PY="not installed"
STATUS_BROWSER="not installed"

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

# 2. Install dtctl (downloads binary from GitHub releases, no curl | bash)
echo ""
echo "[2/5] Installing dtctl..."
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
echo "[3/5] Installing Python dependencies..."
if pip3 install --quiet pyyaml jsonschema 2>/tmp/pip-install.log; then
  STATUS_PY="OK"
else
  STATUS_PY="FAILED — see /tmp/pip-install.log"
fi
echo "      $STATUS_PY"

# 4. Chromium (for in-container OAuth — both Claude and dtctl sign in via the desktop browser)
echo ""
echo "[4/5] Installing Chromium..."
if apt-get install -y -qq chromium-browser 2>/tmp/chromium-install.log \
    || apt-get install -y -qq chromium 2>>/tmp/chromium-install.log; then
  # Resolve whichever name was installed
  CHROMIUM_BIN=$(command -v chromium-browser 2>/dev/null || command -v chromium 2>/dev/null || true)
  if [ -n "$CHROMIUM_BIN" ]; then
    STATUS_BROWSER="OK ($CHROMIUM_BIN)"
  else
    STATUS_BROWSER="installed but not found on PATH"
  fi
else
  STATUS_BROWSER="FAILED — see /tmp/chromium-install.log (login wizard falls back to paste-back)"
fi
echo "      $STATUS_BROWSER"

# 5. Plugin files are auto-discovered — no install step needed.
# .claude/commands/*.md, skills/*/SKILL.md and .claude/settings.json are picked up by
# Claude Code just by being present in the project directory.
echo ""
echo "[5/5] Plugin files (.claude/commands, skills/) — auto-discovered, no install needed."

echo ""
echo "================================================================"
echo "  Setup summary:"
echo "    Claude Code CLI : $STATUS_CLAUDE"
echo "    dtctl           : $STATUS_DTCTL"
echo "    Python deps     : $STATUS_PY"
echo "    Chromium        : $STATUS_BROWSER"
echo "================================================================"
echo ""
echo "  One sign-in step remains:"
echo ""
echo "  Sign in to Claude and to the Dynatrace Playground via the in-container browser:"
echo ""
echo "    1. Forward port 6080 (the desktop/noVNC port) and open it in your browser."
echo "       Default VNC password: changeme  (set in devcontainer.json → desktop-lite.password)"
echo ""
echo "    2. Inside the desktop, sign in to Claude Code:"
echo "         BROWSER=chromium-browser claude login"
echo "       The browser opens inside the container — the OAuth callback resolves normally."
echo ""
echo "    3. Authenticate against the Dynatrace Playground:"
echo "         python tools/preflight.py login"
echo "       The browser also opens inside the container; sign-in completes automatically."
echo ""
echo "  Then, in Claude Code:"
echo "    /demo-doctor   (verify everything is wired)"
echo "    /demo          (start an incident investigation)"
echo ""
echo "================================================================"
echo ""
