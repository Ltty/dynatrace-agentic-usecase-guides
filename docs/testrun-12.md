# Demo Test Run 12 — payment-failure as a walk-through (`/demo`, briefing delivery)

**Date:** 2026-10-08
**Runtime:** `/demo` — `demo-agent` instructions + `investigating-playground-incidents` skill, mapped onto
Claude Code by `skills/local-runtime/SKILL.md` (dtctl in place of `execute-dql`). First run of the walk-through
delivery (`references/briefing-mode.md`).
**Model:** Sonnet 5.5
**Scenario:** payment-failure (P-2610781)
**Mode:** `live_recent` (problem CLOSED; started 2026-10-08 09:11:00 UTC, ended 09:46:00 UTC; resolver ran 10:17:16 UTC)
**Delivery:** `briefing` from the user's second message
**Elapsed (resolver → last beat query):** 4 minutes (10:17:16 → 10:21:21 UTC)
**Entry path:** `/demo` (empty, greeting) → "what's going on?" (survey, three findings) → "walk me through the payment
incident" (beat 1) → "ok, go on" (beat 2) → "go on" (beat 3) → "ok, go on" (beat 4) → "ok show me" (beat 5 + handoff
block) → this file request

The values marked **verify** are the ones I summed or derived by hand. Everything else was read from a result.

---

## The reason for this file

The run followed the rules. The user's verdict after it was: **no red line.** Each turn was correct and the whole
was not a story. The user's brief for the next iteration, quoted so the intent isn't paraphrased away:

> Assume I am the CPO who gets informed about an incident. I don't have any detailed technical knowledge. I am
> trying to understand what happened, how it's causally connected, which impact it has and why it happened.
> Like: there's been an incident affecting x users in y minutes costing us z$... Failure rates started to rise
> after team x shipped commit z, previously x% errors, after commit z %, 6 minutes later team obviously deployed
> the fix, back to x%. Looking at the exact trace, we can pinpoint the exception, which shows the team
> accidentally introduced a bug that led the system to refuse amex credit cards. User analytics shows it was a
> global outage, affecting x users in z countries. Session replays are available if we want to understand the
> error from a user's angle. So the user is the manager who picks up the phone when the SRE agent says:
> "Houston, we have a problem."

Section "Where the story broke" below is my analysis of why this run did not deliver that. "Target story" shows what
the same data supports. Both are input for the session that owns `briefing-mode.md`; I changed no skill file.

---

## Startup and survey

- Empty message treated as a greeting; the skill's greeting used verbatim ✅
- **User:** "what's going on?" → status line "Checking Astroshop for any open issues." (exact wording) ✅
- `python tools/preflight.py dtctl-path` printed `dtctl`; every query used it bare with `--context playground` ✅
- Three resolvers ran in parallel with no text between the calls ✅

| | payment-failure | broken-images | disk-cpu-cascade |
|---|---|---|---|
| Problem | P-2610781, CLOSED | P-2610759, CLOSED | P-26092140, ACTIVE |
| Impact (problem record) | 350 affected users | 273 affected users | 2 affected entities |
| Duration | 35 min | 34 min | 23 days 12 hours (still open) |
| Ended | 31 min ago | 399 min ago, said "about 7 hours" | — |

**Engine output:** one bullet per finding. Payment: 350 users, 35 minutes, "roughly $30,450" (350 × $87, **verify**).
Images framed as a slowdown, no revenue figure. Host framed as still open, "less than 3%" from the problem
description. Three entry angles, then the exact closing sentence "Or I can take you through the whole thing, start to
finish." ✅

**Notes:**

- The disk-cpu primary resolver returned zero rows and the **fallback** returned P-26092140. The scenario file says
  "this scenario's entities exist on the `dev` tenant only. On any other tenant the resolver returns nothing and the
  survey does not list it." This run was on `playground` and it was listed. Either the tenant note is wrong or the
  fallback matches something the primary was meant to exclude. **Needs a look.**
- The fallback's `root_cause` came back null on that record. The survey line named the `/data` disk from the
  problem description instead, which is honest, but the hook template expects `{root_cause}`.
- **Deviation:** my first fallback call was a field-trimmed copy of the file's DQL, not the file's DQL, and I had to
  rerun the full one for the duration fields. Cost: one extra query (queryIds below). The DQL should be copied
  whole.

---

## Beat 1 — The Page (briefing turn)

**User:** "walk me through the payment incident" → `briefing-mode.md` read before the first beat ✅

**Query:** `fetch dt.davis.problems` pinned to the problem ID. One row.

