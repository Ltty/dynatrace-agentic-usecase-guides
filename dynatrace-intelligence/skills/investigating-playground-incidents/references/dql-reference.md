# DQL Reference — Verified Field Names and Gotchas

Verified live on the Playground. Trust this list over intuition or generic DQL docs.
Token substitution is in `references/session-protocol.md` → "Session state".

## Contents

- [Span field names](#span-field-names-verified-live)
- [Trace ID filtering](#trace-id-filtering-uid-type-gotcha)
- [Event field names](#event-field-names-deployment-events)
- [User session field names](#user-session-field-names-verified-live)
- [Problems field names](#problems-field-names-verified-live)
- [Chained queries](#chained-queries)

---

## Span field names (verified live)

```text
Correct                          Wrong (and why)
start_time                       timestamp → bin(timestamp, 5m) silently returns null buckets
request.is_failed == true        span.status_code == "ERROR" → value is lowercase "error",
                                   and is_failed is the more direct signal
trace.id                         dt.trace_id → doesn't exist on this object
toDouble(duration) / 1000000     duration → it's a numeric STRING, not a number; wrap in toDouble()
round(x, decimals: 1)            round(x, 1) → TOO_MANY_POSITIONAL_PARAMETERS_WITH_OPTIONS error
span.events[exception.message]   exception.message → expand does NOT flatten nested keys onto the row
```

### Aggregating spans by time bucket

```dql
summarize total = count(), failures = countIf(request.is_failed == true),
    by: { bucket = bin(start_time, 5m) }
```

### Accessing exception fields after expand

```dql
| expand span.events
| fields
    exc_type = span.events[exception.type],
    exc_msg  = span.events[exception.message],
    exc_file = span.events[exception.file.full],
    exc_line = span.events[exception.line_number]
```

`expand span.events` does **not** flatten `exception.*` onto the row as top-level fields — the
object stays nested. Project with bracket access.

One incident can carry more than one distinct exception message on the same endpoint. Don't
assume the first row tells the whole story — skim all returned rows.

---

## Trace ID filtering (uid type gotcha)

`trace.id` is a `uid`-typed field, not a plain string — even though it displays as hex.

```text
Wrong — silently matches nothing (no error, no warning):
  filter trace.id == "abc123def456..."
  filter matchesValue(trace.id, "abc123def456...")

Correct:
  filter trace.id == toUid("abc123def456...")
```

Scenario trace queries already use `toUid("{{TRACE_ID}}")` — just substitute the token.

A failing request marks every hop that relays the error as failed, not just the origin.
The origin is the deepest failing service; upstream exceptions usually wrap its message.

For a slowdown, filter on duration, not `request.is_failed` — slow spans are usually not
failed. `sort` a computed `duration_ms` field, since `duration` is a numeric string.

---

## Event field names (deployment events)

ArgoCD deployment events carry `commit` and `gitUrl` directly:

```dql
fetch events
| filter event.type == "CUSTOM_DEPLOYMENT"
| fields timestamp, service = dt.entity.service.name, commit, git_url = gitUrl,
    stage, app, owner, deploy_name = event.name
```

`dt.release_version` / `dt.release_build_version` do **not** exist on this event shape.

GitHub Actions events leave `commit`, `gitUrl`, and `owner` NULL. The commit link is a
markdown URL in `event.description`. Parse it in DQL rather than by eye, and collapse the
repeated re-deploys of one commit:

```dql
| parse event.description, "LD \"(\" LD:git_url \")\""
| parse git_url, "LD \"/commit/\" ALNUM:commit"
| summarize first_deploy = min(timestamp), deploys = count(), by: { commit, git_url }
```

A fix deploy landing during the incident window appears as a second distinct commit —
recognise it as the remediation, not a second regression. Its description may read exactly
like the regression's; tell them apart by timing.

---

## User session field names (verified live)

```dql
fetch user.sessions
| filter error.http_5xx_count > 0
| summarize sessions = count(),
            with_replay = countIf(characteristics.has_replay == true),
    by: { country = geo.country.iso_code }
```

`matchesPhrase(useraction.errors, ...)` — that field doesn't exist.
`session.hasSessionReplay` — use `characteristics.has_replay` instead.
`user.sessions` is NOT tagged with a service entity ID — do not filter on `dt.entity.service`
here. Scoping to the incident timeframe is sufficient since the failure is service-wide during
that window.

**Slowdowns don't show up as 5xx.** Slow requests still return 200, so
`error.http_5xx_count > 0` finds almost nobody. Use per-request RUM data in `user.events`
instead, and join to `user.sessions` for replay:

```dql
fetch user.events
| filter characteristics.has_request == true
| filter dt.rum.user_type == "real_user"          // excludes the synthetic monitor
| filter toDouble(duration) > 1000000000         // duration is nanoseconds
| summarize slow = count(), by: { session_id = dt.rum.session.id, country = geo.country.iso_code }
| lookup [fetch user.sessions | fields session_id = dt.rum.session.id, has_replay = characteristics.has_replay],
    sourceField: session_id, lookupField: session_id, prefix: "s."
```

Give the inner `fetch` in a `lookup` the same `from:`/`to:` as the outer one.

---

## Problems field names (verified live)

```dql
fetch dt.davis.problems
| filter dt.davis.is_duplicate == false
| fields
    problem_id     = event.id,
    display_id,
    status         = event.status,
    started        = event.start,
    ended          = event.end,
    affected_users = dt.davis.affected_users_count,
    owning_team    = team,
    root_cause     = root_cause_entity_name,
    also_affected  = affected_entity_names,
    impact_level   = dt.davis.impact_level,
    description    = event.description
```

Recurring Playground patterns fire as a cluster of near-duplicate Davis problems.
`dt.davis.is_duplicate == false` selects Davis's merged umbrella problem. Its `event.name` is
often generic ("Multiple application problems") — do not additionally filter on `event.name`.

Duration math belongs in DQL: subtracting timestamps gives a duration in nanoseconds, e.g.
`round(toDouble(coalesce(event.end, now()) - event.start) / 60000000000, decimals: 0)` minutes.

---

## Chained queries

A chained query needs a value only a prior query returns (e.g. a trace ID from a failing
span). Run the producer, read the aliased field (`trace_id = trace.id`) from its **first
record**, substitute the token, then run the consumer. Never run the consumer first.
