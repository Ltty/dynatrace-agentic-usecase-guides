# Demo Test Run 14 — payment-failure, hands-on (`/demo`, explore delivery)

**Date:** 2026-10-20
**Runtime:** `/demo` — `demo-agent` instructions + `investigating-playground-incidents` skill, mapped onto
Claude Code by `skills/local-runtime/SKILL.md` (dtctl in place of `execute-dql`).
**Model:** Sonnet 5.5
**Scenario:** payment-failure (P-26102005)
**Mode:** `live_recent` (problem CLOSED; started 2026-10-20 09:06:51 UTC, ended 09:43:00 UTC; survey ran 10:09:15 UTC)
**Delivery:** `explore`, chosen at the mode question
**Elapsed (survey → last beat query):** 5 minutes (10:09:15 → 10:14:27 UTC)
**Entry path:** `/demo` (empty, greeting) → "what's going on at the moment?" (survey, two findings) → "payment"
(pick, mode question) → "hands-on" (beat 1) → "let's investigate the deployment history" (beat 2) → "show me the
spikes" (beat 3) → "I want to dig into the root cause. can you show me the trace and is there an exception?"
(beat 4) → "yes, show me the customers who were affected" (beat 5 + close) → "give me the handoff for the team"
(handoff block) → "can you show me the code change that resulted in the issue?" (out of telemetry) → this file request

Every value below was read from a result; nothing was summed by hand except where marked **verify**.

---

## User observations (the reason for this file)

The user's notes after the run, in their words, then what the run shows about each.

### 1. The replay link errors in Error Inspector

> the link with the replays gives me an error in error inspector. did you hallucinate a link or is this documented
> somewhere?

Not invented. It is the beat 5 deep link in `scenario-payment-failure.md` (line 327), with `{{TF_FROM_MS}}`,
`{{TF_TO_MS}}` and `{{PROBLEM_ID}}` substituted from the survey row:

```text
https://playground.apps.dynatrace.com/ui/apps/dynatrace.error.inspector/error-explorer?tf=1792486311908%3B1792490280000&problemId=3355862557452222170_1792487211908V2&perspective=impact&sort=affected_users%3Adescending
```

