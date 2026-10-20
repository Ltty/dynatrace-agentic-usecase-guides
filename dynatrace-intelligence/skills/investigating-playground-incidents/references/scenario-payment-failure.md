# Scenario: Payment Failure — Context and Beats

Read once the user has picked a scenario. The survey query and the discovery hooks are in `references/session-protocol.md`.
Reveals describe the *shape* of a finding, never its values. Commit SHA, exception text, line number, user counts, and timestamps rotate every problem cycle — read them from the live result.

## Contents

- [Business context](#business-context)
- [Scope](#scope)
- [Handoff fields](#handoff-fields)
- [Beat 1 — The Page](#beat-1--the-page)
- [Beat 2 — The Change](#beat-2--the-change)
- [Beat 3 — Service Deep Dive](#beat-3--service-deep-dive)
- [Beat 4 — Failing Traces](#beat-4--failing-traces) (peak)
- [Beat 5 — The Humans](#beat-5--the-humans) (peak)

---

## Business context

| Field | Value |
|---|---|
| `service_name` | "payment service" |
| `avg_order_value_usd` | 87 (also in the survey query's `revenue_usd`) |
| `symptom` | "card payments failing at checkout" |
| `pull_line` | "Pulling the deployments, the failure rate, the failing requests and the affected sessions together." |

The failure rate comes from the service deep dive (beat 3), never from the problem record.

## Scope

**Data objects:** `dt.davis.problems`, `spans`, `logs`, `events`, `user.sessions`, `entities`

**Stable IDs** (Playground entities):

| Name | ID |
|---|---|
| astroshop-payment (root cause) | `SERVICE-531CE26849E95EC1` |
| astroshop-checkout (listed as affected) | `SERVICE-5ACC60E0079F8E6D` |
| Charge endpoint | `endpoint.name == "Charge"` |
| Segment (problem deep link) | `Apy24Rcu0cO` |

## Handoff fields

Where the values for a remediation handoff come from. Three populations coexist — always say
which one a number counts.

| Value | Source |
|---|---|
| `owning_team` | Survey row (beat 1 shows it); who to page first |
| `Goes to` | `owning_team` |
| `commit`, `git_url`, `owner` | Beat 2 — The Change; `owner` is who shipped it. If it differs from `owning_team`, list both and say which is which |
| Affected users (problem record) | survey row `affected_users` |
| Sessions with server errors (5xx) | Beat 5 — sum of `sessions` across all countries |
| Per-country sessions | Beat 5 — individual rows |
| Session replay link | Beat 5 deep link |

---

## Beat 1 — The Page

**Objective:** User grasps the blast radius: root-cause service, impacted users, onset, that
checkout is listed as affected, and which team owns the failing service.

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
    description   = event.description,
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

**Reveal:** The problem record names the payment service as root cause and counts a large
number of affected users; quote the failing endpoint from `description`.
Checkout shows as impacted, but `root_cause` points at payment — checkout is listed as affected,
not named as the cause. This result has no call direction, so don't say
checkout calls payment until the trace in beat 4 shows it. State the actual numbers, and name
`owning_team` explicitly: Dynatrace already knows who to page.

**Success signal:** User names payment or Charge, or asks to drill into the payment service.

**Deep link:**

```text
https://playground.apps.dynatrace.com/ui/apps/dynatrace.davis.problems/problem/{{PROBLEM_ID}}?from={{TF_FROM_MS}}&to={{TF_TO_MS}}&segments=%5B%7B%22id%22%3A%22Apy24Rcu0cO%22%7D%5D
```

---

## Beat 2 — The Change

**Objective:** User sees which deployment lines up with the start of the failure, who shipped
it, and a concise read of the timing naming the commit and who it goes to.

**Evidence DQL:**

```dql
fetch events, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter event.type == "CUSTOM_DEPLOYMENT"
| filter in(dt.entity.service, "SERVICE-531CE26849E95EC1", "SERVICE-5ACC60E0079F8E6D")
| summarize
    first_deploy = min(timestamp),
    deploys      = count(),
    services     = collectDistinct(dt.entity.service.name),
    by: { commit, git_url = gitUrl, owner, stage, app }
| sort first_deploy asc
| fieldsAdd deploy_before_problem_min = round(toDouble(toTimestamp("{{STARTED}}") - first_deploy) / 60000000000, decimals: 1), queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

One row per commit. ArgoCD syncs one commit many times, once per resource; `deploys` counts
those syncs and `first_deploy` is when the change actually landed. A sync event is recorded when
the sync completes, so the first failures can appear seconds before `first_deploy`. Onset within
a minute of it is the same change: say so plainly, without hedging over the seconds.

**Reveal:** Typically two rows. The first commit's `first_deploy` falls at or just before the
problem `started` (beat 1) — the change that lines up with the start. The second lands shortly before the
problem ended and is not a second regression; whether the failures stop around it is for beat 3,
and what it changed is in the diff, not the telemetry. Surface explicitly: the culprit
`commit` and `git_url`, the `owner` (who to call first), and the gap
between `first_deploy` and the problem start (`deploy_before_problem_min`; negative means the deploy came after). Give the read yourself, from the timing.

**Success signal:** User asks which commit to revert, who owns it, or for deployment details.

**Deep link:**

```text
https://playground.apps.dynatrace.com/ui/intent/dynatrace.davis.copilot/ask-question#%7B%22prompt%22%3A%22Explain%20what%20happened%20in%20the%20problem%20with%20id%20{{PROBLEM_ID}}%2C%20why%20it%20happened%2C%20and%20actionable%20steps%20to%20remediate%20it.%22%2C%22execute%22%3Atrue%7D
```

---

## Beat 3 — Service Deep Dive

**Objective:** User reads the Charge endpoint's failure rate over time and sees the spike align
with the deployment marker.

**Fold in on a jump:** if the user jumps to beat 4, run the failure-rate query below in the same
turn and show the rise in one line. It is the evidence that ties the deploy to the
failures.

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
| fields bucket, total, failures, failure_rate_pct, queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

**Evidence DQL — deployment marker:**

```dql
fetch events, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter event.type == "CUSTOM_DEPLOYMENT"
| filter dt.entity.service == "SERVICE-531CE26849E95EC1"
| summarize timestamp = min(timestamp), by: { commit }
| sort timestamp asc
```

Skip this query when beat 2 has run in this conversation: its rows already give each commit's
first deploy.

**Reveal:** A rise from near-zero to an elevated failure rate that stays elevated until the
later deploy. It can ramp over several buckets rather than step. The first failures fall in or
just before the bucket that holds the culprit's `first_deploy`. Read it from the rows: a bucket
that holds the deploy can still show a low rate. State the actual before/after percentages, with
failures and totals, and the bucket timestamps. A later deploy after which the rate falls back is
not a second regression: the failures stopping around it reads as the fix landing, though what it
changed is in the diff, not the telemetry.

**Success signal:** User connects the deploy to the spike, or asks for the failing requests.

**Deep link:**

```text
https://playground.apps.dynatrace.com/ui/apps/dynatrace.services/explorer/services?detailsId=SERVICE-531CE26849E95EC1&perspective=performance&problemId={{PROBLEM_ID}}&tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}
```

---

## Beat 4 — Failing Traces

**`peak_moment: true`**

**Objective:** User sees the exact exception, source file, and line, and the whole request it
broke: where the failure originates, how it propagates upstream, and which calls stayed clean.

**Evidence DQL — exceptions across the whole window (run first):**

```dql
fetch spans, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter dt.entity.service == "SERVICE-531CE26849E95EC1"
| filter request.is_failed == true
| expand span.events
| fieldsAdd
    exception_type = span.events[exception.type],
    exception_msg  = span.events[exception.message],
    exception_file = span.events[exception.file.full],
    exception_line = span.events[exception.line_number]
| filter isNotNull(exception_msg)
| sort start_time asc
| summarize
    failed_spans = count(),
    first_seen   = min(start_time),
    last_seen    = max(start_time),
    trace_id     = takeFirst(trace.id),
    by: { exception_type, exception_msg, exception_file, exception_line }
| sort first_seen asc
| fieldsAdd detected_after_min = round(toDouble(toTimestamp("{{STARTED}}") - first_seen) / 60000000000, decimals: 1), queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

One row per distinct exception, oldest first. `trace_id` is the earliest failing trace for that
message, so the trace below shows the failure as it started.

**Evidence DQL — per-service trace summary (chained; substitute `trace_id` from the first
record above):**

```dql
fetch spans, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter trace.id == toUid("{{TRACE_ID}}")
| summarize
    spans       = count(),
    failed      = countIf(request.is_failed == true),
    first_start = min(start_time),
    max_ms      = round(max(toDouble(duration)) / 1000000, decimals: 1),
    by: { service = dt.service.name }
| sort first_start asc
```

One row per service in call order. Failure propagates: the ingress, frontend, and checkout rows
also show `failed > 0` because they return the error payment raised — checkout's own exception
wraps payment's message. Payment is the origin; the rows with `failed == 0` are the clean calls.

**Reveal:** The failing payment spans carry a specific exception — quote it verbatim. Say what
the data shows: the service itself raises it, at the file and line returned, with a message that
names the rejected input — not an infrastructure error. Whether the rejection was intended is
the owning team's call, not something the telemetry shows. Note the file and line, `failed_spans` (a span count, not users), and how
`first_seen` lines up with the culprit's `first_deploy` (seconds before it is normal — see
beat 2). Also state when the problem opened relative to the first failure: the problem's
`started` against `first_seen`, both times and `detected_after_min` (the gap, from the first row), said plainly, with no judgement on the gap. If more than one distinct message
appears, say so — that's a second finding; one first seen after the later deploy is a separate finding, reported as returned.

**Success signal:** User identifies the exception or the failing code path.

**Staging:**

1. The exception alone on its own line, before any commentary:
   `Exception: [verbatim exception_msg]`
2. Blank line.
3. What the exception says and where it is raised (file and line) — an error the service
   itself raises, not an infrastructure fault.
4. The trace as a short chain plus one summary line:

   ```text
   ingress → frontend → checkout → payment   failed (origin: payment)
   checkout also called: cart, catalog, currency, shipping, quote — all clean
   ```

   Build both lines from the summary rows; list the clean services the query actually returned.
5. State it plainly: one call originates the failure, everything it touches upstream just
   relays it, and every sibling call was clean.

**Deep link:**

```text
https://playground.apps.dynatrace.com/ui/apps/dynatrace.distributedtracing/explorer?filter=request.is_failed+%3D+Failure+AND+dt.smartscape.service+%3D+SERVICE-531CE26849E95EC1+AND+endpoint.name+%3D+Charge&tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}
```

---

## Beat 5 — The Humans

**`peak_moment: true`**

**Objective:** User understands the real-world impact: how many sessions hit errors, where, and
that session replay shows exactly what a customer saw.

**Evidence DQL:**

```dql
fetch user.sessions, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter error.http_5xx_count > 0
| summarize sessions = count(), with_replay = countIf(characteristics.has_replay == true), by: { country = geo.country.iso_code }
| sort sessions desc
| summarize rows = collectArray(record(country, sessions, with_replay)), total_sessions = sum(sessions),
    total_with_replay = sum(with_replay), no_country = sum(if(isNull(country), sessions)),
    countries = countDistinct(country), rows_returned = count()
| fieldsAdd top_rows = arraySlice(rows, from: 0, to: 5)
| fields total_sessions, total_with_replay, countries, no_country, rows_returned, top_rows, queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

The query sums in DQL: `total_sessions` is the whole population, `no_country` the part of it with no country, `countries` the
distinct countries, `rows_returned` the rows before the top five. Never present `top_rows` as the full population, and never
call it "affected users" (that's the problem record's count). `elapsed_min` is for the close, not for the table.

**Reveal:** Sessions with 5xx errors span many countries, and nearly all have replay. State
`total_sessions`, `countries` and `no_country` (a row with no country is reported as exactly that, never folded into a
country), and the `top_rows`. Don't add geography the
rows don't contain. The point isn't the number — each failure is a replayable
recording of a real customer hitting a real error.

**Success signal:** User asks about affected users, customer experience, or replay.

**Staging:** After the numbers, make replay concrete with one customer: open one recording and watch exactly what
that customer saw and clicked at the failed payment, instead of inferring it from logs. What the UI showed at the
failed payment, any feedback or silence, is not in the DQL result; the replay shows it, via the deep link.

**Deep link:**

```text
https://playground.apps.dynatrace.com/ui/apps/dynatrace.error.inspector/error-explorer?tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}&problemId={{PROBLEM_ID}}&perspective=impact&sort=affected_users%3Adescending
```
