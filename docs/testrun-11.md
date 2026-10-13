# Demo Test Run 11 — payment-failure on the Dynatrace skill (`/demo`)

**Date:** 2026-10-08
**Runtime:** `/demo` — `demo-agent` instructions + `investigating-playground-incidents` skill, mapped onto
Claude Code by `skills/local-runtime/SKILL.md` (dtctl in place of `execute-dql`; no `.demo-state`)
**Scenario:** payment-failure (P-2610744)
**Mode:** `live_recent` (problem CLOSED; started 2026-10-07 21:06:54 UTC, ended 21:43:00 UTC; resolver ran 2026-10-08 08:21:24 UTC)
**Elapsed (resolver → last beat query):** 2 minutes (08:21:24 → 08:23:45 UTC)
**Entry path:** `/demo` (empty, greeting) → `/demo-doctor` (all checks passed) → `/demo` again (empty, greeting) →
"what's going on" (survey, two scenarios) → "payment" (beat 1) → "show me the deployments" (beat 2) →
"can you pinpoint exact issue?" (jump to beat 4, beat 3 folded in) → "show me the customer impact" (beat 5 + close) →
"ok, write the handoff" → this file request

All numbers below were read from this session's query results. The values marked **verify** are the ones I
derived by hand and are the ones to check first.

---

## Startup

- Read `instructions.md`, `skills/local-runtime/SKILL.md` and SKILL.md first ✅
- Empty message treated as a greeting; the skill's greeting used verbatim: no scenario, no incident, no numbers ✅
- `python tools/preflight.py dtctl-path` printed `dtctl` (on PATH); every query used it bare with `--context playground` ✅
- Before the survey I read both scenario resolver files and `dql-reference.md`, with no text between the reads ✅

---

## Survey

**User:** "what's going on"

**Status line:** "Checking Astroshop for any open issues." (exact wording) ✅
Both primary resolvers ran together. Neither returned empty, so no fallback.

| | payment-failure | broken-images |
|---|---|---|
| Problem | P-2610744, CLOSED | P-2610759, CLOSED |
| Affected users (problem record) | 413 | 273 |
| Duration | 36 min | 34 min |
| Ended | 638 min ago | 283 min ago |

**Engine output:** One bullet per scenario. Payment framed as failing checkouts, images as a slowdown and not an
outage. Time-ago wording "about 11 hours" (638 min) and "about 5 hours" (283 min). Revenue impact on payment:
413 × $87 = $35,931, said as "roughly $35,900" (**verify**). No revenue figure for images. Ended on a choice
between the two incidents.

**Notes:**

- Past tense for both `live_recent` problems ✅
- No proof stamp in the survey ✅
- No resolver, fallback or file mentions ✅

---

## Beat 1 — The Page

**User:** "payment"

**Query:** `fetch dt.davis.problems` pinned to the resolved problem ID. One row.

| Field | Value |
|---|---|
| Problem | P-2610744, CLOSED |
| Started | 2026-10-07 21:06:54 UTC |
| Root cause | astroshop-payment |
| Affected users (problem record) | 413 |
| Owning team | Team-Financial-Services |

- Read stated and attached to a choice (what changed on payment vs. the exception) ✅
- Checkout framed as collateral; the 55.74% on both payment and checkout came from the problem description
  fetched in the survey ✅
- Owning team named from live data ✅
- Deep link: problem view with the segment ✅
- **Error:** proof stamp read "queryId …2a4f5". The real last 8 characters are **aa03a4f5**
  (queryId `01a11a9a-a290-7bd9-b938-c1d2aa03a4f5`). It was five characters, and one of them was wrong.

---

## Beat 2 — The Change

**User:** "show me the deployments"

**Query:** deployment events on payment + checkout, grouped by commit.

| Commit | First deployed (UTC) | Syncs | Owner |
|---|---|---|---|
| 1d9f3b | 2026-10-07 21:04:22 | 10 | team-astroshop |
| 348e4e | 2026-10-07 21:37:18 | 2 | team-astroshop |

- 1d9f3b named as the suspect (about 2.5 min before the problem opened), 348e4e as the likely fix
  (about 6 min before it closed) ✅
- Said explicitly that this was timing only and that failures starting with 1d9f3b was still to confirm ✅
- Offered two concrete next angles ✅
- Deep link: the Dynatrace Intelligence ask-question link from the beats file ✅
- **Error:** proof stamp read "…9750200", seven characters. The last 8 are **99750200**.

---

## Beats 3 + 4 — Service Deep Dive (folded in) and Failing Traces (peak)

**User:** "can you pinpoint exact issue?"

**Queries (3):** exceptions across the window; Charge failure rate per 5 min bucket (beat 3, folded in);
chained per-service trace summary on `3abbb62f18ee4bc11a67793206d6ba84` (`toUid()` used). The first two ran in
parallel. Beat 3's deployment-marker query was skipped; beat 2 had already established the deploy times.

**Failure rate:** 0% at 20:55; 6.9% at 21:00 (6 of 87); 47.7% at 21:05 (31 of 65); 34.2–53.2% from 21:10 to
21:30; 7.4% at 21:35; 0% from 21:40.

**Exception (one distinct message):**

> Sorry, we cannot process American Express credit cards. Only Mastercard or Visa are accepted.

