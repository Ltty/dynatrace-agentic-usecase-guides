# Demo Test Run — payment-failure scenario
**Date:** 2026-09-28
**Scenario:** payment-failure (P-26093359)
**Mode:** live_recent (problem CLOSED ~21:40 UTC prior night; session started ~06:57 UTC)
**Duration:** ~10 minutes

---

## Preflight

Not run explicitly this session — `/demo-doctor` was not invoked before starting.

---

## Discovery (`/demo`)

**Trigger:** "Are there any open issues right now?"

**Resolver output:** `mode: live_recent`, `status: CLOSED`, 431 affected users, started
21:06, ended 21:40, 33-minute window.

**Engine output (paraphrased):**

> The environment is quiet right now, but there's a recent incident worth pulling up.
> The payment service failed hard last night — 431 users hit checkout errors over a 33-minute
> window. That's roughly $37,500 in abandoned carts. Davis closed the problem about 9 hours
> ago, but the traces, logs, deployment markers, and session recordings are all still live
> and queryable.
>
> Start with the deployment that likely caused it, the failing traces that show the exact
> exception, or the customer sessions that got hit?

**Notes:**

- `avg_order_value_usd` ($87) × `affected_users` (431) = $37,497 → displayed as $37,500 ✅
- Resolver ran twice: once without `--write` (survey), once with `--write` (after user
  confirmed). Correct separation of concerns ✅
- `live_recent` framing: past tense, no "Running on recorded data" announcement (that's
  fixture-only) ✅
- Ended on 3 concrete entry angles, not a yes/no ✅

---

## Beat 01 — The Page

**User:** "Yes, I want to understand what went wrong" (generic assent post-survey → auto-routed
to beat 1)

**Query:** `beat-01-problem-summary.dql` — ran cleanly, 1 record returned ✅

**Evidence returned:**

| Field | Value |
|---|---|
| Problem | P-26093359 |
| Root cause (Davis) | `astroshop-payment` |
| Payment failure rate | 52.38% |
| Checkout failure rate | 52.38% (PlaceOrder) |
| Frontend failure rate | 17.55% |
| Affected users | 431 |
| Duration | 33 min |

**Engine:** Asked user for their read — payment vs checkout as root cause. Did not hand over
reveal upfront ✅

**Side quest triggered:** User asked "show me the affected users by country" before resolving
beat 1's objective.

- Engine ran `beat-05-affected-sessions.dql` (beat 5 query, mid-beat-1) ✅
- Answered in full, then redirected back to the open beat-1 question ✅
- No beats marked complete yet; no state advance ✅

**User follow-up:** "How can I verify?" (engaging with the payment-vs-checkout question)

**Engine:** Explained Davis's `root_cause` field (dependency graph analysis) and named the
failing traces as definitive confirmation. Beat 1 objective met; transitioned to beat 2.

**Deep link:** Problems app, P-26093359 ✅

---

## Beat 02 — Explain with Davis

**User:** "yes, show me what changed"

**Query:** `beat-02-deployment-events.dql` — ran cleanly, 5 records returned ✅

**Evidence returned:**

| Time (UTC) | Commit | Services |
|---|---|---|
| 21:06:53 | — | Problem starts |
| 21:12:31 | `b35672` | payment + checkout |
| 21:15:57 | `b35672` | payment (re-sync) |
| 21:34:10 | `8b677d` | payment + checkout |
| 21:40:00 | — | Problem closes |

**Note on timing:** `b35672` was recorded 6 minutes *after* the problem started — the
deployment event timestamp lags behind pod activation. `8b677d` landed at 21:34 and the
problem closed at 21:40, confirming it as the revert/fix.

**Engine:** Asked what the sequence tells the user.

**User:** "tell me" (no engagement — rung 4 of nudge ladder)

**Engine:** Stated reveal (b35672 introduced the regression, 8b677d reverted it), then
called Davis CoPilot.

**Davis CoPilot attempt 1:** `dtctl exec copilot ... --max-field-chars 0` — failed with
`unknown flag --max-field-chars`. This flag is only valid for `dtctl query`, not `exec
copilot`. ⚠️

**Davis CoPilot attempt 2:** Same call without `--max-field-chars 0` — succeeded but
returned a weak response: could not determine the specific technical cause from the
problem-level metadata alone; deferred to the traces.

**Notes:**

