# Demo Test Run 16 — cloud-observability, hands-on, entered at the bill from a greeting (`/demo`, explore delivery)

**Date:** 2026-11-04
**Runtime:** `/demo` — `demo-agent` instructions + `investigating-playground-incidents` skill, mapped onto
Claude Code by `skills/local-runtime/SKILL.md` (dtctl in place of `execute-dql`).
**Model:** Sonnet 5.5
**Environment:** `demo-live` (`guu84124.apps.dynatrace.com`), context current, safety level `readonly`
**Scenario:** cloud-observability (showcase; no `problem_state`)
**Delivery:** `explore` — never chosen, the mode question was never asked (see issue 1)
**Beat order as run:** 5 → 6 → (untagged side quest) → 1 → 2 → 3 → 4, then the Extra
**Wall clock (first query → last query):** 10:36:52 → 10:51:40 UTC, ~14.8 min. Reported elapsed at the estate
close: 9 min, which matches the anchor (first query of the conversation) — the fix from run 15 held.
**Entry path:** `/demo` (empty → config check + greeting, no query) → "I want to look at my cloud costs" (beat 5) →
"Let's correlate utilization" (beat 6 + cost action list + close + report) → "I want to understand the costs that
don't have an owner" (side quest) → "yeah, let's go through the estate" (beat 1) → "show me" (beat 2) → "ok" (beat 3)
→ "ok" (beat 4, peak, estate close + report) → "Can you give me a summary of how much we saved where in the console?"
→ "i want to see your optimization goal. how much money can we change on each item…" → "go on" (the Extra) →
this file request

Every value below was read from a result. Hand-worked figures are marked **verify**.

---

## Why this run is interesting

It is the first run entered from a greeting straight into the bill, with no survey and no probe: beat 5's bill
query was the first query of the conversation, so `{{SURVEY_AT}}` anchored there with nothing to re-anchor later.
It is also the first run where the user asked for **savings per item**, which the showcase has no data for.

---

## Startup

- Empty `/demo`: `dtctl config get-contexts` ran first (adapter, once per session), then the greeting verbatim.
  The cloud line was named because `demo-live` lists the showcase. No survey, no probe, no numbers ✅
- "I want to look at my cloud costs" → SKILL.md "Cloud cost" row: status line "Pulling the cloud bill.", beat 5,
  no question. Read `scenario-cloud-observability.md` and `conversation-craft.md` in one batch, no text before ✅
- The bill was **not** run with the probe's `filter total_usd > 0` appended: nothing needed the probe's row (the
  showcase was already known from the environment). Beat 5's own bill query was used, with `elapsed_min = 0`
  substituted for the not-yet-set anchor (issue 6).

---

## Beat 5 — The Bill and the Target

| Field | Value |
|---|---|
| Total (30 days of charges) | $13,319 |
| Working assumption (10%) | $1,332 |
| Top categories | Compute $4,951, Management and Governance $4,684, Networking $1,131, Storage $939 |
| Untagged | $6,725 (50%) |
| Largest line | AmazonCloudWatch `PutLogEvents`, $2,454, teams UNTAGGED / team-demoability / team-unc |

- Opened with the owned assumption ("my working assumption is there's at least 10%") ✅; no CTO framing ✅
- The target was **proposed, not asked**. See issue 1.
- **Misread, later corrected:** the narration said the `PutLogEvents` line "carries team-demoability and team-unc
  tags, and some of its spend is untagged". The side quest showed $2,453 of the $2,454 is untagged. The `teams`
  list only says which tags occur on any row of the line, not how the dollars split (issue 2).
- "that one line is larger than the whole 10%" — a comparison of two returned numbers ✅
- Proof stamp from the bill query, above the deep link ✅

---

## Beat 6 — Cost Next to Utilization (peak) and the cost close

