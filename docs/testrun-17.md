# Demo Test Run 17 — cloud-observability, cost track as a walk-through, with a number beyond the evidence (`/demo`, walk-through delivery)

**Date:** 2026-11-04
**Runtime:** `/demo` — `demo-agent` instructions + `investigating-playground-incidents` skill, mapped onto
Claude Code by `skills/local-runtime/SKILL.md` (dtctl in place of `execute-dql`).
**Model:** Sonnet 5.5
**Environment:** `demo-live` (`guu84124.apps.dynatrace.com`), context current, safety level `readonly`
**Scenario:** cloud-observability (showcase; no `problem_state`)
**Delivery:** `walk-through` — chosen at the mode question with "guide me through it"
**Beat order as run:** 5 → (opening report: 5 and 6 together) → 6, then the cost close
**Wall clock (first query → last query):** 12:04:08 → ~12:10:27 UTC, ~6.3 min. Reported elapsed at the close:
1 minute — wrong (issue 1).
**Entry path:** `/demo` (empty → config check + greeting, no query) → "let's take a look at cloud costs" (beat 5, target
question) → "HOw about 30%" (largest-lines query, target negotiation, mode question) → "guide me through it" (opening
report) → "go" (beat 6, cost action list, close, report) → "write the testrun" (out-of-lane reply) → "write the testrun
to the docs so I can improve the scenario" (stepped out, this file)

Every value below was read from a result. Hand-worked figures are marked **verify**.

---

## Why this run is interesting

It is the first run of the run-16 fixes: the bill is stated before the goal question, `teams` is no longer read as a
split, beat 6 runs with no quote trouble, and the cost close leads with "What we know". It is also the first cost-track
run delivered as a walk-through, and the first where the user named a target (30%) the evidence only partly covers.

---

## Startup

- Empty `/demo`: `dtctl config get-contexts` ran first, then the greeting verbatim, cloud line named because `demo-live`
  lists the showcase. No query, no numbers ✅
- "let's take a look at cloud costs" → status line "Pulling the cloud bill.", then the showcase file and
  `conversation-craft.md` in one batch, then beat 5's bill query with `elapsed_min = 0` ✅

---

## Beat 5 — The Bill and the Target

| Field | Value |
|---|---|
| Total (30 days of charges) | $13,318 |
| Working assumption (10%) | $1,332 |
| Top categories | Compute $4,950, Management and Governance $4,684, Networking $1,131, Storage $939 |
| Untagged | $6,725 (50%) |

| Largest line | USD | Untagged |
|---|---|---|
| CloudWatch `PutLogEvents` | 2,454 | 2,453 |
| EC2 `RunInstances` (t3.xlarge) | 1,703 | 0 |
| S3 `GetObject` (data transfer out) | 707 | 0 |
| CloudWatch `GetMetricData` | 654 | 654 |
| EC2 `RunInstances:0002` (m5.large) | 620 | 0 |

- Run-16 issue 1 held: the bill and what the untagged share means were stated first, then "Do you have a savings goal
  in mind, or shall I propose one?" ✅
- Run-16 issue 2 held: `untagged_usd` per line is returned, and no sentence reads `teams` as ownership ✅
- The 10% was not proposed until the user named a number.
- "HOw about 30%" → ran the largest-lines query, said what 30% comes to in dollars ($3,995 — hand-worked, **verify**),
  named three lines ($2,454, $1,703, $707), and proposed 10% = $1,332 with "if you'd rather hold to 30%, we work to
  it". Ended on the mode question. See issue 3.

---

## Opening report (walk-through)

