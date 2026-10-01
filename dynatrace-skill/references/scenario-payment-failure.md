# Scenario: Payment Failure

**Source guide:** `96474054-260e-4b94-805e-d10fcbfb8e7a`
**Duration:** 8–15 minutes

## Contents

- [Persona](#persona)
- [Business context](#business-context)
- [Scope](#scope)
- [Resolver DQL](#resolver-dql)
- [Beats](#beats)

---

> **NOTE ON REVEALS:** Every reveal in this file describes the *shape* of a finding, never its
> current values. The payment-failure pattern is recurring — commit SHA, exception message, line
> number, affected-user count, and deployment timestamp all rotate between problem cycles.
> The agent reads actual values from live query results at runtime. Never copy a specific value
> from a past run into what you tell the user.

---

## Persona

**Role:** On-call SRE pairing with the user. Matches the engine default persona.

**Register:** Calm, concrete, mild time pressure. Speaks in facts and next steps. Never
breathless or panicked. Uses "we" — this is a pair exercise. Keeps responses tight: 2–4
sentences to set a scene, one open question.

---

## Business context

| Field | Value |
|---|---|
| `service_name` | "payment service" |
| `avg_order_value_usd` | 87 |
| `user_action` | "checkout" |
| `urgency_phrase` | "Every minute this is open costs your team customers and revenue." |

**Discovery hook template** (single-brace tokens, filled from session state at survey time):

```
The {service_name} is failing for {affected_users} users. Checkout requests
are erroring hard — it's been going on for {duration_min} minutes. That's
roughly ${revenue_impact} in abandoned carts.
```

There is deliberately no `{failure_rate}` placeholder: the resolver's problem record buries
the failure percentage in unstructured markdown in `event.description`, which is too fragile to
parse reliably. Use "erroring hard" qualitatively; the exact rate comes from beat 3's evidence.

---

## Scope

**Services:**
- `SERVICE-531CE26849E95EC1` — astroshop-payment (root cause)
- `SERVICE-5ACC60E0079F8E6D` — astroshop-checkout (downstream impact)

**Data objects in scope:** `dt.davis.problems`, `spans`, `logs`, `events`, `user.sessions`,
`entities`

**Stable entity IDs** — safe to hardcode because they identify Playground service entities,
not any rotating incident artifact:

| Name | ID |
|---|---|
| astroshop-payment | `SERVICE-531CE26849E95EC1` |
| astroshop-checkout | `SERVICE-5ACC60E0079F8E6D` |
| Charge endpoint | filter `endpoint.name == "Charge"` |
| Segment | `Apy24Rcu0cO` (beat 1 deep link) |

---

## Resolver DQL

Run once at session start (silently, before any in-character response that needs problem data).
See `references/session-protocol.md` → "Resolver contract" for the field contract and fallback
logic. Both queries below must return all required fields, including `window_from`, `window_to`,
`tf_from_ms`, and `tf_to_ms`.

### Primary resolver

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter root_cause_entity_id == "SERVICE-531CE26849E95EC1"
| filter dt.davis.is_duplicate == false
| sort timestamp desc
| limit 1
| fieldsAdd window_from = event.start - 15m,
            window_to   = coalesce(event.end, now()) + 15m
| fieldsAdd tf_from_ms  = toLong(window_from) / 1000000,
            tf_to_ms    = toLong(window_to) / 1000000
| fields problem_id     = event.id,
         display_id,
         status         = event.status,
         started        = event.start,
         ended          = event.end,
         affected_users = dt.davis.affected_users_count,
         root_cause     = root_cause_entity_name,
         description    = event.description,
         window_from,
         window_to,
         tf_from_ms,
         tf_to_ms
```

**Why `is_duplicate == false`:** the payment-failure pattern fires as a cluster of near-duplicate
Davis problems. Davis's merged umbrella problem has `is_duplicate == false`. Its `event.name` is
"Multiple application problems" — do not additionally filter on `event.name`.

**`toLong(window_from) / 1000000`:** DQL timestamps are stored as nanoseconds since epoch.
Dividing by 1,000,000 converts to milliseconds. The result is stored as `tf_from_ms` and
`tf_to_ms` for use in deep-link URLs via `{{TF_FROM_MS}}` and `{{TF_TO_MS}}`.

### Fallback resolver

Run only if the primary returns zero rows:

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter root_cause_entity_id == "SERVICE-531CE26849E95EC1"
| sort dt.davis.affected_users_count desc, timestamp desc
| limit 1
| fieldsAdd window_from = event.start - 15m,
            window_to   = coalesce(event.end, now()) + 15m
| fieldsAdd tf_from_ms  = toLong(window_from) / 1000000,
            tf_to_ms    = toLong(window_to) / 1000000
| fields problem_id     = event.id,
         display_id,
         status         = event.status,
         started        = event.start,
         ended          = event.end,
         affected_users = dt.davis.affected_users_count,
         root_cause     = root_cause_entity_name,
         window_from,
         window_to,
         tf_from_ms,
         tf_to_ms
```

If both return zero rows: mode is `no_live_problem`. Stay in character:
"Environment looks clean — nothing I'd page on right now. Check back in a bit if you want to
catch it live." No implementation details, no slash commands.

---

## Beats

---

### Beat 1 — The Page

**Objective:** User grasps the blast radius: which service is the root cause, how many users
are impacted, when it started, that checkout is a downstream victim not the source, and which
team owns the failing service.

**Evidence DQL:**

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter event.id == "{{PROBLEM_ID}}"
| fields
    display_id,
    status        = event.status,
    started       = event.start,
    affected_users = dt.davis.affected_users_count,
    root_cause    = root_cause_entity_name,
    owning_team   = team,
    also_affected = affected_entity_names,
    impact_level  = dt.davis.impact_level,
    description   = event.description
```

This query uses `now()-48h` (not `{{DQL_FROM}}`/`{{DQL_TO}}`) because it is pinned to the
exact problem ID resolved at session start — the incident window would be unnecessarily
restrictive here.

**Reveal:** A sharp failure-rate spike on the payment service's Charge endpoint, started
recently, affecting a large user count. Checkout shows up as impacted too, but the root-cause
field points at payment — checkout is collateral, not the cause. State the actual numbers from
the query result. Also state the owning team by name (`owning_team` field) — Dynatrace already
knows who to page, no separate lookup needed. Surface the team name explicitly; don't treat it
as a footnote.

**Success signal:** User names "payment" or "Charge" as the failing service/endpoint, OR asks
to drill into the payment service.

**Deep link:**
```
https://playground.apps.dynatrace.com/ui/apps/dynatrace.davis.problems/problem/{{PROBLEM_ID}}?from={{TF_FROM_MS}}&to={{TF_TO_MS}}&segments=%5B%7B"id"%3A"Apy24Rcu0cO"%7D%5D
```

---

### Beat 2 — Explain with Davis

**Objective:** User sees which deployment caused the failure, who owns it, and gets a concise
causal explanation that names the commit and the remediation step.

**Evidence DQL:**

```dql
fetch events, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter event.type == "CUSTOM_DEPLOYMENT"
| filter in(dt.entity.service, "SERVICE-531CE26849E95EC1", "SERVICE-5ACC60E0079F8E6D")
| sort timestamp desc
| limit 5
| fields
    timestamp,
    service     = dt.entity.service.name,
    commit,
    git_url     = gitUrl,
    stage,
    app,
    owner,
    deploy_name = event.name
```

**Reveal:** A recent deployment to astroshop-payment (an ArgoCD sync carrying a specific git
commit SHA) lines up with the failure onset. Extract and surface three things explicitly from
the query result:
1. The commit SHA and git_url — that's the exact change that needs reverting.
2. The owner field — that's the team who shipped it and the first call to make.
3. The deployment timestamp, to confirm the timing.

Surface the owner before any Davis CoPilot call — this is the answer to "who do I wake up
right now," not a footnote to the technical diagnosis.

**Note on Davis CoPilot:** If available in this runtime (and non-circular — you may already
*be* CoPilot), call it after you have the commit, owner, and timestamp. Feed those values as
context. If unavailable or circular, give the causal read yourself from the evidence.

**Success signal:** User asks which commit to revert, asks who owns the service/deployment, or
asks for the deployment details.

**Deep link:**
```
https://playground.apps.dynatrace.com/ui/intent/dynatrace.davis.copilot/ask-question#%7B%22prompt%22%3A%22Explain%20what%20happened%20in%20the%20problem%20with%20id%20{{PROBLEM_ID}}%2C%20why%20it%20happened%2C%20and%20actionable%20steps%20to%20remediate%20it.%22%2C%22execute%22%3Atrue%7D
```

---

### Beat 3 — Service Deep Dive

**Objective:** User can read the service performance data: failure rate on the Charge endpoint
over time, the deployment marker, and that the failure rate spike aligns exactly with the
deployment timestamp.

**Evidence DQL — failure rate over time:**

```dql
fetch spans, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter dt.entity.service == "SERVICE-531CE26849E95EC1"
| filter endpoint.name == "Charge"
| summarize
    total    = count(),
    failures = countIf(request.is_failed == true),
    by: { bucket = bin(start_time, 5m) }
| fieldsAdd failure_rate_pct = round(toDouble(failures) / toDouble(total) * 100, decimals: 1)
| sort bucket asc
| fields bucket, total, failures, failure_rate_pct
```

**Evidence DQL — deployment marker:**

```dql
fetch events, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter event.type == "CUSTOM_DEPLOYMENT"
| filter dt.entity.service == "SERVICE-531CE26849E95EC1"
| summarize timestamp = min(timestamp), by: { commit }
| sort timestamp asc
```

This query returns **all deployments** in the incident window. A `limit 1` with `sort desc`
would return only the fix/rollback deploy, missing the culprit deploy that aligns with the spike
onset. Typically 2 rows: culprit + fix.

**Reveal:** The failure-rate time series shows a step change from near-zero to a sustained
elevated rate, and the deployment marker timestamp lands inside the same 5-minute bucket as the
jump. That alignment is the smoking gun — state the actual before/after percentages and the
bucket timestamp from the two queries, not approximations.

**Success signal:** User connects the deployment timestamp to the failure rate spike, or asks
to see the traces/logs for the failing requests.

**Deep link:**
```
https://playground.apps.dynatrace.com/ui/apps/dynatrace.services/explorer/services?detailsId=SERVICE-531CE26849E95EC1&perspective=performance&problemId={{PROBLEM_ID}}&tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}
```

---

### Beat 4 — Failing Traces

**`peak_moment: true`**

**Objective:** User sees the FULL distributed trace end-to-end — not just the one failing
payment span — so it's visible that the frontend and checkout legs of the request were clean,
and the failure is isolated to the payment call: the exact exception message, source file, and
line number that identifies the faulty code path.

**Evidence DQL — failing spans (run first):**

```dql
fetch spans, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter dt.entity.service == "SERVICE-531CE26849E95EC1"
| filter request.is_failed == true
| sort start_time desc
| limit 5
| expand span.events
| fields
    start_time,
    trace_id       = trace.id,
    exception_type = span.events[exception.type],
    exception_msg  = span.events[exception.message],
    exception_file = span.events[exception.file.full],
    exception_line = span.events[exception.line_number],
    duration_ms    = round(toDouble(duration) / 1000000, decimals: 0)
```

Extract `trace_id` from the **first record** of this result. That value substitutes into
`{{TRACE_ID}}` in the waterfall query below.

**Evidence DQL — trace waterfall (chained, run after extracting trace_id):**

```dql
fetch spans, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter trace.id == toUid("{{TRACE_ID}}")
| sort start_time asc
| fields
    span.id,
    span.parent_id,
    start_time,
    service     = dt.service.name,
    span_name   = span.name,
    duration_ms = round(toDouble(duration) / 1000000, decimals: 2),
    failed      = request.is_failed,
    status      = span.status_code
```

`toUid()` is required — see `references/dql-reference.md` → "Trace ID filtering".
For condensing the waterfall into a readable 3–5 row output, follow `references/waterfall-rendering.md`.

**Reveal:** The failing spans carry a specific exception message from the payment charge code —
read it verbatim from the query result, do not paraphrase it. It reads as a business-logic
validation regression (rejecting input that should be valid), not an infrastructure fault.
Note the exact file and line number. If more than one distinct exception message appears across
the failing spans, say so — that's a second finding, not noise to filter out.

Then: the waterfall shows the whole request, one row per service hop, in call order. Everything
before payment is clean. Payment is the one hop that fails. State this explicitly.

**Success signal:** User identifies the exception message or the failing code path from the
trace data.

**Staging:**
This is the climax of the investigation. Sequence:
1. Land the exception message alone on its own line before any other commentary:
   ```
   Exception: [verbatim exception_msg from failing-spans query]
   ```
2. Blank line (pause).
3. Explain what kind of bug it is (business-logic validation regression, not infrastructure).
   Note the file and line number verbatim from the query result.
4. Then show the condensed waterfall (3–4 rows, clean siblings collapsed to one line).
5. State explicitly: everything before payment was clean. The fault is fully isolated to one
   call. Don't just show the table and move on.

Don't compress this into the flat evidence-table rhythm. This beat is the payoff.

**Deep link:**
```
https://playground.apps.dynatrace.com/ui/apps/dynatrace.distributedtracing/explorer?filter=request.is_failed+%3D+Failure+AND+dt.smartscape.service+%3D+SERVICE-531CE26849E95EC1+AND+endpoint.name+%3D+Charge&tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}
```

---

### Beat 5 — The Humans

**`peak_moment: true`**

**Objective:** User understands the real-world impact: how many real user sessions were affected,
where in the world they were, and that session replay exists to show the exact UX a customer hit.

**Evidence DQL:**

```dql
fetch user.sessions, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter error.http_5xx_count > 0
| summarize
    sessions    = count(),
    with_replay = countIf(characteristics.has_replay == true),
    by: { country = geo.country.iso_code }
| sort sessions desc
```

No `limit` — return all countries. The total sessions count is the sum of the `sessions` column.
Never present a top-N sum as the full population.

**Reveal:** Sessions with 5xx errors span many countries, and nearly all of them have session
replay available. State the actual session count and top countries from the query result. The
point isn't the number — it's that every one of those failures is a replayable recording of a
real customer hitting a real error.

**Success signal:** User asks about affected users, the customer experience, or session replay.

**Staging:**
This is the emotional payoff, not another data table. After the numbers, make concrete what
"session replay" means: an SRE can open a recording and watch exactly what that customer saw and
clicked, not infer it from logs. Pose the genuine question the source guide asks here: "for a
front-end problem, what did the user actually see?" Invite the user to open one replay via the
deep link and check for themselves whether the UI gave any visual feedback on the failed payment,
or whether it silently did nothing. This is a genuine open question the DQL evidence can't answer
by itself — frame it as exactly the kind of thing you'd pull up the replay to check.

**Deep link:**
```
https://playground.apps.dynatrace.com/ui/apps/dynatrace.error.inspector/error-explorer?tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}&problemId={{PROBLEM_ID}}&perspective=impact&sort=affected_users%3Adescending
```
