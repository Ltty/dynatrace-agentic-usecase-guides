# Demo Test Run 05 — payment-failure scenario

**Date:** 2026-09-28
**Scenario:** payment-failure (P-26093359)
**Mode:** live_recent (problem CLOSED ~21:40 UTC prior night; session started ~08:41 UTC)
**Duration:** ~6 minutes
**Entry path:** Survey → deployment angle → traces (skipping beat-03) → affected users

---

## Preflight

Not run explicitly this session.

---

## Discovery (`/demo`)

**Trigger:** "Any problems I should be aware of?"

**Resolver output (no `--write`):** `mode: live_recent`, `status: CLOSED`, 431 affected users,
started 21:06, ended 21:40, 33-minute window.

**Engine output (paraphrased):**

> Something hit production about 11 hours ago. The payment service failed for 431 users over a
> 33-minute window — checkout requests were erroring hard. At $87 average order value that's
> roughly $37,500 in abandoned carts. Ended on three entry angles: the deployment, the failing
> traces, or the customers who hit it.

**Notes:**

- Survey correctly triggered on "Any problems I should be aware of?" phrasing ✅
- Past-tense `live_recent` framing used throughout ✅
- Revenue impact computed correctly: 431 × $87 = $37,497 ✅
- Resolver called without `--write` for the survey, then with `--write` when the session started ✅
- Ended on 3 concrete entry angles, not yes/no ✅

---

## Beat 01 — The Page

**Skipped.** User asked "Let's start with the deployment. What went wrong?" — jumped directly
to the deployment entry angle from the survey. Engine folded blast-radius context (payment as
root cause, 52.38% failure rate on Charge, checkout as collateral, owning team
Team-Financial-Services) into the beat-02 narration. Beat marked complete in state alongside
beat-02 ✅

---

## Beat 02 — Explain with Davis

**User:** "Let's start with the deployment. What went wrong?"

**Engine:** Ran `python tools/preflight.py resolve payment-failure --write` to write state,
then ran the deployment evidence query.

**Query:** `beat-02-deployment-events.dql` — ran cleanly, 5 records returned ✅

**Evidence returned:**

| Time (UTC) | Commit | Services | Role |
|---|---|---|---|
| 21:06:53 | — | — | Problem starts |
| 21:12:31 | `b35672` | payment + checkout | Culprit deploy |
| 21:15:57 | `b35672` | payment | Re-sync |
| 21:34:10 | `8b677d` | payment + checkout | Fix/rollback |
| 21:40:00 | — | — | Problem closes |

**Davis CoPilot:** Called with PATH set correctly before the raw `dtctl` call ✅. No
`--max-field-chars 0` flag passed ✅. Fed commit SHAs and timestamps as context; confirmed
`b35672` as the regression carrier, `8b677d` as the fix, with specific recommendation to diff
the two commits. Sharp, grounded answer.

**State update order:** `Edit .demo-state.json` before narrative text ✅

**Deep link:** Davis Problem view, placeholder resolved from state ✅

---

## Beat 03 — Service Deep Dive

**Skipped entirely.** User front-ran to traces immediately after the deployment evidence. The
deployment-to-failure correlation was solid enough from beat-02 that the failure-rate time
series was not needed. Beat marked complete in state alongside beat-04.

---

## Beat 04 — Failing Traces (peak moment)

**User:** "show me the traces"

**Queries:**

- `beat-04-failing-spans.dql` — ran cleanly, 5 records returned, two distinct exceptions ✅
- `beat-04-trace-waterfall.dql` (chained, `--var TRACE_ID=8af0d233...`) — ran cleanly,
  34 spans returned, ASCII waterfall rendered ✅

**Evidence — two distinct exceptions in `charge.js`:**

| Exception message | File | Line | Spans |
|---|---|---|---|
| "Sorry, we cannot process American Express credit cards. Only Visa or Mastercard are accepted." | charge.js | 77 | 4 of 5 |
| "Credit card info is invalid." | charge.js | 66 | 1 of 5 |

**Evidence — waterfall (condensed):**