| Field | Value |
|---|---|
| Problem | P-2610781, CLOSED |
| Root cause | astroshop-payment (Charge endpoint, error rate up to 60%) |
| Affected users | 350 (problem record) |
| Owning team | Team-Financial-Services |
| Also affected | astroshop-checkout, astroshop-frontend, Astroshop, browser monitor, one payment process |

- Finding first, table, proof stamp, meaning, one line naming what comes next, deep link ✅
- Ended on "Next is what changed on payment right before it started." ✅
- **Overreach:** the opening sentence "Checkout calls payment" is not in any result at that point. The problem record
  lists checkout as affected; the call relationship only appears in the trace in beat 4. It should have said
  checkout is listed as affected and wait for the trace.
- The problem's start (09:11:00) was stated as "the Charge endpoint began failing at 09:11 UTC". Beat 4 later showed
  the first failed span at 09:07:06. Beat 1 therefore stated the problem's start as the failure's start, and it was
  corrected only implicitly.

---

## Beat 2 — The Change

**Query:** deployment events on payment + checkout, grouped by commit.

| Commit | First deployed (UTC) | Events | Shipped by |
|---|---|---|---|
| c590ec | 09:07:14 | 10 | team-astroshop |
| dcca03 | 09:37:18 | 2 | team-astroshop |

- c590ec named as the lead suspect from timing alone; said the events don't show what the commit changed ✅
- Owning team (Team-Financial-Services) and shipper (team-astroshop) both named and told apart ✅ — the point run 11
  issue 5 asked for
- dcca03 deliberately not called "the fix" yet ✅
- Gap stated as "about four minutes" before the problem opened (09:07:14 vs 09:11:00 is 3 min 46 s) ✅

---

## Beat 3 — Service Deep Dive

**Queries (2, parallel):** Charge failure rate per 5-minute bucket; deployment markers.

| Bucket (UTC) | Failures / calls | Rate |
|---|---|---|
| 09:00 | 0 / 59 | 0% |
| 09:05 | 12 / 61 | 19.7% |
| 09:10 | 21 / 58 | 36.2% |
| 09:15 | 28 / 60 | 46.7% |
| 09:20 | 24 / 56 | 42.9% |
| 09:25 | 21 / 59 | 35.6% |
| 09:30 | 33 / 54 | 61.1% |
| 09:35 | 11 / 58 | 19.0% |
| 09:40 onward | 0 per bucket | 0% |

- Said plainly that this is a rise and not a clean step, and that 5-minute buckets can't place the first failure
  inside the 09:05 bucket ✅ (the beats file expects a "step change"; the data here has a ramp)
- **Wording error:** the first line said failures "stop in the five minutes that hold dcca03". The 09:35 bucket holds
  that deploy and still has 11 failures; they stop in the next bucket. The table was right and the sentence was
  loose. Beat 4 later gave the last failure at 09:36:55.
- "Stays elevated for as long as c590ec is the latest change" is a causal-sounding line. It is true of the timing; it
  is as far as the data goes.

---

## Beat 4 — Failing Traces (peak)

**Queries (2, chained, no text between):** exceptions across the window, then the per-service summary for
`4cb4b105bd18c87e58c3eedec8c7f3eb` (`toUid()` used).

**Exception (one distinct message):** "Sorry, we cannot process American Express credit cards. Only Mastercard or Visa
are accepted." `/usr/src/app/charge.js` line 77, 150 failed spans, first seen 09:07:06, last seen 09:36:55.

```text
ingress → frontend → checkout → payment   failed (origin: payment)
checkout also called: cart, catalog, currency, shipping, quote, flagd — all clean
```

- Exception alone on its own line, blank line, then what it says and where it is raised ✅
- Onset placed 8 s before c590ec's event and the last failure 23 s before dcca03's event, with the "sync event is
  recorded on completion" reading from the beats file (**verify**: 09:07:06.499 vs 09:07:14.922, and 09:36:55.408 vs
  09:37:18.300) ✅
- "Whether the rule was intended is the owning team's call" ✅
- `failed_spans` labelled a span count, not users ✅
- Run 11 issue 2 (the "validation regression" overreach) did **not** recur ✅

---

## Beat 5 — The Humans (peak) and the handoff block

**Query:** `user.sessions` with `error.http_5xx_count > 0`, grouped by country. 16 rows.

**Evidence:** 160 sessions with a 5xx, 148 with replay (**verify** both sums; the query returns rows only).
US 39/39, no country 17/5, NL 15/15, AU 14/14, CN 12/12, then GB 10 down to IN 3.

- Finding alone on its own line, then the pause ✅
- Populations kept apart: 350 users (problem record) vs. 160 sessions vs. 150 failed spans ✅
- The row with no country reported as exactly that, and not counted as a country ✅ (run 11 issue 4 did not recur;
  the turn says "16 rows", never "16 countries"; it is 15 countries plus the null row)
