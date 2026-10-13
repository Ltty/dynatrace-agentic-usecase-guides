# DQL Reference — Verified Field Names and Gotchas

Verified live on the Playground. Trust this list over intuition or generic DQL docs.
Token substitution is in `references/session-protocol.md` → "Session state".

## Contents

- [Span field names](#span-field-names-verified-live)
- [Trace ID filtering](#trace-id-filtering-uid-type-gotcha)
- [Event field names](#event-field-names-deployment-events)
- [User session field names](#user-session-field-names-verified-live)
- [Metrics](#metrics-timeseries-verified-live)
- [Logs](#logs-verified-live)
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

One incident can carry more than one distinct exception message on the same endpoint: the
result has one row per message.

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
`commit` is the short git SHA; `gitUrl` links straight to the commit.

GitHub Actions events leave `commit`, `gitUrl`, and `owner` NULL. The commit link is a
markdown URL in `event.description` — a null `commit` doesn't mean the trail is cold. Parse it
in DQL rather than by eye, and collapse the repeated re-deploys of one commit:

```dql
| parse event.description, "LD \"(\" LD:git_url \")\""
| parse git_url, "LD \"/commit/\" ALNUM:commit"
| summarize first_deploy = min(timestamp), deploys = count(), by: { commit, git_url }
```

A second deploy landing during the incident window appears as a second distinct commit. Its
description may read exactly like the first one's; only the timestamps tell them apart.

---

## User session field names (verified live)

```dql
fetch user.sessions
| filter error.http_5xx_count > 0
| summarize sessions = count(),
            with_replay = countIf(characteristics.has_replay == true),
    by: { country = geo.country.iso_code }
```

Sessions expose `start_time`, not `startTime`.
`matchesPhrase(useraction.errors, ...)` — that field doesn't exist.
`session.hasSessionReplay` — use `characteristics.has_replay` instead.
`user.sessions` is NOT tagged with a service entity ID — do not filter on `dt.entity.service`
here. Scope by the incident timeframe, and by country, session or user-event fields.

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

## Metrics (timeseries, verified live)

A `by` field the metric doesn't carry does **not** fail: every series aggregates into one tenant-wide row, which
looks like a result. Check that the by-field comes back as a column. On the host metrics:

- `dt.host.cpu.usage` and `dt.host.cpu.iowait` (percent) are split by `host.name`, **not** `dt.entity.host`.
- Disk metrics are split by `dt.entity.disk`. `dt.host.disk.free` is the free **percent**, `dt.host.disk.used.percent`
  the used percent, `dt.host.disk.avail` the available **bytes**. `dt.host.disk.avail.percent` does not exist; a metric
  that doesn't exist also returns zero series, not an error.
- Filter inside the command (`timeseries ..., filter: host.name == "x"`) rather than after it.
- Summarise a long series in DQL instead of reading it: `fieldsAdd lo = arrayMin(v), avg = arrayAvg(v), hi = arrayMax(v)`
  gives one row for a window of any length. The `interval` field says how long each bucket is.

---

## Logs (verified live)

Logs are **not** tagged with the service ID from spans or problems: filtering on
`dt.entity.service == "SERVICE-…"` returns nothing. Scope by container and a narrow window,
and aggregate before listing rows — an unscoped `or` of keywords returns unrelated noise:

```dql
fetch logs, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter k8s.container.name == "payment"
| summarize lines = count(), by: { loglevel }
```

Then list the few rows you need (`| filter loglevel == "ERROR" | sort timestamp asc | limit 5
| fields timestamp, content`). `content` is the raw line; on payment it is JSON carrying
`dt.trace_id`, which links a log line to a trace.

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

A problem is stored once per update, so one problem has several rows with different `timestamp`s, and not every
row carries every field. `root_cause.smartscape_entity` (a record with `id`, `name`, `type`) exists only on some
rows; read it with bracket access, `root_cause.smartscape_entity[id]`. That id is smartscape-typed: compare
`toString(x) == "DISK-…"`, or the filter silently matches nothing (the same trap as `trace.id`). Events carry
`host.name`, not `dt.entity.host`.

Recurring Playground patterns fire as a cluster of near-duplicate problems.
`dt.davis.is_duplicate == false` selects the merged umbrella problem. Its `event.name` is
often generic ("Multiple application problems") — do not additionally filter on `event.name`.

Duration math belongs in DQL: subtracting timestamps gives a duration in nanoseconds, e.g.
`round(toDouble(coalesce(event.end, now()) - event.start) / 60000000000, decimals: 0)` minutes.

---

## Chained queries

A chained query needs a value only a prior query returns (e.g. a trace ID from a failing
span). Run the producer, read the aliased field (`trace_id = trace.id`) from its **first
record**, substitute the token, then run the consumer. Never run the consumer first.