- `--max-field-chars 0` is not a valid flag for `dtctl exec copilot` — remove it from any
  future CoPilot calls ⚠️
- CoPilot is most useful when fed actual query results (trace data, exception text), not
  just problem metadata. Feeding it only the commit SHA and timestamps produced a hedged
  non-answer. Better to invoke CoPilot *after* the traces beat with the exception text
  as context, or skip CoPilot on beat 2 and let the traces do the talking.

**Deep link:** Davis CoPilot intent URL ✅

---

## Beat 03 — Service Deep Dive

**Skipped.** User front-ran to traces. Engine folded past beat 3 per front-running rule ✅

---

## Beat 04 — Failing Traces

**User:** "yes, show me the traces"

**Query:** `beat-04-failing-spans.dql` — ran cleanly, 5 records returned ✅

**Evidence returned — two distinct exceptions:**

| Exception message | File | Line | Traces |
|---|---|---|---|
| "Sorry, we cannot process American Express credit cards. Only Visa or Mastercard are accepted." | `/usr/src/app/charge.js` | 77 | 4 |
| "Credit card info is invalid." | `/usr/src/app/charge.js` | 66 | 1 |

**Engine:** Peak moment delivery — exception message landed verbatim on its own line before
commentary ✅

**Interpretation:** Business-logic validation regression. `b35672` added an explicit Amex
rejection. Invisible to unit tests using Visa/Mastercard fixtures only; real traffic exposed
it immediately. Two distinct exception messages surfaced and both reported (not filtered
as noise) ✅

**Deep link:** Distributed Tracing — failed Charge spans ✅

---

## Beat 05 — The Humans

**User:** "yes" (generic assent — data already in context from beat-1 side quest)

**Query:** Re-used `beat-05-affected-sessions.dql` result from earlier; no second query
needed.

**Evidence presented (top 10 countries):**

| Country | Sessions | With Replay |
|---|---|---|
| US | 51 | 51 |
| (unknown) | 20 | 8 |
| GB | 14 | 14 |
| CN | 13 | 13 |
| AU, NG | 11 each | 11 each |
| BR | 9 | 9 |
| CZ, EG, JP | 7 each | 7 each |

**Engine:** Peak moment framing — session replay described concretely as a recording of the
exact UX, not a log entry ✅

**Deep link:** Error Inspector — affected sessions ✅

---

## Session Close

**Incident timeline:**

1. Davis opened P-26093359 at 21:06 — 52% failure rate on `astroshop-payment`, 431 users,
   checkout downstream collateral
2. Commit `b35672` deployed to payment + checkout during the incident window; identified as
   the regression carrier
3. `charge.js:77` threw `"Sorry, we cannot process American Express credit cards."` — Amex
   rejection added in `b35672`, invisible to Visa/Mastercard test suites
4. 431 users across US, GB, CN, AU, NG, BR and more — near-100% session replay coverage
5. Commit `8b677d` reverted at 21:34; problem closed at 21:40 — 33 minutes total

---

## Issues to Fix

### `dtctl exec copilot` flag incompatibility (non-blocking)

`--max-field-chars 0` is a `dtctl query` flag, not valid for `dtctl exec copilot`. Remove it
from any CoPilot call template in the skill or docs.

### Davis CoPilot placement (UX)

Invoking CoPilot on beat 2 with only problem metadata produces a hedged, low-value response.
Consider moving CoPilot to after beat 4 (traces), feeding it the exception message and commit
as context — that produces a sharper remediation recommendation. Alternatively, skip CoPilot
on beat 2 entirely and use the deployment timeline to carry the beat.

### Beat 1 deep link URL encoding

The deep link contains literal `"` characters in the segments parameter
(`%5B%7B"id"%3A"Apy24Rcu0cO"%7D%5D`). These should be `%22` to be valid URL-encoded JSON.
Works in practice (browsers decode it) but worth fixing for correctness.

---

## What Worked Well

- All five beat queries executed cleanly — fixes from testrun-01 are in place ✅
- `live_recent` mode handled correctly throughout (past tense, no fixture announcement) ✅
- Side quest (country breakdown mid-beat-1) answered in full and redirected cleanly ✅
- Front-running beat 3→4 handled correctly ✅
- Two distinct exceptions in beat 04 both surfaced and reported ✅
- Peak moment delivery on beats 04 and 05 felt distinct from the routine evidence turns ✅
- Session close with incident timeline and elapsed time delivered cleanly ✅