So it is documented, and the documentation is what is wrong or stale. `dynatrace-intelligence/README.md` ("Open
items") already says the error-inspector links "haven't been opened against a live problem yet", and names only
broken-images; payment-failure uses the same link shape and was never opened either. Why Error Inspector rejects it
was not diagnosed in this run (the `problemId` parameter, the `perspective` value and the `sort` value are all
candidates; none was tested).

The block also called it "Replays", which is a claim the link has not earned: it opens an error view, and the replay
list is a step further.

### 2. The failing-requests link opens on the last 30 minutes

> The failing requests link by default comes with a last 30 minutes view instead of setting the correct time
> period, so the view is empty if the error did not occur within the past 30 minutes

The link carried `tf=1792486311908%3B1792490280000` (problem window ± 15 min, from the survey row), and the
distributed-tracing explorer ignored it. Same source: beat 4's deep link in `scenario-payment-failure.md` (line 282).
The `tf` format that the Services explorer link (beat 3) takes does not carry over to this app, or this app needs a
different parameter. The user's read, after the run: a working URL carries `tf=now-12h%3Bnow&v=requests`, and the epoch-millisecond form
the beats file generates is probably not a format this app accepts. Not yet confirmed against an absolute range.
The other deep links of the run were not reported broken. For a closed problem this link is
empty by default, which is the `live_recent` case the demo is mostly run in.

### 3. The "Same view in Dynatrace" link opens the assistant, not the problem record

> This link opens the assistant instead of showing the problem record. I guess it should not show the assist and
> ask something there?

That link is beat 2's deep link in `scenario-payment-failure.md` (line 137), the
`dynatrace.davis.copilot/ask-question` intent with an "Explain what happened in the problem …" prompt and
`execute: true`. It was written for the Dynatrace-hosted agent, where beat 2 hands the causal read to Dynatrace
Intelligence (README: "No separate AI call in beat 2"). Locally the run introduced it with the skill's fixed
"Same view in Dynatrace:" wording (SKILL.md → "Link and close"), which promises the same view as the answer on screen
and delivers a chat. The problem-record link (beat 1) is the one that matches that wording; beat 2 has no
problem-record view of its own to point to. Testruns 10 and 11 marked this link ✅ on the grounds that it is the one
in the beats file; nobody had opened it and judged it against the wording.

---

## Startup and survey

- Empty message treated as a greeting; the skill's greeting used verbatim ✅
- "what's going on at the moment?" → status line "Checking for open issues." (exact wording) ✅
- `dtctl` on PATH; every query bare with `--context playground` ✅
- One survey query, copied whole; no text between the status line and the call ✅

| | payment-failure | broken-images |
|---|---|---|
| Problem | P-26102005, CLOSED | P-26101987, CLOSED |
| Impact (problem record) | 323 affected users | 630 affected users |
| Duration | 36 min | 34 min |
| Ended | 26 min ago | 391 min ago, said "about 7 hours" |
| Cost | roughly $28,101 (`revenue_usd`) | none |

- `disk-cpu-cascade` returned no row and was not mentioned ✅
- Opened on "Two incidents in the last 48 hours, both resolved", one sentence each, ended on exactly "Which one
  should we look at first — payment or images?" ✅
- "payment" → "Payment it is." + the exact mode question, no query ✅
- "hands-on" → one status line, beat 1 at once ✅

---

## Beat 1 — The Page

**Query:** `fetch dt.davis.problems` pinned to the problem ID. One row.

| Field | Value |
|---|---|
| Problem | P-26102005, closed, started 09:06 UTC |
| Root cause | astroshop-payment, failure rate up to 55.36% |
| Affected users | 323 (problem record) |
| Owning team | Team-Financial-Services |
| Also affected | astroshop-frontend (up to 19.14%), the ingress, the browser monitor; 10 entities in all |

- Proof stamp carried the full queryId ✅
- Said checkout-style framing as "listed as affected, not named as the cause" and made no call-direction claim ✅
  (testrun 12 issue 6 did not recur)
- The scenario's reveal says to quote the failing endpoint from `description`. The description names the frontend's
  `POST /*` endpoint and gives no endpoint for payment; none was claimed for payment. The beats file expects more
  than this record holds.
- The problem record's `affected_entity_names` lists 8 names and the description says 10 entities; both were
  reported as returned, 10 as the count.

---

## Beat 2 — The Change

| Commit | First deploy (UTC) | Syncs | vs. problem start |
|---|---|---|---|
| e501ad | 09:04:30 | 5 | 2.4 min before |
| cb8cc4 | 09:37:17 | 1 | 30.4 min after |

- Both on astroshop-payment, shipped by team-astroshop; the owning team (Team-Financial-Services) and the shipper told
  apart ✅
- cb8cc4 not called "the fix" at this point; the read was "only a sequence at this point" ✅
- The turn's "Same view in Dynatrace" link is the Assist link — see observation 3.

---

## Beat 3 — Service Deep Dive

| Bucket (UTC) | Failures / requests | Rate |
|---|---|---|
| 08:50 – 08:55 | 0 / 35, 0 / 61 | 0% |
| 09:00 | 5 / 54 | 9.3% |
| 09:05 | 26 / 56 | 46.4% |
| 09:10 | 30 / 55 | 54.5% (peak) |
| 09:15 – 09:30 | 24–29 per bucket | 43.9–53.7% |
| 09:35 | 11 / 56 | 19.6% |
| 09:40 onward | 0–1 per bucket | 0–1.8% |

- Said it ramps rather than steps, and put each deploy in the bucket that holds it ✅ (testrun 12 issue 7 not
  needed)
- Deployment-marker query skipped because beat 2 had run ✅
- "Failures stop within a few minutes of cb8cc4, which reads as the fix landing; what either commit changed is in
  the diff" — labelled inference, as the data-only rule allows ✅
- Failures labelled as failed Charge spans, not users ✅

---

## Beat 4 — Failing Traces (peak)

**Queries (2, chained, no text between):** exceptions across the window, then the per-service summary for
`d5a2c482ddf84f2c687e190923fbfda4` (`toUid()` used).

**Exception:** "Sorry, we cannot process American Express credit cards. Only Visa or Mastercard are accepted."
`/usr/src/app/charge.js` line 77, 177 failed spans, first seen 09:04:12, last seen 09:36:55.

A second message, "Credit card info is invalid." (line 66), appeared once at 09:45:11, after cb8cc4. Reported as a
separate finding, one span, not recurring.

```text
ingress → frontend → payment   failed (origin: payment)
frontend also called: cart, catalog, currency, shipping, quote, flagd — all clean
```

- Exception alone on its own line before any commentary ✅
- The trace has **no checkout service**. The scenario's staging template reads
  `ingress → frontend → checkout → payment`; this trace had the frontend call payment directly (by the rows' start
  order), so the chain was built from the rows, not from the template. Testrun 12's trace had checkout.
- Onset 09:04:12 against e501ad's event at 09:04:30, and the last failure 09:36:55 against cb8cc4's at 09:37:17:
  "a sync is recorded when it completes" reading used ✅
- Detection: problem opened 2.6 minutes after the first failed span, stated with no judgement ✅
- `failed_spans` labelled span counts, not users ✅
- Proof-stamp placement: the staging wants the exception alone first, the adapter wants the stamp after the beat's
  first query. The run put the exception first and the stamp second. Neither file says which wins.

---

## Beat 5 — The Humans (peak), close and handoff

**Query:** `user.sessions` with `error.http_5xx_count > 0`, grouped by country.

| | Value |
|---|---|
| Sessions with server errors (5xx) | 183 |
| With a replay | 169 |
| Countries | 16, plus 20 sessions with no country recorded |
| Top | US 49/49, no country 20/6, AU 16/16, CN 13/13, GB 12/12 (sessions / with replay) |

- The row with no country reported as exactly that, not counted as a country ✅
- Populations kept apart: 323 users (problem record), 177 failed spans, 183 sessions ✅
- Close delivered in the same response as beat 5: timeline, payoff line ("5 minutes"), replay link, the explore
  way out naming the other incident ✅
- Handoff block on request: rows only from results; `Goes to` Team-Financial-Services, shipper team-astroshop in
  `Cause`; commit shortened to 7 characters (e501adc); `Still open` assembled from stated limits ✅
- Cost in the block came from `revenue_usd` (roughly $28,101) ✅
- The "Replays" and "Failing requests" lines of the block carry the two links from observations 1 and 2.

**Out of telemetry:** "show me the code change" → "That's not in the telemetry", the commit link, the file and
line that point at where to look ✅. The commit link is the `git_url` beat 2 returned, not a constructed one.

---

## Issues to fix

### 1. Verify and repair the payment-failure Error Inspector link (beat 5)

Open the Error Inspector for a real payment problem in the UI, copy the URL it uses, and compare it with the one in
`scenario-payment-failure.md` line 327. Fix the parameters. Same check for broken-images (line 310). Until it is
verified, the handoff block should not call the line "Replays".

### 2. Fix the time range on the failing-requests link (beat 4)

The distributed-tracing explorer did not take `tf=<from>%3B<to>`. Find the parameter that app does take and put it in
line 282; confirm against a closed problem more than 30 minutes old.

### 3. Do not label the Assist link "Same view in Dynatrace" (beat 2)

Either give beat 2 a link that shows a view (the problem record, or the deployment events), or keep the Assist link
and say what it is ("Ask Dynatrace Intelligence to explain it"). SKILL.md's "Link and close" wording makes every
link a promise of the same view as the answer. A link that opens a chat breaks it.

### 4. Check every deep link against a closed problem before ✅-ing it

Testruns 10 and 11 recorded the Assist link as ✅ because it matched the beats file. Add "opened it, it shows what the
label says, for a problem that has ended" to the checklist in `docs/AUTHORING.md`.

### 5. Scenario file: the trace chain template assumes checkout

Beat 4's staging template includes checkout between frontend and payment. This run's trace had none. Say "build the
chain from the rows" ahead of the template, or drop checkout from the example.

### 6. Scenario file: beat 1 expects an endpoint in the description

The reveal says to quote the failing endpoint from `description`. For this problem the description gives the
frontend's endpoint only. Say so, or take the endpoint from beat 3's query.

### 7. Proof stamp vs. peak staging

State in `local-runtime/SKILL.md` or the beat 4 staging whether the stamp goes above or below the exception line.

---

## What worked well

- Greeting, survey, mode question and status lines exactly as written; no resolver, file or survey mentions ✅
- All tool calls before narration; every turn ended on text; no text between chained calls ✅
- Full queryId in every beat's proof stamp ✅
- Two-owner mismatch (Team-Financial-Services vs. team-astroshop) named in beat 2 and used in the handoff ✅
- Three populations kept apart and the null-country row not counted as a country ✅
- Intent and diff content left to the owning team; no "validation regression", no "accidentally", no "global" ✅
- A separate second exception reported as returned, not folded into the first ✅
- Persona held: "we", no "I can't", no "Davis"/"CoPilot" ✅

---

## Proof-stamp queryIds (for verification)

| Query | queryId |
|---|---|
| Survey | `01a158c9-61da-7c0b-b4c7-b341663659b4` |
| Beat 1 problem record | `01a158ca-2dc2-7a6f-ad69-461ad38cf290` |
| Beat 2 deployments | `01a158cb-0bb1-7bea-a983-844ddedffc08` |
| Beat 3 failure rate | `01a158cb-ec96-7e5a-87ed-94a46c5d0c0d` |
| Beat 4 exceptions | `01a158cc-fdae-7aad-84df-3359142ed2c3` |
| Beat 4 trace summary | `01a158cd-16ec-7a09-b54e-da085f495b58` |
| Beat 5 sessions | `01a158ce-24ce-7d90-9c53-7a2cf823fffb` |
