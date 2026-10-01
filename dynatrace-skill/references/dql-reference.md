# DQL Reference — Verified Field Names and Gotchas

All of these were wrong in earlier query drafts and cost real debugging time. Trust this list
over intuition, generic DQL docs, or naming conventions from other data sources.

## Contents

- [Token substitution](#token-substitution)
- [Span field names](#span-field-names)
- [Trace ID filtering](#trace-id-filtering)
- [Event field names](#event-field-names)
- [User session field names](#user-session-field-names)
- [Problems field names](#problems-field-names)
- [Chained queries](#chained-queries)

---

## Token substitution

Beat DQL uses `{{UPPER_SNAKE_CASE}}` placeholder tokens. Substitute before running:

| Token | Value | Format |
|---|---|---|
| `{{PROBLEM_ID}}` | `problem_id` from session state | bare string, used inside `"..."` in DQL |
| `{{DQL_FROM}}` | `window_from` from session state | ISO8601 `YYYY-MM-DDTHH:MM:SSZ`, used inside `"..."` after `from:` |
| `{{DQL_TO}}` | `window_to` from session state | ISO8601 `YYYY-MM-DDTHH:MM:SSZ`, used inside `"..."` after `to:` |
| `{{TF_FROM_MS}}` | `tf_from_ms` from session state | epoch milliseconds (long), used in deep-link URLs |
| `{{TF_TO_MS}}` | `tf_to_ms` from session state | epoch milliseconds (long), used in deep-link URLs |
| `{{TRACE_ID}}` | extracted from beat 4's first query result | runtime-only, substituted inline |

`{{TF_FROM_MS}}` and `{{TF_TO_MS}}` appear only in deep-link URLs, never in DQL.
`{{DQL_FROM}}` and `{{DQL_TO}}` appear only in DQL `from:`/`to:` clauses, never in URLs.
`{{TRACE_ID}}` is a runtime-only token: it's extracted from a live query result, not from
session state.

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

The waterfall query already uses `toUid("{{TRACE_ID}}")` — just substitute the token.

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

GitHub Actions events leave `commit` and `gitUrl` NULL. The commit SHA is embedded in
`event.description` as a markdown URL — include `description = event.description` in the
projection and parse the SHA from the URL in description.

A single regression deploy may appear multiple times (once per affected resource).
A fix deploy landing during the incident window appears as a second distinct description URL —
recognise it as the remediation, not a second regression.

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

Note: the payment-failure pattern fires as a cluster of near-duplicate Davis problems.
`dt.davis.is_duplicate == false` selects Davis's merged umbrella problem. Its `event.name`
is "Multiple application problems" — do not additionally filter on `event.name`.

---

## Chained queries

Beat 4 uses chained evidence: run failing-spans first, extract `trace_id`, substitute into
the waterfall query.

```text
Step 1: run beat 4 failing-spans DQL → read trace_id from first record
Step 2: in the waterfall DQL, replace {{TRACE_ID}} with the actual trace_id value
        (the toUid() cast is already in the query — just substitute the token)
Step 3: run the substituted waterfall DQL
```

The field returned by the failing-spans query is aliased as `trace_id = trace.id`. Read it
from the first record of that query's result set.
