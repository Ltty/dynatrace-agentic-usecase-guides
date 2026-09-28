# Adding a New Demo

Adding a new Use Case Guide to this repo is a content task, not a code task.
Zero changes to `skills/`, `commands/`, or `tools/` are required.

## The contract

Everything the engine needs lives in `scenarios/<id>/`:

```
scenarios/my-new-demo/
├── scenario.yaml          # manifest — the only required file
├── queries/
│   ├── find-problem.dql   # resolver: finds the live problem instance
│   ├── beat-01-*.dql      # one DQL per beat evidence entry
│   └── ...
└── source/
    ├── usecase.json           # original guide JSON (provenance)
    └── video-transcript.vtt   # video narration transcript, if you have one (provenance)
```

**Read the video transcript before writing beats, if one exists.** It's often richer than
the step titles in `usecase.json` alone — the payment-failure scenario's transcript revealed
an entire missing beat (which team owns the failing service — straight off the Services app
Properties tab, and free: the field is already on the Davis problem record) and reframed what
"show me the trace" should mean (the full waterfall, confirming upstream services are clean,
not just the one failing span). Mine it for beats, not just flavor text.

## Step-by-step

### 1. Copy the template

```bash
cp -r scenarios/_template scenarios/my-new-demo
cd scenarios/my-new-demo
```

Edit `scenario.yaml`. The `id` field must match the directory name.

### 2. Write the resolver query

`queries/find-problem.dql` — a DQL query that returns exactly one row: the canonical
instance of your problem pattern on the Playground.

Required output fields (name them exactly):
- `problem_id` — the `event.id` value
- `display_id` — the `P-XXXXXXX` display identifier
- `status` — `event.status` (`ACTIVE` or `CLOSED`)
- `started` — `event.start`
- `ended` — `event.end` (null if still active)
- `affected_users` — `dt.davis.affected_users_count`
- `root_cause` — `root_cause_entity_name`

Always filter `from: now()-48h, to: now()` — patterns fire on a schedule (typically twice
daily) and this window reliably catches the most recent occurrence with comfortable margin.

**Filter `dt.davis.is_duplicate == false`, not on `event.name`.** Recurring problem patterns
fire as a cluster of near-duplicate Davis problems (same root cause, overlapping windows,
different affected-user counts). Without the duplicate filter, `sort ... | limit 1` picks one
arbitrarily and your affected-user count (hence any revenue-impact figure) changes every run.
Davis's own merged/umbrella problem — the one with `is_duplicate == false` — is often named
generically (e.g. "Multiple application problems") rather than the specific symptom name, so
don't additionally filter on `event.name` expecting a descriptive string; you'll exclude the
umbrella record you actually want.

Verify determinism before moving on: run `python tools/preflight.py resolve my-new-demo`
five times in a row and confirm identical `display_id` and `affected_users` each time.

### 3. Write per-beat evidence queries

One `.dql` file per entry in `beats[n].evidence`. Keep each query focused:
- Return ≤8 columns (the engine formats them; walls of JSON are useless)
- Use `| limit 20` as a default unless you need more
- Use `| fields ...` to select exactly what the beat needs

**Use `{{DQL_TIMEFRAME_FROM}}` / `{{DQL_TIMEFRAME_TO}}` for the query window, not
`now()-Nh`.** These resolve to the actual incident window computed by the resolver
(with 15-minute padding either side), so the query always covers the incident regardless
of how long ago it closed. A hardcoded `now()-3h` misses the window entirely once the
problem is more than 3 hours in the past — this was the single most disruptive bug in the
first version of this scenario.

```dql
fetch spans, from: "{{DQL_TIMEFRAME_FROM}}", to: "{{DQL_TIMEFRAME_TO}}"
| filter dt.entity.service == "SERVICE-XXXXXXXXXXXXXXXX"
| ...
```

**Test with the substitution helper, not raw dtctl** — raw `dtctl query --file` won't
substitute the placeholder tokens:

```bash
python tools/preflight.py resolve my-new-demo --write     # writes .demo-state.json once
python tools/preflight.py run-query my-new-demo queries/beat-01-something.dql
```

**DQL must never contain: INGEST, INSERT, UPDATE, DELETE, PUT, WRITE.**
The validator and hook both enforce this, but don't make them work for it.

**Trust nothing from a spec or a past run — verify every field name against the live
Playground before it goes in a query file.** Field names in this environment are not what
generic DQL documentation or intuition suggests. Concrete examples that cost real debugging
time in this scenario, kept here as a warning, not a copy-paste field list (span/session field
names on your data object may differ — verify your own):
- Aggregate fields sometimes use a different name than the plain fetch (spans expose
  `start_time`, not `timestamp` — and `bin(timestamp, 5m)` fails **silently**, returning
  `null` for every bucket rather than an error).