`/usr/src/app/charge.js` line 77, 186 failed spans, first seen 21:04:02, last seen 21:36:40.

**First failing trace:** ingress, frontend, checkout and payment failed; cart, product-catalog, currency,
shipping, quote and flagd were clean. Payment was the origin.

- Peak staging followed: exception alone on its own line, then the kind of bug, then the chain and the plain
  statement of origin ✅
- Onset 20 s before the first deploy event treated as the same change, per the beats file ✅
- Last failure (21:36:40) placed 38 s before 348e4e was recorded, supporting it as the fix ✅
- `failed_spans` labelled a span count, not users ✅
- Said the diff is not in the telemetry ✅
- Ended on a choice (customer impact vs. handoff) ✅
- **Error:** I wrote a line between tool calls ("Now the trace for the earliest failure.") after the first
  status line. The instructions say nothing between tool calls.
- **Overreach:** "a validation regression in the payment code" and "the exact issue is commit 1d9f3b, which made
  payment reject American Express cards" state a code-level cause. The telemetry shows the timing, the failure
  rate and the exception, not what the commit changed. I did add that I had not read the diff.
- **Error:** proof stamp covered only the trace query, and read "…b1dc441", seven characters. The last 8 are
  **6b1dc441**. The exception and failure-rate queryIds were not shown.

---

## Beat 5 — The Humans (peak) and Session close

**User:** "show me the customer impact"

**Query:** `user.sessions` with `error.http_5xx_count > 0`, grouped by country. 16 rows.

**Evidence:** 195 sessions with a 5xx, 182 with replay (**verify** both sums; the query returns rows only).
Top rows: US 47/47, no country 20/7, AU 17/17, NL 14/14, CN 13/13, GB 12/12.

- Populations labelled correctly: 195 sessions vs. 413 affected users on the problem record ✅
- The no-country row called out with its replay count ✅
- Replay framed concretely; the "what did the shopper see?" question posed as the open item ✅
- Session close delivered in the same response: one line per beat, "2 minutes", the payoff line, the replay link ✅
- **Error:** proof stamp read "…531a82f", seven characters. The last 8 are **8531a82f**.
- **Error:** "16 country buckets" counted the no-country row as a country. It is 15 countries plus one
  null-country row.

---

## Off-script asks

**"ok, write the handoff"** is not an out-of-role ask: an incident was open. Answered with the full package from
results already in the conversation, headed "Written for: Team-Financial-Services" ✅ It listed the service
owner (Team-Financial-Services) and the deploy owner (team-astroshop) but did not point out that they differ.

**"write this testrun to testrun-11.md"** is a developer request, the same case as run 10. I stepped out of
character to write this file, since the user said it was for the skill development session.

---

## Issues to fix

### 1. Proof stamps are still wrong (carried over from run 10)

Every stamp this run was short: five characters (and one wrong) in beat 1, seven in beats 2, 4 and 5. The skill
asks for the last 8 characters and the stamp is copied by hand from a long queryId. Suggest the local runtime
adds the last 8 characters to what it prints, or the skill shows a stamp for the primary query only and says to
count eight from the end.

### 2. The beat 4 reveal invites a causal claim the telemetry does not support

The beats file says the exception "reads as a business-logic validation regression (rejecting input that should
be valid)". That is a statement about intent, and the same overreach was noted in run 10 ("rejected valid
input"). Suggest rewording to: a business-rule rejection that starts with the deploy; whether it was intended is
the owner's call.

### 3. Text between tool calls

The chained trace query is run after the exception query returns, which makes a line of narration between the
calls tempting. The rule is clear in instructions.md but the chained-query section of conversation-craft doesn't
repeat it. Suggest a one-line reminder there.

### 4. Counts that include a null bucket

"16 country buckets" included the no-country row. The beat 5 reveal could say "countries plus a row with no
country" so the count isn't misstated.

### 5. Handoff owner mismatch

The handoff shows two different owners without saying who to call. Run 10 flagged the mismatch explicitly. The
handoff fields table could say: owning_team pages first, the deploy owner is who shipped it.

### 6. Beat 3 deploy-bucket nuance (carried over)

The deploy at 21:04:22 sits in the 21:00 bucket (6.9%) and the step to 47.7% shows in the 21:05 bucket. I put
this in a table note. The beats file still says the deploy is "inside the same 5-minute bucket as the jump".

### 7. Elapsed time depends on how fast the user types

2 minutes this run vs. 13 in run 10, same scenario. The payoff line is built on this number, so a fast run
undercuts the "hours of grepping" comparison. No change proposed; noting it.

---

## What worked well

- Greeting, survey, status line and the no-mention-of-resolvers rule followed exactly ✅
- All tool calls before narration in every turn (apart from the one stray line in beat 4); every turn ended on text ✅
- Persona held: "we", no "I can't", no "Davis"/"CoPilot", no beat/step vocabulary ✅
- Every rotating value (SHA, exception, line, counts, team) came from a live result ✅
- Three populations kept apart: 413 problem-record users, 186 failed spans, 195 sessions ✅
- Honest about what the data cannot show (the diff, what the UI displayed to customers) ✅
- Jump to the exception handled with the failure-rate fold-in and peak staging ✅
- Close delivered in the same response as the last beat ✅
