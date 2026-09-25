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
├── fixtures/
│   └── problem.json       # frozen resolver output for offline/fixture mode
└── source/
    └── usecase.json       # original guide JSON (provenance)
```

## Step-by-step

### 1. Copy the template

```bash
cp -r scenarios/_template scenarios/my-new-demo
cd scenarios/my-new-demo
```

Edit `scenario.yaml`. The `id` field must match the directory name.

### 2. Write the resolver query

`queries/find-problem.dql` — a DQL query that returns exactly one row: the most recent
instance of your problem pattern on the Playground.

Required output fields (name them exactly):
- `problem_id` — the `event.id` value
- `display_id` — the `P-XXXXXXX` display identifier
- `status` — `event.status` (`ACTIVE` or `CLOSED`)
- `started` — `event.start`
- `ended` — `event.end` (null if still active)
- `affected_users` — `dt.davis.affected_users_count`
- `root_cause` — `root_cause_entity_name`

Always filter for both `ACTIVE` and recent `CLOSED` (last 24h) — patterns fire on a schedule.
Always `sort timestamp desc | limit 1`.

### 3. Write per-beat evidence queries

One `.dql` file per entry in `beats[n].evidence`. Keep each query focused:
- Return ≤8 columns (the engine formats them; walls of JSON are useless)
- Use `| limit 20` as a default unless you need more
- Use `| fields ...` to select exactly what the beat needs
- Always test the query with: `dtctl query --file queries/my-beat.dql --agent -o json --plain`

**DQL must never contain: INGEST, INSERT, UPDATE, DELETE, PUT, WRITE.**
The validator and hook both enforce this, but don't make them work for it.

### 4. Capture a fixture

Run the resolver against the live Playground and save the output:

```bash
dtctl query --file queries/find-problem.dql --agent -o json --plain --max-field-chars 0 \
  > fixtures/problem.json
```

The fixture must be captured from a real live run — never hand-written.
It must cover the problem occurring (even if `status: CLOSED` by the time you capture it).

### 5. Write the beats

Each beat in `scenario.yaml` maps to one step in the source guide JSON.
Fields:

- `id` — kebab-case, unique within the scenario
- `source_step_id` — UUID from the source guide's step (provenance)
- `objective` — what the user should understand (not what they should *do*)
- `evidence` — list of `queries/*.dql` paths that produce the evidence
- `reveal` — the insight the beat delivers (engine's target; not shown verbatim to user)
- `success` — what user output signals comprehension
- `nudges` — always: `[open, narrowing, concrete, do-it-for-them]`
- `deep_link` — the Dynatrace app URL from the source guide's `action.url`, with `{{PLACEHOLDER}}` variables

### 6. Fill in `business_context`

Used by the ambient discovery flow (`/demo` without arguments):

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

### 7. Register the scenario

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

### 8. Validate

```bash
python tools/validate_scenarios.py scenarios/my-new-demo
```

Fix every ERROR. WARN items are informational.

### 9. Run in fixture mode

```bash
python tools/preflight.py resolve my-new-demo
```

Should print state JSON with `"mode": "live"` or `"mode": "fixture"`.
In fixture mode the demo still runs — verify the narrative makes sense on recorded data.

### 10. Change state to `published` and commit

Update `scenarios/registry.yaml` → `state: published`.

## Naming conventions

- Scenario ID: `[topic]-[variant]`, e.g. `k8s-oom-kill`, `db-slow-query`
- DQL files: `beat-NN-[signal].dql`, e.g. `beat-03-service-failure-rate.dql`
- Fixture files: `problem.json` (resolver output) + optional `beat-NN.json` for offline beat evidence

## What the engine guarantees

The engine reads your scenario manifest and runs your queries. It will:
- Never add scenario knowledge it didn't read from your files
- Never modify the Playground (readonly context + hook)
- Always offer the deep link from your beat at the end of the beat
- Follow the nudge ladder if the user stalls
- Fall back to your fixtures if the live problem is not in the last 24h

What it will not do:
- Guarantee `dtctl exec copilot` output is deterministic (use it for narrative colour, not as primary evidence)
- Guarantee entity IDs stay stable if Dynatrace resets the Playground environment
