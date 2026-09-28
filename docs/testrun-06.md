# Demo Test Run 06 — payment-failure scenario

**Date:** 2026-09-28
**Scenario:** payment-failure (P-26093359)
**Mode:** live_recent (problem CLOSED ~21:40 UTC prior night; session started ~08:55 UTC)
**Duration:** ~15 minutes
**Entry path:** Survey → deployment timeline (beat-02) → failure-rate time series (beat-03) →
failing traces (beat-04) → affected users (beat-05) → explicit recap

---

## Preflight

Not run explicitly this session.

---

## Discovery (`/demo`)

**Trigger:** "Are there any ongoing issues I should be aware of?"

**Resolver output (no `--write`):** `mode: live_recent`, `status: CLOSED`, 431 affected users,
started 21:06, ended 21:40, 33-minute window.

**Engine output (paraphrased):**

> Something's wrong in production. The payment service failed hard for 431 users over a
> 33-minute window. Checkout was down with it — but checkout is downstream; payment's the actual
> break. At $87 average order value, roughly $37,500 in abandoned carts. Ended on three concrete
> entry angles: the deployment timeline, the failing traces, or the affected customers.

**Notes:**

- Survey triggered correctly on "Are there any ongoing issues I should be aware of?" — a new
  natural-language variant not seen in previous testruns ✅
- Past-tense `live_recent` framing used throughout ✅
- Revenue impact computed correctly: 431 × $87 = $37,497 ✅
- Resolver called without `--write` for survey step; `--write` deferred until session started ✅
- Ended on 3 concrete entry angles, not yes/no ✅

---

## Beat 01 — The Page

**Skipped.** User chose "show me the deployment timeline to identify the root cause" directly
from the survey entry angles. Blast-radius context (payment as root cause, 431 users, checkout
as collateral) already established in the survey response and carried into beat-02 narration.
Beat marked complete alongside beat-02 ✅

---

## Beat 02 — Explain with Davis

**User:** "show me the deployment timeline to identify the rootcause"

**Engine:** Ran `python tools/preflight.py resolve payment-failure --write` to write state,
then ran the deployment evidence query, then Davis CoPilot.

**Query:** `beat-02-deployment-events.dql` — ran cleanly, 5 records returned ✅

**Evidence returned:**

| Time (UTC) | Commit | Services | Role |
|---|---|---|---|
| 21:04 | — | — | b35672 first touches payment (see beat-03 note) |
| 21:06 | — | — | Davis opens problem (431 users) |
| 21:12 | `b35672` | payment + checkout | Culprit deploy (ArgoCD sync event) |
| 21:15 | `b35672` | payment | Re-sync |
| 21:34 | `8b677d` | payment + checkout | Fix deploy |
| 21:40 | — | — | Problem closes |

**Davis CoPilot:** Called with PATH set correctly ✅. No `--max-field-chars 0` flag passed ✅.
Fed commit SHAs, problem start, and fix-deploy timestamps as context; confirmed `b35672` as
likely root cause, `8b677d` as fix, recommended revert. Sharp, grounded answer.

**Apparent 6-minute gap flagged:** Beat-02 events query showed `b35672` at 21:12 while Davis
logged the problem at 21:06, creating an apparent timing discrepancy. Engine flagged this
explicitly and noted the failure-rate time series (beat-03) would resolve it ✅

**Deep link:** Davis CoPilot analysis of P-26093359, placeholder resolved from state ✅

---

## Beat 03 — Service Deep Dive

**User:** "pull the failure rate time series"

**Queries:**

- `beat-03-service-failure-rate.dql` — ran cleanly, 13 5-minute buckets returned ✅
- `beat-03-deployment-marker.dql` — ran cleanly, 2 commits returned ✅

**Deployment marker timestamp discrepancy resolved:** The deployment-marker query uses
`min(timestamp)` per commit on the payment service directly, returning `b35672` at
**21:04:13** — earlier than the ArgoCD sync event timestamp of 21:12 reported in beat-02.
This resolves the apparent gap: `b35672` touched payment at 21:04, *before* Davis detected
the problem at 21:06. ArgoCD's pipeline produces multiple event timestamps; beat-02 returned
the sync event, beat-03 the earliest activity. Engine reconciled both without contradiction ✅

**Evidence — failure rate on Charge endpoint (5-min buckets):**

| Bucket (UTC) | Failure rate | Note |
|---|---|---|
| 20:50–21:00 | 0% | clean baseline |
| 21:00 | 6.8% | b35672 at 21:04 — failures begin |
| 21:05 | 46.9% | full spike; Davis pages at 21:06 |
| 21:10–21:30 | 27–44% | sustained |
| 21:35 | 0% | 8b677d at 21:34 — immediate recovery |
| 21:40+ | ~0% | back to baseline |

**Narration quality:**
- Deployment marker at 21:04 confirmed as falling inside the 21:00 bucket, same as failure
  onset — "smoking gun" alignment stated explicitly ✅
- Actual before/after percentages stated (0% → 47%) ✅
- Fix-to-recovery alignment also noted: 8b677d at 21:34, next bucket clean ✅
- Deep link: Payment service performance — incident window ✅

---

## Beat 04 — Failing Traces (peak moment)

**User:** "yes" (accepting suggestion to pull the failing traces)

**Queries:**