- Handoff block in the same response, then elapsed time ("4 minutes"), the payoff line and the replay link ✅
- The block's "Goes to" row names Team-Financial-Services; the shipper is team-astroshop in "Cause" ✅
- **No revenue figure in the block.** The scenario defines `avg_order_value_usd` (87) and `briefing-mode.md` allows
  `affected_users × avg_order_value_usd`. The only dollar figure of the whole walk-through is in the survey.
- **No "Written for:" line** on the handoff block. Run 11's handoff had one. The system guidance for this session
  asks for it whenever the output is meant for someone else.
- Briefing never named as a mode ✅; "beat", "step N" and "the demo" never used ✅

---

## Where the story broke

The beats are correct and in the right order. The result is five findings, not an incident. Seven specific reasons:

1. **The answer comes last.** The only turn that contains the whole causal chain is the handoff block, delivered in
   turn 5. A CPO who stops listening after turn 1 knows the root-cause service and nothing about cost, duration,
   change or cause. The first briefing turn should be the whole story in a few lines, and the beats should then be
   the evidence for it.
2. **The money is stated once and dropped.** $30,450 appears in the survey. Beats 1 to 5 and the handoff block never
   repeat it, though the scenario defines the number and the brief asks for it.
3. **The vocabulary is the SRE's.** Charge endpoint, 5xx, span, bucket, ArgoCD sync, queryId. `briefing-mode.md` says
   plain word first, term once; the beat 3 turn is still a table of five-minute buckets. A CPO reads "failure rate
   went from 0% to about 40%", not the bucket rows.
4. **The timeline is never drawn in one place.** The facts exist in the conversation, scattered over four turns:
   first failure 09:07:06, deploy event 09:07:14, problem opened 09:11:00, last failure 09:36:55, second deploy
   09:37:18, problem closed 09:46:00.
5. **Before/after is in beat 3 and not in the handoff block.** The block has no error rate at all. The user's own
   example turns on it ("previously x% errors, after commit z %, back to x%").
6. **Detection time is never said.** Failures began 09:07:06 and the problem opened 09:11:00, about four minutes
   later. It is in the results and is exactly what a CPO asks ("how long were we blind?"). Nothing in the beats file
   asks for it.
7. **Each turn ends on a topic, not on a link to the last turn.** "Next is the exact exception" says what comes
   next, not why the previous finding makes it the next question. The red line is the sentence that joins the turns:
   "the errors started with the change, so what exactly broke?"

---

## Target story from this run's data

What the same results support, in the CPO's order. Every value is from this session's results; the three lines
marked ⚠ are the places the user's example asks for more than the telemetry holds.

> Between 09:11 and 09:46 UTC today (35 minutes), card payments failed in checkout. The problem record counts 350
> affected users; at the scenario's $87 average order that is roughly $30,450 in abandoned carts (350 × $87).
>
> **Cause.** Payment errors began at 09:07:06, 8 seconds before the first deployment event for commit c590ec,
> shipped by team-astroshop. Before it, the payment charge call failed 0 of 59 times (09:00 window); within 25
> minutes it was failing 36% to 61% of calls per five-minute window. About 30 minutes later a second commit, dcca03,
> was deployed (09:37:18); the last failure was 23 seconds before it, and the next window onward shows 0 failures.
> ⚠ "Fix": the data shows the failures stopped around dcca03, not what dcca03 changed. And it was 30 minutes
> later, not "6 minutes later".
>
> **What exactly broke.** The payment service itself refuses the card: "Sorry, we cannot process American Express
> credit cards. Only Mastercard or Visa are accepted." (charge.js line 77). Every other call in the trace was clean.
> ⚠ "Accidentally introduced a bug": the telemetry shows the rule and the timing, not intent. Whether it was a
> mistake or a decision is for Team-Financial-Services, who own the service.
>
> **Who it hit.** 160 customer sessions saw server errors, from 15 countries plus 17 sessions with no country
> recorded; 148 of the 160 have a session replay. ⚠ "Global outage": the data gives a country count, not a
> statement about reach; say the count.
>
> **Detection.** The first failure was at 09:07:06 and the problem opened at 09:11:00, about four minutes later.
>
> **What's needed from you.** Team-Financial-Services owns the revert decision and team-astroshop shipped the
> change. The replays show what customers saw.

That is nine lines. Today's run takes five turns plus a handoff block to deliver the same facts.

---

## Issues to fix

### 1. Add a headline turn that carries the red line

