# Adding a New Demo

A scenario is two markdown files in the skill, plus a row in its registry table. No engine code changes:
the same skill runs in Dynatrace (`@demo-agent`) and locally (`/demo`), so one scenario serves both.

All paths below are under `dynatrace-intelligence/skills/investigating-playground-incidents/`.

## The contract

```text
references/scenario-<id>.md         # persona, business context, scope, handoff fields, resolver DQL
references/scenario-<id>-beats.md   # the beats: evidence DQL, reveal, staging, deep link
SKILL.md                            # one row in the Scenarios table
```

The survey reads only the first file for every scenario; the beats file is read once the user picks a
direction. Keep the split, or the survey gets slow and expensive as scenarios are added. `references/` stays
flat: no subfolders, unique names, linked as `references/<name>.md`. Keep `SKILL.md` under 150 lines.

Maintainer-only notes (entity IDs, history, source material) go in `docs/scenarios/`, never in the skill
folder: the agent reads everything in it and would repeat it to the user.

**Read the video transcript before writing beats, if one exists** (`docs/scenarios/payment-failure-source/`
is the example). It is often richer than the step titles in the guide JSON: the payment-failure transcript
revealed a missing beat (which team owns the failing service, already on the problem record) and reframed
what "show me the trace" means (the whole request, confirming the upstream services are clean).

## Step by step

### 1. Copy a scenario and rename it

Start from `scenario-payment-failure.md` and `scenario-payment-failure-beats.md`. The `<id>` is
`[topic]-[variant]`, e.g. `k8s-oom-kill`.

### 2. Write the resolver DQL

In `scenario-<id>.md`: a primary and a fallback block, in that order. Each returns **one row** with exactly the
fields the session protocol names (`references/session-protocol.md` → "Session state"): `problem_id`,
`display_id`, `status`, `started`, `ended`, `affected_users`, `root_cause`, `description`, `duration_min`,
`ended_min_ago`, `queried_at`, `window_from`, `window_to`, `tf_from_ms`, `tf_to_ms`. Copy the payment-failure
resolver and change only the root-cause service ID. Date arithmetic belongs in the DQL, not in the model.

- Look back `from: now()-48h, to: now()`. Patterns fire on a schedule; this window reliably catches the latest
  occurrence.
- **Filter `dt.davis.is_duplicate == false`, not on `event.name`.** Recurring patterns fire as a cluster of
  near-duplicate problems with overlapping windows and different affected-user counts. Without the filter,
  `sort … | limit 1` picks one arbitrarily and any revenue figure changes every run. The merged problem is
  often named generically ("Multiple application problems"), so an `event.name` filter excludes the one you want.
- The fallback drops `is_duplicate` and sorts by `dt.davis.affected_users_count desc`; it runs only if the
  primary returns no rows.

### 3. Write the beats

In `scenario-<id>-beats.md`, one `## Beat N — Title` section each, with: **Objective**, **Evidence DQL**,
**Reveal**, **Success signal**, **Deep link**, and for a climax `**peak_moment: true**` plus **Staging**.
Optional: an **Objection** paragraph (skeptic pushback and the answer, used only when the user raises it) and a
**Fold in on a jump** note when a beat's evidence is needed even if the user skips it.

- Window every query with `from: "{{DQL_FROM}}", to: "{{DQL_TO}}"`, never `now()-Nh`: these are the incident
  window from the resolver (15 minutes of padding each side), so the query works however long ago it closed.
  Other tokens: `{{PROBLEM_ID}}`, `{{TF_FROM_MS}}`, `{{TF_TO_MS}}` (deep links), `{{TRACE_ID}}` (chained).
- Never use `limit` where the beat's claim is about *everything* (all deploys, all distinct exceptions, the
  total sessions). Aggregate instead: `summarize … by:` per commit or per exception, oldest first, with
  `first_seen` / `last_seen`. A `sort desc | limit 5` once hid the deploy that caused the incident.
- Return few columns; select exactly what the beat needs.
- DQL must never contain INGEST, INSERT, UPDATE, DELETE, PUT or WRITE; the guard hook rejects it.
- A **chained** query takes a value from another query's first record (a trace ID, say): say so in the beat,
  name the field, and use `toUid("{{TRACE_ID}}")` for `trace.id`.

