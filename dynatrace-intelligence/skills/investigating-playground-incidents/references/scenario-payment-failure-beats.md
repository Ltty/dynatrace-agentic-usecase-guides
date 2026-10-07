# Scenario: Payment Failure — Beats

Read once the user has picked a direction from the survey. Resolver, scope, and handoff fields:
`references/scenario-payment-failure.md`.

Reveals describe the *shape* of a finding, never its values. Commit SHA, exception text, line
number, user counts, and timestamps rotate every problem cycle — read them from the live result.

## Contents

- [Beat 1 — The Page](#beat-1--the-page)
- [Beat 2 — Explain with Davis](#beat-2--explain-with-davis)
- [Beat 3 — Service Deep Dive](#beat-3--service-deep-dive)
- [Beat 4 — Failing Traces](#beat-4--failing-traces) (peak)
- [Beat 5 — The Humans](#beat-5--the-humans) (peak)

---

## Beat 1 — The Page

**Objective:** User grasps the blast radius: root-cause service, impacted users, onset, that
checkout is a downstream victim, and which team owns the failing service.

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

Pinned to the resolved problem ID, so the 48h range is safe — the incident window would only
risk cutting off the problem record.

**Reveal:** A sharp failure spike on the payment service's Charge endpoint, affecting a large
user count. Checkout shows as impacted, but `root_cause` points at payment — checkout is
collateral. State the actual numbers, and name `owning_team` explicitly: Dynatrace already
knows who to page.

**Success signal:** User names payment or Charge, or asks to drill into the payment service.

**Deep link:**

```text
https://playground.apps.dynatrace.com/ui/apps/dynatrace.davis.problems/problem/{{PROBLEM_ID}}?from={{TF_FROM_MS}}&to={{TF_TO_MS}}&segments=%5B%7B%22id%22%3A%22Apy24Rcu0cO%22%7D%5D
```

---

## Beat 2 — Explain with Davis

**Objective:** User sees which deployment caused the failure, who shipped it, and a concise
causal explanation naming the commit and the remediation step.

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

**Reveal:** An ArgoCD deployment to astroshop-payment lines up with the onset. Surface three
things explicitly: the `commit` and `git_url` (the change to revert), the `owner` (who to call
first), and the deployment `timestamp`. Give the causal read yourself, from the evidence.

**Success signal:** User asks which commit to revert, who owns it, or for deployment details.

**Deep link:**

```text
https://playground.apps.dynatrace.com/ui/intent/dynatrace.davis.copilot/ask-question#%7B%22prompt%22%3A%22Explain%20what%20happened%20in%20the%20problem%20with%20id%20{{PROBLEM_ID}}%2C%20why%20it%20happened%2C%20and%20actionable%20steps%20to%20remediate%20it.%22%2C%22execute%22%3Atrue%7D
```

---

## Beat 3 — Service Deep Dive

**Objective:** User reads the Charge endpoint's failure rate over time and sees the spike align
with the deployment marker.

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

Returns every deployment in the window — typically the culprit and the fix. `sort desc | limit 1`
would return only the fix.

**Reveal:** A step change from near-zero to a sustained elevated failure rate, with the culprit
deployment inside the same 5-minute bucket as the jump. State the actual before/after
percentages and the bucket timestamp. A later deploy that brings the rate back down is the fix,
not a second regression.

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

**Reveal:** The failing payment spans carry a specific exception — quote it verbatim. It reads
as a business-logic validation regression (rejecting input that should be valid), not an
infrastructure fault. Note the file and line. If more than one distinct message appears, say
so — that's a second finding.

**Success signal:** User identifies the exception or the failing code path.

**Staging:**

1. The exception alone on its own line, before any commentary:
   `Exception: [verbatim exception_msg]`
2. Blank line.
3. What kind of bug it is (validation regression, not infrastructure), with file and line.
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
| summarize
    sessions    = count(),
    with_replay = countIf(characteristics.has_replay == true),
    by: { country = geo.country.iso_code }
| sort sessions desc
```

No `limit` — the total is the sum of `sessions` across all rows. Never present a top-N sum as
the full population, and never call it "affected users" (that's the Davis count).

**Reveal:** Sessions with 5xx errors span many countries, and nearly all have replay. State the
actual total and top countries. The point isn't the number — each failure is a replayable
recording of a real customer hitting a real error.

**Success signal:** User asks about affected users, customer experience, or replay.

**Staging:** After the numbers, make replay concrete: open a recording and watch exactly what
the customer saw and clicked, instead of inferring it from logs. Ask the source guide's
question — "for a front-end problem, what did the user actually see?" — and invite the user to
open a replay via the deep link to check whether the UI showed any feedback on the failed
payment or silently did nothing. The DQL can't answer that; the replay can.

**Deep link:**

```text
https://playground.apps.dynatrace.com/ui/apps/dynatrace.error.inspector/error-explorer?tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}&problemId={{PROBLEM_ID}}&perspective=impact&sort=affected_users%3Adescending
```
