# Scenario: Kubernetes CPU Throttling (Slowdown) — Context and Beats

**The "Beat N" headings below number the steps for authors only. Never print a heading, a number or the word "beat" to the user: name a step by its subject ("the deploy"). Steps can come in any order.**

Read once the user has picked a scenario. The survey query and the discovery hooks are in `references/session-protocol.md`.
Reveals describe the *shape* of a finding, never its values. Response times, millicore figures, throttling, user counts, the window and the agent's own wording rotate every cycle — read them from the live result.

## Contents

- [Business context](#business-context)
- [Scope](#scope)
- [Handoff fields](#handoff-fields)
- [Beat 1 — The Page](#beat-1--the-page)
- [Beat 2 — Where the Time Goes](#beat-2--where-the-time-goes)
- [Beat 3 — Throttled, Not Busy](#beat-3--throttled-not-busy) (peak)
- [Beat 4 — The Change](#beat-4--the-change)
- [Beat 5 — The Agent's Analysis](#beat-5--the-agents-analysis)

---

## Business context

| Field | Value |
|---|---|
| `service_name` | "EasyTrade" |
| `symptom` | "the trading app responding slowly" |
| `approach` | "Here's how I'd work it: who it hit, then which service is holding the time, then that container's own CPU numbers, then the change behind them, and what the troubleshooting agent wrote on the record." |
| `pull_line` | "Pulling the problem, the slow services, the container's CPU against its limit, the spec change and the agent's analysis together." |

This is a **slowdown, not an outage**: requests succeed, they take far longer than normal. Never call it failing or erroring. No `avg_order_value_usd` is defined: no revenue figure.

What makes this scenario worth running is the lesson in it. Tuning a Kubernetes workload down is supposed to save money; done to the wrong field it costs user experience instead, and the evidence for that is three numbers that only mean something next to each other — usage, limit and throttling.

## Scope

**Data objects:** `dt.davis.problems`, `spans`, `timeseries` on `dt.kubernetes.container.*`, `events` (deployment spec changes, agent notes)

**Stable IDs** (one row per environment; the beats filter on names, so no query uses these IDs):

| Name | ID |
|---|---|
| `[eks-live][easytrade] TradeManagement`, `demo-live` | `SERVICE-8491B5DDF5BDAB93` |
| `[eks-live][easytrade] NotMiningBitcoin`, `demo-live` | `SERVICE-DA275964FAFD97CA` |
| EasyTrade (the application), `demo-live` | `APPLICATION-5DCD0C470BC8680A` |
| easytrade-broker-service (the throttled workload), `demo-live` | `K8S_DEPLOYMENT-98DBB38AEB111C5B` |
| `[eks-playground][easytrade] TradeManagement`, `playground` | `SERVICE-BE742741A316B7EE` |
| `[eks-playground][easytrade] NotMiningBitcoin`, `playground` | `SERVICE-766A1FAD228EB11C` |
| easytrade-broker-service (the throttled workload), `playground` | `K8S_DEPLOYMENT-6AD992C0EE5B466D` |
| The container whose limit moves | `k8s.container.name == "broker-service"` |
| The Kubernetes troubleshooting agent's notes | `events` where `annotation.source == "Dynatrace AI Workflow"` |

**`{{ROOT_CAUSE_ID}}` rotates between the entities above** — Dynatrace names whichever service or
application the slowdown surfaced on, and it is not the same one every day. Never build a deep link on it: on
demo-live one of them is an `APPLICATION`, and a service route will not open it. Beat 1 states it as returned and
the scenario does not depend on which it is.

**The workload that changes is not the root cause entity.** The limit moves on `easytrade-broker-service`,
while the problem is rooted on a service that got slow because of it. That gap is the scenario, not a mistake
in the data — connecting the two is what beat 4 and the agent in beat 5 do.

Playground runs its own EasyTrade with the same problem and namespace names, which is why the survey branch
matches entity IDs only. Beat queries run after the environment is resolved, so the namespace filter in them is safe.

## Handoff fields

Several populations coexist — always say which one a number counts.

| Value | Source |
|---|---|
| `owning_team` | Survey row; these problems usually carry none, so say plainly there is no owner on record |
| `Goes to` | `owning_team`, or the workload when there is none: `easytrade-broker-service` in the `easytrade` namespace, on the cluster beat 1 returns (`cluster`) |
| Affected users (problem record) | survey row `affected_users` |
| Slowest service and its p95 | Beat 2 |
| Usage, limit and throttling | Beat 3, as three series over the same window |
| What changed | Beat 4 — `change_details`, verbatim, with the restore |
| What to change | Beat 5 — the agent's own Solution section |

---

## Beat 1 — The Page

**Requires:** none

**Why this step:** Before we tune anything we need what the user actually felt: what is slow, for how many, and how far it spread.

**Objective:** User grasps the blast radius: a trading application is slow for real users, the problem names a
root cause inside the cluster, and the affected list runs across several services.

**Evidence DQL:**

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter event.id == "{{PROBLEM_ID}}"
| fields
    display_id,
    status         = event.status,
    started        = event.start,
    ended          = event.end,
    affected_users = dt.davis.affected_users_count,
    root_cause     = root_cause_entity_name,
    owning_team    = team,
    also_affected  = affected_entity_names,
    cluster        = k8s.cluster.name,
    namespace      = k8s.namespace.name,
    description    = event.description,
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

**Show:** Headline "Who felt the slowdown and how far". Table: Field | Value, 5 rows (one fact per row: affected users
with its population label, root cause, owning team, cluster, namespace). Finding: {affected_users} users hit for
{duration}, response time {response} against a learned baseline of {baseline}. Bullets: Root cause service inside the
namespace and cluster; Spread from the root cause out to the application; No owning team on record so it goes to the
workload; A version change landed with it.

**Reveal:** Lead with the users and the duration, not the row. Dynatrace classifies this as a slowdown —
`description` carries the response time against the baseline it learned from this application's own normal
behaviour; quote both and say which is which, because the comparison is the finding. Name `root_cause` as
returned, and say it is a service inside `namespace` on `cluster` rather than a machine. `also_affected` is the
spread: read it as a chain from the root cause out to the application the user opens. `owning_team` is usually
null here — say there is no team on the record rather than leaving a gap, and the handoff goes to the workload.
The description also carries an `Info: EasyTrade version change` line; note it in passing as something a
deploy landed, and leave what it changed to beat 4 rather than guessing here.

**Success signal:** User asks which service is slow, or why it got slow.

**Deep link** (label "Problem in Dynatrace"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.davis.problems/problem/{{PROBLEM_ID}}?from={{TF_FROM_MS}}&to={{TF_TO_MS}}
```

---

## Beat 2 — Where the Time Goes

**Requires:** 1

**Why this step:** The problem names a root cause but not a magnitude, so the next thing we need is which service in the namespace is actually holding the time, and by how much against its neighbours.

**Objective:** User sees the slowdown concentrated in one or two services while the rest of the namespace is
normal, which is what makes it a workload problem rather than a cluster problem.

**Evidence DQL:**

```dql
fetch spans, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter k8s.namespace.name == "easytrade"
| filter request.is_root_span == true
| summarize requests = count(),
    p50_ms = round(percentile(toDouble(duration), 50) / 1000000, decimals: 1),
    p95_ms = round(percentile(toDouble(duration), 95) / 1000000, decimals: 1),
    by: { service = dt.service.name }
| sort p95_ms desc
| limit 6
| fields service, requests, p50_ms, p95_ms,
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

**Show:** Headline "Which service is holding the time". Table: Service | Requests | Median (ms) | p95 (ms), 6 rows. Finding: {slowest service} p95 is {ratio} times the next service down, {p95_ms} against {next p95_ms}. Bullets: Slow rows far above an ordinary rest of the namespace; Median stays reasonable while p95 runs away; Identical figures on two names are the same requests.

**Reveal:** Lead with the gap between the slowest service's `p95_ms` and the next one down — that ratio is the
finding, not the row count. The slow rows sit far above the rest of the namespace, and the rest look ordinary,
which rules out the node, the cluster and the network: those would slow everything here, not one workload.
`p50_ms` next to `p95_ms` says the same thing again — a median that stays reasonable while the 95th percentile
runs away is a workload being interrupted, not one that has become uniformly slower.

Two service names can come back with identical figures when the same requests are attributed to both. Say that
as returned rather than presenting them as two separate findings.

**Success signal:** User names the slow service, or asks what that service is waiting on.

**Deep link** (label "EasyTrade requests in tracing"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.distributedtracing/explorer?filter=k8s.namespace.name+%3D+easytrade&tf={{TF_FROM_ISO}}%3B{{TF_TO_ISO}}&v=requests
```

---

## Beat 3 — Throttled, Not Busy

**`peak_moment: true`**

**Requires:** 2

**Why this step:** A service that is slow without an error is usually waiting on something, and for a container the thing it waits on is its own CPU allowance — so we put usage, limit and throttling on one timeline.

**Objective:** User sees the mechanism: the container's CPU ceiling drops, throttling climbs with it, and
actual usage never reaches the new ceiling — so this is not a container that ran out of CPU.

**Evidence DQL:**

```dql
timeseries { usage = avg(dt.kubernetes.container.cpu_usage),
             limit = avg(dt.kubernetes.container.limits_cpu),
             requests = avg(dt.kubernetes.container.requests_cpu),
             throttled = avg(dt.kubernetes.container.cpu_throttled) },
  from: "{{DQL_FROM}}", to: "{{DQL_TO}}", interval: 5m,
  filter: { k8s.namespace.name == "easytrade" and k8s.container.name == "broker-service" }
```

Four series on one window. `limit` and `requests` are the configured ceiling and the configured reservation;
`usage` is what the container actually consumed; `throttled` is how much it was held back. Read each series'
`min`, `max` and the time of each from the result, and say what the unit is only if the result names it.

**Show:** Headline "Throttled while barely busy". Table: Series | Lowest | Highest | Highest at (UTC), 4 rows. Finding: {usage max} used against a {limit min} ceiling, and throttled {throttled max} anyway. Bullets: Limit drops then returns inside the window; Throttling rises and falls with the limit; Bursty demand exceeds each slice while the average stays low; Requests never moved so only the limit is in play.

**Reveal:** Three things, in this order, and the third is the one that matters.

First, `limit` moves inside the window — a low stretch with the original value either side of it. Say the two
values and when it dropped. Second, `throttled` rises on the same stretch and falls when the limit returns:
throttling means the kernel stopped the container mid-work because it had used its allowance for that
scheduling slice. Third — and this is the finding — `usage` at its highest is still **below** the reduced
`limit`. State both numbers together. A container averaging well under its ceiling is not short of CPU in any
sense a capacity review would notice, and it is being throttled anyway, because a limit is enforced in short
slices and this workload's demand is bursty: it exceeds the allowance inside a slice without ever coming
close on average.

`requests` is flat across the whole window. Say so explicitly: the reservation never moved, so nothing about
scheduling or placement changed, and the limit is the only field in play. That is the distinction the whole
scenario rests on.

**Success signal:** User asks what changed the limit, or asks why a container under its limit is throttled.

**Staging:**

1. The finding alone on its own line, before any commentary:
   `[usage max] used against a [limit min] ceiling — and throttled [throttled max] anyway`
2. Blank line.
3. What kind of problem it is: not a shortage. The container is not out of CPU, it is being cut off. A limit
   is a hard stop applied in slices of a fraction of a second, so a workload that bursts hits it while its
   average sits comfortably underneath. Average usage is exactly the number that hides this.
4. The four series as a short before-and-during, built only from the values the result returned, with
   `requests` named as the one that did not move.
5. Tie it to beat 2: every request through this container waits out those stops, which is the p95 that ran
   away while the median held.

**Objection** — "then just raise the limit and move on": that is the fix, and it is also how the workload got
here. Someone lowered the ceiling to save resources without checking how this container actually uses CPU.
Rightsizing works when usage over time is the input; this was a number changed against a reservation that was
already half the old ceiling.

**Deep link** (label "The workload in Kubernetes"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.infraops/explorer?entityId=K8S_DEPLOYMENT-98DBB38AEB111C5B&tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}
```

---

## Beat 4 — The Change

**Requires:** 3

**Why this step:** A limit does not move on its own, and the platform records every change to a deployment spec — so we can name the edit, the container it hit and the minute it landed.

**Objective:** User sees the exact field that changed, in the platform's own words, close enough to the
problem start to be the trigger, and sees it changed back.

**Evidence DQL:**

```dql
fetch events, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter event.name == "Deployment spec change"
| filter k8s.namespace.name == "easytrade"
| filter contains(toString(change_details), "resources/limits")
| fieldsAdd detail = toString(change_details)
| summarize events = count(), first_at = min(timestamp), last_at = max(timestamp),
    by: { workload = k8s.workload.name, detail }
| sort first_at asc
| fieldsAdd change_before_problem_min = round(toDouble(toTimestamp("{{STARTED}}") - first_at) / 60000000000, decimals: 1),
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

One row per distinct change text; a single edit is recorded several times as the rollout replaces pods, which
is what `events` counts.

**Show:** Headline "What changed just before it started". Table: Workload | Change detail | Events | First seen (UTC) | Minutes before the problem (min), 2 rows. Finding: {change_before_problem_min} minutes before the problem started,
{workload} had its limit changed as {detail}. Bullets: The change quoted verbatim with field container and values;
Limits not requests so it throttles whatever the node load; Reduction then restore tell apart by value and timing;
Version change rode along and why is the owning team's to say.

**Reveal:** Lead with `change_before_problem_min`, the gap between the first change and the problem start.
Quote `detail` verbatim — it names the field, the container and both values, and it is the platform's record
rather than anyone's reconstruction. Typically two rows: the reduction, re-recorded several times as the
rollout proceeds, and the restore afterwards. Tell them apart by their values and timing.

Name the field precisely. It is `resources/limits`, the ceiling — not `resources/requests`, which beat 3 shows
flat. Those two are routinely confused and they fail in different ways: a reservation that is too low affects
where a pod is scheduled and who it competes with, while a ceiling that is too low throttles the container no
matter how idle the node is. This incident is the second kind.

Beat 1's `description` carries an `Info: EasyTrade version change` line with a version number. Say the two
together as returned — a new application version went out, and the spec change rode along with it — without
claiming the version itself did anything: the field that changed is the one in this result.

What the change was *for* is not in the result — whether it was a cost exercise, a copy-paste or a bad default
is the owning team's to say. The restore is also not a conclusion: it stops the symptom, it does not establish
the right number.

**Objection** — "a couple of minutes apart isn't proof": agree. What makes it more than a coincidence is beat
3, where throttling tracks the ceiling across the same minutes and returns when it does. Timing alone is
suggestive; timing plus a mechanism is the argument.

No `resources/limits` change in this window is a finding too, not a dead end: say the platform recorded none,
and that this occurrence then has a different cause from the usual one — beat 3's series still say whether the
ceiling moved.

**Success signal:** User names the limit reduction as the trigger, or asks who changed it.

**Deep link** (label "The broker service workload"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.infraops/explorer?entityId=K8S_DEPLOYMENT-98DBB38AEB111C5B&tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}
```

The spec change is **not** on the problem record, so this beat does not link there: the workload is
where the change and its effect sit together.

---

## Beat 5 — The Agent's Analysis

**Requires:** 3

**Why this step:** We have the mechanism and the edit; what we do not have is a number to put back — and the Kubernetes troubleshooting agent was handed this problem's context and wrote exactly that onto the record.

**Objective:** User sees an AI agent close the loop on the same problem record: its root cause, what it
checked and ruled out, and a concrete configuration to apply — all written where the on-call engineer is
already looking.

Two queries, so two turns: first that the agent ran and nobody started it, then what it wrote.

**Evidence DQL — the run (first):**

```dql
fetch dt.system.events, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter event.kind == "WORKFLOW_EVENT" and event.type == "WORKFLOW_EXECUTION"
| filter dt.automation_engine.state.is_final == true
| filter dt.automation_engine.workflow.title == "k8s-troubleshooting-agent"
| summarize runs = count(), states = collectDistinct(dt.automation_engine.state),
    trigger = takeFirst(dt.automation_engine.workflow_execution.trigger.type),
    first_done = min(timestamp), last_done = max(timestamp)
| fieldsAdd done_after_problem_min = round(toDouble(first_done - toTimestamp("{{STARTED}}")) / 60000000000, decimals: 1),
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

`timestamp` is when a run finished; a run writes more than one event, which is why the filter keeps the final one.
Several runs in the window means the workflow was triggered once per problem in the cluster of near-duplicates.

**Show:** Headline "The agent ran on its own". Table: Runs | Outcome | Triggered by | First finished (UTC) |
Minutes after the problem (min), 1 row. Finding: The troubleshooting workflow ran {runs} times, triggered by {trigger},
the first finished {done_after_problem_min} minutes after the problem opened. Bullets: Nobody started it; What it
gathers before it reasons; Where its conclusion goes.

**Reveal:** Lead with `trigger` and `done_after_problem_min`: a workflow ran on its own, set off by the platform, and
was done minutes after the problem opened — before anyone on call had opened the record. Say what kind of thing it is
in plain words: a Dynatrace workflow that gathers the affected workload's spec changes, metrics, logs and YAML, has an
AI agent reason over them, and writes the conclusion back onto the problem. Say `trigger` as returned and nothing
more specific: the result says it was an event, not which one, so never claim it fires "when a problem opens".
`states` is the outcome; any value other than `SUCCESS` is said as returned. No rows means no run finished in this
window: say so, and that the notes below may still exist from a run outside it.

Never promise that it opens a pull request or applies the change: nothing in the result says it does.

**Evidence DQL — what it wrote:**

```dql
fetch events, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter annotation.source == "Dynatrace AI Workflow"
| expand pid = annotation.problem_ids
| lookup [fetch dt.davis.problems, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
          | filter in("easytrade", k8s.namespace.name)
          | fields pid = event.id, display_id, problem = event.name],
    sourceField: pid, lookupField: pid, fields: { display_id, problem }
| filter isNotNull(display_id)
| fieldsAdd d = toString(event.description)
| fieldsAdd rc = indexOf(d, "## Root Cause"), sol = indexOf(d, "## Solution"), chk = indexOf(d, "## What Was Checked")
| fieldsAdd sections = if(rc >= 0, 1, else: 0) + if(chk >= 0, 1, else: 0) + if(sol >= 0, 1, else: 0)
| sort sections desc
| summarize notes = count(), on_problems = countDistinct(display_id), problems = collectDistinct(problem),
    first_note = min(timestamp), last_note = max(timestamp),
    agent_root_cause = takeFirst(if(rc >= 0, substring(d, from: rc + 14, to: rc + 360), else: "")),
    agent_ruled_out = takeFirst(if(chk >= 0, substring(d, from: chk + 20, to: chk + 300), else: "")),
    agent_solution = takeFirst(if(sol >= 0, substring(d, from: sol + 12, to: sol + 330), else: ""))
| fields notes, on_problems, problems, first_note, last_note, agent_root_cause, agent_ruled_out, agent_solution,
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

The agent writes onto several records of the same cluster of problems, which is why `on_problems` can exceed
one and why the lookup matches on the namespace rather than on `{{PROBLEM_ID}}` alone.

**Say which record the notes are on.** `problems` names them; when none of them is the record this session has
been working, say so rather than implying the notes are on it — the link opens our record, not necessarily the
annotated one — and put that in `Still open`. A label is a promise about what opens. The note's own section
headings are `## Root Cause`, `## What Was Checked (No Issues Found)` and `## Solution`; each extract is the
start of that section, so the text may run into the next heading — quote only as far as the sentence ends.

**Show:** Headline "What the troubleshooting agent wrote". Table: Notes | Problems annotated | First note (UTC) | Last
note (UTC), 1 row. Finding: The agent wrote {notes} notes on {on_problems} problems, the first {first_note} minutes
after the problem opened. Bullets: Agent root cause quoted and checked against our own; What it ruled out; Its
recommended configuration for the owning team to review; Which record the notes sit on. Quote one sentence at a time,
give the proposed value, and show the YAML only when asked.

**Reveal:** One sentence on the chain, then the agent's own words, attributed to it and quoted, never paraphrased
into our own read:

- **The chain:** Dynatrace correlated the signals into these problems, triggered the agent with them, and the agent
  wrote back onto the same records `first_note` minutes after the problem opened. Every investigation is in one
  place, and from there it can go to a ticket or a coding agent with the evidence attached.
- **`agent_root_cause`:** compare it with what the CPU numbers and the spec change already established. When it
  agrees, say so plainly: the agent reached the same conclusion from the same platform data, which makes it
  checkable rather than something to take on trust.
- **`agent_ruled_out`:** the negative findings are worth as much as the positive one: an engineer at three in the
  morning would have spent that time themselves.
- **`agent_solution`:** a concrete configuration, often with the YAML. State it as the agent's recommendation for the
  owning team to review, never as applied. Where it proposes a value, say the value and that the right ceiling is
  set from usage over time, not from one incident.
- **Different figures:** where the agent's differ from ours (another average, another baseline), state both and say
  they are different measurements of the same window, not a contradiction to resolve. Never replace ours with its.
- **Gaps:** an empty `agent_root_cause`, `agent_solution` or `agent_ruled_out` means the note carried no such
  section: say that, and never fill it from the earlier steps. No rows at all means nothing is written yet; on a
  problem still open that is what it sounds like, since the agent takes minutes.

**Objection** — "so it fixed it?": no. The agent investigated and recommended; the restored ceiling, where that step has run, is what was changed
back is the platform's record of a deployment, not the agent acting. Every step it took is written down and
attributed, with a human deciding whether to apply it.

**Success signal:** User asks what limit to set, or how to size the rest of the cluster.

**Deep link** (label "The problem record the notes sit on"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.davis.problems/problem/{{PROBLEM_ID}}?from={{TF_FROM_MS}}&to={{TF_TO_MS}}
```