Open a walk-through with one turn that states the whole chain (what, how long, who and how many, cost, cause,
status) in plain words and in the CPO's order, then let the beats be the proof: "Here's how we know". The five
beats keep their DQL and staging unchanged. This is the main change; everything below supports it.

### 2. Carry the headline numbers through every turn and into the handoff block

Duration, affected users (labelled), the dollar figure (when `avg_order_value_usd` is defined) and the before/after
failure rate belong in the block. Suggest adding `Cost:` and `Rate:` rows to the block's template, omitted when the
scenario has no value, like the other rows.

### 3. Give every turn a connecting line

The closing "next is X" line should say why X follows ("the errors started with the change, so next is what exactly
failed").

### 4. Add detection time as a stated fact

First failed request vs. problem start is in the results of beats 1 and 4. Suggest one line in the beat 4 reveal, or
in the headline: "Dynatrace opened the problem about N minutes after the first failure". Never "N minutes of
blindness" (that's inference).

### 5. Decide the policy for the user's three stronger words

"Accidentally", "fix" and "global" are what a CPO will say and what the data-only rule forbids. The skill should say
what to answer when the CPO asks "so was it a bug?": the data shows a rule that rejects one card type, from the
deploy on; intent is the owning team's call. A one-line answer in `briefing-mode.md` → "What does that mean" would
keep the agent from improvising it.

### 6. Beat 1 asserts a link the data hasn't shown

"Checkout calls payment" appears before any trace is read. The beats file's reveal for beat 1 says "checkout is
collateral"; that holds only once beat 4 has run. Suggest "checkout is listed as affected".

### 7. Beat 3's expected "step change" doesn't match this data

The failure rate here is a ramp (19.7%, 36.2%, 46.7%, …, 61.1%, 19.0%, 0%). The beats file asks for "a step change
from near-zero to a sustained elevated failure rate" and "reaches its full level in the next bucket". Run 11 had
the same shape. Suggest "a rise that stays elevated until the second deploy".

### 8. Disk-cpu tenant scope

See Survey notes: the scenario is documented as dev-only and surfaced on `playground` through the fallback, with a
null `root_cause`. Check whether the fallback should be tenant-guarded or the doc corrected.

### 9. "Written for:" on the handoff block

Decide whether the block is a deliverable for someone else (then add the line, as in run 11) or part of the
briefing (then say so in `briefing-mode.md`).

### 10. Resolver DQL should be copied whole

A hand-trimmed fallback query cost one extra round trip. `local-runtime/SKILL.md` could say "run the file's DQL
unchanged".

---

## What worked well

- Greeting, survey, status line, no resolver or fallback mentions ✅
- All tool calls before narration in every turn; every turn ended on text; no text between chained calls ✅
- **Proof stamps carried the full queryId in all five beats.** That was run 10 and 11's top issue ✅
- The two-owner mismatch named and explained in beat 2 and used in the handoff ✅
- Three populations kept apart (350 users, 150 failed spans, 160 sessions) and the null-country row not counted as a
  country ✅
- Intent and diff content left to the owning team; the "validation regression" overreach from runs 10 and 11 gone ✅
- Peak staging followed for beats 4 and 5; the handoff block rows came only from results, nothing guessed ✅
- Elapsed time computed from the two `queried_at` values (4 minutes), not estimated ✅
- Persona held: "we", no "I can't", no "Davis"/"CoPilot", "briefing" never named ✅

---

## Proof-stamp queryIds (for verification)

| Query | queryId |
|---|---|
| Payment resolver (survey) | `01a11b04-68b5-7aac-b6f3-99f0a978240e` |
| Image resolver (survey) | `01a11b04-709a-74a7-8a4c-b122bba04bd4` |
| Disk-cpu primary (survey, empty) | `01a11b04-7842-7fad-9be3-4dedf5326e13` |
| Disk-cpu fallback, trimmed copy | `01a11b04-9515-7d37-b744-2792f75170c3` |
| Disk-cpu fallback, full | `01a11b04-b387-7343-8825-ff7e4310088e` |
| Beat 1 problem record | `01a11b05-6b89-7a1e-9be6-89fa92345574` |
| Beat 2 deployments | `01a11b06-3063-768d-b665-ffd04dc58ce9` |
| Beat 3 failure rate | `01a11b06-d185-7adf-a9e2-8df10168c562` |
| Beat 3 deployment markers | `01a11b06-d88d-7ddf-8634-eb51ff0c5e8b` |
| Beat 4 exceptions | `01a11b07-6820-7f31-a582-d2166e2341c2` |
| Beat 4 trace summary | `01a11b07-7b9a-7232-83dc-76b599525a4a` |
| Beat 5 sessions | `01a11b08-25c8-7b51-ab20-9f8bcacc8d37` |
