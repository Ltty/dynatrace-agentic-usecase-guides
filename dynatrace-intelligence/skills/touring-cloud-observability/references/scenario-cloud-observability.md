# Scenario: Cloud Observability (Showcase) — Context and Beats

Read once the user has picked a scenario. This is a **showcase**, not an incident: there is no page to answer and no
root cause to find. We show the cloud estate we run, from all three clouds down to one function, what runs on it, the
agents that work its problems, and what it costs. The survey query does not cover it; its beats supply their own tokens
(see "Tokens").
Reveals describe the *shape* of a finding, never its values. Resource counts, request counts, problem IDs, agent notes,
workflow runs and costs change every day — read them from the live result.

## Contents

- [Business context](#business-context)
- [Scope](#scope)
- [Tracks](#tracks)
- [Tokens](#tokens)
- [Handoff fields](#handoff-fields)
- [Beat 1 — The Estate](#beat-1--the-estate)
- [Beat 2 — One Function in Depth](#beat-2--one-function-in-depth)
- [Beat 3 — What Runs on It](#beat-3--what-runs-on-it)
- [Beat 4 — Agents on the Problem](#beat-4--agents-on-the-problem) (peak)
- [Beat 5 — The Bill and the Target](#beat-5--the-bill-and-the-target)
- [Beat 6 — Cost Next to Utilization](#beat-6--cost-next-to-utilization) (peak)
- [Extra — Workflows That Act](#extra--workflows-that-act) (on request, after the close)

---

## Business context

| Field | Value |
|---|---|
| `kind` | `showcase` |
| `service_name` | "cloud estate" |
| `symptom` | "the cloud estate, what runs on it and what it costs" |
| delivery | presentation only — no `pull_line`, no `mode_question`, no walk-through |

No `avg_order_value_usd`: no revenue figure. The costs in beats 5 and 6 are the cloud bill (FOCUS `EffectiveCost`, the
price actually paid after discounts), not lost revenue; never mix the two.

**Framing.** Present tense, no urgency, still "we". The tour answers four challenges that grow with cloud complexity: no
unified view (beats 1 and 2: all clouds in one place, one resource in depth), manual correlation (beat 3: the service on
the function and one problem with its root cause and business impact), wasted AI potential (beat 4: agents that work
problems with the same connected context), and rising cloud cost (beats 5 and 6).

**The cost track is a method demonstration**, not a savings engagement: what it shows is *how* to find money on a
cloud bill from real data — what the bill says, where it concentrates, what is safe to touch, and who owns it. A
figure the user brings is a lens that makes the method concrete, never a target the session is scored against. Open
beat 5 by putting the question yourself, then answer it from the data, the way an analyst would.

**The 10% is this scenario's own constant,** the same way beat 6's CPU and memory thresholds are. No row returns it
and nobody in the session asked for it, so it is never "the target" and never attributed to a CTO or any other
stakeholder the conversation does not contain. It is the SRE's working assumption, said as one — "my working
assumption is there's at least 10% in here" — and motivated by a figure that did come back, the untagged share.
State it that way every time it is used, including in the action list and the report. The workflows that prevent, remediate and optimize are an extra,
offered after the close.

Cloud cost is in scope here: the bill is part of this scenario. Dynatrace's own pricing and licensing are not.

## Scope

**Tenant:** dtctl context `demo-live` (`https://guu84124.apps.dynatrace.com`, read-only). Its entities and the bill exist
on that tenant only.

**Data objects:** `smartscapeNodes`, `smartscapeEdges`, `spans`, `dt.davis.problems`, `events` (agent notes on
problems, Kubernetes spec changes), `dt.system.events` (workflow executions), `bizevents`
(`event.type == "cost.real.spend"`, FOCUS 1.2), `timeseries` on `cloud.aws.rds.*`

**Agents** — each writes its notes onto problems as annotation events (`annotation.source`, with `annotation.problem_ids`):

| `annotation.source` | Agent | Its notes |
|---|---|---|
| `aws_devopsagent` | AWS DevOps Agent | investigation results and mitigation recommendations |
| `SRE Agent` | SRE Agent (Cloud SRE Agents) | investigation started, then a root cause analysis with a verdict |
| `Dynatrace AI Workflow` | Kubernetes troubleshooting agent (the `k8s-troubleshooting-agent` workflow) | "Dynatrace AI Analysis": the incident context (cluster, namespace, workload), a root cause and a proposed fix |

**Stable IDs** (demo-live):

| Name | ID |
|---|---|
| image-provider-live Lambda (Clouds app node) | `AWS_LAMBDA_FUNCTION-9365828D44E6A036` |
| Its ARN (carried by the spans as `cloud.resource_id`) | `arn:aws:lambda:us-east-1:246186168471:function:image-provider-live` |
| image-provider-live in us-east-1 (the service on the function) | `SERVICE-42411741F5F4AC50` |
| image-provider-live-products in us-east-1 (root cause of the daily problem the AWS DevOps Agent annotates) | `SERVICE-F4E5246FA8EA27D7` |
| EasyTrade Kubernetes namespace (the problems the Kubernetes troubleshooting agent annotates in beat 4) | `easytrade` |
| Workflow: k8s-troubleshooting-agent | `1e4e7449-b32a-32e3-8bb8-0e2319f23daf` |
| Workflow: AWS EBS remediate low storage (prevent) | `dd59f7b0-1154-4c06-b677-b3c64a17d475` |
| Workflow: AWS regional outage failover Lambda (remediate) | `4df6c4b4-407e-4703-95a7-783481a22545` |
| Workflow: Cost & Carbon Optimization: Calculation (optimize) | `9f1eb5e4-8733-496e-8d76-81d7f2e1e60c` |

**Other views**, offered only when the user asks for them (they are not a beat's link):

| Ask | Label | URL |
|---|---|---|
| Kubernetes troubleshooting agent | "k8s troubleshooting workflow" | `https://{{LINK_HOST}}/ui/apps/dynatrace.automations/workflows/1e4e7449-b32a-32e3-8bb8-0e2319f23daf` |
| What affected users saw (beat 3) | "Astroshop sessions, last 12 hours" | `https://{{LINK_HOST}}/ui/apps/dynatrace.users.sessions/sessions/finished-sessions?perspective=general&sort=start_time%3Adescending&tf=now-12h%3Bnow#filtering=Frontends+%3D+Astroshop` |
| Asking Dynatrace Assist about cost | "Clouds services explorer" (open Dynatrace Assist from there) | `https://{{LINK_HOST}}/ui/apps/dynatrace.clouds/smartscape/services?perspective=health&sort=healthIndicators%3Aascending%3BcustomAlerts%3Aascending%3Bname%3Aascending` |
| On-premise VMware estate | "VMware overview dashboard" | `https://{{LINK_HOST}}/ui/apps/dynatrace.dashboards/dashboard/com-dynatrace-vmware-integration-overview#from=now%28%29-30d&to=now%28%29` |
| A VMware virtual machine in Infrastructure & Operations | "VMware virtual machines" | `https://{{LINK_HOST}}/ui/apps/dynatrace.infraops/smartscape/virtualization/com.dynatrace.vmware-integration/VMWARE_VIRTUALMACHINE-inventory?perspective=health&tf=now-30d%3Bnow&detailsId=VMWARE_VIRTUALMACHINE-182F4D63E3FCACFE#filtering=hypervisor.type+%3D+VMware` |

## Tracks

The six beats are two arcs, each a complete story on its own. Which one the user is on is set by how
they arrived, and the session close fires when that track's beats have all run ("Session close").

| Track | Beats | Ends on |
|---|---|---|
| `cost` | 5 → 6 | the cost action list |
| `estate` | 1 → 2 → 3 → 4 | the four challenges |

- Arriving at the bill — a cloud-cost ask, or the opening's cloud line — walks `cost`. When it closes,
  the estate tour is the way out, offered **forward**: "that's the money; the other half of this is
  what we actually run". Never walk back into beats 1–4 as a continuation of the cost story.
- A pick of the cloud tour walks `estate`, then `cost`, as one sequence — that is the full guide.
- The Extra comes after either close, on request.
- Beat 3 shows a problem at tour depth and beat 4 counts the notes on it; the investigation that walks
  that same problem to its root cause is `lambda-iam-denied`. Offer it **only after a close**, never
  mid-tour, and only as what it is — the long way round the problem just shown, not a second tour.
  Name it by what it investigates, never by its id.

## Tokens

There is no survey row. Every token comes from a result in this conversation:

| Token | Source |
|---|---|
| `{{SURVEY_AT}}` | The `queried_at` of the **first query of the conversation**, whatever that query was, fixed from then on |
| `{{PROBLEM_ID}}`, `{{TF_FROM_MS}}`, `{{TF_TO_MS}}` | Beat 3's problem query (`problem_id`, `tf_from_ms`, `tf_to_ms`) |

`{{SURVEY_AT}}` never moves once set. Entering the tour at any beat is fine: the opening query or the probe already
anchored it, and re-anchoring on a later beat is what makes `elapsed_min` run backwards. When a beat's own query
**is** the conversation's first — a cost ask straight from the greeting, say — there is nothing to subtract yet:
`elapsed_min` is `0` on that query, and its `queried_at` is the anchor for every query after it. A jump to beat 4 or later
does not need beat 3's problem: beat 4 finds its own.

## Handoff fields

There is no incident to hand off. The handoff is the **cost action list** that beat 6 ends with; beat 6 is that block
(the incidents skill's session-protocol → "Handoff block": a beat that is itself the handoff summary).

| Value | Source |
|---|---|
| `Goes to` | Beat 6's team split: the owner teams by their `dt_owner_team` tag; the untagged spend is named as having no owner |
| Working assumption | Beat 5 `target_usd` (10% of `total_usd`) — the SRE's, never "the target" |
| Largest line | Beat 5's cost-lines query, first row, with its `teams` |
| Do not shrink | Beat 6 rows with verdict "low CPU, no memory headroom" |
| Monitor first | Beat 6 row "no utilization data": `dbs` and `usd_30d` |
| No owner | Beat 5 `untagged_usd`, `untagged_pct` |
| Problem owner (beat 3) | `owning_team` on the problem record, when asked who owns the problem, not the bill |

Populations here: cloud resources (beat 1), requests on the service (beat 3), the problem record's affected users
(beat 3), problems with agent notes and the notes themselves (beat 4), workflow runs (the extra), dollars of `EffectiveCost` over the last 30 days of charges (beats 5 and 6). Never mix
them, and say "the last 30 days of charges imported so far": the bill arrives once a day.

---

## Beat 1 — The Estate

**Why this step:** To talk about what the cloud costs and what runs on it, we first need what is actually out there — across every provider, in one place.

**Objective:** User sees all three clouds in one place: how many resources each one holds, from one query, with no cloud
console opened.

**Evidence DQL:**

```dql
smartscapeNodes "*"
| filter startsWith(type, "AWS_") or startsWith(type, "AZURE_") or startsWith(type, "GCP_")
| fieldsAdd cloud = if(startsWith(type, "AWS_"), "AWS", else: if(startsWith(type, "AZURE_"), "Azure", else: "Google Cloud"))
| summarize resources = count(), resource_types = countDistinct(type), by: { cloud }
| sort resources desc
| fieldsAdd queried_at = now()
```

`queried_at` is `{{SURVEY_AT}}` only when this is the first query of the conversation (see "Tokens").

**Reveal:** One row per cloud: AWS, Azure and Google Cloud, each with its resource count and the number of distinct
resource types. State all three. These are discovered through each provider's native integration and kept current in
Smartscape; this one query replaces opening three consoles. Say nothing about health here: this query counts resources,
it does not rate them.

**Success signal:** User asks what is inside one of the clouds, or how a resource is connected.

**Deep link** (label "Clouds overview"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.clouds/home
```

---

## Beat 2 — One Function in Depth

**Why this step:** Counting resources says nothing about any one of them, so we take a single function and see it the way the provider describes it.

**Objective:** User sees one resource the way the cloud provider describes it — configuration, tags, owner, cloud
relationships — without opening AWS.

**Evidence DQL — the function:**

```dql
smartscapeNodes "AWS_LAMBDA_FUNCTION"
| filter id == toSmartscapeId("AWS_LAMBDA_FUNCTION-9365828D44E6A036")
| parse aws.object, "JSON:obj"
| fieldsAdd cfg = obj[configuration][configuration]
| fields name, region = aws.region, runtime = cfg[runtime], memory_mb = cfg[memorySize], timeout_s = cfg[timeout],
    last_modified = cfg[lastModified], stage = primary_tags.stage, application = primary_tags.application,
    team = primary_tags.team, owner_team_tag = `tags:aws`[dt_owner_team], cost_center = `tags:aws`[costcenter],
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

**Evidence DQL — its cloud relationships:**

```dql
smartscapeEdges "*"
| filter source_id == toSmartscapeId("AWS_LAMBDA_FUNCTION-9365828D44E6A036")
| summarize related = collectDistinct(target_type), by: { relationship = type }
```

**Reveal:** The function's live configuration (runtime, memory, timeout, when it was last modified) and its tags (stage,
application, cost center), read from the AWS API. Two ownership tags are set: `team` and `owner_team_tag`. When they
differ, state both as returned; which one is right is the owners' call. Its relationships are the cloud-native ones —
the IAM role and security group it uses, the VPC and subnet it is attached to. State `last_modified` as a UTC time; it
is not evidence of anything by itself.

**Success signal:** User asks what runs on the function, or who owns it.

**Deep link** (label "image-provider-live in the Clouds app"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.clouds/smartscape/functions?perspective=health&detailsId=AWS_LAMBDA_FUNCTION-9365828D44E6A036&sidebarOpen=false&tf=now-24h%3Bnow
```

---

## Beat 3 — What Runs on It

**Why this step:** Configuration does not tell us whether anything depends on it — for that we need the service running on the function and what has gone wrong on it.

**Objective:** User connects the infrastructure to the application: the service running on the function, how it
behaves, and the latest problem on it, with the business context and the AWS DevOps Agent's notes on the same record.

**Evidence DQL — the service on the function (last 6 hours):**

```dql
fetch spans, from: now()-6h
| filter cloud.resource_id == "arn:aws:lambda:us-east-1:246186168471:function:image-provider-live"
| filter request.is_root_span == true
| summarize requests = count(), failed = countIf(request.is_failed == true),
    p50_ms = round(percentile(toDouble(duration), 50) / 1000000, decimals: 0),
    p95_ms = round(percentile(toDouble(duration), 95) / 1000000, decimals: 0),
    by: { service = dt.service.name }
| sort requests desc
| limit 1
| fieldsAdd failure_rate_pct = round(100.0 * failed / requests, decimals: 2)
| fields service, requests, failed, failure_rate_pct, p50_ms, p95_ms,
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

The spans name the function by its ARN; the service is joined to the Clouds-app resource through it —
that join is the point of the step, so the ARN filter stays even though it is the expensive one.

**Six hours, not twenty-four.** The same shape over 24h scans 6.83 GB against 1.67 GB for 6h, which made
this the heaviest query in the framework — heavier than the whole cost track. The function takes roughly
48,000 requests an hour, so 6 hours is never empty and the behaviour reads the same. Adding a service-id
filter alongside the ARN does not prune anything: measured at 6.84 GB, marginally worse.

**Evidence DQL — its latest problem, with the AWS DevOps Agent's notes:**

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter dt.davis.is_duplicate == false
| filter in(root_cause_entity_id, "SERVICE-F4E5246FA8EA27D7", "SERVICE-42411741F5F4AC50")
| lookup [fetch events, from: now()-48h
          | filter annotation.source == "aws_devopsagent"
          | expand pid = annotation.problem_ids
          | summarize agent_notes = count(), agent_summaries = countIf(not contains(event.name, "summary not available")),
              by: { pid }],
    sourceField: event.id, lookupField: pid, fields: { agent_notes, agent_summaries }
| sort coalesce(agent_notes, 0) desc, event.start desc
| limit 1
| fieldsAdd window_from = event.start - 15m, window_to = coalesce(event.end, now()) + 15m
| fields problem_id = event.id, display_id, title = event.name, status = event.status, started = event.start, ended = event.end,
    root_cause = root_cause_entity_name, affected = affected_entity_names, owning_team = team,
    affected_users = dt.davis.affected_users_count, agent_notes, agent_summaries,
    tf_from_ms = toLong(window_from) / 1000000, tf_to_ms = toLong(window_to) / 1000000
```

The problem the AWS DevOps Agent annotated comes first; without one, the newest. `problem_id`, `tf_from_ms` and
`tf_to_ms` fill the deep link.

**Reveal:** The service's requests, failure rate and p50/p95 over 6 hours come straight from its traces — label them
"requests in the last 6 hours". A window that holds no failures is a clean window, said as that, not as an absence of data: the incident has its own step. Every signal is correlated into one problem, not a pile of alerts: the problem card
gives the business impact first — `affected_users` as the problem record's affected users, and an `affected` list that
runs from the services to the Astroshop frontend, the ingress, the application and a synthetic image check (that list is
the business context, what depends on the function) — then the root cause, and `owning_team`. The dependency picture
(the Visual Resolution Path) is on the problem page, one link away. Then the AWS DevOps Agent: Dynatrace handed it the
problem's context, and it wrote `agent_notes` notes back onto this same problem, so the investigation is tracked in one
place and can go on to ServiceNow or a coding agent from there. When `agent_summaries` is 0, say the notes are on the
record but carry no readable summary — the findings are in the agent's own task. Never describe findings the result does
not hold. What affected users saw is in Users & Sessions ("Other views"), offered on request.

No problem in 48 hours is a finding too: the function has had no problem in that time; skip the deep link's problem and
go on to beat 4.

**Objection** — "so the problem is solved?": this is the record, not the fix. Whether it closed, and when, is
`status` and `ended`; what changed is the owning team's to say. Beat 4 shows the agents that work problems like this one.

**Success signal:** User asks who or what works on the problem, or asks about the business impact.

**Deep link** (label "Problem in Dynatrace"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.davis.problems/problem/{{PROBLEM_ID}}?from={{TF_FROM_MS}}&to={{TF_TO_MS}}
```

---

## Beat 4 — Agents on the Problem

**`peak_moment: true`**

**Why this step:** A problem with full context is what an AI agent can actually work, so the next thing to see is the agents doing exactly that on these records.

**Objective:** User sees AI agents work problems with the context Dynatrace already holds: three agents writing onto
problem records around the clock, and one Kubernetes problem where the troubleshooting agent names the change behind a
slowdown and proposes the fix.

**Evidence DQL — the agents on problem records (7 days):**

```dql
fetch events, from: now()-7d
| filter in(annotation.source, "aws_devopsagent", "SRE Agent", "Dynatrace AI Workflow")
| fieldsAdd agent = if(annotation.source == "aws_devopsagent", "AWS DevOps Agent",
    else: if(annotation.source == "SRE Agent", "SRE Agent", else: "Kubernetes troubleshooting agent"))
| expand pid = annotation.problem_ids
| summarize problems = countDistinct(pid), notes = count(), note_types = collectDistinct(event.name), last_note = max(timestamp),
    by: { agent }
| sort problems desc
| fields agent, problems, notes, note_types, last_note,
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

**Evidence DQL — the Kubernetes troubleshooting agent on an EasyTrade problem:**

```dql
fetch dt.davis.problems, from: now()-7d, to: now()
| filter dt.davis.is_duplicate == false
| filter in("easytrade", k8s.namespace.name)
| lookup [fetch events, from: now()-7d
          | filter annotation.source == "Dynatrace AI Workflow"
          | expand pid = annotation.problem_ids
          | sort timestamp desc
          | summarize agent_notes = count(), note = takeFirst(event.description), workload = takeFirst(dt.entity.cloud_application.name),
              by: { pid }],
    sourceField: event.id, lookupField: pid, fields: { agent_notes, note, workload }
| filter isNotNull(agent_notes)
| fieldsAdd ns = "easytrade"
| join [fetch events, from: now()-8d
        | filter event.name == "Deployment spec change" and k8s.namespace.name == "easytrade"
        | filter contains(toString(change_details), "resources/limits")
        | fields ns = k8s.namespace.name, change_at = event.start, change = change_details, changed_workload = k8s.workload.name],
    on: { ns }, fields: { change_at, change, changed_workload }, kind: leftOuter
| filter isNull(change_at) or (change_at <= event.start and change_at >= event.start - 2h)
| sort change_at desc
| summarize change_at = takeFirst(change_at), change = takeFirst(change), changed_workload = takeFirst(changed_workload),
    by: { event.id, display_id, event.name, event.category, event.start, event.end, event.status, workload, agent_notes, note,
          affected_users = dt.davis.affected_users_count, owning_team = team }
| sort if(event.category == "SLOWDOWN", 0, else: 1) asc, if(isNotNull(change_at), 0, else: 1) asc, event.start desc
| limit 1
| fieldsAdd rc_at = indexOf(note, "## Root Cause"), sol_at = indexOf(note, "## Solution"),
    rf_at = indexOf(note, "Recommended Fix")
| fieldsAdd fix_at = if(sol_at >= 0, sol_at + 12, else: rf_at)
| fieldsAdd agent_root_cause = if(rc_at >= 0, substring(note, from: rc_at, to: rc_at + 500), else: substring(note, from: 0, to: 500))
| fieldsAdd agent_fix = if(fix_at >= 0, substring(note, from: fix_at, to: fix_at + 300), else: "")
| fields display_id, title = event.name, status = event.status, started = event.start, ended = event.end, affected_users,
    owning_team, agent_workload = workload, agent_notes, agent_root_cause, agent_fix, change_at, changed_workload, change,
    change_lead_min = round(toDouble(event.start - change_at) / 60000000000, decimals: 0)
```

A slowdown with a resource-limit change in the two hours before it comes first; without one, the newest annotated
EasyTrade problem. `change` is the Kubernetes spec-change event's own text; `agent_fix` is the note's own
"Solution" section, which is what staging step 5 quotes; its notes head that section `## Solution` and only
rarely "Recommended Fix", so the query prefers the first and falls back to the second; `agent_root_cause` is the start of the
agent's note at its root-cause heading.

**Reveal:** First the agents: one row each, with the problems they wrote on in 7 days and their note types — the AWS
DevOps Agent (investigation and mitigation, the one annotating the problem earlier in the tour if that step has run), the SRE Agent from Cloud SRE Agents (investigation, then a root
cause with a verdict) and the Kubernetes troubleshooting agent ("Dynatrace AI Analysis"). They are triggered from the
problems and post back onto them, so the on-call engineer reads every investigation in one place. Then one of them at
work: an EasyTrade problem (`title`, `display_id`, its window as UTC times) where the Kubernetes troubleshooting agent
wrote a note on `agent_workload`. Quote the root cause from `agent_root_cause` in the agent's words, attributed to the
agent. `change` is the platform's record of a spec change on `changed_workload`, `change_lead_min` minutes before the
problem started: state it as returned. Kubernetes tuning cuts both ways — too little CPU or memory and the application
slows or fails — and that is what the change and the note show side by side. When the note gives a different time for the
change than `change_at`, the event is the record. The fix the note proposes is the agent's recommendation for the owning
team to review, not something applied — and that team is this problem's `owning_team` or nobody,
never one carried over from beat 3. No `change` row: say the platform recorded no resource-limit change in the two
hours before it, and give the agent's root cause alone.

**Success signal:** User asks what the agent recommends, or what can act on its own.

**Staging:**

1. The finding alone on its own line, before any commentary:
   `[changed_workload]: [change, in plain words] — [change_lead_min] minutes before [title]`
   (with no `change`: `[agent_problems] problems in 7 days with an agent's notes on them`, the sum of `problems`).
2. Blank line.
3. What kind of finding it is: an agent with the problem's full context — the slowdown, the workload, the spec change on
   it — goes from alert to a named cause and a proposed fix without anyone assembling the evidence by hand. AI is only as
   good as the context it gets.
4. The agent's root cause, quoted and attributed, then the agents table, one row per agent.
5. The proposed fix in one line, quoted from `agent_fix` — the note's own "Solution" section — as the
   agent's recommendation, not something applied. Empty `agent_fix` means the note carried no fix
   section: say that, and do not infer one from the root cause. Name the team only from **this**
   problem's `owning_team`; it is often null, and then it is "the owning team", never the team
   beat 3 returned for a different problem.

**Deep link** (label "Cloud SRE Agents"):

```text
https://{{LINK_HOST}}/ui/apps/community.cloudsreagents/
```

---

## Beat 5 — The Bill and the Target

**Why this step:** To find money we can take off the bill, we first have to know what the bill is and how much of it nobody is accountable for.

**Objective:** User sees the real bill answer the question the SRE put: what a 10% working assumption is in dollars,
where the money goes, and how much of it has no owner.

Open by putting the question yourself, in one line, with the assumption owned: "Half this bill has no owner, so my
working assumption is there's at least 10% in here — about $[target_usd]. Let's find out where." Then work through it
in steps, the way an analyst would: the bill first (this beat), then utilization next to cost (beat 6). The bill and the monitoring data sit in the same place, which is what lets a cost be
matched to the resource behind it and to how busy that resource is.

**Evidence DQL — the bill:**

```dql
fetch bizevents, from: now()-7d
| filter event.type == "cost.real.spend"
| filter toTimestamp(focus.ChargePeriodStart) >= now()-30d and toTimestamp(focus.ChargePeriodStart) < now()
| parse focus.Tags, "JSON:tags"
| summarize cost = sum(toDouble(focus.EffectiveCost)),
    untagged = sum(if(isNull(tags[dt_owner_team]), toDouble(focus.EffectiveCost), else: 0.0)),
    by: { category = focus.ServiceCategory }
| sort cost desc
| summarize total_usd = round(sum(cost), decimals: 0), untagged_usd = round(sum(untagged), decimals: 0),
    categories = collectArray(record(category, usd = round(cost, decimals: 0)))
| fieldsAdd target_usd = round(total_usd * 0.1, decimals: 0), untagged_pct = round(100.0 * untagged_usd / total_usd, decimals: 0),
    top_categories = arraySlice(categories, from: 0, to: 4)
| fields total_usd, target_usd, untagged_usd, untagged_pct, top_categories,
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

**Evidence DQL — the largest lines:**

```dql
fetch bizevents, from: now()-7d
| filter event.type == "cost.real.spend"
| filter toTimestamp(focus.ChargePeriodStart) >= now()-30d and toTimestamp(focus.ChargePeriodStart) < now()
| parse focus.Tags, "JSON:tags"
| summarize usd = round(sum(toDouble(focus.EffectiveCost)), decimals: 0),
    untagged_usd = round(sum(if(isNull(tags[dt_owner_team]), toDouble(focus.EffectiveCost), else: 0.0)), decimals: 0),
    teams = collectDistinct(coalesce(tags[dt_owner_team], "UNTAGGED")),
    by: { service = focus.ServiceName, operation = aws.x_Operation, usage = focus.SkuMeter }
| sort usd desc
| limit 5
```

The charge period, not the import `timestamp`, places a cost in the window. The whole bill is re-imported daily in one
go, so a 7-day fetch already holds every row of the last 30 days of charges and reads about a sixth of what a 75-day
fetch does. If the import ever stops for more than a week the query returns nothing and the showcase reads as
unavailable — check the import first when that happens, rather than widening the window.

**Reveal:** `total_usd` over the last 30 days of charges, and `target_usd` as the 10% you are assuming is in there —
your assumption, not a target anyone set. The `top_categories`, with
their dollars. `untagged_usd` and `untagged_pct`: that share of the bill carries no team tag, so nobody is asked to
explain or reduce it. The largest single line is usually CloudWatch log ingestion (`PutLogEvents`, billed per byte); state
whichever line is first, its dollars, and how much of it is `untagged_usd`. **`teams` is the set of tags that
appear anywhere on that line, not how the dollars split** — a line that is almost entirely untagged still lists
every team that touched it, so never read it as ownership. `untagged_usd` against `usd` is the split. Compare the
line with the target. What can be cut from it is a
retention and volume decision for its owners; the bill shows the size, not the waste.

**Evidence DQL — the untagged spend, on request** (the user asks what the unowned half is):

```dql
fetch bizevents, from: now()-7d
| filter event.type == "cost.real.spend"
| filter toTimestamp(focus.ChargePeriodStart) >= now()-30d and toTimestamp(focus.ChargePeriodStart) < now()
| parse focus.Tags, "JSON:tags"
| filter isNull(tags[dt_owner_team])
| summarize usd = round(sum(toDouble(focus.EffectiveCost)), decimals: 0),
    by: { category = focus.ServiceCategory, service = focus.ServiceName, operation = aws.x_Operation }
| sort usd desc
| limit 6
```

Run it when the user asks where the unowned money sits — they do, and it is the natural question after the
untagged share is named. The lines are the same shape as the largest-lines query, filtered to rows with no
`dt_owner_team`. Name the categories as returned; a category is not a product, so never say "which is
CloudWatch" unless `service` says so.

**Success signal:** User asks which of it is waste, or who owns a line.

**Deep link** (label "Cost explorer by service category"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.biz.carbon/cost-explorer?from=now%28%29-30d&to=now%28%29&costType=focus.EffectiveCost&dimensions=field%3Afocus.ServiceCategory
```

---

## Beat 6 — Cost Next to Utilization

**`peak_moment: true`**

**Why this step:** The bill alone cannot tell us what is safe to cut — for that we need utilisation sitting next to the cost of each resource.

**Objective:** User sees why the bill alone is not enough: a resource that looks idle on the bill can be full where it
matters, and a resource with no utilization data cannot be judged at all. Every action ends with an owner.

**Evidence DQL — databases: cost next to CPU and memory:**

```dql
fetch bizevents, from: now()-7d
| filter event.type == "cost.real.spend"
| filter toTimestamp(focus.ChargePeriodStart) >= now()-30d and toTimestamp(focus.ChargePeriodStart) < now()
| filter focus.ServiceName == "Amazon Relational Database Service" and contains(focus.ResourceId, ":db:")
| fieldsAdd db = splitString(focus.ResourceId, ":db:")[1]
| parse focus.Tags, "JSON:tags"
| summarize usd_30d = round(sum(toDouble(focus.EffectiveCost)), decimals: 0), teams = collectDistinct(tags[dt_owner_team]), by: { db }
| lookup [timeseries { cpu = avg(cloud.aws.rds.CPUUtilization.By.DBInstanceIdentifier), mem = min(cloud.aws.rds.FreeableMemory.By.DBInstanceIdentifier) },
            by: { DBInstanceIdentifier }, from: now()-14d
          | fieldsAdd cpu_avg_pct = round(arrayAvg(cpu), decimals: 1), free_mem_min_mb = round(arrayMin(mem) / 1048576, decimals: 0)],
    sourceField: db, lookupField: DBInstanceIdentifier, fields: { cpu_avg_pct, free_mem_min_mb }
| fieldsAdd verdict = if(isNull(cpu_avg_pct), "no utilization data",
    else: if(cpu_avg_pct < 10 and free_mem_min_mb < 256, "low CPU, no memory headroom",
    else: if(cpu_avg_pct < 10, "low CPU, memory headroom", else: "in use")))
| sort usd_30d desc
| summarize dbs = count(), usd_30d = sum(usd_30d), rows = collectArray(record(db, usd_30d, cpu_avg_pct, free_mem_min_mb, teams)), by: { verdict }
| fields verdict, dbs, usd_30d, shown = arraySlice(rows, from: 0, to: 3)
| sort usd_30d desc
| fieldsAdd queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

CPU is the 14-day average, memory the 14-day minimum of freeable memory. The verdict thresholds (under 10% CPU, under
256 MB free) are this scenario's, computed in the query: say them when you use a verdict. `shown` is the top three rows
of each verdict by cost, not all of them; `dbs` is the full count.

**Evidence DQL — who owns the bill:**

```dql
fetch bizevents, from: now()-7d
| filter event.type == "cost.real.spend"
| filter toTimestamp(focus.ChargePeriodStart) >= now()-30d and toTimestamp(focus.ChargePeriodStart) < now()
| parse focus.Tags, "JSON:tags"
| summarize usd = round(sum(toDouble(focus.EffectiveCost)), decimals: 0), by: { team = coalesce(tags[dt_owner_team], "UNTAGGED") }
| sort usd desc
```

**Reveal:** The databases fall into verdicts. "low CPU, no memory headroom": live databases idle on CPU but with almost
no free memory — a bill-only report would call them oversized, and shrinking them would take memory they do not have.
That is the finding: do not shrink. "no utilization data": the largest share of database spend, with no CPU or memory
series at all — the first step is to monitor them, not to cut them. A database whose name says staging is a candidate
for stopping outside working hours; the name is the only signal, so whether it can stop is its owners' call. Then the
team split: each team's dollars, and the UNTAGGED line as spend with no owner. A resource can carry two teams when its
tag changed inside the window; list both, as returned.

**Success signal:** User says not to shrink the database, asks who acts on a line, or asks for the action list.

**Staging:**

1. The finding alone on its own line, before any commentary:
   `[db] — [cpu_avg_pct]% CPU, [free_mem_min_mb] MB free memory: idle on the bill, full in memory`
   (the first row of "low CPU, no memory headroom"; with no such row, the largest "no utilization data" row:
   `[dbs] databases, $[usd_30d] — no utilization data at all`).
2. Blank line.
3. What kind of finding it is: a cost recommendation that is only safe because utilization sits next to it. This is the
   difference between a cost report and an answer.
4. The table: verdict, `dbs`, `usd_30d`, the shown rows.
5. The cost action list (it is this scenario's handoff block), built only from beat 5 and 6 results:

   ```text
   Cloud cost findings — last 30 days of charges
   Working target: 10% of $[total_usd] = $[target_usd] (my assumption, not a figure anyone set)

   What we know
     Unowned:      $[untagged_usd] ([untagged_pct]%) carries no team tag — nobody is asked to reduce it
     Concentrated: [service] [operation], $[usd], of which $[untagged_usd for that line] is untagged
     Unmeasured:   [dbs] databases, $[usd_30d], with no CPU or memory series at all
     Not to touch: [db] ([cpu_avg_pct]% CPU, [free_mem_min_mb] MB free) — low CPU, no memory headroom

   Goes to:       [the teams from the team split] — they act, we supply the evidence
   Evidence:      [every labelled link given in this session, one per line, in the order they were given]
   Still open:    which lines close the gap to $[target_usd] is the owners' call
   ```

**Evidence is every link, not the last one.** A tour that opened the Clouds overview, the function, its
problem, the agents app and the cost explorer hands over all of them; a cost-track-only session hands
over what that track gave. This block is also what the local report's `evidence` list is built from
(`skills/local-runtime/SKILL.md` → "Report (local only)"), which is why a single-line Evidence section
produced reports with one link where the incidents carried three to five.

   **These are findings, not a forecast.** The block says where the money is and where the evidence is
   thinnest — the best places to look first. It never says what any of them would save. Say that in the
   line after the block, in your own words.

   A row without a source is left out. These come from an analysis, so each owner reviews an item before
   applying it: say that once, in the line after the block.

   **No per-item saving exists, and none is to be estimated.** Users ask for one — twice in testrun 16 —
   and no result holds it: a saving is what happens after an owner acts and the next bill arrives. Say
   that plainly, give the dollars in play per line, and never split the working target across items as
   though it were a forecast.

**Deep link** (label "Cost explorer"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.biz.carbon/cost-explorer
```

---

## Extra — Workflows That Act

**On request only, after the close.** Not a beat: it is not in the walk-through report and not in the beat count. Run
it when the user asks what can be automated, about workflows, or takes the close's offer of it.

**Why this step:** Agents investigate and hand back a recommendation; the last thing worth seeing is what the same data drives without anyone in the loop.

**Objective:** Agents investigate; workflows act. User sees the three kinds of automation the same data drives: prevent
(resize a volume before it fills), remediate (fail a Lambda over to a healthy region), optimize (a regular cost
calculation that tells owners where to act).

**Evidence DQL:**

```dql
fetch dt.system.events, from: now()-7d
| filter event.kind == "WORKFLOW_EVENT" and event.type == "WORKFLOW_EXECUTION"
| filter dt.automation_engine.state.is_final == true
| filter in(dt.automation_engine.workflow.id, "dd59f7b0-1154-4c06-b677-b3c64a17d475", "4df6c4b4-407e-4703-95a7-783481a22545",
    "9f1eb5e4-8733-496e-8d76-81d7f2e1e60c")
| fieldsAdd role = if(dt.automation_engine.workflow.id == "dd59f7b0-1154-4c06-b677-b3c64a17d475", "prevent",
    else: if(dt.automation_engine.workflow.id == "4df6c4b4-407e-4703-95a7-783481a22545", "remediate", else: "optimize"))
| summarize runs = count(), succeeded = countIf(dt.automation_engine.state == "SUCCESS"),
    triggers = collectDistinct(dt.automation_engine.workflow_execution.trigger.type), last_run = max(start_time),
    by: { role, workflow = dt.automation_engine.workflow.title }
| sort role asc
| fields role, workflow, triggers, runs, succeeded, last_run,
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

Each execution writes more than one event; `state.is_final` keeps one per run.

**Reveal:** One row per kind, over 7 days: runs, how many succeeded, what triggered them, the last run (UTC). State the
totals and trigger types as returned: `Event` means the run started from an event, not a person; `Schedule` means it
runs on a timer. When `succeeded` is below `runs`, say so as returned; why a run failed is in the workflow's history. The
Lambda failover in plain words: when a function's region has trouble, it picks a healthy region, moves the function and
closes the problem. Never tie a run to a problem from beat 3 or 4: the query does not join them.

**Deep link** (label "AWS Business Resilience launchpad"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.launcher/launchpad/b1f1c799-de60-456d-b62c-a1f13256077b
```