**Verify every field name against the live Playground; trust nothing from a spec or a past run.** The verified
gotchas (`start_time` not `timestamp`, `toDouble(duration)`, named `round(x, decimals: 1)`, bracket access after
`expand span.events`, `toUid()` on `trace.id`, deployment events, user sessions, logs) are in
`references/dql-reference.md`. Add each new one there, with the reason.

**Write `Reveal` as the shape of the finding, never its values.** Exception messages, commit SHAs, line
numbers, counts and teams rotate every problem cycle. "The failing spans carry a specific exception — quote it
verbatim" stays true; "the exception is X" is stale the next time the pattern fires. The agent reads the value
at run time. A reveal also states only what the returned fields show. Say what the data says, and say where
the data stops ("whether it was intended is the owning team's call"); never a cause, intent or geography that
no returned field contains.

**Success signal** is recognition, not compliance: "user names the failing service", not "user clicks next".

**Deep links** matter as much as queries: each beat should let the user open the real Dynatrace view of what
they just found in the terminal.

### 4. Peak moments

A climax (the finding that *is* the answer) or an emotional payoff (making the human impact concrete) gets
`peak_moment: true` and a **Staging** list: land the finding on its own line before commentary, pause, explain
what kind of finding it is, then the concrete next action. The skill's rule for the shared rhythm is in
`references/conversation-craft.md` → "Peak moments".

### 5. Business context and handoff

In `scenario-<id>.md`: `service_name`, `user_action`, optional `avg_order_value_usd` (omit it and the survey
reports no revenue figure rather than an invented one), and a discovery-hook template with single-brace tokens
(`{service_name}`, `{affected_users}`, `{duration_min}`, `{revenue_impact}`). Only reference values the resolver
supplies. If the problem record carries no clean rate, describe severity qualitatively and let a beat's query
carry the exact number.

The **Handoff fields** table says which beat provides each value the agent needs to hand an incident to its
owner (owning team, commit and link, populations, replay link). If the owning team and the deploy owner
differ, say which is who. The row `Goes to` says who the handoff goes to: the team, or the host when there is no
team. The **Business context** table carries a `symptom` (a short phrase for what is failing) and, optionally,
`avg_order_value_usd` and a `payoff` sentence for the close; without them a scenario gets no cost line and no
payoff.

### 6. Register, validate, evaluate

1. Add the row to the Scenarios table in `SKILL.md` and the files to `SCENARIO_FILES` in
   `tools/validate_dt_skill.py` (the same dict feeds `run_dt_evals.py` and `preflight.py preflight`).
   A scenario whose entities exist on another tenant (the `disk-cpu-cascade` one is dev-only) also goes in
   `SCENARIO_CONTEXT` there: the validator then uses that dtctl context for it, and `preflight.py preflight`
   skips it instead of reporting it empty. The local `/demo` is pinned to the Playground and cannot reach it. Its
   fallback resolver must also carry a predicate only that tenant's entities satisfy, or a Playground survey lists it
   (testruns 12 and 13).
2. `python tools/dt_agent.py check` — layout rules.
3. `python tools/validate_dt_skill.py --scenario <id>` — runs the resolver and **every** beat query live,
   including chained ones, and fails on a bad field name or `round()` call. Do not call a scenario done
   until it passes clean.
4. `python tools/preflight.py preflight` — the scenario shows as live, or as SKIP when its data lives on another
   tenant.
5. Upload and evaluate: `docs/DYNATRACE-SKILL.md`. Add an eval case under `tests/evals/dt-agent/` for any new
   behaviour. Run a full `/demo` session and write it up as a `docs/testrun-NN.md`.

## What the agent guarantees

It reads your two files and runs your queries. It will:

- add no scenario knowledge it did not read from them, and state no value it did not read from a result;
- never modify the Playground (read-only context, guard hook, permission allow-list);
- narrate your Reveal as its own read of the evidence in the same turn, attached to a next step, never
  withheld until the user guesses and never a dead end;
- offer the deep link at the end of each beat, and follow the user's detours before re-anchoring on what is
  still unknown;
- when the user asks to be walked through it, deliver the same beats as a report and close with a handoff
  block built only from your Handoff fields table. A value the table has no source for is left out of the
  block, so say plainly there when a scenario has no owning team or no user count;
- show a proof stamp (query ID, records scanned, milliseconds) after each beat's evidence.

It will not guarantee that entity IDs stay stable if the Playground is reset, and it does not parse a failure
rate out of the problem description text: take exact rates from an evidence query.
