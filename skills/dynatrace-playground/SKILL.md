# Dynatrace Playground — dtctl Reference Skill

This skill teaches you how to query the Dynatrace Playground via `dtctl`
in agent mode, interpret the response envelope, and present evidence clearly.

## dtctl basics for agent use

Always pass `--agent` (or rely on auto-detection via `CLAUDECODE` env var).
Always pass `-o json` when you need exact field names (agent default is `-o auto` which may emit YAML).
Always pass `--max-field-chars 0` when the full value of a field matters (default clips at 500 chars).
Use `--plain` to suppress ANSI colours.

```bash
dtctl query "fetch dt.davis.problems | limit 5" --agent -o json --plain
dtctl query --file scenarios/payment-failure/queries/find-problem.dql --agent -o json --plain
dtctl exec copilot   # interactive Davis CoPilot session
dtctl inventory --agent
dtctl doctor
```

## Response envelope shape

```json
{
  "ok": true,
  "envelope_version": 1,
  "result": {
    "kind": "records",     // inline; or "result-file" (spilled) | "summary-only"
    "constant": { ... },   // fields identical in every row; absent key = use constant value
    "records": [ ... ]     // per-row delta; absent key means use constant
  },
  "context": {
    "total": 5,
    "suggestions": [ ... ],
    "truncated": true,
    "truncated_fields": ["event.description"]
  },
  "metadata": {
    "analysisTimeframe": { "start": "...", "end": "..." },
    "executionTimeMilliseconds": 46,
    "scannedBytes": 10064354
  }
}
```

**Reconstruct a full row:** merge `result.constant` with the record dict; the record wins on conflicts.

**Truncated fields:** re-run with `--max-field-chars 0 | fields <truncated_field>` to get the full value.

## Exit codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Parse and use result |
| 3 | Auth failure | Run `dtctl auth login` |
| 4 | Not found | Try a broader filter or check entity ID |
| 5 | Permission denied | Token scope insufficient |
| 127 | dtctl not found | Run devcontainer setup |

## Presenting evidence to the user

Never dump raw JSON. Always:
1. Extract 3–5 key fields.
2. Present as a short table or 2–4 bullet points.
3. Follow immediately with the "so what" — one or two sentences of interpretation.
4. Offer the deep link for the equivalent Dynatrace app view.

Example — good:
```
Payment service Charge endpoint:
  • Failure rate: 54.7% (was <1% before 09:11 UTC)
  • Affected users: 310
  • Root cause: astroshop-payment → astroshop-checkout downstream

The spike is sharp — this isn't gradual degradation, it's a hard break.
That pattern usually means a bad deployment or a config push. Want to check recent deploys?

→ Open in Dynatrace: [Problems app link]
```

Example — bad (never do this):
```
Here is the full JSON: {"ok":true,"result":{"records":[{"event.id":"..."...
```

## Key entity IDs for the payment-failure scenario

| Name | Entity ID | Type |
|------|-----------|------|
| astroshop-payment | SERVICE-531CE26849E95EC1 | Service (root cause) |
| astroshop-checkout | SERVICE-5ACC60E0079F8E6D | Service (downstream) |
| payment K8s app | CLOUD_APPLICATION-C3724834CF7ADFFF | K8s workload |
| checkout K8s app | CLOUD_APPLICATION-7D7961E55D2923B0 | K8s workload |

## DQL patterns for this environment

```dql
// Problems (last 24h, sorted newest first)
fetch dt.davis.problems, from: now()-24h, to: now()
| sort timestamp desc

// Spans for a service with error filter
fetch spans
| filter dt.entity.service == "SERVICE-531CE26849E95EC1"
| filter span.status_code == "ERROR"
| limit 20

// Failure rate by 5-minute bucket
fetch spans
| filter endpoint.name == "Charge"
| summarize total = count(), failures = countIf(span.status_code == "ERROR"), by: bin(timestamp, 5m)
| fieldsAdd rate = round(toDouble(failures)/toDouble(total)*100, 1)

// Deployment events
fetch events
| filter event.type == "CUSTOM_DEPLOYMENT"
| filter dt.entity.service == "SERVICE-531CE26849E95EC1"
| sort timestamp desc
| limit 5
```

## Placeholder resolution

Scenario placeholders (`{{PAYMENT_FAILURE_PROBLEM}}`, `{{TIMEFRAME_FROM}}`, `{{TIMEFRAME_TO}}`)
are resolved at `/demo start` and stored in `.demo-state.json` under `placeholders`.
Read that file and substitute before presenting any deep link URL.
