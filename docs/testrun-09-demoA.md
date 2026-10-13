# Demo Test Run 09 — payment-failure scenario (`/demo`, mode A)

**Date:** 2026-10-08
**Scenario:** payment-failure (P-2610744)
**Runtime:** `/demo` → mode A (Investigate) — `skills/demo-engine/SKILL.md` +
`skills/dynatrace-playground/SKILL.md`, pre-loaded DQL from `tools/preflight.py load-queries`
**Mode:** live_recent (problem CLOSED; started 2026-10-07 21:06:54 UTC, ended 21:43:00 UTC;
setup ran 07:15 UTC, about 9.5 h after close)
**Duration:** not measured. The run was stopped by the user before the customer-impact beat, so no
session close was delivered.
**Entry path:** `/demo` → mode menu → "A" → greeting → "what's going on?" (survey, two scenarios) →
"payment" → problem summary → "check the deployment" → "pinpoint the problem" (failing traces) →
stopped

---

## Setup

Silent: read `scenarios/registry.yaml`, both `scenario.yaml` manifests, ran `preflight.py resolve
--write` for both scenarios (one Bash call, sequential), then `load-queries` for both with the output
discarded (`> /dev/null`).

**Defect in my own setup:** the `load-queries` output was thrown away, so the `queries` dict was not
in context. It had to be re-run after "payment" was chosen. See Issue 1.

No text was emitted before the mode menu ✅

---

## Mode menu and greeting

Mode menu verbatim, first visible output ✅. "A" → greeting verbatim, generic, three example prompts,
no scenario or numbers ✅

---

## Survey

**User:** "what's going on?"

No new tool calls (state already cached) ✅

| | payment-failure | broken-images |
|---|---|---|
| Problem | P-2610744 | P-2610759 |
| Status | CLOSED | CLOSED |
| Window (UTC) | 2026-10-07 21:06–21:43 | 2026-10-08 03:04–03:38 |
| Duration | ~36 min | ~34 min |
| Davis affected users | 413 | 273 |
| Ended | ~9.5 h ago | ~3.5 h ago |

Revenue for payment only (413 × $87 = $35,931); none for images (no `avg_order_value_usd`). Past
tense, image problem described as a slowdown, not a failure. Said the two user counts are not
comparable one to one ✅. Ended on "which one", with a pointer to each (bigger revenue vs more
recent) — a triage question, not a yes/no ✅

---

## Problem summary (beat 1)

**User:** "payment"

| Field | Value |
|---|---|
| Problem | P-2610744, CLOSED |
| Started | 2026-10-07 21:06:54 UTC |
| Root cause | astroshop-payment, Charge endpoint |
| Failure rate | payment 55.74%, checkout 55.74%, frontend 18.78% |
| Davis affected users | 413 |
| Owning team | Team-Financial-Services |

1 record, 55 ms, queryId 01a11a60, 13,557 records scanned. canonicalQuery shown, proof stamp shown,
deep link shown (with the `segments` parameter) ✅. Read stated with a forward option (deployment vs
traces) ✅

---

## Deployments (beat 2)

**User:** "check the deployment"

**Query:** beat-2 DQL as pre-loaded. It is the working-tree version (`summarize first_deploy =
min(timestamp) … by commit`), not the `limit 5` form from run 08, so the Issue 1 / run-08 truncation
did not recur ✅

| Commit | First deployed (UTC) | Deploy events |
|---|---|---|
| 1d9f3b | 2026-10-07 21:04:22 | 10 |
| 348e4e | 2026-10-07 21:37:18 | 2 |

Owner team-astroshop, stage prod, app astroshop, services payment + checkout on both. 2 records, 26
ms, queryId 01a11a62.

**Davis CoPilot** called once with the commit, owner, timestamps, and problem facts, per the beat
manifest. It answered that 1d9f3b explains the failure and 348e4e is the remediation. Because the
context contained that framing already, this is agreement, not independent confirmation. See Issue 3.

**Agent said:** 1d9f3b landed about 2.5 minutes before Davis opened the problem and reads as the
regression; 348e4e landed while the problem was still open and reads as the fix. Said a gap that
short is suggestive, not proof ✅. Offered failure-rate alignment vs failing traces ✅

---

## Pinpoint (beats 3 and 4, front-run)

**User:** "pinpoint the problem" → treated as front-running to the failing traces; beat 3 (failure
rate buckets) was not run and not claimed as done.

**Queries:**

1. Failing spans grouped by exception message, `first_seen` / `last_seen` / `failed_spans` /
   `trace_id` (no `limit`, no newest-5) — the shape run 08 Issue 7 asked for ✅. 1 record, 35 ms,
   queryId 01a11a62, 3,658,835 records scanned.
2. Waterfall for the returned trace (chained, `toUid` cast in place), piped to
   `render_waterfall.py`.

**Found:**

