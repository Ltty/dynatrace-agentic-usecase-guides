# Scenario: Disk / CPU Cascade — Lookup and Context

Read at survey time. The beats live in `references/scenario-disk-cpu-cascade-beats.md`; read that only once the user
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
| `service_name` | "frontend-high-cpu host" |
| `user_action` | "platform operations" |
| `symptom` | "low disk space on /data, with CPU saturation on the same host" |
| `pull_line` | "Pulling the disk, the CPU, the blocked update and the problem record together." |

No `avg_order_value_usd` is defined for this scenario — omit the revenue figure in the survey. The problem
record carries no affected-user count either: report `affected_count` (entities in the problem), never users.
Its impact level is Infrastructure; nothing in this scenario's data says whether any user was affected, so
don't claim either way.

**Discovery hook template** (single-brace tokens, filled from session state at survey time):

```text
The {service_name} has had a problem open for {duration_days} days and {duration_hours} hours: low available
disk space on {root_cause}, with CPU saturation on the same host. It affects {affected_count} entities.
```

The problem stays open until someone acts, so it can be weeks old: use `duration_days` and `duration_hours` from
the lookup (computed in DQL; never convert `duration_min` yourself), and for an active problem say it is
still open.

"Cascade" is the scenario's name, not a finding. Don't say the disk cascades into, causes or drives the CPU: say the
problem record lists CPU saturation as affected on the same host. The data ties one other symptom to the disk
in its own words, the OneAgent update failure (beat 4).

## Scope

**Data objects:** `dt.davis.problems`, `events`, and `timeseries` on `dt.host.*` metrics

**Tenant:** this scenario's entities exist on the `dev` tenant only. On any other tenant the lookup returns
nothing and the survey does not list it.

**Stable IDs** (cloud-alerts-demo entities):

| Name | ID |
|---|---|
| Root cause disk entity | `DISK-2B3DB86FA32F6CE1` |
| Affected host | `HOST-A2BABAD05D401471` |
| Host name | `frontend-high-cpu` |
| Host group | `cloud-alerts-demo` |
| AWS region | `us-east-1` |

**Metric dimensions** (verified live — they differ from what the entity IDs suggest):

- Disk metrics are split by `dt.entity.disk`. Free space in percent is `dt.host.disk.free`; bytes are `dt.host.disk.avail`.
  There is no `dt.host.disk.avail.percent`.
- CPU metrics (`dt.host.cpu.usage`, `dt.host.cpu.iowait`) are split by `host.name`, not `dt.entity.host`. A `by` field
  the metric doesn't have doesn't fail: everything aggregates into one tenant-wide series.
- Events carry `host.name`, not `dt.entity.host`.

## Handoff fields

| Value | Source |
|---|---|
| `owning_team` | None: the problem record has no owner. Hand off by host (`frontend-high-cpu`) and host group; never name a team |
| `Goes to` | The host `frontend-high-cpu` and its host group `cloud-alerts-demo`; never a team |
| `root_cause` | Lookup (`root_cause` = the `/data` disk) |
| Disk and CPU thresholds | Beat 1 — the problem `description` ("lower than 3%", "above 95%") |
| Blocked OneAgent version | Beat 4 — the newest update-failure event, not the problem description (see Beat 4) |
| Entities in the problem | Lookup `affected_count` |
| Disk free space | Beat 2 |
| CPU and I/O wait | Beat 3 |

## Lookup DQL

Contract and backup logic: `references/session-protocol.md` → "Session state".

The main lookup filters on the root cause's id. It is a smartscape-typed value: compare it as
`toString(root_cause_id)`, or the filter silently matches nothing.

### Main lookup

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter dt.davis.is_duplicate == false
| fieldsAdd root_cause_id = root_cause.smartscape_entity[id]
| filter toString(root_cause_id) == "DISK-2B3DB86FA32F6CE1"
| sort timestamp desc
| limit 1
| fieldsAdd window_from = event.start - 15m,
            window_to   = coalesce(event.end, now()) + 15m
| fieldsAdd tf_from_ms    = toLong(window_from) / 1000000,
            tf_to_ms      = toLong(window_to) / 1000000,
            duration_min  = round(toDouble(coalesce(event.end, now()) - event.start) / 60000000000, decimals: 0),
            ended_min_ago = round(toDouble(now() - event.end) / 60000000000, decimals: 0),
            queried_at    = now()
| fieldsAdd duration_days  = floor(duration_min / 1440),
            duration_hours = floor((duration_min - floor(duration_min / 1440) * 1440) / 60)
| fields problem_id     = event.id,
         display_id,
         status         = event.status,
         started        = event.start,
         ended          = event.end,
         affected_count = arraySize(smartscape.affected_entities),
         root_cause     = root_cause.smartscape_entity[name],
         description    = event.description,
         duration_min,
         duration_days,
         duration_hours,
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
| filter dt.davis.is_duplicate == false
| filter matchesPhrase(event.description, "/data") and matchesPhrase(event.description, "frontend-high-cpu")
| filter contains(toString(smartscape.affected_entities), "HOST-A2BABAD05D401471")
| sort timestamp desc
| limit 1
| fieldsAdd window_from = event.start - 15m,
            window_to   = coalesce(event.end, now()) + 15m
| fieldsAdd tf_from_ms    = toLong(window_from) / 1000000,
            tf_to_ms      = toLong(window_to) / 1000000,
            duration_min  = round(toDouble(coalesce(event.end, now()) - event.start) / 60000000000, decimals: 0),
            ended_min_ago = round(toDouble(now() - event.end) / 60000000000, decimals: 0),
            queried_at    = now()
| fieldsAdd duration_days  = floor(duration_min / 1440),
            duration_hours = floor((duration_min - floor(duration_min / 1440) * 1440) / 60)
| fields problem_id     = event.id,
         display_id,
         status         = event.status,
         started        = event.start,
         ended          = event.end,
         affected_count = arraySize(smartscape.affected_entities),
         root_cause     = root_cause.smartscape_entity[name],
         description    = event.description,
         duration_min,
         duration_days,
         duration_hours,
         ended_min_ago,
         queried_at,
         window_from,
         window_to,
         tf_from_ms,
         tf_to_ms
```
