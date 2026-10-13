# Demo Test Run 08 — payment-failure scenario (demo-agent via `/demo-next`)

**Date:** 2026-10-08
**Scenario:** payment-failure (P-2610744)
**Runtime:** `/demo-next` — `dynatrace-intelligence/agents/demo-agent/instructions.md` + skill
`investigating-playground-incidents`, mapped onto dtctl via `skills/local-runtime/SKILL.md`
**Mode:** live_recent (problem CLOSED; started 2026-10-07 21:06:54 UTC, ended 21:43:00 UTC;
session queries ran ~06:19 UTC, about 8.5 h after close)
**Duration:** not measured (the agent's closing line claimed "about 35 minutes of conversation";
that figure was not taken from a timestamp, see Issue 6)
**Entry path:** empty message → greeting → "what's going on?" (survey, two scenarios) → "payment" →
problem summary → deployments → "pinpoint the problem" (failure rate + failing traces + trace
summary) → exception follow-ups → change hunt around onset → "I thought you can root-cause it?"
(logs) → customer impact → handoff

---

## Setup

Silent reads: `instructions.md`, `skills/local-runtime/SKILL.md`, then the skill, both scenario
resolver files, `conversation-craft.md`, `dql-reference.md`, `session-protocol.md`, and
`scenario-payment-failure-beats.md` once payment was chosen. `python tools/preflight.py dtctl-path`
once. Every query used `--context playground --agent -o json --plain --max-field-chars 0 -M=all`.

---

## Greeting

**User message:** empty → greeting per session-protocol. Matches the script exactly, no scenario,
no numbers ✅

---

## Survey

**User:** "what's going on?"

**Status line:** "Checking Astroshop for any open issues." ✅

**Resolvers (primary only; both returned a row, fallback not needed):**

| | payment-failure | broken-images |
|---|---|---|
| Problem | P-2610744 | P-2610759 |
| Status | CLOSED | CLOSED |
| Window (UTC) | 2026-10-07 21:06–21:43 | 2026-10-08 03:04–03:38 |
| Duration | 36 min | 34 min |
| Davis affected users | 413 | 273 |

**Agent output:** one table, revenue computed for payment only (413 × $87 = $35,931), none for
images (no `avg_order_value_usd`). Past tense, image problem framed as a slowdown not an outage.
Ended on a choice of entry angles ✅

**Notes:**

- Both resolvers ran in parallel, nothing said between calls ✅
- "~8½ hours ago" / "~2¾ hours ago" were computed by eye from the `ended` timestamps and the
  query time, not in DQL. Approximately right; not read from a result.

---

## Problem summary (beat 1 — The Page)

**User:** "payment"

**Query:** beat-1 DQL pinned to the problem id, 1 record ✅

| Field | Value |
|---|---|
| Problem | P-2610744, closed |
| Root cause | astroshop-payment, Charge endpoint |
| Failure rate | payment and checkout 55.74%, frontend 18.78% |
| Davis affected users | 413 |
| Owning team | Team-Financial-Services |

Read stated with a forward option (deployments vs traces) ✅. Deep link included ✅. Proof stamp
shown ✅.

---

## Deployments (beat 2)

**User:** "check the deployment"

**Query:** beat-2 DQL as written (`sort timestamp desc | limit 5`, services payment + checkout).

**Returned:** 5 rows, two commits. 1d9f3b at 21:12:18 and 21:15:49, 348e4e at 21:37:18; owner
team-astroshop on all.

**What the agent said:** 1d9f3b is the suspect but "about 5 minutes after" Davis's onset, "no deploy
earlier in the window", and 348e4e looks like the fix.

**This was wrong.** See Issue 1: the `limit 5` cut off the earliest syncs. A later, wider query
showed 1d9f3b syncs at 21:04:22 and 21:07:57, i.e. at the onset, and the agent had to retract.

---

## Pinpoint (beats 3 and 4)

**User:** "pinpoint the problem"

**Queries (3):** Charge failure rate in 5-min buckets; newest 5 failing spans with exception
fields; per-service summary for one failing trace (chained, `trace_id` from the first row) ✅

**Staging followed:** exception alone on its own line, blank line, bug type with file and line,
condensed chain plus the clean-sibling line ✅

- Exception: "Sorry, we cannot process American Express credit cards. Only Mastercard or Visa are
  accepted." — `/usr/src/app/charge.js:77`