Held-back blocks run: beat 6 databases and beat 6 team split (beat 5's two queries were reused).

| Verdict | DBs | USD (30d) | Shown |
|---|---|---|---|
| no utilization data | 18 | 335 | flow-logs-database $101, live-large-db1 $62, staging-large-db1 $62 |
| low CPU, no memory headroom | 2 | 17 | sf-live-postgres (3.8%, 121 MB), astroshop-live-productcatalog-db (5.7%, 38 MB) |
| low CPU, memory headroom | 1 | 0 | pure-otel-live (5.9%, 2,992 MB) |

Team split: UNTAGGED $6,725, team-demoability $5,607, team-unc $979, demoability $8.

- Showcase report shape: one sentence per beat Objective, owner part, the exact offer, beat 5's deep link last ✅
- Two proof stamps, one per beat, above the link ✅
- Run-16 issue 3 held: the beat 6 query ran as written, no `'"'"'` escaping needed ✅
- The status line was improvised (issue 2). The beat 6 part carried two numbers (issue 4).

---

## Beat 6 — Cost Next to Utilization (peak) and the cost close

- Staging followed: finding alone on its line (`sf-live-postgres — 3.8% CPU, 121 MB free memory: idle on the bill,
  full in memory`), blank line, what kind of finding with the thresholds named (under 10% CPU, under 256 MB free), table,
  action list ✅
- Action list led with "What we know" (unowned / concentrated / unmeasured / not to touch), then "findings, not a
  forecast", no per-item saving, owners review before applying ✅ (run-16 issue 5 held)
- `staging-large-db1` called out as the name being the only signal, owners' call ✅
- Cost track complete → close in the same turn: payoff line, way out walk-through-style, report as the last line ✅
- Elapsed time was wrong (issue 1). Working target in the report is $1,332 although the user named 30% (issue 3).

---

## Out of role, then out of the demo

- "write the testrun" → the verbatim "Not my lane on this shift — I'm here for incidents. Want me to check what's
  open?" ✅ as specified.
- The user then said it was for the docs, to improve the scenario. Stepped out of character for that, and wrote this
  file. The instructions have no path for a maintainer's request mid-session (issue 6).

---

## Issues to fix

### 1. `elapsed_min` was hardcoded on a later query, and the close reported a wrong time

Beat 5's bill query was the conversation's first (`queried_at` 2026-11-04T12:04:08.553141192Z), so `{{SURVEY_AT}}`
was known from then on. Beat 6's query was run with `elapsed_min = 1` typed in, not computed from the anchor, and the
close said "in 1 minute". The queries ran at 12:04:08 and 12:10:27, so ~6 minutes. The Tokens table says `0` on the
first query only; the run carried that hardcode into a later one. The skill should make the substitution mechanical
(the anchor goes into `toTimestamp("...")`, never a number), or the adapter should say so.

### 2. The walk-through's status line has no value for the cost track

`pull_line` is "Pulling the clouds, the image function, its service and latest problem, the agents' notes and the bill
together." That describes the estate tour; the cost track pulls two beats. This run wrote its own line ("Pulling the
utilization and owners next to the bill."). Give each track its own pull line, or say the walk-through of a track uses
a line naming that track's beats.

### 3. A target the evidence partly covers has no rule, and the report ignored the user's number

The target rules have two branches: a number the evidence can cover (take it), and a number beyond it ("cut it in
half": propose the figure the lines support). 30% sits between: the largest line alone is $2,454, but nothing in the
results says which dollars of it can go. This run took the beyond-evidence branch by judgement, and named three lines
where the template names the largest line and the monitor-first dollars. It then moved on to the mode question without
the user agreeing to 10%, and the report and action list carry "10% = $1,332". The user's 30% appears nowhere in them.
Say where the line between the two branches is, and what the report states when the user's number and the working
assumption differ ("Still open" is the stated home for the gap). $3,995 is also a hand-worked figure.

### 4. A report part with two numbers

The opening report allows at most one number per part. The beat 6 sentence said "two" databases with no memory headroom
and "18" with no utilization series. Either split into two parts or drop one number from the opening report; the
evidence turn holds both.

### 5. The walk-through starts after beat 5's evidence has already been shown

On the cost track the target negotiation already put beat 5's bill and largest lines on screen before the opening
report, so the report stands in for a beat whose evidence the user has seen, and there is no beat 5 evidence turn to
prove "half the bill has no owner" (the offer starts at beat 6). The walk-through file says the report stands in for
beat 1; it is silent on a track that begins at beat 5.

### 6. A maintainer's ask during `/demo` has no route

"write the testrun" got the in-character redirect twice over. That is what the instructions say, and the user had to
say what it was for before the session stepped out. If maintainers are expected to ask for repo work mid-session, the
local adapter could name the phrase that leaves the persona; if not, this is as intended.

---

## What worked well

- Greeting verbatim with the cloud line, no numbers ✅
- Bill stated before the goal question, so the goal means something ✅
- The target was never called unrealistic, and no saving was invented ✅
- Populations kept apart: dollars of EffectiveCost, databases, tag coverage ✅
- Nulls stated as nulls: 18 databases with no CPU or memory series ✅
- Read-only throughout ✅
- No "Davis"/"CoPilot", no mention of tools, files or the survey ✅

---

## Proof-stamp queryIds (for verification)

| Query | queryId | Scanned |
|---|---|---|
| Beat 5 bill | `01a1a671-f4b1-7139-8c25-bb11a68a945b` | 511,723 |
| Beat 5 largest lines | `01a1a672-647f-76e2-9e06-905f69391d21` | 512,831 |
| Beat 6 databases | `01a1a677-bd6d-765e-a14a-06b11918ff91` | 524,889 |
| Beat 6 team split | `01a1a677-c999-727b-bf53-26a22fc8d4b0` | 524,948 |

Run 16's beat 6 queries scanned 21,021,039 and 21,021,105 records; these scanned about 525,000. The run did not
investigate why.

**Report:** `reports/20261104T121145Z-demo-live-cloud-observability.html`
