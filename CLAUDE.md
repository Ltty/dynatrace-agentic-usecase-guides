# Dynatrace Agentic Use Case Guides

## What this repo is

A Claude Code plugin that turns Dynatrace Use Case Guides into interactive, CLI-driven
troubleshooting sessions. The user explores real Playground data as if responding to a
production incident — guided, but explorative.

## Quick start (for contributors)

```bash
# 1. Authenticate against the Playground (browser, one-time per machine)
dtctl auth login --context playground --environment https://playground.apps.dynatrace.com

# 2. Verify everything is wired
/demo-doctor

# 3. Start a demo
/demo start payment-failure
```

## Architecture in one paragraph

One scenario-agnostic engine skill (`skills/demo-engine/SKILL.md`) drives all demos.
Everything scenario-specific lives in `scenarios/<id>/` as YAML, DQL, and Markdown data files.
Adding a new demo means adding a folder — no engine changes. The engine reads the active
scenario's manifest, resolves live Playground state via `dtctl`, and runs a beat loop that
feels like pair-debugging on a real incident.

## Connectivity

- **Tool:** `dtctl` (Dynatrace CLI) — `dtctl query`, `dtctl exec copilot`, `dtctl inventory`
- **Context:** `playground` / `https://playground.apps.dynatrace.com`
- **Safety level:** `readonly` — hard-enforced at the dtctl context layer
- **Agent mode:** auto-activates (`CLAUDECODE` env var present); output is JSON envelope
- **Auth:** per-user browser OAuth; no shared tokens exist in this repo

## Directory map

```
.claude/          Claude Code settings, hooks (guardrail enforcement)
.claude-plugin/   Plugin manifest
skills/           Engine skill + Playground DQL skill
commands/         /demo and /demo-doctor slash commands
scenarios/        One folder per demo; schema in _schema/
tools/            Python validators and preflight scripts
docs/             AUTHORING.md, SECURITY.md, spike-notes.md
```

## Guardrails

Hard (hook-enforced, cannot be prompted away):
- `dtctl` context locked to `readonly` safety level
- `.claude/settings.json` deny-by-default; only vetted dtctl read verbs allowed
- `PreToolUse` hook `guard-dtctl.py` validates every Bash call at the verb+DQL level

Soft (skill-level):
- Active scenario scope limits which data objects and services Claude queries
- Off-script prompts get an in-character redirect, not an error

## Adding a demo

See `docs/AUTHORING.md`. The contract: add `scenarios/<new-id>/scenario.yaml` plus beats,
queries, and fixtures. Register in `scenarios/registry.yaml`. Run `python tools/validate_scenarios.py`.
Zero changes to `skills/` or `commands/`.

## dtctl reference

- `dtctl query "<DQL>" --agent` — run a DQL query, get JSON envelope
- `dtctl exec copilot` — chat with Davis CoPilot
- `dtctl inventory --agent` — discover what data exists in the environment
- `dtctl doctor` — verify auth and connectivity
- `dtctl config describe-context playground` — show current context and safety level

## Known constraints

- Playground problem IDs change on each problem cycle; the resolver derives them fresh at `/demo start`
- `dtctl exec copilot` output is non-deterministic; used for colour/narrative, not as primary evidence
- The Playground is read-only; the engine must never attempt a write (hook enforces this)
