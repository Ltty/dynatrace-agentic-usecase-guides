# Scenario: Payment Failure — Lookup and Context

Read at survey time. The beats live in `references/scenario-payment-failure-beats.md`; read that only once the user
picks a direction.

**Duration:** 8–15 minutes

## Contents

- [Persona](#persona)
- [Business context](#business-context)
- [Scope](#scope)
- [Handoff fields](#handoff-fields)
- [Lookup DQL](#lookup-dql)

## Persona

On-call SRE pairing with the user. Calm, concrete, mild time pressure. Speaks in facts and next
steps. Never breathless. Uses "we".

## Business context

| Field | Value |
|---|---|
| `service_name` | "payment service" |
| `avg_order_value_usd` | 87 |
| `user_action` | "checkout" |
| `symptom` | "card payments failing at checkout" |
| `pull_line` | "Pulling the deployments, the failure rate, the failing requests and the affected sessions together." |

**Discovery hook template** (single-brace tokens, filled from session state at survey time):

```text
The {service_name} is failing for {affected_users} users — it's been going on for
{duration_min} minutes. That's roughly ${revenue_impact} in abandoned carts.
```

The failure rate comes from the service deep dive, never from the problem record.

## Scope

**Data objects:** `dt.davis.problems`, `spans`, `logs`, `events`, `user.sessions`, `entities`

**Stable IDs** (Playground entities):

| Name | ID |
|---|---|
| astroshop-payment (root cause) | `SERVICE-531CE26849E95EC1` |
| astroshop-checkout (downstream) | `SERVICE-5ACC60E0079F8E6D` |
| Charge endpoint | `endpoint.name == "Charge"` |
| Segment (problem deep link) | `Apy24Rcu0cO` |

## Handoff fields

Where the values for a remediation handoff come from. Three populations coexist — always say
which one a number counts.

| Value | Source |
|---|---|
| `owning_team` | Beat 1 — The Page; who to page first |
| `Goes to` | `owning_team` |
| `commit`, `git_url`, `owner` | Beat 2 — The Change; `owner` is who shipped it. If it differs from `owning_team`, list both and say which is which |
| Affected users (problem record) | lookup `affected_users` |
| Sessions with 5xx errors | Beat 5 — sum of `sessions` across all countries |
| Per-country sessions | Beat 5 — individual rows |
| Session replay link | Beat 5 deep link |

## Lookup DQL

Contract and backup logic: `references/session-protocol.md` → "Session state".

### Main lookup

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter root_cause_entity_id == "SERVICE-531CE26849E95EC1"
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

### Backup lookup

Run only if the main lookup returns zero rows.

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter root_cause_entity_id == "SERVICE-531CE26849E95EC1"
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
