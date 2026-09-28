# Demo Test Run 04 — payment-failure scenario

**Date:** 2026-09-28
**Scenario:** payment-failure (P-26093359)
**Mode:** live_recent (problem CLOSED ~21:40 UTC prior night; session started ~08:01 UTC)
**Duration:** ~8 minutes
**Entry path:** Survey → deployment angle → traces (skipping beat-03) → affected users

---

## Preflight

Not run explicitly this session.

---

## Discovery (`/demo`)

**Trigger:** "What changed in the last few hours?"

**Resolver output (no `--write`):** `mode: live_recent`, `status: CLOSED`, 431 affected users,
started 21:06, ended 21:40, 33-minute window.

**Engine output (paraphrased):**

> Something hit production last night. The payment service failed for 431 users over a
> 33-minute window — checkout requests were erroring hard. At $87 average order value that's
> roughly $37,500 in abandoned carts. End on three entry angles: the deployment, the failing
> traces, or the customers who hit it.

**Notes:**

- Survey correctly triggered on the "What changed in the last few hours?" phrasing — not just
  the exact greeting starters ✅
- Past-tense `live_recent` framing used throughout ✅
- Revenue impact computed correctly: 431 × $87 = $37,497 ✅
- Resolver called without `--write` for the survey ✅
- Ended on 3 concrete entry angles, not yes/no ✅

---

## Beat 01 — The Page

**Skipped.** User chose the deployment entry angle from the survey. Engine folded the
blast-radius context (payment as root cause, checkout as collateral) into the beat-02
narration. Beat marked complete alongside beat-02 in state ✅

---

## Beat 02 — Explain with Davis

**User:** "the deployment that likely caused it"

**Engine:** Ran `python tools/preflight.py resolve payment-failure --write` to start the
session, then ran the deployment evidence query.

**Query:** `beat-02-deployment-events.dql` — ran cleanly, 5 records returned ✅

**Evidence returned:**

| Time (UTC) | Commit | Services | Role |
|---|---|---|---|
| 21:06:53 | — | — | Problem starts |
| 21:12:31 | `b35672` | payment + checkout | Culprit deploy |
| 21:15:57 | `b35672` | payment | Re-sync |
| 21:34:10 | `8b677d` | payment + checkout | Fix/rollback |
| 21:40:00 | — | — | Problem closes |

**Davis CoPilot:** Called correctly — no `--max-field-chars 0` flag ✅. Fed commit SHA and
timestamps as context; confirmed `b35672` as the regression, `8b677d` as the fix, recommended
reverting. Sharp, specific answer because it was grounded in actual deployment data.

**State update order:** `Edit .demo-state.json` ran before the narrative text — trailing tool
call bug did NOT occur this turn ✅

**Deep link:** Davis Problem view, placeholder resolved from state ✅

---

## Beat 03 — Service Deep Dive

**Skipped entirely.** User front-ran directly to traces. The deployment-to-failure correlation
was already established in beat-02 with sufficient clarity that the failure-rate time series
was not needed to advance the investigation. Beat marked complete in state alongside beat-04.

---

## Beat 04 — Failing Traces (peak moment)

**User:** "show me the traces"

**Queries:**

- `beat-04-failing-spans.dql` — ran cleanly, 5 records returned, two distinct exceptions ✅
- `beat-04-trace-waterfall.dql` (chained, `--var TRACE_ID=8af0d233...`) — ran cleanly,
  16 spans returned ✅

**Evidence — two distinct exceptions in `charge.js`:**

| Exception message | File | Line | Spans |
|---|---|---|---|
| "Sorry, we cannot process American Express credit cards. Only Visa or Mastercard are accepted." | charge.js | 77 | 4 of 5 |
| "Credit card info is invalid." | charge.js | 66 | 1 of 5 |

**Evidence — waterfall (condensed):**

Entry (edge) → frontend → checkout PlaceOrder → [cart, catalog ×2, currency ×3, shipping,
quote, flagd ×2 — all clean] → **payment Charge ❌**

