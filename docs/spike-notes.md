# Phase 0 Connectivity Spike Notes

**Date:** 2026-09-25  
**dtctl version:** 0.40.0 (commit: efd558d)  
**Context:** playground → https://playground.apps.dynatrace.com  
**Safety level:** readonly  
**Auth:** OAuth (Windows Credential Manager)

## Gate result: ALL PASSED

`dtctl doctor` output (all OK):
- dtctl version 0.40.0
- Config: `%LOCALAPPDATA%\dtctl\config`
- Current context: playground, safety: readonly
- Token: Windows Credential Manager
- OAuth session: access + refresh token present
- Connectivity: playground reachable
- Authentication: florian.lettner@dynatrace.com

## Probe 1 — `dt.davis.problems`

```
dtctl query "fetch dt.davis.problems | limit 5" -o json
```

**Confirmed:** Problems queryable. Payment-failure problem found in results:
- `display_id`: P-26093148
- `event.name`: "Failure rate increase"
- `root_cause_entity_id`: SERVICE-531CE26849E95EC1 (astroshop-payment) ← matches usecase.json
- `event.status`: CLOSED (was active 09:11–09:40 UTC today; problem fires on a schedule)
- `affected_entity_names`: ["astroshop-payment", "astroshop-checkout", ...]
- `dt.davis.affected_users_count`: "310"
- `dt.davis.is_duplicate`: true (recurring pattern)

**Key field names for resolver query:**
```
event.name, event.status, event.start, event.end,
root_cause_entity_id, root_cause_entity_name,
affected_entity_names, affected_entity_ids,
display_id, dt.davis.affected_users_count,
dt.davis.event_ids, smartscape.affected_entities
```

## Probe 2 — Spans for SERVICE-531CE26849E95EC1

```
dtctl query "fetch spans | filter dt.entity.service == \"SERVICE-531CE26849E95EC1\" 
             | limit 3 | fields timestamp, endpoint.name, span.status_code, dt.trace_id"
```

**Confirmed:** Spans reachable, `endpoint.name: Charge` present (matches use-case step 4).

## Probe 3 — `dtctl inventory`

**Confirmed:**
- 17 capabilities, 28 data objects, 425 entity views, 41 buckets, 22 segments
- Relevant data objects available: logs, spans, metrics, events, user.sessions, entities
- Discovery method: queries

## `--agent` JSON envelope shape (stable contract)

```json
{
  "ok": true,
  "envelope_version": 1,
  "result": {
    "kind": "records",          // or "result-file" | "summary-only"
    "constant": { ... },        // fields common to all rows (avoids repetition)
    "records": [ ... ]          // per-row deltas; absent key = constant value
  },
  "context": {
    "total": 5,
    "verb": "query",
    "resource": "dt.davis.problems",
    "suggestions": [ ... ],     // follow-up hints
    "decided": "inline",
    "truncated": true,
    "max_field_chars": 500,
    "truncated_fields": ["event.description"]
  },
  "metadata": {
    "analysisTimeframe": { "start": "...", "end": "..." },
    "executionTimeMilliseconds": 46,
    "scannedBytes": 10064354
  }
}
```

Exit codes: 0 success, 3 auth failure, 4 not found, 5 permission denied.

## Open items from spike

1. The payment-failure problem fires on a schedule (seen as CLOSED after a run this morning).
   Resolver must filter for BOTH active and very-recent CLOSED instances, not just ACTIVE.
   Query: `event.status in ("ACTIVE","CLOSED") AND root_cause_entity_id == "SERVICE-531CE26849E95EC1"`
   with a time window covering "last 24h" to ensure we catch the most recent occurrence.
2. `dtctl exec copilot` — not tested in this spike; exercise in Phase 2.
3. No `dtctl get problems` command exists; DQL-only access confirmed.
