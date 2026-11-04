# Demo Test Run 15 — cloud-observability, hands-on, entered at the bill (`/demo`, explore delivery)

**Date:** 2026-11-04
**Runtime:** `/demo` — `demo-agent` instructions + `investigating-playground-incidents` skill, mapped onto
Claude Code by `skills/local-runtime/SKILL.md` (dtctl in place of `execute-dql`).
**Model:** Opus 5
**Environment:** `demo-live` (`guu84124.apps.dynatrace.com`), context current, safety level `readonly`
**Scenario:** cloud-observability (showcase; no `problem_state`)
**Delivery:** `explore` — never chosen, the mode question was never asked (see issue 2)
**Beat order as run:** 5 → 6 → 1 → 2 → 3 → 4, then the Extra
**Wall clock (survey → last query):** 09:10:59 → 09:26:29 UTC, ~15.5 min. Reported elapsed: 9 min (see issue 3)
**Entry path:** `/demo-doctor` → `/demo` (empty, greeting + survey + showcase probe) → "what do you mean with where
10% of it is?" (→ beat 5) → "no, show me utilization" (beat 6 + cost action list) → "show me" (beat 1) → "yes"
(beat 2) → "ok" (beat 3) → "show me" (beat 4, peak) → "ok, so what?" (session close + report) → "what's the logical
next step?" (recommendation, no query) → "workflows" (Extra) → "Is there an HTML report you can show me?" →
this file request

Every value below was read from a result. Two figures in the narration and the report were summed by hand —
marked **verify**.

---

## Why this run is interesting

It is the first recorded run that enters the showcase through the bill rather than through a pick, and the first
that runs the beats out of order (5 → 6 → 1 → 2 → 3 → 4). Most of the issues below come from that: the skill
describes a forward tour and a jump-forward case, but not a tour entered at the end and walked backwards.

---

## Startup and survey

- `/demo-doctor` ran first and reported `demo-live`, `readonly`, 2 of 2 scenarios live.
- The adapter's `dtctl config get-contexts` call (`skills/local-runtime/SKILL.md:27`, "once per session") was
  **skipped**: `/demo-doctor` had already printed the environment and the safety level in the same session. The
  environment and `{{LINK_HOST}}` were taken from that output instead. Correct result, path not as written.
- Opening ran **two** queries, not one: the survey, then the showcase probe. The adapter
  (`skills/local-runtime/SKILL.md:38`) says a runtime that knows the environment up front appends the probe to the
  opening query — one call. No text between them, so the user saw one turn ✅ (see issue 1).
- Greeting verbatim ✅. No environment, tenant or application named ✅.

| | payment-failure | cloud-observability (probe) |
|---|---|---|
| Problem | P-2611944, CLOSED | — (showcase, no problem record) |
| Impact | 689 affected users (problem record) | — |
| Duration | 38 min, ended 1349 min ago | — |
| Cost | roughly $59,943 (`revenue_usd`) | $13,320 total, $1,332 target |
| Root cause / owner | astroshop-payment, Team-Financial-Services | — |

- `broken-images` and `disk-cpu-cascade` returned no row and were **not mentioned** ✅
- Cloud line added after the bullets with both live figures, not presented as an incident ✅
- Ended on exactly "Which should we take first — the payment service, or the cloud bill?" ✅
- No failure-rate percentage stated in the survey ✅
- `ended_min_ago` 1349 → "about 22 hours ago", rounded, not estimated from timestamps ✅
- **Tense:** the bullet was written from the hook template verbatim (`session-protocol.md:200`, present tense:
  "is failing", "it's been going on") and then closed with a past-tense sentence. `problem_state` is `live_recent`,
  which `session-protocol.md:147` says is past tense. The hook and the state rule disagree (issue 6).

---

## Beat 5 — The Bill and the Target (entered from a clarifying question)

**Queries:** the probe's result reused as beat 5's first query ✅ (`session-protocol.md:233`), then the
largest-lines query.