| Verdict | DBs | USD (30d) | Shown |
|---|---|---|---|
| no utilization data | 18 | 335 | flow-logs-database $101, live-large-db1 $62, staging-large-db1 $62 |
| low CPU, no memory headroom | 2 | 17 | sf-live-postgres (3.8%, 121 MB), astroshop-live-productcatalog-db (5.7%, 38 MB) |
| low CPU, memory headroom | 1 | 0 | pure-otel-live (5.9%, 2992 MB) |

Team split: UNTAGGED $6,725, team-demoability $5,607, team-unc $979, demoability $8.

- Staging followed: finding alone on its line, blank line, what kind of finding, table, action list ✅
- Cost track complete (5, 6) → close in the same turn, payoff line, way out from inside the scenario (estate tour
  and the Extra), report rendered and named as the last line ✅
- **Query broke on first transcription:** the DQL has `parse focus.ResourceId, "LD ':db:' LD:db"`, which
  contains single quotes inside the adapter's single-quoted wrapper. Run only after escaping them as `'"'"'`
  (issue 3).

---

## Side quest — the untagged half

Two queries: untagged spend by service/operation/usage, and by service category. Both are the beat 5 shape with
`filter isNull(tags[dt_owner_team])`; the skill has no such query.

| Untagged line | USD |
|---|---|
| CloudWatch `PutLogEvents` | 2,453 |
| CloudWatch `GetMetricData` | 654 |
| Savings Plans for AWS Compute (3yr partial upfront) | 475 |
| Amazon Translate | 363 |
| CloudWatch EKS observation count | 357 |
| CloudWatch Application Signals | 258 |

By category: Management and Governance $4,623, Networking $670, Compute $655, AI and Machine Learning $378.

- Corrected the earlier misread out loud ✅
- "which is CloudWatch" for Management and Governance is an inference from the line names, not a returned field —
  **verify**. "about 1.8 times the working assumption" is a ratio I worked out ($2,454 / $1,332) — **verify**; the
  data-only rule says a derived number should come from the query.
- The reply ran well over the side quest's 6-line budget (`conversation-craft.md` length table). It did end on a
  re-anchor to the open question ✅
- Report re-rendered at the end of the turn, as the adapter says to ✅

---

## Beats 1–4 — the estate

| Beat | Finding |
|---|---|
| 1 Estate | AWS 2,719 (65 types), Azure 289 (29), Google Cloud 193 (14); no total stated ✅ |
| 2 Function | image-provider-live, us-east-1, nodejs22.x, 512 MB/10 s, last modified 2026-11-04 05:45 UTC; `team` = Team-Cloud-Services vs `dt_owner_team` = team-unc, both stated as returned ✅ |
| 3 Service and problem | 1,139,832 requests in 24h, 8,927 failed (0.78%), p50 23 ms, p95 66 ms; P-26111073 "Request error rate increase", CLOSED, 344 affected users (problem record), root cause image-provider-live-products, owner Team-UI; 2 agent notes, 0 readable summaries ✅ |
| 4 Agents (peak) | K8s agent 204 problems / 204 notes, SRE Agent 30 / 60, AWS DevOps Agent 13 / 26; P-26111254 "Response time degradation", easytrade-broker-service CPU limit 600m → 300m, 4 min before the problem, 56 affected users (problem record), `owning_team` null → "the owning team" ✅ |

- Past tense for the closed problems ✅; no "downstream"/"upstream" ✅
- Beat 4 staging: finding alone first, kind of finding, root cause quoted and attributed, table. **The proposed fix
  was left out**: the 500-character `agent_root_cause` excerpt ends before the note's fix (issue 4).
- All four estate beats done → close in the same turn, with report ✅. Payoff line named the four challenges ✅
- Beat 3's deep link and beat 4's link given; every turn ended on next step + one alternative ✅

---

## Savings and optimization asks (out of the script)

- "how much we saved where in the console" → answered with no query: nothing has been saved, no returned field
  holds a saving; where the money sits, and what each line still needs ✅. "The console" was not asked about.
