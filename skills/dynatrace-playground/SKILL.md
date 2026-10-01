# Dynatrace Playground — dtctl Reference Skill

This skill teaches you how to query the Dynatrace Playground via `dtctl`
in agent mode, interpret the response envelope, and present evidence clearly.

## Running a beat's evidence query — use pre-loaded DQL, not the file

At session start `python tools/preflight.py load-queries <scenario-id>` pre-substitutes every
`{{PLACEHOLDER}}` token and collapses each query to a single line. The engine holds the result
as a `queries` dict in conversation context. The dict includes `_dtctl_path` — the full
resolved path to the dtctl binary — so beats never depend on PATH being set. Per beat:

```bash
"<queries['_dtctl_path']>" query "<queries['queries/beat-04-failing-spans.dql']>" --agent -o json --plain --max-field-chars 0 -M=all
```

For chained queries (e.g. trace waterfall), substitute the runtime placeholder yourself first:

```bash
# dql = queries['queries/beat-04-trace-waterfall.dql'].replace('{{TRACE_ID}}', trace_id)
"<queries['_dtctl_path']>" query "<dql-with-trace-id>" --agent -o json --plain --max-field-chars 0 | python tools/render_waterfall.py
```

For ad-hoc exploration beyond the scripted beats:

```bash
"<queries['_dtctl_path']>" query "fetch dt.davis.problems | limit 5" --agent -o json --plain --max-field-chars 0
```

## Liveness proof stamp

Build the proof stamp from the envelope after each successful agent query:

```
canonical_dql    = envelope.metadata.canonicalQuery   # Grail's own reformatted echo of what ran
queryId          = envelope.metadata.queryId[:8]
ms               = envelope.metadata.executionTimeMilliseconds
scanned_records  = envelope.metadata.scannedRecords
total            = envelope.context.total
```

**Include canonicalQuery and proof in your narration.** Open with the canonicalQuery in a fenced
`dql` block — it's Grail's echo, not your own paraphrase. Then show the evidence table, then:
*"5 records in 25ms — queryId 01a0e712, 62,398 records scanned."*

Always pass `-M=all` on agent beat queries so `envelope.metadata` is populated.

For agent queries, always pass `-o json --plain --max-field-chars 0` — agent mode ignores `-o table`
and `-o json` forces exact field names with untruncated values. For the verbatim-table call on
peak-moment beats, use `-o table --plain` without `--agent` — that is the only call in the
session that intentionally bypasses the JSON envelope. See `skills/demo-engine/SKILL.md` step 3b.

## Chained queries — a value discovered by one query, fed into a second

Some beats declare `chained_evidence` in `scenario.yaml`: a query that needs a value only
known after running a different query first (e.g. a trace ID, discovered from a failing
span, then used to fetch the full waterfall). `load-queries` pre-substitutes all state-level
tokens but leaves runtime-only tokens like `{{TRACE_ID}}` as literals. Substitute them
yourself before running:

```bash
# 1. Run the dependency beat query from the pre-loaded queries dict
"<queries['_dtctl_path']>" query "<queries['queries/beat-04-failing-spans.dql']>" --agent -o json --plain --max-field-chars 0 -M=all
#    -> read `trace_id` from the first record of the result

# 2. Substitute {{TRACE_ID}} in the chained query and run:
#    dql = queries['queries/beat-04-trace-waterfall.dql'].replace('{{TRACE_ID}}', trace_id)
"<queries['_dtctl_path']>" query "<dql-with-trace-id>" --agent -o json --plain --max-field-chars 0 | python tools/render_waterfall.py
```

**Filtering by `trace.id` requires a cast — this is the one gotcha in the whole chain.**
`trace.id` is a `uid`-typed field, not a plain string, even though it displays as a hex
string in results. `filter trace.id == "<hex>"` and `matchesValue(trace.id, "<hex>")` both
silently match nothing — no error, `matchesValue` only warns if you pass `--metadata` to see
it. Cast the literal first: `filter trace.id == toUid("<hex>")`. The `beat-04-trace-waterfall.dql`
query already uses `toUid("{{TRACE_ID}}")` — just replace the token and the cast is in place.

**Waterfall rendering:** pipe the dtctl envelope directly to `render_waterfall.py`. The
renderer handles the 6 spans in the Astroshop trace whose `parent_id` points at a span
outside the result set (mixed OneAgent/OTel instrumentation) via a time-containment fallback:
it finds the smallest containing span by `[start, end]` interval rather than exact parent match.

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
  "context": { "total": 5, "suggestions": [ ... ], "truncated": true },
  "metadata": { "executionTimeMilliseconds": 46, "scannedBytes": 10064354, "queryId": "01a0e712-..." }
}
```

**Reconstruct a full row:** merge `result.constant` with the record dict; the record wins.

## Exit codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Parse and use result |
| 3 | Auth failure | Run `python tools/preflight.py login` |
| 4 | Not found | Try a broader filter or check entity ID |
| 5 | Permission denied | Token scope insufficient |
| 127 | dtctl not found | `preflight.py` commands auto-locate dtctl; direct calls need PATH set |

## Presenting evidence to the user

Never dump raw JSON as evidence. Always:
1. Extract 3–5 key fields.
2. Present as a short table or 2–4 bullet points.
3. Follow immediately with the "so what" — one or two sentences of interpretation.
4. Offer the deep link for the equivalent Dynatrace app view.

A verbatim CLI table from a non-agent `-o table --plain` call on a peak-moment beat is not
raw JSON — paste it in a fenced block as intended. See `skills/demo-engine/SKILL.md` step 3b.

See `skills/demo-engine/SKILL.md` → "The beat loop" for the full pattern: state your own read
as confident SRE narration in the same turn as the evidence, then attach it to a forward-looking
option rather than a bare question. Don't withhold the interpretation waiting for the user to
guess it first — that reads as a quiz, not an investigation.

## Scenario-specific entity IDs

Entity IDs and stable constants for each scenario are kept in `scenarios/<id>/dev-notes.md`
(if present) and in the scenario's own `scenario.yaml → scope.services`.
Never hardcode them here — this skill is shared across all scenarios.

What always rotates and must be read live: problem id, affected-user count, exception text,
exception line numbers, deployment commit SHA, incident timestamps.

## Verified DQL field names and gotchas

These were wrong in earlier drafts of the beat queries and cost real time debugging live —
trust this list over intuition or generic DQL docs.

```dql
// Rounding takes a NAMED second argument. round(x, 1) errors with
// TOO_MANY_POSITIONAL_PARAMETERS_WITH_OPTIONS.
round(value, decimals: 1)