| Field | Value |
|---|---|
| Total (30 days of charges) | $13,320 |
| Target (10%) | $1,332 |
| Top categories | Compute $4,951, Management and Governance $4,684, Networking $1,131, Storage $939 |
| Untagged | $6,725 (50%) |
| Largest line | AmazonCloudWatch `PutLogEvents`, `USE1-DataProcessing-Bytes`, $2,454, teams UNTAGGED / team-demoability / team-unc |

- Opened with the CTO framing in one line ✅; "the last 30 days of charges imported so far" said ✅
- "the bill shows the size, not the waste" and "its owners' call" stated ✅
- Showcase register held: present tense, no urgency, ended on next step + one alternative ✅
- Proof stamp used the **probe's** metadata (the beat's first query), placed above the deep link ✅

---

## Beat 6 — Cost Next to Utilization (peak)

**Queries:** databases cost-vs-utilization, then the team split.

| Verdict | DBs | USD (30d) | Shown |
|---|---|---|---|
| no utilization data | 18 | 335 | flow-logs-database $101, live-large-db1 $62, staging-large-db1 $62 |
| low CPU, no memory headroom | 2 | 17 | sf-live-postgres (3.8%, 121 MB), astroshop-live-productcatalog-db (5.7%, 38 MB) |
| low CPU, memory headroom | 1 | 0 | pure-otel-live (5.9%, 2992 MB) |

Team split: UNTAGGED $6,725, team-demoability $5,608, team-unc $979, demoability $8.

- Staging followed: finding alone on its own line, blank line, "difference between a cost report and an answer",
  table, then the cost action list ✅
- Thresholds (under 10% CPU, under 256 MB free) stated with the verdict ✅
- `staging-large-db1` named with "the name is the only signal" ✅
- "each owner reviews their item" line given after the block ✅
- `demoability` ($8) listed as its own team alongside `team-demoability`, as returned — not merged ✅

---

## Beat 1 — The Estate

| Cloud | Resources | Types |
|---|---|---|
| AWS | 2,705 | 65 |
| Azure | 289 | 29 |
| Google Cloud | 193 | 14 |

- All three stated ✅; nothing said about health ✅
- "3,187 resources" is a hand-sum of the three rows — **verify**. The same figure went into the report's stats.
- `queried_at` (09:17:38) became `{{SURVEY_AT}}` from this point on, after beats 5 and 6 had already used the
  problem survey's `queried_at` (09:10:59). See issue 3.

---

## Beat 2 — One Function in Depth

| Field | Value |
|---|---|
| name / region | image-provider-live, us-east-1 |
| runtime | nodejs22.x, 512 MB, 10 s |
| last modified | 2026-11-04 05:45:40 UTC |
| tags | stage `prod`, application `astroshop`, cost center `rnd` |
| ownership | `team` = Team-Cloud-Services, `dt_owner_team` = team-unc |
| relationships | attached to VPC + subnet; uses IAM role + security group |

- Both ownership tags stated as returned, "which one is right is the owners' call" ✅
- `last_modified` given as UTC and explicitly not treated as evidence ✅
- Added an inference the reveal does not carry — that the tag mismatch "is exactly the kind of gap that leaves
  spend hard to attribute". Defensible (beat 5's team split groups by `dt_owner_team`) but it is an inference
  stated without a label.

---

## Beat 3 — What Runs on It

| Field | Value |
|---|---|
| service | image-provider-live in us-east-1 |
| requests (24h) | 1,137,532; 8,927 failed; 0.78% |
| latency | p50 23 ms, p95 66 ms |
| problem | P-26111073 "Request error rate increase", CLOSED, 2026-11-03 16:06–16:44 UTC |
| impact | 344 affected users (problem record); 6 affected entities down to Astroshop |
| root cause / owner | image-provider-live-products in us-east-1, **Team-UI** |
| agent notes | 2, summaries 0 |

