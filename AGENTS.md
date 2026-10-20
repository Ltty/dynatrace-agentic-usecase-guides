# Dynatrace Agentic Use Case Guides

Interactive, CLI-driven incident investigations on the Dynatrace Playground. The user explores real
Playground data as if responding to a production incident — guided, but explorative — or is walked through
the incident as a report.

## One skill, two runtimes

The demo is one skill and one agent prompt, run in two places:

- **Dynatrace** — `@demo-agent` in Dynatrace Assist. Tool: `execute-dql`.
- **Locally** — `/demo` in Claude Code or OpenCode. Tool: `dtctl query`.

Both read `dynatrace-intelligence/skills/investigating-playground-incidents/` (the skill, with its
`references/`) and `dynatrace-intelligence/agents/demo-agent/instructions.md` (the agent prompt).
`skills/local-runtime/SKILL.md` is the only local-only piece: it maps `read_file` to a local Read and
`execute-dql` to `dtctl query --context playground`, and holds no behaviour rules. A rule change goes
in the skill once and both runtimes get it.

`/demo` loads these with `@`-includes. `CLAUDE.md` and `opencode.json` load only this file, so ordinary
sessions in this repo are not the SRE persona.

## Quick start (for contributors)

```bash
# 1. Authenticate against the Playground (browser, one-time per machine)
python tools/preflight.py login

# 2. Verify everything is wired
/demo-doctor

# 3. Start a demo
/demo
```

`dtctl` must be on PATH so `Bash(dtctl query *)` matches without a permission prompt. Windows: add
`%LOCALAPPDATA%\dtctl` to your user PATH; Linux/Mac: `~/.local/bin`.

## Connectivity

- **Tool:** `dtctl` (Dynatrace CLI) — `dtctl query`, `dtctl inventory`
- **Context:** `playground` / `https://playground.apps.dynatrace.com`. Every local query passes
  `--context playground`, whatever the saved context is.
- **Safety level:** `readonly` on the playground context, plus the guard hook (see Guardrails)
- **Agent mode:** auto-activates (`CLAUDECODE` env var present); output is a JSON envelope
- **Auth:** per-user browser OAuth; no shared tokens exist in this repo
- **State:** conversation context only. The survey query in `session-protocol.md` returns each scenario's problem,
  the incident window and the timing fields; there is no state file.
- **Quoting:** run `dtctl` from Bash. Windows PowerShell 5.1 strips the double quotes inside DQL
  string literals, so the query silently returns no rows.

## Directory map

```
.claude/          Claude Code settings, hooks (guardrail enforcement), maintainer-only skills
.claude-plugin/   Claude Code plugin manifest
.opencode/        OpenCode plugin and command definitions
skills/           local-runtime: the adapter that runs the Dynatrace skill with dtctl
commands/         /demo and /demo-doctor (.claude/commands/ is a copy; CI checks they match)
dynatrace-intelligence/  The skill and the demo-agent: the single source for both runtimes
tools/            dt_agent.py (check/upload/test the Dynatrace skill and agent), validate_dt_skill.py,
                  run_dt_evals.py, preflight.py, guard_dtctl.py
tests/            Behaviour evals for the demo-agent (tests/evals/dt-agent/)
docs/             AUTHORING.md, SECURITY.md, DYNATRACE-SKILL.md, skill-backlog.md, test runs
```

## Guardrails

Hard (hook-enforced, cannot be prompted away):

- `dtctl` context locked to `readonly` safety level — harness-independent
- Claude Code: `.claude/settings.json` deny-by-default + a `PreToolUse` hook on Bash and PowerShell
- OpenCode: `opencode.json` permission globs + `.opencode/plugin/guard-dtctl.ts`

Both harnesses call the same script (`tools/guard_dtctl.py`) for verb and DQL enforcement. It checks
every segment of a command: quoted paths, `&&`/`;`/pipes, `&` in PowerShell, variables holding the
dtctl path, wrappers such as `bash -c`, and DQL piped in or read with `-f`.
`tools/tests/test_guard_hook.py` covers each.

Soft (skill-level):

- The scenario's scope limits which data objects and services are queried
- Off-script prompts get an in-character redirect, not an error
- Out-of-role asks and remediation requests get an in-character handoff, never a capability refusal

## Changing the skill or the agent

Edit `dynatrace-intelligence/`, then follow `docs/DYNATRACE-SKILL.md` (check, validate live, upload
with approval, evals). Ideas that are not in the skill yet, and why, are in `docs/skill-backlog.md`.

Adding a scenario: `docs/AUTHORING.md`.

## Tooling reference

- `python tools/dt_agent.py check|pack|docs|template|invoke` — check, copy, upload and test the Dynatrace
  skill and `demo-agent`; every write is a dry run unless `--apply`. Procedure: `docs/DYNATRACE-SKILL.md`
- `python tools/validate_dt_skill.py --scenario <id>` — runs every DQL block of a scenario live
- `python tools/run_dt_evals.py --local` — the same cases on this machine, with a Claude model and `dtctl` instead of a
  deployed agent (needs `ANTHROPIC_API_KEY`; `tools/local_agent.py`)
- `python tools/run_dt_evals.py --tenant dev|playground` — the `demo-agent` behaviour cases (3 runs each,
  scripted assertions, ground-truth numbers); writes a review sheet
- `python tools/preflight.py check` — connectivity/auth/safety-level gate (what `/demo-doctor` runs)
- `python tools/preflight.py preflight` — is each scenario's problem live?
- `python tools/preflight.py dtctl-path` — how to invoke dtctl (bare `dtctl` if on PATH)
- `python tools/tests/test_guard_hook.py`, `test_run_dt_evals.py` — offline tests (CI runs them)

## Known constraints

- Recurring Playground problem patterns fire as a **cluster of near-duplicate problems**. The survey query
  filters `dt.davis.is_duplicate == false` to get one deterministic instance — do not additionally filter
  on `event.name`, the umbrella problem is often generically named.
- Specific values (exception text, commit SHA, line numbers, affected-user counts) **rotate every problem
  cycle** — never hardcode them in a scenario file; read them live.
- Several populations exist in an incident (the problem record's affected users, failed spans, sessions
  with 5xx). Never conflate them — always label which population a number describes.
- **Data is the only source of conclusions.** Counts and nulls are stated as returned; no geography,
  intent or cause that no returned field contains.
- Product naming: all Dynatrace AI is "Dynatrace Intelligence", the chat interface is "Dynatrace Assist";
  never "Davis" or "CoPilot" in what the agent says. `dt.davis.*` fields and app IDs in links are
  identifiers and stay.
- Field names in this Playground do not always match generic DQL documentation — see
  `references/dql-reference.md` in the skill before trusting an assumption.
- The Playground is read-only; the agent must never attempt a write (the hook enforces this).
- No fixture fallback exists — all queries hit the live Playground. The survey query looks back 48h and
  each of those problems fires at least once a day, so a live occurrence is almost always available
  (`disk-cpu-cascade` is one long-running problem on the dev tenant). If nothing is
  found, the agent says the environment is clean and stops.
