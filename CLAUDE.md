# Dynatrace Agentic Use Case Guides

<!--
CONFIRMED WORKING (verified in a fresh session): these two lines make demo-engine/SKILL.md
and dynatrace-playground/SKILL.md show up as their own separate "Contents of ... (project
instructions, checked into the codebase)" blocks at session start, with zero visible Read
call — the same silent-injection mechanism CLAUDE.md's own content uses. This is what lets
.claude/commands/demo.md skip an explicit "read these files" step entirely (see its own
"Your operating rules are already loaded" section) — that step used to cost two visible
Read rows before the very first word of the greeting.

If you ever see the literal "@skills/..." text unexpanded in a session's context instead of
the skill content itself, this has broken (client/version change) — restore the explicit
Read instruction in .claude/commands/demo.md as a fallback until it's fixed.
-->
@skills/demo-engine/SKILL.md
@skills/dynatrace-playground/SKILL.md

## What this repo is

A Claude Code plugin that turns Dynatrace Use Case Guides into interactive, CLI-driven
troubleshooting sessions. The user explores real Playground data as if responding to a
production incident — guided, but explorative.

## Quick start (for contributors)

```bash
# 0. Add dtctl to PATH (new sessions don't always inherit it)
#    Windows (in Bash tool):
export PATH="$PATH:/c/Users/$USERNAME/AppData/Local/dtctl"
#    Linux/Mac:
export PATH="$PATH:$HOME/.local/bin"

# 1. Authenticate against the Playground (browser, one-time per machine)
dtctl auth login --context playground --environment https://playground.apps.dynatrace.com

# 2. Verify everything is wired
/demo-doctor

# 3. Start a demo
/demo
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
- **Resolved state:** `tools/preflight.py resolve <id> --write` → `.demo-state.json`, mode is
  one of `live_active` / `live_recent` / `fixture`
- **Beat queries:** always run via `python tools/preflight.py run-query <id> <dql-path>` —
  substitutes `{{DQL_TIMEFRAME_FROM}}`/`{{DQL_TIMEFRAME_TO}}` etc. from state, and transparently
  falls back to a captured fixture when `mode == fixture`. Raw `dtctl query --file` on a beat
  query will not substitute placeholders.

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
queries, and fixtures. Register in `scenarios/registry.yaml`. Run
`python tools/validate_scenarios.py --live scenarios/<new-id>` — this actually executes every
query against the Playground, not just static checks. Zero changes to `skills/` or `commands/`.

## Tooling reference

- `python tools/preflight.py check` — connectivity/auth/safety-level gate (what `/demo-doctor` runs)
- `python tools/preflight.py resolve <id> [--write]` — find the live problem, derive the incident
  window, optionally write `.demo-state.json`
- `python tools/preflight.py run-query <id> <dql-path>` — substitute placeholders + execute
  (or read a fixture, if `mode == fixture`) — what beat evidence queries actually run through
- `python tools/validate_scenarios.py [--live] [scenarios/<id>]` — schema/integrity/DQL-lint,
  plus (with `--live`) real execution of every query
- `python tools/capture_fixtures.py <id>` — capture fresh beat-level fixtures from a currently-live
  problem occurrence
- `dtctl exec copilot "<question>" --context "<your own query facts>"` — Davis CoPilot; message
  is positional, not stdin

## Known constraints

- Recurring Playground problem patterns fire as a **cluster of near-duplicate Davis problems**.
  The resolver filters `dt.davis.is_duplicate == false` to get one deterministic instance — do
  not additionally filter on `event.name`, the umbrella problem is often generically named.
- Specific values (exception text, commit SHA, line numbers, affected-user counts) **rotate
  every problem cycle** — never hardcode them in a `scenario.yaml` reveal; read them live.
- `dtctl exec copilot` output is non-deterministic; used for colour/narrative fed by your own
  query results, not as primary evidence.
- The Playground is read-only; the engine must never attempt a write (hook enforces this).
- Field names in this Playground do not always match generic DQL documentation — see the
  verified list in `skills/dynatrace-playground/SKILL.md` before trusting an assumption.
