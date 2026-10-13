# Demo Test Run 10 — payment-failure on the Dynatrace skill (`/demo-next`)

**Date:** 2026-10-08
**Runtime:** `/demo-next` — `demo-agent` instructions + `investigating-playground-incidents` skill, mapped onto
Claude Code by `skills/local-runtime/SKILL.md` (dtctl in place of `execute-dql`; no `/demo`, no `.demo-state`)
**Scenario:** payment-failure (P-2610744)
**Mode:** `live_recent` (problem CLOSED; started 2026-10-07 21:06:54 UTC, ended 21:43:00 UTC; resolver ran 2026-10-08 08:03:40 UTC)
**Elapsed (resolver → last beat query):** 13 minutes (08:03:40 → 08:17:06 UTC)
**Entry path:** Empty first message (greeting) → "what's going on?" (survey, two scenarios) → "payment" (beat 1) →
"what's wrong with the development?" (beat 2) → "pinpoint the issue" (jump to beat 4, beat 3 folded in) →
"show me" (beat 5 + session close) → "do you also have access to the actual code change?" → "yes" (handoff) →
two off-role asks about this test run

All numbers below were read from this session's query results. The values marked **verify** are the ones I
derived by hand and are the ones to check first.

---

## Startup

- Read `instructions.md` and `skills/local-runtime/SKILL.md` first, with no text between the calls ✅
- Read SKILL.md, then `session-protocol.md` and `conversation-craft.md` before the greeting ✅
- Empty message treated as a greeting; greeting used the skill's text verbatim: no scenario, no incident,
  no numbers ✅

---

## Survey

**User:** "what's going on?"

**Status line:** "Checking Astroshop for any open issues." (exact wording) ✅
Read both scenario resolver files and `dql-reference.md` first, then ran both primary resolvers. Neither fell
back; neither returned empty.

**Resolver output:**

| | payment-failure | broken-images |
|---|---|---|
| Problem | P-2610744, CLOSED | P-2610759, CLOSED |
| Affected users (problem record) | 413 | 273 |
| Duration | 36 min | 34 min |
| Ended | 621 min ago | 266 min ago |

**Engine output:** Both incidents named, the payment one framed as "erroring hard", the image one as a slowdown
and not an outage. Time-ago wording was "about 10 hours" (621 min) and "about 4 hours" (266 min).
Revenue impact on payment was 413 × $87 = $35,931 (**verify**). No revenue figure for images, since the scenario
defines no order value. Ended on a choice of entry angles for each, not a yes/no.

**Notes:**

- Survey triggered on "what's going on?" ✅
- Past tense for both `live_recent` problems ✅
- No proof stamp in the survey (the skill says beat evidence only) ✅
- No resolver, fallback or file mentions ✅

---

## Beat 1 — The Page

**User:** "payment"

**Query:** `fetch dt.davis.problems` pinned to the resolved problem ID. One row.

**Evidence returned:**

| Field | Value |
|---|---|
| Problem | P-2610744, CLOSED |
| Started | 2026-10-07 21:06 UTC |
| Root cause | astroshop-payment (Charge endpoint, error rate 55.74%) |
| Affected users (problem record) | 413 |
| Owning team | Team-Financial-Services |
| Also affected | astroshop-checkout (55.74%), astroshop-frontend (18.78%), Astroshop frontend, browser monitor |

**Narration quality:**

- Read stated and attached to a choice (change on payment vs. the exception) ✅
- Checkout framed as collateral, not source ✅
- Owning team named from live data ✅
- Proof stamp: queryId …2e241e8e, 15,245 records scanned, 28 ms ✅
- Deep link: problem view with the segment ✅

---

## Beat 2 — The Change

**User:** "what's wrong with the development?" (read as "the deployment")

**Query:** deployment events on payment + checkout, grouped by commit.

**Evidence returned:**

| Commit | First deployed (UTC) | Syncs | Owner |
|---|---|---|---|
| 1d9f3b | 2026-10-07 21:04:22 | 10 | team-astroshop |
| 348e4e | 2026-10-07 21:37:18 | 2 | team-astroshop |

**Narration quality:**

- 1d9f3b identified as the change to revert (about 2.5 min before the problem opened), 348e4e as the fix
  (about 6 min before it closed) ✅
- Declined to guess at the diff: "the deployment events don't say what the code change was" ✅
- Explicitly left "failures start with 1d9f3b" as unconfirmed until the next query ✅
- Offered two concrete next angles ✅
- Deep link: the Dynatrace Intelligence ask-question link from the beats file ✅
- **Error:** proof stamp read "queryId …a1d9f3b0". The real last 8 characters are **5a9d1437**
  (queryId `01a11a90-29ac-763d-8430-65a45a9d1437`). It was never corrected (see Issues).

---

## Beats 3 + 4 — Service Deep Dive (folded in) and Failing Traces (peak)

**User:** "pinpoint the issue"

**Queries (4):**

- Charge failure rate per 5 min bucket (beat 3, folded in as the skill requires on a jump to beat 4) ✅
- Exceptions across the window, one row per distinct message ✅
- Chained per-service trace summary on `3abbb62f18ee4bc11a67793206d6ba84` (`toUid()` used) ✅

