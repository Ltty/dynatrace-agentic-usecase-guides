# /demo

Entry point for the Dynatrace Agentic Use Case Guides.

## Subcommands

- `/demo` — ambient discovery: show current environment state as live incidents
- `/demo list` — plain table of available scenarios (fallback if user prefers)
- `/demo start <id>` — start a demo directly by scenario ID
- `/demo status` — show current progress in an active demo
- `/demo recap` — narrative summary of what was found so far
- `/demo reset` — clear session state

---

## `/demo` — ambient discovery (the default, preferred flow)

This is the showroom entry point. Do NOT show a menu. Instead, surface the Playground
environment as if it's a real production system the user is about to investigate.

### Steps

1. Read `scenarios/registry.yaml` for all `state: published` scenarios.

2. For each scenario, run a lightweight probe to check if the pattern is currently active:
   ```bash
   python tools/preflight.py resolve <scenario-id>
   ```
   Capture the JSON. Note `mode` (live/fixture), `problem.started`, `problem.status`,
   and `placeholders.PAYMENT_FAILURE_PROBLEM`.

3. Also run one quick DQL to get the live failure rate for the hook line
   (use the scenario's `beat-01` evidence query, limit to 1 row, grab `affected_users` and `started`):
   ```bash
   dtctl query "fetch dt.davis.problems, from: now()-24h | filter root_cause_entity_id == 'SERVICE-531CE26849E95EC1' | sort timestamp desc | limit 1 | fields dt.davis.affected_users_count, event.start, event.status" --agent -o json --plain
   ```

4. Construct the discovery message using the scenario's `business_context.discovery_hook` template.
   Fill in:
   - `{service_name}` → `business_context.service_name`
   - `{affected_users}` → live value from the probe (or fixture value)
   - `{failure_rate}` → "54.7" (from beat-01 evidence, or fixture approximation)
   - `{duration_min}` → minutes since `problem.started`
   - `{revenue_impact}` → `affected_users × avg_order_value_usd`, formatted with commas

5. Present one scenario per paragraph. End with an open, natural question — not a menu prompt.

### Example output (payment failure, live mode)

```
Something's wrong in production.

The payment service is failing for 310 users. Checkout requests are erroring at 54.7% —
it's been going on for 29 minutes. That's roughly $26,970 in abandoned carts.

Davis has already flagged the root cause. Want to dig in and find it?
```

If the mode is `fixture` (problem not currently live):
```
The environment is quiet right now, but we've got a recorded incident worth walking through.

The last payment service failure hit 310 users, crashed checkout at 54.7%, and ran for 29 minutes.
Davis traced the root cause to a specific deployment. Want to see how fast we can get there?
```

If multiple scenarios are published:
Present each one as a separate paragraph — concise, incident-framed. End with:
"Which one do you want to look at?"

### Natural follow-up handling

The user might respond with anything — "yes", "let's go", "show me the payment one", "what else is there".
Map natural language to the right scenario ID and call `/demo start <id>`.

---

## `/demo start <id>`

1. Confirm `<id>` is in `scenarios/registry.yaml` with `state: published`.
2. Run `python tools/preflight.py resolve <id>` and write output to `.demo-state.json`.
3. Read `mode` from state:
   - `live` → no announcement, proceed naturally.
   - `fixture` → one line only: "Running on recorded data — same investigation, same findings."
4. Load `scenarios/<id>/scenario.yaml`.
5. Invoke the `demo-engine` skill at beat 0.

---

## `/demo status`

Read `.demo-state.json`. Show concisely:
- Scenario name
- Mode (live / fixture)
- Beats completed / total  
- Elapsed time since `session_started`
- Current beat objective (from `scenario.yaml`)

---

## `/demo recap`

Read `.demo-state.json`. Produce the incident timeline:
- One sentence per completed beat
- Total elapsed time
- End: "From alert to root cause in X minutes."

---

## `/demo reset`

Delete `.demo-state.json`. Confirm: "Session cleared. Run /demo to begin again."
