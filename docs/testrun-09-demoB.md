# Demo Test Run 09 — payment-failure scenario (demo-agent via `/demo-next`, mode B)

**Date:** 2026-10-08
**Scenario:** payment-failure (P-2610744)
**Runtime:** `/demo-next` — `dynatrace-intelligence/agents/demo-agent/instructions.md` + skill
`investigating-playground-incidents`, mapped onto dtctl via `skills/local-runtime/SKILL.md`
**Mode:** live_recent (problem CLOSED; started 2026-10-07 21:06:54 UTC, ended 21:43:00 UTC;
session queries ran about 07:22 UTC, about 9.5 h after close)
**Duration:** not measured. The run stopped after the failing-traces turn, so no session close or
elapsed time was delivered.
**Entry path:** empty message → greeting → "what's going on?" (survey, two scenarios) → "payment" →
problem summary → "check the deployment" → "pinpoint the problem" (exceptions + trace summary) →
stopped

---

## Setup

Silent reads: `instructions.md`, `skills/local-runtime/SKILL.md`, then the skill and
`session-protocol.md` for the greeting. At the survey: both scenario resolver files,
`conversation-craft.md`, `dql-reference.md`. `scenario-payment-failure-beats.md` only once payment
was chosen. `python tools/preflight.py dtctl-path` once. Every query used
`--context playground --agent -o json --plain --max-field-chars 0 -M=all`.

---

## Greeting

**User message:** empty → greeting verbatim from session-protocol. Generic, three starters, no
scenario, no numbers ✅

---

## Survey

**User:** "what's going on?"

**Status line:** "Checking Astroshop for any open issues." ✅ Both primary resolvers ran in parallel,
nothing said between calls, fallback not needed.

| | payment-failure | broken-images |
|---|---|---|
| Problem | P-2610744 | P-2610759 |
| Status | CLOSED | CLOSED |
| Window (UTC) | 2026-10-07 21:06–21:43 | 2026-10-08 03:04–03:38 |
| Duration | 36 min | 34 min |
| Davis affected users | 413 | 273 |

**Agent output:** one table, revenue for payment only (413 × $87 = $35,931), none for images. Past
tense; images framed as a slowdown (6.21 s against a 24.74 ms baseline). Ended on entry angles ✅. No
proof stamp in the survey ✅.

---

## Problem summary (beat 1)

**User:** "payment" → beat 1 query pinned to the problem id, 1 record ✅

- Root cause astroshop-payment, Charge endpoint, error rate up to 55.74% (checkout the same, frontend
  18.78%)
- Davis affected users 413; owning team Team-Financial-Services

Read stated with a forward option ✅. Deep link ✅. Proof stamp ✅.

---

## Deployments (beat 2)

**User:** "check the deployment"

**Query:** the grouped shape (`summarize first_deploy = min(timestamp), deploys = count(), by:
{ commit, git_url, owner, stage, app }`, sort asc, no `limit`). This is the fix for testrun-08
Issue 1 and it held.

| Commit | First deploy (UTC) | Syncs |
|---|---|---|
| 1d9f3b | 21:04:22 | 10 |
| 348e4e | 21:37:18 | 2 |

**Agent said:** 1d9f3b landed about 2.5 minutes before Davis's onset (21:06:54) and is the change to
revert; 348e4e looks like the fix, landing 6 minutes before the problem closed. Named
Team-Financial-Services as the owning team and linked the commit. Said the timing alone doesn't prove
the fix ✅. No truncation, no false absence claim.

---

## Pinpoint (beat 4, front-run past beat 3)

**User:** "pinpoint the problem"

**Queries (2):** grouped exceptions over the whole window (one row per distinct message with
`first_seen`/`last_seen`), then the per-service summary for the first failing trace (chained,
`trace_id` from row 1).

| Exception | File:line | Failed payment spans | First seen | Last seen |
|---|---|---|---|---|
| Amex message | `/usr/src/app/charge.js:77` | 186 | 21:04:02 | 21:36:40 |

Exception line alone first, then the bug type, then the chain (ingress → frontend → checkout →
payment, origin payment, cart/catalog/currency/shipping/quote/flagd clean) ✅. Peak staging followed.

**Agent noted:** the first failure (21:04:02) is about 20 s before the first recorded 1d9f3b deploy
event (21:04:22). It said the exact sequence is unproven (rollout in progress or late-stamped event)
rather than smoothing it over ✅. The last failure (21:36:40) is 40 s before 348e4e's first deploy,
which fits the fix.

Beat 3 (failure rate over time) was skipped because the user jumped ahead. That is allowed
(front-running), but the 55.74% failure-rate step change was never shown as buckets.

---

## Issues to Fix

### 1. "I can't" in the pinpoint answer

The agent wrote "I can't pin that gap down from these results." `instructions.md` bans "I can't".
Same class as testrun-08 Issue 4. Should read "These results don't settle that gap."

### 2. Beat 2 asserted a link the query had not shown

The deployments turn said "the failures follow it closely" about 1d9f3b. At that point only the
problem start time had been read, not any failure timing. The claim happened to hold (first failure
21:04:02), but it was a read ahead of the evidence.

### 3. Same eight-character queryId prefix on different queries

The pinpoint turn cited `01a11a65` for both queries (and earlier turns used the same prefix too).
Correct to eight characters but not usable to tell queries apart. Same as testrun-08 Issue 6. Either
show a longer prefix or the stamp's other fields only.

### 4. 20 s gap before the first deploy event is unexplained

First failure precedes the first deploy event. Telemetry here cannot say whether the rollout started
earlier or the event is stamped late. Worth deciding whether the scenario should state a rule (for
example, "failure onset within a minute of the first sync counts as the same change") so the agent
doesn't have to hedge each time.

---

## What Worked Well

- Greeting, status line and survey followed the script; no text between tool calls ✅
- Beat 2 and beat 4 use the grouped, unlimited queries, which removed the truncation failure seen in
  testrun-08 ✅
- Single exception, one population per number (413 Davis users, 186 failed spans) ✅
- Honest about the timing gap and about what the timing alone proves ✅
- Culprit and fix told apart by timing; owning team and commit named from live results ✅
- Every turn ended on text with a concrete next choice ✅

---

## Summary

The agent reached the root cause in four turns after the survey: Amex rejection at `charge.js:77`,
186 failed payment spans between 21:04:02 and 21:36:40 UTC, caused by commit 1d9f3b (first deploy
21:04:22) and cleared by 348e4e (21:37:18). The run was stopped before customer impact and the
handoff, so those beats are untested in this run. The defects are small phrasing and evidence-ordering
slips, not data errors.
