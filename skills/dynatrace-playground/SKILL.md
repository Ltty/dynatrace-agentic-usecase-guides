# Dynatrace Playground — dtctl Reference Skill

This skill teaches you how to query the Dynatrace Playground via `dtctl`
in agent mode, interpret the response envelope, and present evidence clearly.

## Running a beat's evidence query — use the substitution helper, not raw dtctl

Beat evidence queries contain `{{PLACEHOLDER}}` tokens (incident timeframe, problem id).
Don't call `dtctl query --file` directly on them — the tokens won't be substituted.
Instead:

```bash
python tools/preflight.py run-query <scenario-id> <relative-dql-path>
```

This reads `.demo-state.json`, substitutes every `{{TOKEN}}` in the file against
`placeholders`, executes via dtctl, prints a liveness proof stamp to stderr, and emits the
envelope to stdout. Example:

```bash
python tools/preflight.py run-query payment-failure queries/beat-04-failing-spans.dql
```

For the trace waterfall beat, append `--render waterfall` to get ASCII bar output:

```bash
python tools/preflight.py run-query payment-failure queries/beat-04-trace-waterfall.dql \
  --var TRACE_ID=<id> --render waterfall
```

## Liveness proof stamp

After each successful `run-query` call, `preflight.py` prints a stamp to stderr:

```
------------------------------------------------------------------------
fetch spans, from: "2026-09-27T20:51:00Z", to: "2026-09-27T22:10:00Z"
| filter trace.id == toUid("8af0d233...")
| filter request.is_failed == true
→ live · queryId 01a0e712 · 16 records · 167MB scanned · 33ms
------------------------------------------------------------------------
```

**Include this in your chat narration** — a 2-4 line DQL snippet (the `fetch` and `| filter`
clauses) followed by the `→ live` line. This proves the call hit the Playground in real time,
not a local file. The `queryId` is server-generated and changes on every call. Example narration:
*"Queried the failing payment spans — `filter request.is_failed == true` — 5 traces in 25ms
(queryId 01a0e712, 167MB scanned)."*

The proof stamp fields come from `envelope.metadata` (with `-M=all` passed by `run_query_with_state`):
- `queryId` — server-generated UUID; first 8 chars are enough to distinguish runs
- `executionTimeMilliseconds` — wall-clock query time at the server
- `scannedBytes` — data volume scanned, proves a real index walk happened
- `context.total` — record count returned

For ad-hoc queries with no placeholders (exploring beyond the scripted beats), call dtctl directly:

```bash
dtctl query "fetch dt.davis.problems | limit 5" --agent -o json --plain --max-field-chars 0
```

Always pass `-o json --plain --max-field-chars 0` for exact field names and untruncated values
(agent-mode defaults to `-o auto`, which may emit YAML, and clips fields at 500 chars).

## Chained queries — a value discovered by one query, fed into a second

Some beats declare `chained_evidence` in `scenario.yaml`: a query that needs a value only
known after running a different query first (e.g. a trace ID, discovered from a failing
span, then used to fetch that trace's full waterfall). Run the dependency first via the
normal `run-query`, extract the named field from its **first record**, then pass it to the
chained query with `--var`:

```bash
# 1. Run the dependency (already part of this beat's plain `evidence` list)
python tools/preflight.py run-query payment-failure queries/beat-04-failing-spans.dql
#    -> read `trace_id` from the first record of the result

# 2. Feed it into the chained query as an ad-hoc var
python tools/preflight.py run-query payment-failure queries/beat-04-trace-waterfall.dql \
  --var TRACE_ID=<the trace_id you just read>
```

`--var` merges into the same placeholder set as the state-level ones (`{{DQL_TIMEFRAME_FROM}}`
etc.) — the chained query's `.dql` file just references `{{TRACE_ID}}` like any other token.
This is a general mechanism, not specific to traces: any beat that needs "run query A, then
use a value from A inside query B" uses the same pattern.

**Filtering by `trace.id` requires a cast — this is the one gotcha in the whole chain.**
`trace.id` is a `uid`-typed field, not a plain string, even though it displays as a hex
string in results. `filter trace.id == "<hex>"` and `matchesValue(trace.id, "<hex>")` both
silently match nothing — no error, `matchesValue` only warns if you pass `--metadata` to see
it. Cast the literal first: `filter trace.id == toUid("<hex>")`.

**For the trace waterfall, use `--render waterfall`** to get proportional ASCII bars
instead of raw JSON. The `beat-04-trace-waterfall.dql` query fetches all spans (no
`span.kind` filter) so the renderer has the full parent chain for nesting. The renderer
collapses consecutive successful leaf siblings into one summary line and marks failing
spans with ✗. Run the chained query with render like this:

```bash
python tools/preflight.py run-query payment-failure queries/beat-04-trace-waterfall.dql \
  --var TRACE_ID=<trace_id_from_failing_spans> --render waterfall
```

The renderer handles the 6 spans in the Astroshop trace whose `parent_id` points at a span
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
| 3 | Auth failure | Run `dtctl auth login` |
| 4 | Not found | Try a broader filter or check entity ID |
| 5 | Permission denied | Token scope insufficient |
| 127 | dtctl not found | `run-query`/`preflight.py` auto-locate it; raw calls need PATH set |

## Presenting evidence to the user

Never dump raw JSON. Always:
1. Extract 3–5 key fields.
2. Present as a short table or 2–4 bullet points.
3. Follow immediately with the "so what" — one or two sentences of interpretation.
4. Offer the deep link for the equivalent Dynatrace app view.

See `skills/demo-engine/SKILL.md` → "The beat loop" for the full pattern: state your own read
as confident SRE narration in the same turn as the evidence, then attach it to a forward-looking
option rather than a bare question. Don't withhold the interpretation waiting for the user to
guess it first — that reads as a quiz, not an investigation.

## Key entity IDs for the payment-failure scenario

Stable across problem cycles — safe to hardcode:

| Name | Entity ID | Type |
|------|-----------|------|
| astroshop-payment | SERVICE-531CE26849E95EC1 | Service (root cause) |
| astroshop-checkout | SERVICE-5ACC60E0079F8E6D | Service (downstream) |
| Charge endpoint | (filter `endpoint.name == "Charge"`) | The failing endpoint |
| segment | Apy24Rcu0cO | Filter segment used in deep links |

Rotates every problem cycle — never hardcode, always read from the live query result:
problem id / display id, affected-user count, exception message text, exception line number,
deployment commit SHA, incident timestamps. The exact numbers in this file (e.g. "431 users",
"commit b35672") are illustrative of the *shape* of the data, not values to repeat verbatim.

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

`tools/preflight.py run-query` substitutes these automatically. When building a deep link by
hand, read `.demo-state.json` yourself and substitute the epoch-ms pair.
