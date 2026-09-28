# Dynatrace Agentic Use Case Guides

A Claude Code plugin that turns Dynatrace Use Case Guides into interactive,
CLI-driven troubleshooting sessions. You explore real Playground data as if
responding to a production incident — guided by an AI SRE, but genuinely explorative.

```
/demo          → start an incident investigation
/demo-doctor   → check your environment is wired up
```

---

## How it works

The demo engine plays an on-call SRE who has just been paged. You and Claude
investigate together: it runs live DQL queries against the [Dynatrace Playground](https://playground.apps.dynatrace.com),
surfaces the evidence, and narrates its own read of the data — just as a senior
colleague would during a real incident. You can steer, dive deeper, or let it drive.

Every number comes from the live Playground. No fixtures, no canned responses.

**Current scenarios:**

| Title | Tags | Duration |
|-------|------|----------|
| Resolve production incidents faster: Payment failure | incident-response, tracing, session replay | 8–15 min |

---

## Quickstart

Choose the option that fits your setup.

### Option A — GitHub Codespaces (recommended, zero local setup)

No installs required. Everything provisions automatically.

1. Open this repo on GitHub → **Code** → **Codespaces** → **Create codespace on master**
2. Wait for the container to build — Claude Code, `dtctl`, and Python deps install automatically
3. Sign in to Claude (if the extension hasn't already prompted you):
   ```bash
   claude login
   ```
4. Authenticate against the Dynatrace Playground:
   ```bash
   dtctl auth login --context playground \
     --environment https://playground.apps.dynatrace.com
   ```
   A browser tab opens for Dynatrace SSO.
   No account yet? Free signup: [dynatrace.com/signup/playground](https://www.dynatrace.com/signup/playground/)
5. Verify and start:
   ```bash
   /demo-doctor
   /demo
   ```

Port 3232 is forwarded automatically for the OAuth callback — no extra configuration needed.

---

### Option B — Local VS Code with Dev Containers

Prerequisites: Docker running, VS Code, and the
[Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

1. Clone the repo and open it in VS Code:
   ```bash
   git clone https://github.com/Ltty/dynatrace-agentic-usecase-guides.git
   code agentic-usecase-guides
   ```
2. VS Code detects `.devcontainer/devcontainer.json` → click **Reopen in Container**
3. Wait for `post-create.sh` to finish — same installs as Codespaces
4. In the container terminal, sign in to Claude:
   ```bash
   claude login
   ```
5. Authenticate against the Playground:
   ```bash
   dtctl auth login --context playground \
     --environment https://playground.apps.dynatrace.com
   ```
6. Verify and start:
   ```bash
   /demo-doctor
   /demo
   ```

---

### Option C — Bare machine (no container)

Replicate the container's install steps directly. Requires Node 18+, Python 3.10+.

**1. Claude Code CLI**

```bash
npm install -g @anthropic-ai/claude-code
claude login
```

**2. dtctl**

Download the binary for your platform from the
[dtctl releases page](https://github.com/dynatrace-oss/dtctl/releases), then:

```bash
# Linux/macOS
chmod +x dtctl
mv dtctl ~/.local/bin/

# Windows — move to a directory on your PATH, e.g.:
# C:\Users\<you>\AppData\Local\dtctl\dtctl.exe
# then add that directory to $env:PATH
```

Configure the Playground context:

```bash
dtctl config set-context playground \
  --environment https://playground.apps.dynatrace.com \
  --safety-level readonly
dtctl config use-context playground
dtctl auth login --context playground \
  --environment https://playground.apps.dynatrace.com
```

**3. Python dependencies**

```bash
pip install pyyaml jsonschema
```

**4. PATH (Windows, new terminal sessions)**

```bash
# Bash tool / Git Bash:
export PATH="$PATH:/c/Users/$USERNAME/AppData/Local/dtctl"
```

**5. No plugin install step needed**

`.claude/commands/` and `skills/` are auto-discovered when Claude Code opens
the project folder. `/demo` and `/demo-doctor` work immediately.

**6. Verify and start**

```bash
/demo-doctor
/demo
```

---

## What the two auth steps do

| Step | Purpose | Needed once per |
|------|---------|----------------|
| `claude login` | Browser OAuth → your Anthropic/Claude account | machine / container |
| `dtctl auth login` | Browser OAuth → Dynatrace SSO → token stored in your OS keyring or `~/.config/dtctl/` | machine / container |

No shared tokens exist in this repo. Both are intentionally per-user browser OAuth —
see [docs/SECURITY.md](docs/SECURITY.md) for the full rationale.

---

## If something doesn't work

```bash
/demo-doctor
```

This runs `tools/preflight.py check` and reports exactly which piece is missing:
Claude auth, dtctl availability, Playground connectivity, or safety-level configuration.

---

## Architecture

One scenario-agnostic engine skill drives all demos. Everything scenario-specific
lives in `scenarios/<id>/` as YAML, DQL, and Markdown files. Adding a new demo
means adding a folder — zero changes to `skills/`, `commands/`, or `tools/`.

```
.claude/            Claude Code settings, hooks (guardrail enforcement)
.claude-plugin/     Plugin manifest
skills/             Engine skill + Playground DQL reference skill
commands/           /demo and /demo-doctor slash commands
scenarios/          One folder per demo; schema in _schema/
  registry.yaml     The only file the engine reads to discover available demos
  payment-failure/  First scenario (published)
  _template/        Copy this to start a new scenario
tools/              Python validators and preflight scripts
docs/               AUTHORING.md, SECURITY.md, test run notes
```

The engine reads `.demo-state.json` (written by `tools/preflight.py resolve`) for
the live incident window, problem ID, affected users, and beat progress. It never
reads from fixtures — all queries hit the live Playground.

---

## Safety

The Playground is read-only. Three independent layers enforce this:

| Layer | Mechanism |
|-------|-----------|
| 1 | `dtctl` context `safety-level: readonly` — blocks mutating verbs client-side |
| 2 | `.claude/settings.json` deny-by-default — allowlists only vetted dtctl read verbs |
| 3 | `PreToolUse` hook `guard-dtctl.py` — validates every Bash call at the DQL level |

All three must be bypassed simultaneously to issue a write. In practice this is not possible
without repo write access and OS-level keyring access. See [docs/SECURITY.md](docs/SECURITY.md).

---

## Adding a demo

See [docs/AUTHORING.md](docs/AUTHORING.md). The short version:

1. Copy `scenarios/_template` to `scenarios/<your-id>/`
2. Edit `scenario.yaml` — beats, queries, business context
3. Add a resolver query (`queries/find-problem.dql`) that returns one canonical problem row
4. Write per-beat evidence queries using `{{DQL_TIMEFRAME_FROM}}` / `{{DQL_TIMEFRAME_TO}}`
5. Register in `scenarios/registry.yaml` with `state: draft`
6. Validate:
   ```bash
   python tools/validate_scenarios.py scenarios/<your-id>          # schema + DQL lint
   python tools/validate_scenarios.py --live scenarios/<your-id>   # + live execution
   ```
7. Set `state: published` and commit

Zero changes to engine code required.

---

## Tooling reference

| Command | What it does |
|---------|-------------|
| `python tools/preflight.py check` | Connectivity, auth, and safety-level gate (what `/demo-doctor` runs) |
| `python tools/preflight.py resolve <id> [--write]` | Find the live problem, derive the incident window, optionally write `.demo-state.json` |
| `python tools/preflight.py run-query <id> <dql-path> [--var K=V] [--render waterfall]` | Substitute placeholders and execute a beat query; prints a liveness proof stamp to stderr |
| `python tools/validate_scenarios.py [--live] [scenarios/<id>]` | Schema, integrity, DQL lint; with `--live`, actually executes every query |
| `python tools/render_waterfall.py` | ASCII waterfall renderer — reads dtctl envelope from stdin |