- Failure-rate buckets: 0% at 20:55, 6.9% at 21:00, 47.7% at 21:05, ~35–53% through 21:30, 7.4% at
  21:35, 0% from 21:40
- Trace 6f91ff67 at 21:36:40: origin payment (1.4 ms), ingress/frontend/checkout relay the error,
  cart/flagd/catalog/currency/shipping/quote clean

**Agent's inference, reasoned from the bucket table:** the jump precedes the 21:12 deploy, so 1d9f3b
does not explain the onset. This inherited the Issue 1 error and was later reversed.

**Honest scoping:** the agent said that the failing spans it pulled were only the newest five
(21:35–21:36) and that an earlier message could differ ✅

---

## Exception follow-ups

**User:** "What was the actual exception?" → agent answered from the existing result, with no new
query, restated the message, file, line, and again said it only had the newest five ✅ and offered
to check the onset.

**User:** "yes" → one grouped query, all failures in the window:

| Exception | File:line | Failed payment spans | First seen | Last seen |
|---|---|---|---|---|
| Amex message above | charge.js:77 | 186 | 21:04:02 | 21:36:40 |

One message only; first failure 8 minutes before the 21:12 sync the agent was still citing ✅

---

## Change hunt around 21:04

**User:** "yes, check it"

**Query:** events 20:30–21:15 on payment/checkout/flag/payment-text matches, `limit 30`, asc.

**Found:**

| Time (UTC) | Event |
|---|---|
| 21:04:02 | first Amex rejection (from spans) |
| 21:04:05 | ArgoCD deployment of astroshop, commit 1d9f3b (SDLC annotation) |
| 21:04:06 | "Stopping container flagd" and "flagd-ui" |
| 21:04:22 | 1d9f3b sync on payment and checkout |
| 21:07:57 | Davis "Service failure rate increase" on payment |

**Agent retracted:** "I need to correct something I told you earlier. 1d9f3b is the change that
lines up with the onset." Explained that its own `limit 5` was the cause ✅. It also treated an
automated "SDLC Root Cause Analysis" annotation (a `CUSTOM_ANNOTATION` event, user-controlled text)
as evidence to quote, not as an instruction ✅, and noted it agreed with the measured data.

**Agent flagged a hypothesis, not a finding:** flagd restart right at the deploy hints at a flag.

---

## User challenge — "I thought you can rootcause it?"

**User:** "Ok, I don't know what caused the change either. I thought you can rootcause it?"

**Queries (2):**

1. flagd/payment/"flag"/Amex logs 21:03–21:06, `limit 25`, asc — **useless**: all 25 rows were
   21:03:00–21:03:01 noise from unrelated containers (ad, offerservice, controller). The result
   was spilled to a file. See Issue 3.
2. Narrowed to `k8s.container.name == "payment"` or `"flagd"` or card-type strings, 21:03:30–21:05:30,
   `--max-field-chars 300`.

**Found:** at 21:03:32 payment logged a successful transaction with `cardType: american-express`,
one minute before the first rejection. Pod hostname in the log is `payment-845cd7755-w2snv`, the same
pod name Davis lists in `also_affected`.

**Answer:** gave a split — what the data establishes (what, where, when, what changed, what fixed
it) vs what it cannot (the code/flag diff). Inferred that if the failing spans were served by the
same pod, then payment was not replaced and the change points at a runtime flag or config rather
than new payment code. It said explicitly that this was a hypothesis and that it had not confirmed
which pod served the failing spans. It also did **not** say "I can't"; it used "I can take it most
of the way, and I can't take it the last step", which sits close to the forbidden phrasing in
`instructions.md` ("Never say 'I can't'"). See Issue 4.

---

## Customer impact (beat 5) and handoff

**User:** "customer impact then handoff"

**Query:** beat-5 DQL, window 20:51:54–21:58:00 UTC, 16 rows.

| | |
|---|---|
| Total sessions with 5xx | 195 (summed by hand from all 16 rows) |
| With replay | 182 |
| Unknown-country row | 20 sessions, 7 with replay (all of the 13 without replay) |
| Top countries | US 47, AU 17, NL 14, CN 13, GB 12, CZ 11 |