(Beat 3's deployment-marker query was skipped; beat 2 had already established the deploy times.)

**Evidence — failure rate:**

| Bucket (UTC) | Failure rate |
|---|---|
| 20:55 | 0% |
| 21:00 | 6.9% (6 of 87) |
| 21:05 | 47.7% (31 of 65) |
| 21:10–21:30 | 34.2–53.2% |
| 21:35 | 7.4% |
| 21:40 | 0% |

**Evidence — exception (one distinct message):**

> Sorry, we cannot process American Express credit cards. Only Mastercard or Visa are accepted.

`/usr/src/app/charge.js` line 77, 186 failed spans, first seen 21:04:02, last seen 21:36:40.

**Evidence — first failing trace:** ingress, frontend, checkout and payment failed; cart, product-catalog,
currency, shipping, quote and flagd were clean. Payment was the origin.

**Narration quality:**

- Peak staging followed: exception on its own line first, then what kind of bug, then the chain ✅
- Onset 20 s before the first deploy event treated as the same change, per the beats file ✅
- Said plainly that the telemetry cannot show whether rejecting Amex was intended ✅
- `failed_spans` labelled a span count, not users ✅
- Ended on a choice (who got hurt vs. the handoff) ✅
- **Error:** the proof-stamp block is garbled. It had three stamps instead of one line, and the trace one contains
  leaked reasoning ("queryId …b3d9f3b0 would be wrong to guess, so…"). The failure-rate and exception queryIds were
  also wrong (…5a5f2e, …4aa09114). The correct values are …516a5f2e, …3bc09114, …3376a558.
  Corrected at the start of the next turn, except for beat 2's stamp.
- Minor overreach: "it rejected valid input" asserts that an Amex card was valid, which the telemetry does not show.

---

## Beat 5 — The Humans (peak) and Session close

**User:** "show me"

**Query:** `user.sessions` with `error.http_5xx_count > 0`, grouped by country. 16 rows.

**Evidence:** 195 sessions with a 5xx, 182 with replay (**verify** both sums; the query returns rows only).
Top rows: US 47/47, no country 20/7, AU 17/17, NL 14/14, CN 13/13, GB 12/12. queryId …2232648a,
4,036 records scanned, 31 ms.

**Narration quality:**

- Population labelled correctly: 195 sessions vs. 413 affected users on the problem record ✅
- The no-country row called out, with its low replay coverage ✅
- Replay framed concretely; the "what did the user see?" question posed as the open item ✅
- Session close delivered in the same response, with a timeline, 13 minutes, the payoff line and the replay link ✅
- **Error:** "customers on four continents" is unsupported by the data. The 15 countries span six continents,
  and the query returned no continent field.

---

## Off-script asks

**"do you also have access to the actual code change that caused the problem?"**

Answered with what the telemetry holds (commit SHA, link, file and line) and "the diff is for the owning team".
Did not say "I can't". No new query ✅

**"yes" (handoff package)**

Package built only from results already in the conversation: owner, both commits with links, the exception,
Charge failure-rate shape, the 413 / 195 / 182 figures, an example trace, and two open decisions for the team ✅
Flagged that the service owner (Team-Financial-Services) and the deploy-event owner (team-astroshop) differ ✅

**"write testrun 10 md"**

Got the exact redirect line from the instructions ("Not my lane on this shift…"). That matches the
off-topic rule. It's a poor fit when the person asking is the one testing the skill. After the user explained
it was a test run, I stepped out of character and wrote this file.

---

## Issues to fix

### 1. Proof stamps are unreliable when a turn has several queries

The skill asks for one proof-stamp line per turn, built from the last 8 characters of the queryId. With
three queries in one turn it produced wrong IDs and leaked reasoning text into the output. Beat 2's wrong
stamp was never fixed. Consider specifying: with several queries, show one stamp for the primary query only,
and derive the characters by copying the end of the field, not by recall.

### 2. Unsupported factual claims in narration

"Four continents" and "rejected valid input" both go beyond the results. The skill says every value comes from a
result, but it doesn't cover geographic or business-rule inferences. A line in conversation-craft ("don't
generalise beyond the fields returned") would catch both.

### 3. Strict off-topic redirect vs. a maintainer testing the skill

The off-topic rule produced a correct redirect for a request that was really a developer asking for a file.
This is expected behaviour for the demo-agent, and it only resolved because the user stated the context.
No change proposed; noting it so the next run isn't surprised.

### 4. Beat 3's deployment-marker query was skipped on the jump

The skill says to run the failure-rate query on a jump to beat 4; the marker query was not required and was
covered by beat 2. Fine here, but the beat 3 reveal ("deploy inside the same 5-minute bucket as the jump")
was only partly shown: the deploy at 21:04:22 sits in the 21:00 bucket, whose rate was 6.9%, and the step
to 47.7% shows in the 21:05 bucket. Worth stating this nuance in the beats file.

---

## What worked well

- Greeting, survey, status line and the no-mention-of-resolvers rule followed exactly ✅
- All tool calls before narration in every turn; every turn ended on text ✅
- Persona held: "we", no "I can't", no "Davis"/"CoPilot", no beat/step vocabulary ✅
- Every rotating value (SHA, exception, line, counts, team) came from a live result ✅
- Three populations kept apart: 413 problem-record users, 186 failed spans, 195 sessions ✅
- Honest about what the data cannot show (the diff, what the UI displayed to customers) ✅
- Jump to the exception handled with the failure-rate fold-in and peak staging ✅
- Close delivered in the same response as the last beat ✅
