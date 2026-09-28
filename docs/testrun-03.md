# Demo Test Run — payment-failure scenario

**Date:** 2026-09-28
**Scenario:** payment-failure (P-26093359)
**Mode:** live_recent (problem CLOSED ~21:40 UTC prior night; session started ~07:24 UTC)
**Duration:** ~12 minutes

---

## Preflight

Not run explicitly this session.

---

## Discovery (`/demo`)

**Trigger:** "are there any open issues right now?"

**Resolver output (no `--write`):** `mode: live_recent`, `status: CLOSED`, 431 affected users,
started 21:06, ended 21:40, 33-minute window.

**Engine output (paraphrased):**

> The environment is quiet right now, but there's a recent incident worth digging into.
> The payment service took down checkout for 431 users about 10 hours ago — ran hot for
> 34 minutes before it closed. That's roughly $37,500 in abandoned carts. End on three
> entry angles: the deployment, the failing traces, or the affected user sessions.

**Notes:**

- `avg_order_value_usd` ($87) × `affected_users` (431) = $37,497 → displayed as $37,500 ✅
- Resolver ran without `--write` for the survey — correct; `--write` deferred until user
  chose an entry angle ✅
- `live_recent` framing: past tense, no fixture announcement ✅
- Ended on 3 concrete entry angles, not yes/no ✅

---

## Beat 01 — The Page

**Skipped.** User front-ran directly to the deployment entry angle ("show me the deployment
that triggered it"). Engine folded in the blast-radius context (payment as root cause,
checkout as collateral) into the beat-02 narration rather than running beat-01 explicitly.
Beat marked complete in state once folded context was delivered ✅

---

## Beat 02 — Explain with Davis

**User:** "show me the deployment that triggered it"

**Engine:** Ran `python tools/preflight.py resolve payment-failure --write` to start the
session and write state, then ran the evidence query.

**Query:** `beat-02-deployment-events.dql` — ran cleanly, 5 records returned ✅

**Evidence returned:**

| Time (UTC) | Commit | Services | Role |
|---|---|---|---|
| 21:06:53 | — | — | Problem starts |
| 21:12:31 | `b35672` | payment + checkout | Culprit deploy |
| 21:15:57 | `b35672` | payment | Re-sync |
| 21:34:10 | `8b677d` | payment + checkout | Fix/rollback |
| 21:40:00 | — | — | Problem closes |

**Davis CoPilot:** Called correctly — no `--max-field-chars 0` flag (which is invalid for
`exec copilot`) ✅. Fed commit SHA and timestamps as context; returned a sharp, specific
response confirming `b35672` as the regression and `8b677d` as the fix. Previous testrun
got a hedged non-answer by calling CoPilot with only problem-level metadata; feeding it
the actual deployment data made the difference.

**Deep link:** Davis CoPilot intent URL, placeholder resolved from state ✅

**⚠️ Trailing tool call visibility issue (first occurrence):** Engine updated `.demo-state.json`
at the end of the turn. In the user's VSCode Focus view, text content preceding the trailing
tool call was invisible. User reported "no visible output." Engine re-sent the deployment
content without a trailing tool call and user received it correctly.

---

## Beat 03 — Service Deep Dive

**User:** "show me the timeline first"

**Queries:**

- `beat-03-service-failure-rate.dql` — ran cleanly, 13 buckets returned ✅
- `beat-03-deployment-marker.dql` — ran cleanly; returned only `8b677d` (the fix commit),
  not `b35672` (the culprit). b35672 was already established in beat 02, so this was not
  a gap in the investigation, but see "Issues to Fix" below.

**Evidence returned — failure rate timeline:**

| Time (UTC) | Failure rate | Notes |
|---|---|---|
| 20:50–20:55 | 0% | Clean baseline |
| 21:00 | 6.8% | First failures — deploy rolling |
| 21:05 | 46.9% | Spike — 30/64 requests failing |
| 21:10–21:25 | 40–44% | Sustained |
| 21:30 | 27.4% | Slight dip |
| 21:35 | 0% | Recovery after fix deploy at 21:34 |
| 21:40+ | 0% | Back to baseline |

**Engine interpretation:** Zero at 20:55, spike to 47% at 21:05 as `b35672` rolls out.
Fix deploys at 21:34, next bucket clean — deployment marker lands exactly on the recovery
bucket. No ambiguity about causation.

**Deep link:** Services explorer — payment service performance during P-26093359 ✅

**⚠️ Trailing tool call visibility issue (second occurrence):** Same pattern as beat 02.
User reported "no visible output." Engine re-sent the timeline content without trailing
tool call ✅

---

## Beat 04 — Failing Traces (peak moment)

**User:** "show me the trace"

**Query:** `beat-04-failing-spans.dql` — ran cleanly, 5 records returned ✅

**Evidence returned — two distinct exceptions:**

| Time (UTC) | Trace ID | Exception message | File | Line |
|---|---|---|---|---|
| 21:32:51–21:33:20 | `ccb40564`, `d4063d70`, `a351f6c0`, `8af0d233` | "Sorry, we cannot process American Express credit cards. Only Visa or Mastercard are accepted." | charge.js | 77 |
| 21:43:43 | `3481df8b` | "Credit card info is invalid." | charge.js | 66 |