- `beat-04-failing-spans.dql` — ran cleanly, 5 records, two distinct exception messages ✅
- `beat-04-trace-waterfall.dql` (chained, `--var TRACE_ID=8af0d23389645118aae08e8f4a42e52a`,
  `--render waterfall`) — ran cleanly, 34 spans, ASCII waterfall rendered ✅

**Evidence — two distinct exceptions in `/usr/src/app/charge.js`:**

| Exception message | Line | Spans | Timing |
|---|---|---|---|
| "Sorry, we cannot process American Express credit cards. Only Visa or Mastercard are accepted." | 77 | 4 | 21:32–21:33 (during incident) |
| "Credit card info is invalid." | 66 | 1 | 21:43 (post-fix) |

**Evidence — waterfall (condensed):**

Entry (edge) → frontend → checkout PlaceOrder → [cart, catalog ×2, currency ×3, shipping,
quote, flagd ×2 — all clean] → **payment Charge ❌**

**Narration quality:**
- Exception messages landed verbatim before any commentary ✅
- Both distinct exceptions surfaced ✅
- Peak moment staging followed: exception on its own line, then characterisation, then waterfall ✅
- Bug characterised as business-logic regression (card-type allowlist), not infrastructure ✅
- Waterfall condensed: 13 clean downstream calls folded to one line, 3–4 meaningful hops shown ✅
- Payment isolated as the single failure point; upstream entirely clean ✅
- Deep link: Distributed Tracing / Charge endpoint ✅

**User follow-up:** "does this means there's a mix where some people entered an invalid credit
card info, and a second one where Amex is rejected? or is this the same issue?"

**Engine response:** Correctly disambiguated using timestamps — the Amex rejection (line 77,
4 traces, 21:32–21:33) is the regression; the "credit card info is invalid" (line 66, 1 trace,
21:43) happened 9 minutes after the fix deployed and 3 minutes after the problem closed. Engine
named it as likely a genuine user error on post-fix traffic, not a second bug ✅

This is the first testrun where the user probed the two-exception finding. The timestamp-based
disambiguation worked cleanly and required no additional query.

---

## Beat 05 — The Humans (peak moment)

**User:** "ok, show me the affected users"

**Query:** `beat-05-affected-sessions.dql` — ran cleanly, 16 country records returned ✅

**Evidence (top rows):**

| Country | Sessions | With replay |
|---|---|---|
| US | 51 | 51 |
| (unknown) | 20 | 8 |
| GB | 14 | 14 |
| CN | 13 | 13 |
| AU | 11 | 11 |
| NG | 11 | 11 |
| BR | 9 | 9 |
| + 9 more | 69 | 61 |

Total: **182 sessions** with 5xx errors across 16 countries; **170 with session replay** (93%
coverage).

**Number integrity:** All 16 rows summed to derive 182 — no stale count carried forward ✅

**Population labelling:** Session count (182, from beat-05 query) correctly distinguished from
Davis `affected_users` (431, from problem record). Not conflated ✅

**Peak moment framing:** Reframed count as 182 real people, not 182 error events. Session replay
described concretely — watch exactly what the customer saw and clicked, not infer from logs.
Posed the genuine open question: did the UI give visual feedback on the failed payment, or did
it silently do nothing? Invited the user to open a replay via the deep link ✅

**Deep link:** Error Inspector — affected sessions ✅

---

## Session Close

**Explicit recap requested** ("recap the issue"). Engine delivered the incident timeline as a
structured summary with actual values, total session elapsed time (~10 minutes stated), and the
payoff contrast framing.

Incident timeline delivered:
1. Commit `b35672` deployed to astroshop-payment at 21:04 — card-type allowlist introduced
2. Failure rate: 0% → 47% in one 5-minute bucket; Davis opened P-26093359 at 21:06
3. Root cause: Amex rejection in `/usr/src/app/charge.js` line 77; isolated to payment service
4. Fix: `8b677d` deployed at 21:34; failure rate dropped to 0% in the next bucket
5. Customer impact: 182 sessions with 5xx errors, 170 with session replay, 16 countries

Payoff contrast delivered: "From Davis alert to root cause — specific commit, specific file,
specific line — in about 10 minutes. Without correlated traces, deployment markers, and session
replay, this is hours of grepping logs." ✅

---

## Issues to Fix

None identified. All previously known regressions continue to hold:
- Narration-dropped bug (testrun-04) did not recur ✅
- Stale session count (testrun-04) did not recur ✅
- Trailing tool call bug did not recur ✅
- Mid-session `.demo-state.json` edit (testrun-04) did not recur ✅

---

## What Worked Well

- Survey triggered correctly on an unseen natural-language variant ✅
- Apparent 6-minute timing gap (beat-02 event vs. Davis detection) flagged proactively and
  resolved cleanly by beat-03 deployment-marker query ✅
- Beat-03 ran for the first time in this test series — failure-rate time series + deployment
  marker alignment delivered clearly; before/after percentages and bucket timestamps both stated ✅
- Two distinct exceptions in beat-04 both surfaced; timestamp-based disambiguation answered a
  direct user follow-up question correctly and concisely ✅
- User follow-up ("same issue or different?") handled without additional queries — timing
  evidence already in context ✅
- Waterfall condensed correctly; 34 spans to 4 meaningful rows ✅
- All five beats covered in sequence for the first time across this test series ✅
- Explicit recap delivered cleanly when requested; actual values used throughout, no
  placeholders ✅
- Davis `affected_users` (431) and session-query count (182) never conflated ✅