**State update order:** `Edit .demo-state.json` ran before text output ✅

**⚠️ Narration dropped entirely (new failure mode):** After completing all tool calls and
the state update, the engine wrote "No response requested." instead of narrating the
findings. User was left with visible query results and no interpretation. Required "continue"
to get the narration. This is different from the trailing-tool-call visibility bug in
testruns 02–03 — the state update was in the right position, but the engine forgot to
produce narration at all.

Root cause: engine appears to have treated the state-update `Edit` as the final action of
the turn and mentally closed the beat without writing the narrative. The beat loop rule
("update state first, narrate last") was followed structurally but the narrate step was
skipped.

**After "continue" — narration delivered correctly:**
- Exception messages landed verbatim on their own lines before commentary ✅
- Both distinct exceptions surfaced and flagged as a second finding ✅
- Bug characterised as business-logic regression (Amex rejection) not infrastructure ✅
- Waterfall condensed: downstream calls folded into one line, only 4 meaningful hops shown ✅
- Payment isolated as the single real failure; upstream hops all clean ✅
- Deep link: Distributed Tracing / Charge endpoint ✅

---

## Beat 05 — The Humans (peak moment)

**User:** "show me the affected users"

**Query:** `beat-05-affected-sessions.dql` — ran cleanly, 10 country records returned ✅

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
| + 3 more | — | — |

Near-100% session replay availability on known-country rows.

**State update order:** `Edit .demo-state.json` before narrative text — no visibility
issue ✅

**Peak moment framing:** Session replay described concretely — "310 recordings of real
people trying to pay for something and hitting a wall." Genuine open question posed: did
the UI give any visual feedback on the failed payment, or did it silently do nothing? ✅

**Deep link:** Error Inspector — affected sessions ✅

---

## Session Close

**Inline with beat-05 response** (no explicit recap requested).

Incident timeline delivered:
1. Davis opened P-26093359 at 21:06 — 431 users, payment Charge endpoint, $37,500 at risk
2. ArgoCD deployed commit `b35672` to astroshop-payment at 21:12 — the regression carrier
3. `charge.js` line 77 rejecting Amex outright; line 66 a second validation failure
4. 310 recorded sessions across US, GB, CN, AU, NG, BR and more — near-100% replay coverage
5. `8b677d` rolled back at 21:34; problem closed at 21:40 — 33 minutes total

Payoff contrast: "Page to root cause in ~7 minutes. Without correlated traces, deployment
markers, and session replay, this is hours of grepping logs across services." ✅

---

## Issues to Fix

### Beat 04: narration dropped after correct state update

The trailing-tool-call fix (state update before narration) was applied correctly, but the
engine still failed to narrate — it wrote "No response requested." instead. The structural
order was right; the content was wrong. The beat loop rule needs to be more explicit: updating
state before narrating is necessary but not sufficient — the narration step must actually run,
not be silently skipped.

**Suggested reinforcement in SKILL.md:** Add an explicit note under rule 4 of "The beat loop"
that the final step is mandatory, not optional — something like: "After the state update, you
must write narration. 'No response requested' or a blank turn is a bug, even if the tool calls
completed correctly."

---

## What Worked Well

- Survey triggered correctly on "What changed in the last few hours?" — not just the exact
  greeting starters ✅
- Trailing tool call visibility bug from testruns 02–03 not triggered this session — state
  updates consistently came before narration (except the skipped narration in beat 04) ✅
- Chained waterfall query ran correctly: trace ID extracted from beat-04-failing-spans,
  injected via `--var TRACE_ID=...`, waterfall resolved cleanly ✅
- Two distinct exceptions in beat 04 both surfaced and described ✅
- Waterfall condensed correctly — ~16 spans collapsed to 4 meaningful rows ✅
- Beat 03 skipped without loss — deployment-to-failure causation was already solid from beat 02 ✅
- Davis CoPilot gave a specific, actionable response because it was fed real deployment data ✅
- Beat 05 peak moment framing landed well — concrete description of what session replay
  actually means rather than just a user count ✅