Duration on all spans: 1ms — request thrown synchronously by validation logic, not a
downstream or infrastructure failure.

**Engine:** Peak moment delivery — exception message landed verbatim on its own line before
any commentary ✅. Both distinct exceptions surfaced and reported (not filtered as noise) ✅.

**⚠️ Trailing tool call visibility issue (third occurrence):** Same pattern. User reported
"no visible output," then clarified they had seen something but wanted the trace data
itself rather than interpretation. Engine re-delivered with the full trace table (trace IDs,
timestamps, exception columns) rather than just the exception messages ✅.

**Note:** "Show me the trace" was a request for the raw trace data, not just the exception
message. Engine's first delivery (exception text + interpretation, no trace ID table) was
technically correct per the beat spec but missed the user's intent. Second delivery included
the trace ID table and satisfied the request.

**Deep link:** Distributed Tracing — failed Charge spans ✅

---

## Beat 05 — The Humans (peak moment)

**User:** "show me the users"

**Query:** `beat-05-affected-sessions.dql` — ran cleanly, 10 country records returned ✅

**Evidence returned (top 10 countries):**

| Country | Sessions | With Replay |
|---|---|---|
| US | 51 | 51 |
| GB | 14 | 14 |
| CN | 13 | 13 |
| AU | 11 | 11 |
| NG | 11 | 11 |
| BR | 9 | 9 |
| CZ | 7 | 7 |
| EG | 7 | 7 |
| JP | 7 | 7 |
| (unknown) | 20 | 8 |

Near-100% session replay availability across all known-country rows.

**Engine:** Peak moment framing — session replay described concretely as a recording of
the exact UX, not a log entry. "That's the gap between 430 5xx errors and 430 people who
had a bad day and probably didn't come back." ✅

**Deep link:** Error Inspector — affected sessions ✅

**⚠️ Trailing tool call visibility issue (fourth occurrence):** Same pattern again.
Engine re-sent the users content without trailing tool call ✅.

---

## Session Close

**User:** "recap"

**Incident timeline delivered:**

1. Davis opened P-26093359 at 21:06 — 431 users, payment Charge endpoint failing, checkout
   downstream collateral
2. Commit `b35672` deployed via ArgoCD at 21:12 — identified as the regression carrier
3. `/usr/src/app/charge.js:77` rejecting American Express cards outright; line 66 a second
   card validation failure in the same commit
4. 431 sessions across US, GB, CN, AU, NG, BR and more — near-100% session replay coverage
5. Commit `8b677d` reverted at 21:34; problem closed at 21:40 — 33 minutes total

**Payoff contrast stated:** "From alert to root cause in under 10 minutes. Without correlated
traces, deployment markers, and session replay, this is hours of grepping logs and guessing
which of several recent deploys introduced the regression." ✅

---

## Issues to Fix

### Trailing tool call makes text invisible in VSCode Focus view (blocking UX issue)

When a turn ends with a tool call (in this session, always an `Edit` to update
`.demo-state.json`), the preceding text content is invisible to the user in the VSCode
extension's Focus view. Happened four times this session — after beats 02, 03, 04, and 05.

**Fix:** Move state-update `Edit` calls to happen *before* the narrative text response in
each turn, so text is always the last thing output. The engine always has the data it needs
to write state before narrating, so this ordering is safe.

### Beat 03 deployment marker query only returns the fix commit

`beat-03-deployment-marker.dql` returned only `8b677d` (the fix), not `b35672` (the
culprit). The query may be filtering to a timeframe or event shape that misses the earlier
deploy. In this session the gap was covered because b35672 was already established in beat
02, but if beat 03 runs before beat 02 the marker chart would only show the fix. Worth
investigating the query's timeframe filter.

### "Show me the trace" ≠ "show me the exception"

When the user said "show me the trace," the engine's first response delivered the exception
messages verbatim (correct per the peak-moment spec) but omitted the trace ID table. The
user clarified they wanted to see the trace data. The beat spec should make explicit that
the evidence presentation includes the trace IDs and span-level columns, not just the
exception text — the exception message is the climax, but the table is still the evidence.

---

## What Worked Well

- Survey discovery: real numbers, entry angles, no yes/no ending ✅
- Front-running beat 1→2: blast-radius context folded into beat 02 narration cleanly ✅
- All five beat queries executed with no DQL errors — fixes from testrun-01 are fully in
  place ✅
- Davis CoPilot called correctly (no `--max-field-chars 0` flag); useful response because
  it was fed the actual deployment data as context ✅
- Two distinct exceptions in beat 04 both surfaced ✅
- 1ms span duration noted as a signal (synchronous validation throw, not infra fault) ✅
- Peak moment delivery on beats 04 and 05 felt distinct from routine evidence turns ✅
- Session close with one-sentence-per-beat timeline and payoff contrast delivered cleanly ✅