- Requests labelled "last 24 hours"; impact led with users, then root cause, then owner ✅
- `agent_summaries` 0 handled as written: notes on the record, no readable summary, findings in the agent's own
  task; no findings invented ✅
- Populations kept apart (requests ≠ affected users) ✅

---

## Beat 4 — Agents on the Problem (peak)

| Agent | Problems (7d) | Notes | Note types |
|---|---|---|---|
| Kubernetes troubleshooting agent | 211 | 211 | ✨ Dynatrace AI Analysis |
| SRE Agent | 30 | 60 | Investigation started, Root cause analysis |
| AWS DevOps Agent | 13 | 26 | Investigation Results, Mitigation Recommendations |

EasyTrade problem: P-26111254 "Response time degradation", CLOSED, 03:05–03:40 UTC, 56 affected users,
`owning_team` **null**. Change: `Field 'cpu' in 'resources/limits' for container 'broker-service' changed from
'600m' to '300m'` on `easytrade-broker-service` at 03:01:24 UTC, `change_lead_min` 4.

- Staging followed: finding line alone, blank line, the context argument, the quoted root cause attributed to the
  agent, then the agents table ✅
- The agent's note gives 03:02:25Z for the change, the spec-change event gives 03:01:24Z. The run used the event
  as the record, which is what the reveal says to do, but left the discrepancy unmentioned.
- **The proposed fix was attributed to Team-UI. That is wrong** — Team-UI owns P-26111073 from beat 3; this
  problem's `owning_team` came back null. See issue 5.
- The turn **ended on the deep link**, with no closing line and no options after it. See issue 4.

---

## Session close and report

Delivered one turn late, on "ok, so what?", not in the beat-4 turn (issue 4).

- Timeline, one clause per beat, chronological as the session ran, with live values ✅
- Payoff line named the four challenges in one sentence ✅ (`session-protocol.md:242`)
- Elapsed stated as "five minutes" — the latest `elapsed_min` returned at that point was 5, measured from beat 1's
  `queried_at`, not from the start of the session (~11 min by then). See issue 3.
- "211 problems annotated in 7 days between it, the SRE Agent and the AWS DevOps Agent" — 211 is the Kubernetes
  agent's own count; the three-agent total is 254. Reads as if 211 were the combined figure.
- Way out offered the Extra and the other incident ✅
- Report rendered in the same turn, `kind: showcase`, cost action list under `cost`, 5 evidence links, path given
  as one line, file never read back ✅. Report stats carry two hand-sums (3,187 resources; 254 problems) —
  **verify**.

---

## Extra — Workflows That Act

Asked for after the close, via "what's the logical next step?" → "workflows".

| Kind | Workflow | Runs | Succeeded | Trigger | Last run (UTC) |
|---|---|---|---|---|---|
| prevent | AWS EBS remediate low storage | 63 | 56 | Event | 2026-11-04 06:35:14 |
| remediate | AWS regional outage failover Lambda | 84 | 84 | Event | 2026-11-04 07:42:54 |
| optimize | Cost & Carbon Optimization: Calculation | 336 | 336 | Schedule | 2026-11-04 09:02:04 |

- `Event` vs `Schedule` explained as returned ✅; the 7 non-successful prevention runs stated, with "why is in that
  workflow's own history" ✅; no run tied to a beat 3 or 4 problem ✅
- Proof stamp printed `0 records scanned` (that is what `dt.system.events` returned) — accurate, looks like a bug
  to a viewer (issue 8)
- The Extra ran **after** the report, so none of it is in the report (issue 7)

---

## What was done about each

Fixed 2026-11-04, on `multi-environment-demo`. Issue numbers are the ones above.