Entry (edge) → frontend → checkout PlaceOrder → [cart, catalog ×2, currency ×3, shipping,
quote, flagd ×2 — all clean] → **payment Charge ❌**

**State update order:** `Edit .demo-state.json` before narrative text ✅

**Narration delivered immediately — no "continue" required.** The testrun-04 bug (engine wrote
"No response requested." after the state update) did not recur. The SKILL.md reinforcement
("Complete all tool calls … you MUST write narration") was effective ✅

**Narration quality:**
- Exception messages landed verbatim before commentary ✅
- Both distinct exceptions surfaced and flagged as a second finding ✅
- Bug characterised as business-logic regression (Amex rejection) not infrastructure ✅
- Waterfall condensed: 13 clean downstream calls folded to one line, 4 meaningful hops shown ✅
- Payment isolated as the single real failure; upstream all clean ✅
- Deep link: Distributed Tracing / Charge endpoint ✅

---

## Beat 05 — The Humans (peak moment)

**User:** "yes"

**Query:** `beat-05-affected-sessions.dql` — ran cleanly, 16 country records returned ✅

**Evidence (top rows):**

| Country | Sessions | With Replay |
|---|---|---|
| US | 51 | 51 |
| (unknown) | 20 | 8 |
| GB | 14 | 14 |
| CN | 13 | 13 |
| AU | 11 | 11 |
| NG | 11 | 11 |
| BR | 9 | 9 |
| + 9 more | 53 | 53 |

Total: **182 sessions** with 5xx errors across 16 countries; **170 with session replay**. Near-
total replay coverage on all known-country rows.

**Number integrity:** Correctly summed all 16 rows to derive 182 total — no stale count from
a prior run carried forward (the testrun-04 "310 sessions" error did not recur) ✅

**State update order:** `Edit .demo-state.json` before narrative text ✅

**Peak moment framing:** Reframed the count as 182 real people, not 182 error events. Session
replay described concretely — an SRE can open a recording and watch exactly what the customer
saw and clicked, not infer it from logs. Posed the genuine open question: did the UI give visual
feedback on the failed payment, or did it silently do nothing? Invited the user to open a replay
via the deep link ✅

**Deep link:** Error Inspector — affected sessions ✅

---

## Session Close

**Inline with beat-05 response** (no explicit recap requested).

Incident timeline delivered:
1. Davis opened P-26093359 at 21:06 — 431 users, payment Charge endpoint, $37,500 at risk
2. ArgoCD deployed commit `b35672` at 21:12 — culprit, introducing Amex rejection in charge.js
3. Two distinct exceptions: line 77 (Amex rejection, 4 spans) and line 66 (generic invalid, 1 span)
4. Full distributed trace confirmed: 13 clean downstream hops, failure fully isolated to payment
5. 182 sessions across 16 countries, 170 with session replay
6. `8b677d` rolled back at 21:34; problem closed at 21:40 — 33 minutes total

Payoff contrast delivered: "Page to root cause in under 8 minutes. Without correlated traces,
deployment markers, and session replay, this is hours of grepping logs and guessing which of
several recent deploys is responsible." ✅

---

## Issues to Fix

None identified. All testrun-04 regressions were resolved:
- Narration-dropped bug did not recur ✅
- Stale session count did not recur ✅
- Trailing tool call bug did not recur ✅

---

## What Worked Well

- Survey triggered correctly on "Any problems I should be aware of?" — a natural-language
  variant not in the greeting starters ✅
- Beat 01 blast-radius context folded cleanly into beat-02 narration; owning team
  (Team-Financial-Services) explicitly named as part of the incident-response value ✅
- Mandatory narration rule held across all beats — no silent turns after tool calls ✅
- Two distinct exceptions in beat-04 both surfaced and characterised ✅
- Waterfall condensed correctly — 34 spans collapsed to 4 meaningful rows ✅
- Beat-03 skipped without loss — causation was already established ✅
- Beat-05 session count correctly derived by summing all 16 query rows ✅
- Peak moment beats (04, 05) felt tonally distinct from evidence beats ✅
- Davis CoPilot answer was specific and grounded because it was fed real deployment data ✅
- Session close inline with beat-05 worked naturally; no abrupt "recap" mode ✅