| Exception | File:line | Failed spans | First seen | Last seen |
|---|---|---|---|---|
| "Sorry, we cannot process American Express credit cards. Only Mastercard or Visa are accepted." | /usr/src/app/charge.js:77 | 186 | 21:04:02 | 21:36:40 |

One distinct message, so no second finding. Trace 3abbb62f: frontend, checkout, and payment Charge
(72 ms) all FAIL; 8 other calls (checkout internals, shipping, currency) ok at ≤6 ms; 2 spans collapsed
by the renderer.

**Staging followed:** exception on its own line, bug type next, then the DQL and table, then a
condensed waterfall with the clean calls collapsed ✅. The `-o table --plain` verbatim call was not
run for this peak beat because the waterfall staging overrides it; the manifest and SKILL.md are
ambiguous on whether the failing-spans table also needs it. See Issue 5.

**Agent offered:** who got hit (sessions, countries, replay) or failure-rate vs deploy alignment ✅

---

## Issues to Fix

### 1. `load-queries` output discarded during setup

Setup ran `load-queries` for both scenarios with stdout sent to `/dev/null` (as a "does it run"
check), so the `queries` dict never reached context and the command had to be run again at "payment".
The `/demo` command says to store the output. Not an engine defect, an execution one; worth a
sentence in `commands/demo.md` ("capture the output, do not redirect it").

### 2. Timing claim got the order of two events wrong

The narration said the first failure at 21:04:02 came "right after the 1d9f3b sync at 21:04:22
started rolling out". 21:04:02 is 20 seconds **before** 21:04:22. The sync events are per-resource,
and run 08 found an ArgoCD deployment annotation at 21:04:05 and a flagd stop at 21:04:06, so the
change does start at about the right moment, but this run did not query for that and the sentence as
written is wrong. The same turn described the 21:36:40 last failure as ~40 seconds before 348e4e
(21:37:18); that one is right (38 s). Correct reading: the first failure and the first deploy event are
within about 20 seconds of each other, and deploy events are recorded slightly late relative to the
failures.

### 3. CoPilot cited as corroboration

"Davis CoPilot agrees" was written after feeding CoPilot the conclusion. SKILL.md says CoPilot output
is colour fed by the agent's own facts, not primary evidence. The reply should have called it a
restatement, or been left out of the evidence.

### 4. Overreach in the closing read

"Every failed checkout in that window was a customer paying with an American Express card" is not what
was measured. Measured: all 186 failed Charge spans that carry an exception message carry the Amex
rejection. Failed checkouts with no exception event, or failures at other hops, were not counted. Say
"all 186 failed payment spans in the window".

### 5. Verbatim-table rule for peak beats is ambiguous when a beat has a chained waterfall

SKILL.md step 3b says peak beats get a second `-o table --plain` call, and also that the waterfall
beat's staging overrides it. Beat 4 has both a failing-spans query and a waterfall. This run read the
override as covering the whole beat and skipped the table call. State explicitly which query the
override applies to.

### 6. Waterfall renderer marks every ancestor as `FAIL <-- exception`

The failing leaf and its callers all print the same marker, so the output does not show where the
error originated. The narration inferred propagation from the exception file (`charge.js`) rather
than from the renderer, and the payment-internal span was among the 2 collapsed rows. Consider
marking only spans whose own `span.events` carry the exception, or listing the collapsed spans.

### 7. Elapsed time not measured

No timestamp was recorded when beat 1's first query ran (the `analysisTimeframe` in its envelope shows
07:18:37 UTC, which could serve), so no duration can be given. Same class of gap as run 08 Issue 6.

---

## What Worked Well

- No text before the mode menu; menu and greeting verbatim ✅
- Survey used cached state, no extra tool calls, labelled both populations, ended on a choice ✅
- Revenue computed only where `avg_order_value_usd` exists ✅
- Beat-2 and beat-4 queries are the grouped/summarized forms; no `limit 5` truncation, so the run-08
  deployment retraction did not happen ✅
- First-seen / last-seen window on the exception (21:04:02–21:36:40) bracketed the incident against
  both commits ✅
- Front-run to the traces handled without claiming beat 3 was done ✅
- Every turn ended on a forward option; no quiz, no yes/no ✅
- Proof stamps and canonicalQuery shown on every evidence turn ✅
- Remediation not offered; no vendor or role-breaking moments arose

---

## Summary

The run reached the exception and the fix commit in four turns: Amex rejection at `charge.js:77`
(186 failed spans, 21:04:02–21:36:40), 1d9f3b as the regression and 348e4e as the fix, owner
Team-Financial-Services. The queries now return the full picture, so the run-08 truncation error did
not recur. The defects are in narration: a wrong event ordering at onset (Issue 2), CoPilot cited as
independent agreement (Issue 3), and a closing sentence broader than the data (Issue 4). The customer
impact beat, the failure-rate alignment, and the session close were not reached.