| # | Issue | Outcome |
|---|---|---|
| 1 | Opening probe expensive (12.7 GB), two calls | **Cost fixed, shape unchanged.** The bill is re-imported in full daily, so every cost query reads 7 days instead of 75 — identical `total_usd` and row count at one instant, 2.07 GB instead of 12.7 GB. The two-call form is still what the adapter describes; the user sees one turn either way, so it was left alone. |
| 2 | A clarifying question skips the mode question | **Fixed.** session-protocol → "Showcase": a question *about* the cloud line is answered in two sentences and the turn ends on the mode question. An instruction still starts directly. |
| 3 | `{{SURVEY_AT}}` moved mid-session | **Fixed.** It had three conflicting definitions; it is now the `queried_at` of the first query of the conversation, whatever that query is, fixed from then on. |
| 4 | Beat 4 ended on a deep link; close a turn late | **Fixed.** The close fires when every beat of the track has run, in whatever order. `beats_completed` has a maintenance rule for the first time — it was declared once and read nowhere — and a turn never ends on a bare link. |
| 5 | The fix was attributed to the wrong team | **Fixed, generally.** "A name carries forward only from the result that returned it" is now in the data-only rules; beat 4's staging and reveal name the team from *this* problem's `owning_team`, or say "the owning team". |
| 6 | Payment hook present tense vs `live_recent` | **Fixed.** The hooks table says `problem_state` sets the tense, and the payment row carries its past-tense form. |
| 7 | The Extra can never reach the report | **Fixed.** The adapter re-renders when the session continues past the close and gives the new path. |
| 8 | Proof stamp can read `0 records scanned` | **Fixed.** The record count is dropped when it is 0; the queryId and duration stay. |

Two findings not in the numbered list were also fixed: the report's hand-summed figures (3,187
resources, 254 problems), now forbidden by "never add up rows yourself"; and the 10%, which was
hardcoded in DQL and attributed to a CTO who does not exist in the session — it is now the SRE's own
working assumption, motivated by the untagged share.

---

## Issues to fix

### 1. The opening probe is two queries, and it is expensive

`skills/local-runtime/SKILL.md:38` says to append the probe to the opening query where the environment lists the
showcase. This run issued two separate `dtctl query` calls. Either the adapter should say the two-call form is
acceptable (the user sees one turn either way), or the line should show the appended shape concretely.

Separately: the probe scanned **12.7 GB** before the user chose anything, and dtctl warned on it. Beat 5's
largest-lines query and beat 6's team split each scanned another 12.7 GB — three heavy scans per showcase session.
Worth recording in `docs/AUTHORING.md` as the known cost of offering the showcase on the opening.

### 2. A clarifying question about the cloud line is not a documented entry

"what do you mean with where 10% of it is?" was routed to SKILL.md's "Cloud cost" row (beat 5, no mode question).
That reads right, but it means a user can enter the tour without ever being asked hands-on vs. whole tour
(`session-protocol.md:235`), and `delivery` is then assumed rather than chosen. Say in the Showcase section what
happens when the user asks *about* the cloud line instead of picking it.

### 3. `{{SURVEY_AT}}` changed mid-session and elapsed time went backwards

`scenario-cloud-observability.md:90` makes beat 1's `queried_at` the anchor, and line 99 says a jump past beat 1
runs beat 1's query first. Entering at beat 5 made neither possible: beats 5 and 6 anchored on the problem
survey's `queried_at` (09:10:59, `elapsed_min` 4), then beat 1 re-anchored to 09:17:38 and beat 2 reported
`elapsed_min` 1. The close then said "five minutes" for a session that had been running ~11. Fix: either make the
anchor the first query of the session whatever it is, or state that the showcase anchors on the survey row's
`queried_at` when one exists.

### 4. Beat 4's turn ended on a deep link, and the close was a turn late

All six beats were complete at the end of the beat-4 turn, so `session-protocol.md:293` required the close in that
same response. It was not given, and the turn had no closing line after the link either
(`conversation-craft.md:69`). The out-of-order run is why: nothing tracks "last beat" when the beats do not arrive
in order. Add a note that the close fires when the beat **count** is complete, not when beat 6 runs.

### 5. The agent's proposed fix was attributed to the wrong team