// Spans expose start_time, NOT timestamp. bin(timestamp, 5m) silently
// returns null (no error!) and collapses every bucket into one row.
summarize total = count(), by: { bucket = bin(start_time, 5m) }

// Span failure signal: request.is_failed == true is the direct flag.
// span.status_code also exists but its value is lowercase 'error', not "ERROR".
filter request.is_failed == true

// Trace/duration field names on spans:
trace.id                          // NOT dt.trace_id
toDouble(duration) / 1000000      // NOT span.duration; duration is a numeric STRING

// Exception detail lives in span.events, but `expand span.events` does NOT
// flatten exception.* onto the row as top-level fields. Project with bracket
// access into the expanded object:
| expand span.events
| fields
    exc_type = span.events[exception.type],
    exc_msg  = span.events[exception.message],
    exc_file = span.events[exception.file.full],
    exc_line = span.events[exception.line_number]

// A single incident can carry MORE THAN ONE distinct exception message on the
// same endpoint (e.g. two different validation regressions in one deploy).
// Don't assume the first failing span tells the whole story — skim all rows.

// Deployment events (CUSTOM_DEPLOYMENT, ArgoCD) carry the git commit directly:
fetch events | filter event.type == "CUSTOM_DEPLOYMENT"
| fields commit, gitUrl, stage, app, owner, service = dt.entity.service.name
// NOT dt.release_version / dt.release_build_version — those fields don't exist
// on this event shape. `commit` is the short git SHA; `gitUrl` links straight
// to the GitHub commit.

// User sessions: start_time (not startTime), geo.country.iso_code for geo,
// characteristics.has_replay (not session.hasSessionReplay),
// error.http_5xx_count > 0 (not matchesPhrase(useraction.errors, ...) — that
// field doesn't exist on this data object).
// user.sessions is NOT tagged with a service entity ID — don't filter on
// dt.entity.service here.
fetch user.sessions
| filter error.http_5xx_count > 0
| summarize sessions = count(), with_replay = countIf(characteristics.has_replay == true),
    by: { country = geo.country.iso_code }

// Problems: the pattern fires as a cluster of near-duplicate Davis problems.
// dt.davis.is_duplicate == false selects Davis's own merged/umbrella problem —
// note its event.name is "Multiple application problems", NOT the specific
// symptom name. Do not filter on event.name when selecting the canonical problem.
fetch dt.davis.problems
| filter root_cause_entity_id == "SERVICE-531CE26849E95EC1"
| filter dt.davis.is_duplicate == false
```

## Davis CoPilot

```bash
dtctl exec copilot "<question>" --context "<structured facts from your own queries>" --instruction "<format hint>"
```

The message is a **positional argument**, not stdin (`echo ... | dtctl exec copilot` fails with
"message is required"). Pass the facts you already gathered via `--context` — CoPilot gives a
much sharper answer grounded in your own query results than it does re-deriving them itself.
`--instruction "2-3 sentences max"` keeps the response terse enough for the beat loop's length budget.

**`--max-field-chars 0` is a `dtctl query` flag — it does not exist on `dtctl exec copilot`**
and errors with `unknown flag`. Don't carry it over out of habit just because every `query`
call in this skill uses it.

CoPilot is only as good as what you feed it. Called with just problem-level metadata (id,
timestamps, service names) it tends to hedge — "cannot determine the specific cause from this
alone." Call it *after* you have the actual exception text or trace data from a query, and pass
that in via `--context`; that's what turns a vague answer into a sharp, specific one.

## Placeholder resolution

`.demo-state.json` → `placeholders` holds both representations:
- `TIMEFRAME_FROM` / `TIMEFRAME_TO` — epoch milliseconds, for Dynatrace app deep-link URLs
- `DQL_TIMEFRAME_FROM` / `DQL_TIMEFRAME_TO` — ISO8601 strings, for use inside DQL `from:`/`to:`
- `PAYMENT_FAILURE_PROBLEM` — the resolved problem's event id

`python tools/preflight.py load-queries <id>` substitutes all of these at session start and
returns pre-built DQL strings in the `queries` dict. When building a deep link by hand, read
`.demo-state.json` yourself and substitute the epoch-ms pair.
