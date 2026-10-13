# Demo Test Run 13 — payment-failure as a guided walk-through (`/demo`, briefing delivery)

**Date:** 2026-10-08
**Runtime:** `/demo` — `demo-agent` instructions + `investigating-playground-incidents` skill, mapped onto
Claude Code by `skills/local-runtime/SKILL.md` (dtctl in place of `execute-dql`). Second run of the walk-through
delivery, now with the opening report from `references/briefing-mode.md` (run 12's issue 1).
**Model:** Sonnet 5.5
**Scenario:** payment-failure (P-2610781)
**Mode:** `live_recent` (problem CLOSED; started 2026-10-08 09:11:00 UTC, ended 09:46:00 UTC; resolver ran 10:57:50 UTC)
**Delivery:** `briefing` from the user's third message
**Elapsed (resolver → last beat query):** 1 minute (10:57:50 → 10:58:54 UTC). See issue 1: this number is an artefact
of the opening report, not the length of the walk-through.
**Entry path:** `/demo` (empty, greeting) → "What's going on?" (survey, three findings) → "Take me through the whole
payment incident" (opening report) → "Ok, let's dive into it" (beat 2) → "show me" (beat 3) → "ok" (beat 4) →
"ok" (beat 5 + handoff block) → this file request

The values marked **verify** are the ones I summed or derived by hand. Everything else was read from a result.

---

## What this run tests

Run 12's verdict was "no red line". Its issue 1 asked for a headline turn that carries the whole chain, with the
beats as proof. `briefing-mode.md` now has that. This run checks whether the opening report works as a standalone
story, and whether the five evidence turns read as proof of it rather than as five new findings.

---

## Startup and survey

- Empty message treated as a greeting; the skill's greeting used verbatim ✅
- **User:** "What's going on?" → status line exactly "Checking for open issues." ✅ (run 12 had a reworded one)
- `python tools/preflight.py dtctl-path` printed `dtctl`; every query used it bare with `--context playground` ✅
- Three resolvers ran in parallel with no text between the calls ✅
- The disk-cpu primary returned zero rows, and the **file's fallback DQL ran whole, first time** ✅ (run 12 issue 10)

| | payment-failure | broken-images | disk-cpu-cascade |
|---|---|---|---|
| Problem | P-2610781, CLOSED | P-2610759, CLOSED | P-26092140, ACTIVE |
| Impact (problem record) | 350 affected users | 273 affected users | 2 affected entities |
| Duration | 35 min | 34 min | 23 days 12 hours (still open) |
| Ended | 72 min ago | 440 min ago, said "about 7 hours" | — |

**Engine output:** one bullet per finding. Payment: 350 users, 35 minutes, "roughly $30,450" (350 × $87, **verify**).
Images framed as a slowdown with no revenue figure. Host framed as still open. Three entry angles, then the exact
closing sentence "Or I can take you through the whole thing, start to finish." ✅

**Notes:**

- Run 12's open point recurs: disk-cpu is documented as dev-tenant only, and on `playground` it surfaced through the
  fallback again, with `root_cause` absent on the record. The survey named `/data` from the description. **Still
  needs a look** (run 12 issue 8).

---

## Opening report

**User:** "Take me through the whole payment incident" → `briefing-mode.md`, the beats file and `dql-reference.md`
read before any query ✅

**Queries (5, parallel, no text between):** first fence of beats 1 to 5. The held-back fences (beat 3's deployment
markers, beat 4's trace summary) stayed for the evidence turns ✅ The problem resolver was not rerun ✅

The report ran lead paragraph, Cause, What broke, Who it hit, Detection, then the offer line "I can show you how we
know each of these, starting with the change." One proof stamp, for the first query.

| Part | Value in the report | Source |
|---|---|---|
| Window | 09:11 to 09:46 UTC, 35 minutes | resolver |
| Users, cost | 350 (problem record), about $30,450, labelled an estimate | resolver, **verify** product |
| Cause | first failure 09:07:06, first c590ec sync 09:07:14, 8 s later | beats 2 and 4 |
| Rate | 0% (09:00 bucket) to 61.1% peak (33 of 54), 0% from 09:40 | beat 3 |
| Fix | last failure 09:36:55, 23 s before dcca03 at 09:37:18, "reads as the fix landing" | beats 2 and 4 |
| What broke | American Express rejection, 150 failed spans | beat 4 |
| Who | 160 sessions, 15 countries plus 17 with no country, 148 with replay | beat 5, **verify** sums |
| Detection | problem opened about 4 minutes after the first failure | beats 1 and 4 |

- Every run 12 gap this closes ✅: cost in the first turn (issue 2), before/after rate (issue 2), detection time as a
  fact (issue 4), the fix labelled an inference (issue 5)
- The three words the CPO brief used stayed out: no "accidentally", no "global", and "fix" appeared only as "reads as
  the fix landing" ✅
- **Overreach:** the lead said "On the morning of 8 October". The results hold 09:11 UTC; "morning" assumes a reader's
  time zone. Should have been the UTC time only.
- **Extra part:** I added an "Owner" line (owning team vs. shipper). The spec's six parts have no such line. It is
  useful to the CPO, but it is not in `briefing-mode.md`.
- Length ran at the top of 10–14 lines.

---

## Evidence turn — The Change (beat 2)

**User:** "Ok, let's dive into it". No query; the opening report's deployment result was reused ✅

| Commit | First deploy (UTC) | Syncs | Shipped by |
|---|---|---|---|
| c590ec | 09:07:14 | 10 | team-astroshop |
| dcca03 | 09:37:18 | 2 | team-astroshop |

- Claim clause first ("I said the failures start with the change"), table, stamp, what it adds, connecting line,
  deep link ✅
- The "a sync is recorded when it completes" reading used to explain the 8 s, without hedging ✅
- dcca03 stated as "not a second regression … reads as the fix landing; what it changed is in the diff" ✅
- Owning team and shipper told apart ✅
- Connecting line gave a reason: "The change lines up with the start, so the next question is whether the failure
  rate follows it." ✅ (run 12 issue 3)

---

## Evidence turn — Service Deep Dive (beat 3)

**User:** "show me". One query (the held-back deployment markers); the rate came from the opening report.

| Bucket (UTC) | Calls | Failed | Rate |
|---|---|---|---|
| 09:00 (before) | 59 | 0 | 0% |
| 09:30 (peak) | 54 | 33 | 61.1% |
| 09:40 (after) | 64 | 0 | 0% |

- Condensed to before, peak and after, as `briefing-mode.md` asks, with the span said in words ✅ (run 12 issue 3's
  "table of buckets" is gone)
- Said it is a ramp, not a step, with 19.7% already in the 09:05 bucket that holds the deploy ✅
- Tied the 61.1% peak to the 60% in the problem record ✅
- The stamp is the rate query from the opening report, since that is the beat's main query. The deployment-marker
  query has its own id in the table below.
- The marker query returned only what beat 2 had already shown. It is held back by the briefing table, but it added
  nothing here (issue 4).

---

## Evidence turn — Failing Traces (beat 4, peak)

**User:** "ok". One query (trace summary, chained from the opening report's `trace_id`, `toUid()` used).

Exception on its own line first: "Sorry, we cannot process American Express credit cards. Only Mastercard or Visa are
accepted." `/usr/src/app/charge.js` line 77, 150 failed spans, 09:07:06 to 09:36:55. One distinct message.

```text
ingress → frontend → checkout → payment   failed (origin: payment)
checkout also called: cart, product-catalog, currency, shipping, quote, flagd — all clean
```

- Peak staging followed: finding alone, blank line, explanation, chain, plain statement ✅
- `failed_spans` labelled a span count, not users ✅
- Problem start vs first failure given as times and a gap ✅
- "Whether the rejection was intended is Team-Financial-Services' call" ✅
- **Overreach:** the explanation said payment "throws on purpose" and called it "an error the service throws on
  purpose, not an infrastructure fault". "On purpose" is intent, which the data does not hold, and the very next
  sentence disclaims intent. The beats file's own wording is "an error the service itself raises". Fix the wording
  in the agent, and consider flagging it in the beat 4 reveal.
- The clean calls were listed from the rows, so catalog appears as `product-catalog` and flagd is included. The
  beats file's illustration says "catalog" and omits flagd; the rows were followed ✅

---

## Evidence turn — The Humans (beat 5, peak) and the handoff block

**User:** "ok". No new query; the opening report's session result was reused.

**Evidence:** 160 sessions with a 5xx, 148 with replay (**verify** both sums; the query returns rows only). 16 rows:
15 countries plus the row with no country (17 sessions, 5 with replay).

- Finding alone on its own line, then the pause, then the table ✅
- Populations kept apart: 350 users (problem record) vs. 160 sessions vs. 150 failed spans ✅
- "16 rows in all: 15 countries plus the 17 sessions with no country", reported as exactly that ✅
- Staging asked the source guide's question: what did the checkout screen show when the card was rejected? ✅
- Handoff block in the same response, then elapsed time, payoff and replay link ✅

| Block row | Content | Check |
|---|---|---|
| Impact | 350 affected users (problem record), about $30,450 (estimate) | ✅ run 12 issue 2 |
| Rate | 0% to 61.1% peak, back to 0% | ✅ run 12 issue 2 |
| Detected | problem opened 4 minutes after the first failed request | ✅ run 12 issue 4 |
| Goes to | Team-Financial-Services; shipper team-astroshop in Cause | ✅ |
| Still open | intent, what dcca03 changed, what customers saw on screen | ✅ |

- **Overreach:** "What happened" said checkout failed "for those customers", meaning American Express holders. The
  data shows the rejection message and failed Charge requests, not which customers held which card. Should read as
  the message the payment service returned.
- No "Written for:" line on the block, as `briefing-mode.md` now says ✅ (run 12 issue 9, decided)
- Briefing never named as a mode ✅; "beat", "step N" and "the demo" never used ✅

---

## Issues to fix

### 1. The elapsed time measures query time, not the walk-through

The opening report runs all five beat queries up front, so the last `queried_at` is seconds after the resolver's.
"From page to root cause in 1 minute" is computed correctly by the rule and is misleading: the conversation took far
longer. Either `briefing-mode.md` should say to leave the number out in a walk-through, or the close should take
the elapsed time from the turn that delivers the last evidence, which needs a query there.

### 2. "On purpose" in the beat 4 explanation

See beat 4. It slipped past the data-only rule because it reads like a description, not a conclusion. A one-line
guard in the beat 4 reveal ("raises it itself; never say deliberate or on purpose") would keep it out.

### 3. Two small overreaches to remove

"On the morning of …" in the opening report and "for those customers" in the handoff block. Both add a fact no
field holds.

### 4. Held-back fences that repeat an earlier result

Beat 3's deployment-marker query returned the same two commits and times as beat 2's. In a walk-through the
opening report already holds them. Suggest moving it to "reuse the beat 2 result" in the briefing table.

### 5. Beat 1 has no evidence turn

The opening report covers the problem record, and its closing line offers to start "with the change", so beat 1's
evidence (owning team, impact levels, affected entities) never gets its own table. Decide whether that is intended.
If so, `briefing-mode.md` → "The evidence turns" should say the beats start at 2 in a walk-through.

### 6. Opening report vs. the "Owner" line

The owning-team-versus-shipper line is not one of the six parts. Add it to the spec or drop it.

### 7. Disk-cpu tenant scope (carried from run 12 issue 8)

Unchanged. See the survey notes.

---

## What worked well

- The opening report alone carries the whole story: what, when, how many, cost, cause, rate before and after, who,
  detection, status ✅ This is the red line run 12 lacked.
- The five evidence turns read as proof of the report, each opening with the claim it proves ✅
- Every turn ended on a connecting line that says why the next piece follows ✅
- Full queryId in every stamp, one stamp per turn ✅
- All tool calls before narration; the turn always ended on text; no resolver or fallback mentioned ✅
- Three populations kept apart, and the no-country row never counted as a country ✅
- Fix, intent and reach each stayed within the data (apart from issue 2) ✅
- Persona held: "we", no "I can't", no "Davis"/"CoPilot", "briefing" never named ✅

---

## Proof-stamp queryIds (for verification)

| Query | queryId |
|---|---|
| Payment resolver (survey) | `01a11b29-8e0f-7170-96b4-35b2f9343622` |
| Image resolver (survey) | `01a11b29-9608-7c26-bc64-c1e7ae404141` |
| Disk-cpu primary (survey, empty) | `01a11b29-9dd6-7569-8f8f-19fcc919e50b` |
| Disk-cpu fallback | `01a11b29-bec1-7f91-a52f-d338ac68b94a` |
| Beat 1 problem record (opening report) | `01a11b2a-681f-72f3-ad27-d31fef4c26a6` |
| Beat 2 deployments (opening report) | `01a11b2a-6f53-7a1e-b58f-95f955778ef4` |
| Beat 3 failure rate (opening report) | `01a11b2a-774e-7bfc-8b01-406fd1a84b97` |
| Beat 4 exceptions (opening report) | `01a11b2a-7fc4-79ed-89a5-9ff9f0e389b7` |
| Beat 5 sessions (opening report) | `01a11b2a-8784-75c7-85fc-3450f718f753` |
| Beat 3 deployment markers | `01a11b44-017e-7185-bf3f-624345d48f50` |
| Beat 4 trace summary | `01a11b44-c5e3-7048-9be7-58b9577c3824` |