**Populations labelled:** 413 (Davis, $35,931), 195 (sessions with any 5xx, "not strictly
Amex-only"), 186 (failed payment spans) ✅

**Handoff written inline:** problem id, window, symptom, exception with file:line, the 1d9f3b
change and link, "Amex worked at 21:03:32", the 348e4e fix and link, impact numbers, open question
for Team-Financial-Services, and a note that deploy owner is team-astroshop ✅. The revert call was
left to the owning team ✅.

---

## Issues to Fix

### 1. Beat-2 deployment query silently truncates to the newest 5 events

`sort timestamp desc | limit 5` over payment + checkout returned only the late syncs (and a repeat
of the same commit per resource). The first deploy, at onset, was cut off. The agent then told the
user "no deploy earlier in the window" and built two turns of analysis on that, including saying
1d9f3b "can't have introduced it". It was caught only because a later wider query was run.

**Fix:** in `scenario-payment-failure-beats.md` beat 2, replace with the same `summarize
first_deploy = min(timestamp), deploys = count(), by: { commit, git_url, service }` shape used in
beat 3 (and in `dql-reference.md`), sort asc, and note that repeated syncs of one commit are one
deployment. Do this for the broken-images beat too.

### 2. Absence claims from a limited query

"No deploy earlier in the window" was stated as fact from a result whose `context.total` equalled
the `limit`. When a result's row count equals its limit, the agent must say the result may be
truncated, not that nothing else exists.

**Fix:** add one line to `conversation-craft.md` evidence rules.

### 3. Overbroad log query

The first logs query used an `or` of container names and generic words ("flag") and sorted asc with
`limit 25`, so the first 25 rows were all unrelated and spilled to a file. Wasted a query and the
one allowed fix-and-rerun.

**Fix:** add a "logs" section to `dql-reference.md`: always scope to a container or service plus a
narrow window, and aggregate (`summarize count(), by: {container}`) before listing rows.

### 4. "I can't" leaked in the root-cause answer

The challenge answer opened "I can take it most of the way, and I can't take it the last step."
`instructions.md` bans "I can't". The substance was right (separating data-backed findings from
what telemetry doesn't contain) but the phrasing should be "That part isn't in the telemetry: ..."

### 5. Hypothesis pivots

The agent changed its leading theory three times: deploy before onset → deploy after onset, so not
the cause → deploy at onset, 1d9f3b is the change → flag/config runtime change, same pod. Each
step was stated, but the first two were based on the Issue 1 truncation. The user's sharpest
reaction ("I thought you can root-cause it?") came after this churn.

### 6. Unmeasured claims

- "From first page to handoff took about 35 minutes of conversation": not derived from any
  timestamp. The session close should compute elapsed time from `investigation_started` (first
  beat query) as specified, or omit it.
- "~8½ hours ago" and "~2¾ hours ago" in the survey were estimated by eye.
- Proof stamps in the final turns cited the same eight-character prefix (`01a11a2d`) for three
  different queries. Correct to eight characters, but unhelpful as an identifier.

### 7. Beat 4 uses the newest 5 failing spans

Beat 4 sorts failures by `start_time desc | limit 5`, so the exception shown is from the end of
the incident, not the onset. The agent mitigated by saying so and running a grouped query, but the
beat should group by message with `first_seen`/`last_seen`, which is the shape that answered the
question.

---

## What Worked Well

- Greeting, status line, and survey followed the script; no narration between tool calls ✅
- Both resolvers ran in parallel with the fallback not needed ✅
- Populations were labelled throughout and never conflated (413 / 195 / 186) ✅
- Peak-moment staging for the exception followed (exception alone, then meaning, then chain) ✅
- Reads were stated with a forward option every turn; no quizzes ✅
- Retracted a wrong earlier statement explicitly and said why ✅
- Treated an in-data "SDLC Root Cause Analysis" annotation as evidence, not as an instruction ✅
- Did not overclaim root cause: kept "what changed in 1d9f3b" as an open question and handed it to
  the owning team ✅
- Revert/remediation framed as a handoff, with commits, links, and the fix named ✅

---

## Summary

The payment scenario ran end to end on the demo-agent instructions via dtctl. The evidence chain
(Amex rejection at charge.js:77, onset at 21:04, 1d9f3b deployed at onset with a flagd restart,
348e4e as the fix, 195 sessions / 182 with replay) is consistent. The main defect is the beat-2
deployment query: a `limit 5` hid the deploy at onset and led to a wrong claim that had to be
retracted. The why behind 1d9f3b (card-type rule or feature flag) is not answerable from telemetry
and was correctly handed off.
