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
`tools/preflight.py` auto-searches common install locations too, but this is faster for any
raw `dtctl` call you make directly.

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

2. For each published scenario, resolve its live state — this alone gives you everything
   you need (affected users, start/end, status, display id); no second query required:
   ```bash
   python tools/preflight.py resolve <scenario-id>
   ```
   Note `mode` (`live_active` / `live_recent` / `fixture`), `problem.affected_users`,
   `problem.started`, `problem.status`.

3. Read `scenarios/<id>/scenario.yaml` for `business_context`.

4. Compute estimated revenue impact: `affected_users × business_context.avg_order_value_usd`.
   Compute `duration_min` from `problem.started` to now (or to `problem.ended` if closed).

5. Write a discovery message using `business_context.discovery_hook` as a starting point —
   but rewrite it to sound like a human SRE reporting to a peer, not a filled-in template.
   Use the real numbers. Don't invent a failure-rate percentage — the resolver doesn't
   provide one reliably; describe it qualitatively ("erroring hard", "failure rate spiked").

6. **End on a choice between concrete entry angles, never yes/no.** Offer 2–3 named starting
   points from the scenario's beats (e.g. the deployment timeline, the failing traces, the
   affected customers) so the user's first reply is already a decision.

### Example output — live_active or live_recent mode

```
Something's wrong in production.

The payment service is failing for [N] users. Checkout requests are erroring hard —
it's been going on for [N] minutes. That's roughly $[N] in abandoned carts.

Want to start with the deployment that likely caused it, the failing traces themselves,
or the customers who hit it?
```

### Example output — fixture mode (nothing live right now)

```
The environment is quiet at the moment, but there's a recent incident worth walking through.

The last payment failure hit [N] users and ran for [N] minutes. The data's all here —
traces, logs, the deployment that caused it, affected user sessions.

Start with the deployment timeline, the failing traces, or the affected customers?
```

### Natural language mapping

Map casual user input to actions — including a direct "yes"/"let's go", since the discovery
message itself now poses a choice rather than a yes/no question, but users may still reply
loosely:
- "payment" / "checkout" / "the deployment" / "traces" / "customers" → `/demo start <id>`
  (route to the named angle as the starting beat if the user names one specifically)
- "what else" / "anything else" → show other published scenarios
- generic "yes" / "let's go" / "show me" → `/demo start <most-relevant-id>`, starting at beat 1

---

## `/demo start <id>`

1. Confirm `<id>` is in `scenarios/registry.yaml` with `state: published`.
2. Run `python tools/preflight.py resolve <id> --write` — this both resolves the live problem
   and writes `.demo-state.json` in one step.
3. Read `mode` from the resolved state:
   - `live_active` / `live_recent` → proceed naturally, no announcement needed.
   - `fixture` → one line only: "Running on recorded data — same investigation, same findings."
4. Read `scenarios/<id>/scenario.yaml` (manifest with beats, persona, scope).
5. Begin at beat 0 (or the user-named entry angle from discovery) following the beat loop in
   `skills/demo-engine/SKILL.md`.

---

## `/demo status`

Read `.demo-state.json`. Show:
- Scenario name, mode (`live_active` / `live_recent` / `fixture`)
- Beats completed / total
- Elapsed time since `session_started`
- Current beat objective (from `scenario.yaml`)

---

## `/demo recap`

Read `.demo-state.json` and `scenarios/<id>/scenario.yaml`. Produce:
- One sentence per completed beat (what was actually found, with real values)
- Total elapsed time
- Closing: "From alert to root cause in X minutes."

---

## `/demo reset`

Delete `.demo-state.json`. Say: "Session cleared. Type /demo to begin again."