- A field can hold a numeric-looking value as a **string** (`duration: "714000"`) — wrap in
  `toDouble()`/`toLong()` before arithmetic or comparison.
- `round()` takes a **named** second argument: `round(x, decimals: 1)`, not `round(x, 1)`.
- `expand <nested-array-field>` does not flatten the nested object's keys onto the row as
  top-level fields — project them with bracket access: `span.events[some.nested.key]`.
- A `uid`-typed field (e.g. `trace.id`) displays as a plain hex string but filtering it with
  a string literal — `== "..."` or `matchesValue(...)` — silently matches **nothing**, no
  error. Cast first: `filter trace.id == toUid("...")`.
- Run `python tools/validate_scenarios.py --live scenarios/my-new-demo` (see step 8) as the
  actual proof, not a spec read or a single manual test — it executes every query for real.

### 3b. Chained evidence — when one query needs a value from another

Sometimes a beat's real evidence isn't answerable by one independent query — e.g. "show me
the full trace" requires first finding *which* trace (from a failing-spans query), then
fetching everything in it. Declare this in `scenario.yaml` rather than hand-waving it in
prose:

```yaml
evidence:
  - queries/beat-04-failing-spans.dql        # finds failing spans, including a trace_id field
chained_evidence:
  - query: queries/beat-04-trace-waterfall.dql
    depends_on: queries/beat-04-failing-spans.dql   # must be in this beat's own `evidence` list
    extract_field: trace_id                          # field name, read from depends_on's FIRST record
    var_name: TRACE_ID                                # injected as {{TRACE_ID}} in the chained query
```

The chained query file references `{{TRACE_ID}}` like any other placeholder. At runtime the
engine runs the dependency first, reads `extract_field` from its first record, then runs the
chained query with `--var TRACE_ID=<value>` (see `skills/dynatrace-playground/SKILL.md` →
"Chained queries"). `tools/validate_scenarios.py --live` and `tools/capture_fixtures.py` both
resolve this chain automatically — no extra work to keep it covered by the standing gate or
by fixture capture.

A chained query's fixture (`fixtures/beat-04-trace-waterfall.json`, captured the same way as
any other beat fixture) is fully self-contained — in fixture mode the engine calls `run-query`
on it directly with no `--var` needed at all, since the fixture already holds resolved data.

### 4. Write the beats

Each beat in `scenario.yaml` maps to one step in the source guide JSON.
Fields:

- `id` — kebab-case, unique within the scenario
- `source_step_id` — UUID from the source guide's step (provenance)
- `objective` — what the user should understand (not what they should *do*)
- `evidence` — list of `queries/*.dql` paths that produce the evidence
- `reveal` — the insight the beat delivers, narrated by the engine as its own read of the
  evidence — never withheld until the user guesses it (see skills/demo-engine/SKILL.md →
  "The beat loop"). It's the engine's target content, not verbatim dialogue to paste.
- `success` — an *engagement signal* worth watching for, not a gate the user must clear to
  advance. The engine narrates the reveal regardless of what the user says.
- `nudges` (optional) — omit it. The default (narrate directly, no invite) is correct for
  almost every beat; only add `[invite]` if this specific beat genuinely benefits from an
  optional one-turn guess-invite before narrating anyway. See scenario.schema.json.
- `deep_link` — the Dynatrace app URL from the source guide's `action.url`, with `{{PLACEHOLDER}}` variables
- `peak_moment` (optional, bool) — mark your scenario's climax and emotional-payoff beats.
  See "Staging peak moments" below.
- `staging` (optional, string) — delivery instructions for a `peak_moment` beat.

**Write `reveal` as a description of the *shape* of the finding, never specific values.**
Exception messages, commit SHAs, exact line numbers, deployment version strings, and
affected-user counts all rotate between problem cycles on a recurring Playground pattern.
A `reveal` that says *"the exception message is X"* goes stale the very next time the
pattern fires and the engine either contradicts the live data or quietly drops the script.
Write instead: *"the failing spans carry a specific exception message — read it verbatim
from the query result, don't paraphrase it."* The engine reads the actual value at runtime;
your job is describing what kind of finding it is and why it matters, not what it currently says.

### 6. Staging peak moments

Not every beat is equal. If your scenario has a climax (the finding that *is* the answer) or
an emotional payoff (making the human impact concrete), mark it:

```yaml
peak_moment: true
staging: >
  Land the finding on its own line before any commentary. Then explain what kind of
  problem it is. Then give the concrete next action.
```

The engine's default beat rhythm — evidence, ask what the user thinks, then confirm — is
right for ordinary beats but flattens a climax into the same texture as everything else.
`staging` is where you say what should be different about the delivery for this one beat.
See `skills/demo-engine/SKILL.md` → "Peak moments" for the engine's side of this contract.