- "how much money can we change on each item by applying the suggested actions" → refused to put a number on any
  item, said the 10% is one assumption never split across items, gave dollars in play per item and said they
  do not sum to the target ✅. Offered the optimize workflow's runs as the nearest computed figure.
- "go on" read as a vague yes to that first option → the Extra's query: optimize 336/336 (Schedule), prevent 63 runs,
  56 succeeded (Event), remediate 84/84 (Event). Said the runs hold no dollar figure ✅

The user's question is a fair one the skill cannot answer today (issue 5).

---

## What was done about each

Fixed 2026-11-04, on `multi-environment-demo`. Issue numbers are the ones above.

| # | Issue | Outcome |
|---|---|---|
| 1 | A bare cost ask skips the target question | **Fixed.** The bill is stated first — total and what the untagged share means — and the question follows it. SKILL.md's cost row said "no question", which is what this run followed; it now asks unless the ask already named a figure. |
| 2 | `teams` invites a wrong read | **Fixed.** Beat 5 returns `untagged_usd` per line, and the Reveal says `teams` is the set of tags seen on the line, never how the dollars split. Verified: the CloudWatch line is $2,454 with $2,453 untagged. |
| 3 | Beat 6's DQL cannot be run as written | **Fixed at the source.** `splitString(focus.ResourceId, ":db:")[1]` returns the same db names with no single quotes. The adapter also records the trap. |
| 4 | Beat 4 can never say what the agent proposes | **Fixed.** A second field anchored on "Recommended Fix" returns it. The note is 3,924 chars with the fix at 2,029, so a 500-char excerpt from 313 never could. |
| 5 | "How much would we save" has no answer | **Answered, not invented.** No result holds a per-item saving and none is to be estimated. The close now leads with "What we know" — unowned, concentrated, unmeasured, not-to-touch — as places to look, explicitly not a forecast. The report says the same as template text. |
| 6 | The first-query anchor has no `elapsed_min` | **Fixed.** The Tokens table says it is `0` on that query, and that query's `queried_at` is the anchor afterwards. |
| 7 | A bill without the probe | **Allowed, and now stated.** Where the adapter has resolved the environment, availability is already settled and beat 5's own query serves. |

The run's own framing — "at every step I have the question *so what?*" — produced the larger change:
every beat now carries a **Why this step** line, the beat turn has a causal spine (why, evidence,
meaning, what follows *and why*, readiness cue), and the three contradicting rules about how a turn
ends collapsed into one. The untagged breakdown this run improvised is now a supported query.

---

## Issues to fix

### 1. A bare cloud-cost ask skips both the target question and the mode question

SKILL.md's "Cloud cost" row says status line, beat 5, no question. `session-protocol.md` "Setting the target" says a
no-number ask ("let's optimise the cloud costs") gets "Do you have a figure in mind, or shall I propose one?".
"I want to look at my cloud costs" is neither an instruction like "cut cloud costs" nor a number. This run followed
the table and proposed 10% without asking; whether that is right is not stated. Either say which phrases skip the
question or say the target question applies to every cost entry.

### 2. `teams` on the largest-lines query invites a wrong read

`teams = collectDistinct(...)` lists every tag seen on any row of the line, so a line that is 99.96% untagged reads
as "owned by two teams, partly untagged". Add `untagged_usd` per line to that query, or say in the reveal that
`teams` is a set, not a split.

### 3. Beat 6's DQL cannot be run as written

The adapter says to wrap DQL in single quotes. `parse focus.ResourceId, "LD ':db:' LD:db"` contains single quotes,
so the wrapper breaks the query. The shell needs `'"'"'` for each, or the DQL needs another form. Say so in
`skills/local-runtime/SKILL.md` ("Running DQL"), or change the parse pattern.

### 4. Beat 4 can never say what the agent proposes

`agent_root_cause` is `substring(note, from: rc_at, to: rc_at + 500)`. The note's root-cause section ran past 500
characters in this run, so the "Supporting Findings" are cut mid-sentence and the fix never appears, while staging
step 5 asks for "the proposed fix in one line". Widen the excerpt, or return a second field from the note's fix heading.

