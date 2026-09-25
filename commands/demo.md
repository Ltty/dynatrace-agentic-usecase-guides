Entry point for the Dynatrace Agentic Use Case Guides.

## First: load your operating rules

Before doing anything else, read these files in order:
1. `skills/demo-engine/SKILL.md` — your role, the beat loop, nudge ladder, response rules
2. `skills/dynatrace-playground/SKILL.md` — how to query dtctl, parse the envelope, present evidence

These are your standing instructions for the entire session. Hold them.

Also ensure `dtctl` is on PATH — new sessions often miss it. Run before any dtctl call:
```bash
# Windows (Bash tool):
export PATH="$PATH:/c/Users/$USERNAME/AppData/Local/dtctl"
# Linux/Mac:
export PATH="$PATH:$HOME/.local/bin"
```
The preflight script auto-searches common install locations, but this is faster.

---

## Subcommands

- `/demo` (no args) — ambient discovery: surface the Playground as live incidents
- `/demo list` — plain table fallback
- `/demo start <id>` — start a specific scenario
- `/demo status` — current beat progress
- `/demo recap` — incident timeline narrative
- `/demo reset` — clear `.demo-state.json`

---

## `/demo` — ambient discovery (preferred entry point)

Do NOT show a menu. Surface the Playground as a real production environment.

### Steps

1. Read `scenarios/registry.yaml` — find all `state: published` scenarios.

2. For each published scenario, run the resolver to get live state:
   ```
   python tools/preflight.py resolve <scenario-id>
   ```
   Note: `mode` (live/fixture), `problem.started`, `problem.status`, `placeholders`.

3. Read `scenarios/<id>/scenario.yaml` for `business_context`.

4. Run a quick DQL to get the current failure rate (beat-01 evidence):
   ```
   dtctl query --file scenarios/<id>/queries/beat-01-problem-summary.dql --agent -o json --plain
   ```
   Extract `affected_users`, `started`, `status` from the envelope's records.

5. Compute estimated revenue impact: `affected_users × business_context.avg_order_value_usd`

6. Write a discovery message using `business_context.discovery_hook` as a template — but
   rewrite it to sound like a human SRE talking to a peer, not a filled-in template.
   Include real numbers from the live data.

7. End on a natural open question. Never use a numbered menu.

### Example output (live mode, payment failure)

```
Something's wrong in production right now.

The payment service is down for 310 users — checkout requests are failing at 54.7%.
It's been running for 29 minutes. At the Astroshop's average order value that's roughly
$26,970 sitting in abandoned carts.

Davis has already identified a root cause. Want to dig in and find it?
```

### Fixture mode (problem not currently active)

```
The environment is quiet at the moment, but there's a recent incident worth walking through.

The last payment failure hit 310 users, crashed checkout at 54.7%, and ran for 29 minutes.
The data's all here — traces, logs, the deployment that caused it, affected user sessions.

Want to run through the investigation?
```

### Natural language mapping

Map casual user input to actions:
- "yes" / "let's go" / "show me" → `/demo start <most-relevant-id>`
- "what else" / "anything else" → show other published scenarios
- "payment" / "checkout" / "Astroshop" → `/demo start payment-failure`

---

## `/demo start <id>`

1. Confirm `<id>` is in `scenarios/registry.yaml` with `state: published`.
2. Run `python tools/preflight.py resolve <id>` and write the JSON output to `.demo-state.json`.
3. Read `mode` from state:
   - `live` → proceed naturally, no announcement.
   - `fixture` → one line only: "Running on recorded data — same investigation, same findings."
4. Read `scenarios/<id>/scenario.yaml` (manifest with beats, persona, scope).
5. Begin at beat 0 following the beat loop in `skills/demo-engine/SKILL.md`.

---

## `/demo status`

Read `.demo-state.json`. Show:
- Scenario name, mode (live/fixture)
- Beats completed / total
- Elapsed time since `session_started`
- Current beat objective (from `scenario.yaml`)

---

## `/demo recap`

Read `.demo-state.json` and `scenarios/<id>/scenario.yaml`. Produce:
- One sentence per completed beat (what was found)
- Total elapsed time
- Closing: "From alert to root cause in X minutes."

---

## `/demo reset`

Delete `.demo-state.json`. Say: "Session cleared. Type /demo to begin again."