### 7. Fill in `business_context`

Used by the problem survey — the standing behavior that triggers when the user asks
something like "any problems?" (not `/demo` itself, which only greets — see
`skills/demo-engine/SKILL.md` → "Two-stage entry"). Keep it to what the resolver can
actually supply — don't reference a value no query produces:

```yaml
business_context:
  service_name: "payment service"
  avg_order_value_usd: 87
  user_action: "checkout"
  urgency_phrase: "Every minute this is open costs you customers."
  discovery_hook: >
    The {service_name} is failing for {affected_users} users.
    {user_action} requests are erroring — it's been going on for {duration_min} minutes.
    That's roughly ${revenue_impact} in lost revenue.
```

`affected_users`, `duration_min` (derived from `problem.started`/`ended`), and
`revenue_impact` (`affected_users × avg_order_value_usd`) all come straight from
`tools/preflight.py resolve` — no second query needed. If your problem's Davis record
doesn't carry a clean percentage/rate field (many bury it in unstructured markdown in
`event.description`), don't invent a `{failure_rate}`-style placeholder — describe severity
qualitatively instead ("erroring hard", "failure rate spiked") and let the beat evidence
carry the exact number once the user is inside the investigation.

### 8. Register the scenario

Add an entry to `scenarios/registry.yaml`:

```yaml
- id: my-new-demo
  path: scenarios/my-new-demo
  title: "Your demo title"
  description: "One sentence for /demo list."
  duration_minutes: [8, 15]
  state: draft   # change to 'published' when ready
  tags: [tag1, tag2]
```

Use `state: draft` while building. Draft scenarios are not shown in `/demo`.

### 9. Validate — statically, then live

```bash
python tools/validate_scenarios.py scenarios/my-new-demo          # schema, integrity, DQL lint
python tools/validate_scenarios.py --live scenarios/my-new-demo   # + executes every query
```

Fix every ERROR from the static pass first. Then `--live` actually **runs** the resolver and
every beat's evidence query against the Playground and asserts each returns `ok: true`. This
is the gate that catches a wrong field name or a bad `round()` call before a live session
does — do not skip it and do not consider a scenario done until it passes clean. This is
the standing regression check; wire it into CI for every scenario change.

### 10. Change state to `published` and commit

Update `scenarios/registry.yaml` → `state: published`.

## Naming conventions

- Scenario ID: `[topic]-[variant]`, e.g. `k8s-oom-kill`, `db-slow-query`
- DQL files: `beat-NN-[signal].dql`, e.g. `beat-03-service-failure-rate.dql`

## Conversation design lessons (from the first scenario's test runs)

These generalise beyond payment-failure — read them before writing your beats, not just
your queries. Full detail in `skills/demo-engine/SKILL.md`; summarized here as authoring guidance:

- **Don't write a `reveal` your engine will blurt out before the user has looked at the
  data.** The engine's rule is to ask what the user makes of the evidence before stating the
  reveal — but that only works if your `reveal` text is written as an internal target, not
  as a sentence meant to be read aloud immediately. Write it in third person, as a fact for
  the engine to confirm, not a line of dialogue.
- **A `success` field should describe recognition, not compliance.** "User names the
  failing service" is checkable from what they actually say. "User clicks next" is not
  a comprehension signal at all — don't write success criteria around advancing, only around
  understanding.
- **Deep links matter as much as queries.** Every beat should let the user flip to the real
  Dynatrace UI and see the identical thing they just found in the terminal — that continuity
  is what makes this feel like the same investigation as the video guide, not a chatbot
  imitation of one.

## What the engine guarantees

The engine reads your scenario manifest and runs your queries. It will:
- Never add scenario knowledge it didn't read from your files
- Never modify the Playground (readonly context + hook, enforced at three independent layers)
- Narrate your `reveal` as its own confident read of the evidence, in the same turn — never
  withheld until the user guesses it, and never stated as a flat dead end either; always
  attached to a forward-looking option
- Always offer the deep link from your beat at the end of the beat
- Follow the user wherever they diverge (side quest, front-run, compound question), then
  explicitly re-anchor by naming what's still unknown and proposing the next step back on the path
- Print a DQL snippet and liveness proof stamp (queryId, scannedBytes, ms) to stderr for
  every beat query, and include both in its chat narration so the user can see the query ran
  live against the Playground

What it will not do:
- Guarantee `dtctl exec copilot` output is deterministic (use it for narrative colour fed by
  your own query results via `--context`, not as primary evidence)
- Guarantee entity IDs stay stable if Dynatrace resets the Playground environment
- Parse a failure-rate percentage out of unstructured problem description text for you —
  get exact rates from a real evidence query, not from `event.description`