Beat 4's problem returned `owning_team` null; the run wrote "Team-UI's call to review and apply", carrying the
owner forward from beat 3's unrelated problem. A team name with no source in that result is exactly what the
handoff rules forbid. The beat 4 staging (step 5, "the owning team decides") should say: name the team only from
this problem's `owning_team`, and say "the owning team" when it is null.

### 6. The payment-failure hook is present tense, the state rule says past tense

`session-protocol.md:200` ("is failing", "it's been going on") against `session-protocol.md:147` (`live_recent` →
past tense). The run used the template verbatim and then switched tense in the next sentence. Give the hook a
past-tense variant, or say the tense rule rewrites the hook.

### 7. The Extra can never reach the report

The report is written in the close turn (`skills/local-runtime/SKILL.md:65`); the Extra runs after the close
(`scenario-cloud-observability.md:525`). A session that takes the Extra ends with a report that omits it. Either
allow a re-render after the Extra, or note in the adapter that the report covers the beats only.

### 8. Proof stamp can read `0 records scanned`

The workflow query returned `scannedRecords: 0` with 3 rows. Accurate, but a stamp claiming zero records next to a
populated table invites a "is this real?" question in a demo. Consider omitting the record count when it is 0.

---

## What worked well

- Greeting, survey listing, cloud line and the one closing question exactly as written ✅
- Scenarios with no row never mentioned ✅
- Showcase register held throughout: present tense, no urgency, no clock, every beat ended on the next step plus
  one alternative (except beat 4) ✅
- Both peak beats followed their staging, finding alone on its own line first ✅
- Populations kept apart: cloud resources, dollars of `EffectiveCost`, requests, affected users, problems with
  agent notes, workflow runs ✅
- Nulls reported as nulls: `agent_summaries` 0, 18 databases with no utilization series, 7 prevention runs that
  did not succeed ✅
- Two disagreeing owner tags and two similarly-named teams (`demoability` / `team-demoability`) stated as
  returned, not reconciled ✅
- Agent recommendation framed as a recommendation, not as something applied ✅
- Persona held: "we", no "I can't", no "Davis"/"CoPilot", no file or tool mentions; report path given as one line
  and never read back ✅
- Read-only throughout; no write attempted ✅

---

## Proof-stamp queryIds (for verification)

| Query | queryId | Scanned |
|---|---|---|
| Survey | `01a1a5d3-6d23-77d2-a6cc-87fb0a7832bc` | 113,487 |
| Showcase probe / beat 5 bill | `01a1a5d3-9948-707e-be75-63c4fe0fd9a7` | 2,804,078 (12.7 GB) |
| Beat 5 largest lines | `01a1a5d5-f629-7c6d-8c10-0096dfb3b505` | 2,809,178 (12.7 GB) |
| Beat 6 databases | `01a1a5d7-270f-7de5-8dcb-169cacf5c853` | 2,811,901 |
| Beat 6 team split | `01a1a5d7-569b-7e87-a0a6-07179bc6c707` | 2,812,222 (12.7 GB) |
| Beat 1 estate | `01a1a5d9-8684-77bc-9e46-902e86dbc773` | 3,247 |
| Beat 2 function | `01a1a5da-c987-733c-874f-349fa621f2b3` | 1 |
| Beat 2 relationships | `01a1a5da-e6b6-7e50-881d-a64eb348cdf2` | 6,194 |
| Beat 3 service | `01a1a5dd-7faa-7196-8cdb-73668338bf4a` | 51,045,297 |
| Beat 3 problem | `01a1a5dd-a8a0-7a99-b672-1bdc18a3861c` | 260,888 |
| Beat 4 agents | `01a1a5de-5857-7e1f-bbd0-69a821b6db79` | 319,220 |
| Beat 4 EasyTrade problem | `01a1a5de-8edd-7914-95ba-dae3d35904e8` | 949,649 |
| Extra workflows | `01a1a5e1-a061-76af-b0d6-b9f1abe9404e` | 0 |

**Report:** `reports/20261104T092416Z-demo-live-cloud-observability.html`
