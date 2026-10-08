# Scenario: Broken Images (Slowdown) — Resolver and Context

Read at survey time. The beats live in `references/scenario-broken-images-beats.md`; read that
only once the user picks a direction.

**Duration:** 8–15 minutes

## Contents

- [Persona](#persona)
- [Business context](#business-context)
- [Scope](#scope)
- [Handoff fields](#handoff-fields)
- [Resolver DQL](#resolver-dql)

## Persona

On-call SRE pairing with the user. Calm, concrete, mild time pressure. Speaks in facts and next
steps. Never breathless. Uses "we".

## Business context

| Field | Value |
|---|---|
| `service_name` | "image service" |
| `user_action` | "browse products" |
| `symptom` | "product images loading slowly" |
| `payoff` | "Without correlated traces, deployment markers, and session replay, this is hours of grepping logs and guessing which of several recent deploys is responsible." |

No `avg_order_value_usd` is defined for this scenario — omit the revenue figure in the survey.

**Discovery hook template** (single-brace tokens, filled from session state at survey time):

```text
The {service_name} is degraded — product images are slow for {affected_users} users, and it's
been going on for {duration_min} minutes. State response times only if `description` gives them.
```

This is a **slowdown, not an outage**: image requests still return 200, just seconds late.
Don't call it failing or erroring.

## Scope

**Data objects:** `dt.davis.problems`, `spans`, `events`, `user.sessions`, `user.events`

**Stable IDs** (Playground entities):

| Name | ID |
|---|---|
| image-provider-playground in us-east-1 (root cause Lambda) | `SERVICE-5A0CD2879D2F37BE` |
| Lambda entry span | `span.name == "Invoke lambda /images/presign."` |
| Resize step span | `span.name == "Resize original product image"` |
| Image requests in RUM | `contains(url.full, "/api/images/")` |

## Handoff fields

Three populations coexist — always say which one a number counts.

| Value | Source |
|---|---|
| `owning_team` | Beat 1 — The Page (deploy `owner` is null on these GitHub Actions events) |
| `Goes to` | `owning_team` |
| `commit`, `git_url` | Beat 2 — The Deploy (parsed from `event.description` in DQL) |
| Affected users (problem record) | resolver `affected_users` |
| Real-user sessions with a slow image load (>1 s) | Beat 5 — sum of `sessions` across all countries |
| Per-country sessions | Beat 5 — individual rows |
| Session replay link | Beat 5 deep link |

## Resolver DQL

Contract and fallback logic: `references/session-protocol.md` → "Session state".

### Primary resolver

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter root_cause_entity_id == "SERVICE-5A0CD2879D2F37BE"
| filter dt.davis.is_duplicate == false
| sort timestamp desc
| limit 1
| fieldsAdd window_from = event.start - 15m,
            window_to   = coalesce(event.end, now()) + 15m
| fieldsAdd tf_from_ms    = toLong(window_from) / 1000000,
            tf_to_ms      = toLong(window_to) / 1000000,
            duration_min  = round(toDouble(coalesce(event.end, now()) - event.start) / 60000000000, decimals: 0),
            ended_min_ago = round(toDouble(now() - event.end) / 60000000000, decimals: 0),
            queried_at    = now()
| fields problem_id     = event.id,
         display_id,
         status         = event.status,
         started        = event.start,
         ended          = event.end,
         affected_users = dt.davis.affected_users_count,
         root_cause     = root_cause_entity_name,
         description    = event.description,
         duration_min,
         ended_min_ago,
         queried_at,
         window_from,
         window_to,
         tf_from_ms,
         tf_to_ms
```

### Fallback resolver

Run only if the primary returns zero rows.

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter root_cause_entity_id == "SERVICE-5A0CD2879D2F37BE"
| sort dt.davis.affected_users_count desc, timestamp desc
| limit 1
| fieldsAdd window_from = event.start - 15m,
            window_to   = coalesce(event.end, now()) + 15m
| fieldsAdd tf_from_ms    = toLong(window_from) / 1000000,
            tf_to_ms      = toLong(window_to) / 1000000,
            duration_min  = round(toDouble(coalesce(event.end, now()) - event.start) / 60000000000, decimals: 0),
            ended_min_ago = round(toDouble(now() - event.end) / 60000000000, decimals: 0),
            queried_at    = now()
| fields problem_id     = event.id,
         display_id,
         status         = event.status,
         started        = event.start,
         ended          = event.end,
         affected_users = dt.davis.affected_users_count,
         root_cause     = root_cause_entity_name,
         description    = event.description,
         duration_min,
         ended_min_ago,
         queried_at,
         window_from,
         window_to,
         tf_from_ms,
         tf_to_ms
```