### 5. "How much would we save" has no answer in the showcase

The tour ends on a 10% assumption and dollars in play per item, never a per-item figure, because no result holds
one. Users ask for it twice in a row. Either the optimize workflow's own output (the Cost & Carbon Optimization
calculation) can be queried and that is the answer, or the skill says in one line why there is none and what would
produce it (an owner's decision and a later bill). This run said both from the data, not from the skill.

### 6. The first-query anchor has no value to put in `elapsed_min`

When beat 5's bill query is the first query, `elapsed_min` has no `{{SURVEY_AT}}` yet. This run hardcoded
`elapsed_min = 0` in the DQL. The scenario's "Tokens" table says the first query sets the anchor but does not say
what `elapsed_min` is on that query.

### 7. A bill without the probe

The probe's `filter total_usd > 0` is the showcase's availability test. With the environment known from the
adapter, this run skipped it and used beat 5 directly. Say that is allowed when the adapter has resolved the
environment, or the probe should run on a cost entry too.

---

## What worked well

- Greeting verbatim, with the cloud line, and no numbers ✅
- Anchor fix from run 15 held: the close said 9 minutes for a session whose last estate query was 9 minutes in ✅
- Close fired on set completion for both tracks, and a re-render followed every turn that continued past it ✅
- Out-of-order survey of the data held its populations apart: dollars, resources, requests, affected users,
  problems with notes, workflow runs ✅
- Nulls stated as nulls: `agent_summaries` 0, `owning_team` null, 18 databases with no utilization series, 7
  prevention runs that did not succeed ✅
- No savings figure invented when asked twice ✅
- Persona held: "we", no "I can't", no "Davis"/"CoPilot", no tool mentions; report path given as one line ✅
- Read-only throughout ✅

---

## Proof-stamp queryIds (for verification)

| Query | queryId | Scanned |
|---|---|---|
| Beat 5 bill | `01a1a622-0e5a-7fae-bf42-00f12bc97ad7` | 332,350 |
| Beat 5 largest lines | `01a1a622-1817-7475-a557-baeda2a722a5` | 332,442 |
| Beat 6 databases | `01a1a623-b85d-75da-851d-d0445615f8d9` | 21,021,039 |
| Beat 6 team split | `01a1a623-c0c7-7633-bd96-716f6a3aaad8` | 21,021,105 |
| Side quest, untagged lines | `01a1a625-61f2-7aad-8b6c-b0db1c4f0622` | 339,681 |
| Side quest, untagged by category | `01a1a625-6b90-7440-80ee-4c8066e0e780` | 339,757 |
| Beat 1 estate | `01a1a626-75e2-7d01-9f70-3095a4e7e7d2` | 3,253 |
| Beat 2 function | `01a1a627-536c-7054-ba13-9b0b86191b4c` | 1 |
| Beat 2 relationships | `01a1a627-5b50-7b83-ad13-6751ecf96d29` | 3,216 |
| Beat 3 service | `01a1a629-7e2c-70c0-90c5-66ddbe1cb2a0` | 51,363,903 |
| Beat 3 problem | `01a1a629-87ff-7d19-b7ce-ee92bf282518` | 171,635 |
| Beat 4 agents | `01a1a62a-12a7-79e2-9fe1-e5bf5baeadc8` | 224,040 |
| Beat 4 EasyTrade problem | `01a1a62a-1b96-7eba-a900-7add645947d4` | 577,401 |
| Extra workflows | `01a1a62f-9a7c-75a9-afdf-e4ea74ae3653` | 0 |

**Reports (one per turn that continued past a close):**
`reports/20261104T103856Z-demo-live-cloud-observability.html`,
`reports/20261104T104041Z-demo-live-cloud-observability.html`,
`reports/20261104T104553Z-demo-live-cloud-observability.html`,
`reports/20261104T105153Z-demo-live-cloud-observability.html`
