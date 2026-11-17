# Scenario: Kubernetes Complexity (Showcase) — Context and Beats

**The "Beat N" headings below number the steps for authors only. Never print a heading, a number or the word "beat" to the user: name a step by its subject ("the database's CPU"). Steps can come in any order.**

Read once the user has picked the Kubernetes tour. This is a **showcase**, not an incident: there is no page to answer.
We show one Kubernetes estate three ways — finding the cause of a slowdown, sorting out what is starved and what is
wasted, and what the clusters run on in the cloud — and the user picks where to start. The survey query does not cover
it; its beats supply their own tokens (see "Tokens").
Reveals describe the *shape* of a finding, never its values. Entity counts, memory and CPU figures, hours near a limit,
reclaimable millicores, instance IDs and the alert's status change every day — read them from the live result.

## Contents

- [Business context](#business-context)
- [Opening](#opening)
- [Scope](#scope)
- [Tracks](#tracks)
- [Moving between tracks](#moving-between-tracks)
- [Tokens](#tokens)
- [Handoff fields](#handoff-fields)
- [Beat 1 — The Estate](#beat-1--the-estate)
- [Beat 2 — A Starved Workload](#beat-2--a-starved-workload)
- [Beat 3 — A Bloated Workload](#beat-3--a-bloated-workload) (peak)
- [Beat 4 — From Node to Instance](#beat-4--from-node-to-instance)
- [Beat 5 — Is the Cloud Alert Our Cluster?](#beat-5--is-the-cloud-alert-our-cluster) (peak)

---

## Business context

| Field | Value |
|---|---|
| `kind` | `showcase` |
| `service_name` | "Kubernetes estate" |
| `symptom` | "a Kubernetes estate too large to read by hand" |
| delivery | presentation only — no `pull_line`, no `mode_question`, no walk-through |

No `avg_order_value_usd` and no cloud bill: no revenue or cost figure. Reclaimable CPU is millicores, never dollars.

**Framing.** Present tense, no urgency, still "we". The tour has one idea running through it: the estate is
complicated, alerts are easy, and **the hard part is knowing where to start looking.** Every track ends on the same
point in its own terms — the answer was one number among hundreds, and it came from the data, not from an hour of tabs.

## Opening

What the first turn of a picked tour says, before the first step's evidence. Four things, in plain words and in this
order, as prose and not bullets. No figure: nothing has been read yet.

1. **The job.** Put the user in the seat: picture the environment you are on call for — several Kubernetes clusters,
   a couple of hundred workloads, spread across more than one cloud. When something breaks at three in the morning,
   knowing that it is broken is the easy part. The hard part is knowing where to start looking.
2. **The questions,** said as the three moments from a normal week: what caused a slowdown; which workloads are starved
   and which are wasting capacity; and what the clusters run on in the cloud, and whether a cloud alert is ours.
3. **The route:** first the estate itself, on live data, then whichever of the three they pick.
4. **How it goes:** they choose; each part ends with a way into the others; they say next or ask about anything.

Beat 1 then runs in the same turn and ends on the question: "Which of these hurts most: finding the cause of a problem,
wasted or starved resources, or knowing whether the cloud underneath is your problem?" Asked once.

This is the one turn of the tour allowed past the usual length: up to 20 lines, the opening at most seven of them. It is
said once; a later step never recites it.

A track asked for by name ("show me the over-provisioned workloads", "is that EC2 alert our cluster?") is not a pick:
one line naming its steps, then that track's first beat. No Opening.

## Scope

**Environment:** `demo-live`, the only environment that has these clusters, the EKS-to-EC2 links and the alert VM.

**Data objects:** `smartscapeNodes`, `smartscapeEdges`, `dt.davis.problems`, `timeseries` on `dt.kubernetes.container.*`

**Stable IDs** (demo-live):

| Name | ID |
|---|---|
| easytrade-calculationservice (the starved workload), `demo-live` | `K8S_DEPLOYMENT-EC6A3214218AE471` — resolves as `{{CALC_DEPLOYMENT_ID}}` |
| easytrade-db (the over-requested database, a StatefulSet), `demo-live` | `K8S_STATEFULSET-96920965601CF900` — resolves as `{{DB_STATEFULSET_ID}}` |
| The cluster the resources and cloud tracks use | `k8s.cluster.name == "eks-live"` (EKS) |
| The namespace both resource steps scope to | `k8s.namespace.name == "easytrade"` |
| The cloud alert | `dt.davis.problems` where `event.name == "Amazon EC2 CPU Utilization High"` |

**Why the resource steps are scoped to `easytrade`.** Across the whole estate, Dynatrace's own components
(`dynatrace-webhook` on every cluster) top the over-provisioning list. They are not the story, and a user asking
about "my workloads" means the application.

**Memory ratios are per container, never per workload.** A workload-level series sums or averages across pods and
containers and runs past 100% of a limit that applies per container.

**Other views**, offered only when the user asks for them (they are not a beat's link):

| Ask | Label | URL |
|---|---|---|
| The EC2 instances in the Clouds app | "EC2 instances in Clouds" | `https://{{LINK_HOST}}/ui/apps/dynatrace.clouds/smartscape/vm?perspective=health&sort=healthIndicators%3Aascending%3BcustomAlerts%3Aascending%3Bname%3Aascending&tf=now-24h%3Bnow` |
| The calculation service's problems | "Calculation service problems, 30 days" | `https://{{LINK_HOST}}/ui/apps/dynatrace.davis.problems/?from=now%28%29-30d&to=now%28%29&filters=*+%7E+easytrade-calculationservice` |

## Tracks

| Track | Beats | Ends on |
|---|---|---|
| `troubleshoot` | the incidents skill's `k8s-cpu-throttling`, its beats in order | one CPU limit, among more than a hundred deployments, found and explained by the agent overnight |
| `resources` | 2 → 3 | the same app, wrong in both directions |
| `cloud` | 4 → 5 | a cloud alert ruled in or out without a cloud console |

Beat 1 belongs to no track: it is the estate every track starts from, and it ends on the question that picks one.

- The answer to the question picks the track: finding the cause, on-call pain → `troubleshoot`; cost, capacity,
  noisy neighbours, wasted or starved → `resources`; the cloud or platform layer underneath → `cloud`. No preference
  runs `troubleshoot`, then `resources`, then `cloud`.
- **`troubleshoot` is the incidents skill's investigation, not a copy of it.** Read
  `/resources/documents/skills/investigating-demo-incidents/references/scenario-k8s-cpu-throttling.md` and
  `references/conversation-craft.md` there, run the opening query (that skill's session-protocol → "Session state")
  if this conversation holds no row for it, and take its beats from the first, as a presentation: no mode question,
  a **Next:** line after each. Its first beat says the scenario's `approach` line as usual. If the opening query
  returns no row for it, the nightly slowdown has not fired in the window: say that in one line and offer the other
  two tracks.
- The session close fires when the visitor has seen enough, or when all three tracks have run.

## Moving between tracks

When a track's last beat has run, its **Next:** line offers the other tracks the visitor has not walked, with the
bridge below, and proposes one of them once (`conversation-craft.md` → Reactance). The bridges carry no figure:
the figure is in the finding before it.

| From | To | Bridge |
|---|---|---|
| `troubleshoot` | `resources` | That was a workload starved of CPU by one setting; the flip side is the workloads wasting capacity. |
| `troubleshoot` | `cloud` | That was a workload problem; a workload sits on a cluster, and a cluster sits on a cloud — one layer down. |
| `resources` | `cloud` | That was the workloads; next is what they run on: the nodes and the cloud instances under them. |
| `resources` | `troubleshoot` | We found waste and starvation; the three-in-the-morning question is who works out why, when something does break. |
| `cloud` | `troubleshoot` | You can see the layers now; next is what happens when something in one of them breaks. |
| `cloud` | `resources` | Once you can see the layers, you can see what is wasted in each of them. |

**The close** (the layout is `tour-protocol.md` → "Session close"): the payoff line goes back to where the tour started
— the same estate, and when you ask what changed and what to do about it, the answer comes from the data, not an hour of
tabs. Name each walked track's finding in its own words in one sentence. One bullet, **What we saw**, holding that
sentence; a second, **What is left**, only if a track was not walked. No roadmap, no product promises. The way out is
the track not walked, or a view from "Other views".

## Tokens

There is no survey row. The entity IDs come from the "Stable IDs" rows labelled with this conversation's environment.
Every other token comes from a result in this conversation:

| Token | Source |
|---|---|
| `{{SURVEY_AT}}` | The `queried_at` of the **first query of the conversation**, whatever that query was, fixed from then on |
| `{{PROBLEM_ID}}`, `{{TF_FROM_MS}}`, `{{TF_TO_MS}}` | Beat 5's alert query (`problem_id`, `tf_from_ms`, `tf_to_ms`) |

The `troubleshoot` track takes its tokens from the opening query's row, as any incident does.

## Handoff fields

There is no incident to hand off and no owning team on these records. Each track's last beat is its handoff: what was
found, and who would act on it.

| Value | Source |
|---|---|
| `Goes to` | The team that owns the `easytrade` namespace (no owner is on record: say so); for the cloud track, whoever owns the alert VM |
| Starved workload | Beat 2: limit, peak and hours near it, per resource |
| Over-requested workloads | Beat 3: the top rows and `reclaimable_total_m` across `over_requested` workloads |
| Node to instance | Beat 4: every node with its instance |
| The alert, ruled in or out | Beat 5: the problem and `is_k8s_node` |

Populations here: Kubernetes entities (beat 1), problems on one workload (beat 2), container time series (beats 2 and 3),
nodes and instances (beat 4), one problem and its instance (beat 5). Never mix them.

---

## Beat 1 — The Estate

**Why this step:** Before we decide where to look, we need what is actually out there: every cluster, and how much runs on each.

**Objective:** User sees the scale in one table — four clusters on three distributions, tens of namespaces and hundreds of
pods — and feels why "where do I start" is the hard part.

**Evidence DQL:**

```dql
smartscapeNodes "K8S_CLUSTER"
| fields cluster = name, distribution = k8s.cluster.distribution
| lookup [smartscapeNodes "K8S_NODE", "K8S_NAMESPACE", "K8S_DEPLOYMENT", "K8S_POD"
          | summarize nodes = countIf(type == "K8S_NODE"), namespaces = countIf(type == "K8S_NAMESPACE"),
              deployments = countIf(type == "K8S_DEPLOYMENT"), pods = countIf(type == "K8S_POD"),
              by: { cluster = k8s.cluster.name }],
    sourceField: cluster, lookupField: cluster, fields: { nodes, namespaces, deployments, pods }
| sort pods desc
| fieldsAdd queried_at = now()
```

**Show:** Headline "Every cluster we run". Table: Cluster | Distribution | Nodes | Deployments | Pods, 3-6 rows.
Finding: {clusters} clusters on {distributions} distributions, {pods total} pods across {namespaces total} namespaces.
Bullets: More than one cloud in one view; Where most of it runs; Why the hard part is where to look.

**Reveal:** Lead with the totals, summed from the rows, then the spread: the `distribution` column is the point that
this is more than one cloud — EKS, AKS and GKE side by side, read in one query with no console opened. Name the
cluster that carries most of the pods; the resource and cloud steps use it. Then say the idea the tour runs on: with
this many moving parts, an alert tells you something is wrong, not where to start. End on the Opening's question,
asked once, as the turn's call to action instead of a **Next:** line.

**Success signal:** User picks a track, or asks where the money or the risk is.

**Deep link** (label "Clusters in Kubernetes"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.kubernetes/smartscape/K8S_CLUSTER?perspective=Metadata&sort=healthIndicators%3Adescending
```

---

## Beat 2 — A Starved Workload

**Why this step:** The team says the calculation service keeps having problems and nobody can say why, so we check its problems and then its memory and CPU against their limits.

**Objective:** User sees a pattern of problems on one workload, then the reason: its memory ceiling is so small that it
spends much of its time near it, while CPU is nowhere close.

Two queries, so two turns: the problems first, then the limits.

**Evidence DQL — its problems (first):**

```dql
fetch dt.davis.problems, from: now()-30d, to: now()
| filter matchesPhrase(toString(affected_entity_names), "easytrade-calculationservice")
| filter dt.davis.is_duplicate == false
| sort event.start asc
| summarize problems = count(), first_seen = min(event.start), last_seen = max(event.start),
    still_open = countIf(event.status == "ACTIVE"), by: { problem = event.name }
| sort last_seen desc
| fieldsAdd queried_at = now()
```

**Show:** Headline "Problems on the calculation service". Table: Problem | Count | First seen (UTC) | Last seen (UTC),
3-6 rows. Finding: {total} problems in 30 days across {kinds} kinds, the latest {last_seen}. Bullets: A pattern, not one
smoking gun; Which kinds point at memory; Whether any is open now.

**Reveal:** Lead with the total and the spread of kinds, summed from the rows. The point is that no single problem
explains it — a run of infrastructure trouble under several names. Name, as returned, the kinds that point at memory
(out-of-memory kills, memory close to its limit, restarts) and say that is a hint, not yet a cause: the limits are the
next query. `still_open` decides the tense: say a problem is open only where it is non-zero. When the 30-day window
holds no rows, say so plainly and go straight to the limits, which stand on their own.

**Evidence DQL — memory and CPU against their limits:**

```dql
timeseries { ws = max(dt.kubernetes.container.memory_working_set), mem_limit = max(dt.kubernetes.container.limits_memory),
             ws_avg = avg(dt.kubernetes.container.memory_working_set),
             cpu = max(dt.kubernetes.container.cpu_usage), cpu_limit = max(dt.kubernetes.container.limits_cpu),
             cpu_avg = avg(dt.kubernetes.container.cpu_usage) },
  from: now()-30d, to: now(), interval: 1h,
  filter: { k8s.cluster.name == "eks-live" and k8s.namespace.name == "easytrade" and k8s.container.name == "calculationservice" }
| fieldsAdd mem_limit_mib = round(arrayMax(mem_limit) / 1048576, decimals: 1),
    mem_peak_mib = round(arrayMax(ws) / 1048576, decimals: 1),
    mem_avg_pct = round(100 * arrayAvg(ws_avg) / arrayAvg(mem_limit), decimals: 0),
    mem_hours_over_90pct = arraySize(arrayRemoveNulls(iCollectArray(if(ws[] >= 0.9 * mem_limit[], 1)))),
    cpu_limit_m = round(arrayMax(cpu_limit), decimals: 0),
    cpu_peak_m = round(arrayMax(cpu), decimals: 1),
    cpu_avg_pct = round(100 * arrayAvg(cpu_avg) / arrayAvg(cpu_limit), decimals: 0),
    cpu_hours_over_90pct = arraySize(arrayRemoveNulls(iCollectArray(if(cpu[] >= 0.9 * cpu_limit[], 1)))),
    hours_measured = arraySize(arrayRemoveNulls(ws))
| fields mem_limit_mib, mem_peak_mib, mem_avg_pct, mem_hours_over_90pct,
    cpu_limit_m, cpu_peak_m, cpu_avg_pct, cpu_hours_over_90pct, hours_measured, queried_at = now()
```

Hourly maxima over 30 days, per container. `*_hours_over_90pct` counts the hours whose peak reached 90% of the limit,
out of `hours_measured`.

**Show:** Headline "Memory with no headroom". Table: Resource | Limit | Average use (%) | Peak | Hours near the limit,
2 rows (memory in MiB, CPU in millicores). Finding: A {mem_limit_mib} MiB memory limit, averaging {mem_avg_pct}% of it
and near it for {mem_hours_over_90pct} of {hours_measured} hours. Bullets: Memory lives at its ceiling; CPU sits far
below its own; Why that means alerts and kills; Sized once and never revisited.

**Reveal:** Lead with memory: the limit, the average share of it, and the hours near it, said together — the
comparison is the finding. A container that spends that share of its hours near its ceiling has no headroom: any
burst is an out-of-memory kill, which is the run of problems the first query showed. Then CPU, the same three numbers,
for contrast: average use is a small share of its limit and it is rarely near it. Say CPU's peak as returned if it is
high, and that a peak in a handful of hours is not where the time goes. This is a starved workload — the limit is the
problem, not the code — and the remedy is sizing memory from usage over time, which is the owning team's to set.
Never give a new limit: no row says what it should be.

**Success signal:** User names memory as the constraint, or asks what the limit should be.

**Deep link** (label "The calculation service in Kubernetes"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.kubernetes/smartscape/workload/K8S_DEPLOYMENT?detailsId={{CALC_DEPLOYMENT_ID}}&sidebarOpen=false&perspective=Health&detailsTab=Utilization#filtering=Cluster+%3D+%22eks-live%22+AND+Namespace+%3D+%22easytrade%22
```

---

## Beat 3 — A Bloated Workload

**`peak_moment: true`**

**Why this step:** The opposite problem costs money quietly: Kubernetes reserves what a workload requests, not what it uses, so we put the two side by side for every workload in the app.

**Objective:** User sees one workload reserving many times what it uses, the total that could be handed back across
the app, and that it is the same app that was starved a moment ago.

**Evidence DQL:**

```dql
timeseries { used = avg(dt.kubernetes.container.cpu_usage), requested = avg(dt.kubernetes.container.requests_cpu) },
  from: now()-6h, to: now(), by: { k8s.workload.name, k8s.pod.name, k8s.container.name },
  filter: { k8s.cluster.name == "eks-live" and k8s.namespace.name == "easytrade" }
| summarize used_m = round(sum(arrayAvg(used)), decimals: 0), requested_m = round(sum(arrayAvg(requested)), decimals: 0),
    by: { workload = k8s.workload.name }
| filter requested_m > 0
| fieldsAdd reclaimable_m = requested_m - used_m, used_pct = round(100 * used_m / requested_m, decimals: 0), k = 1
| lookup [timeseries { used = avg(dt.kubernetes.container.cpu_usage), requested = avg(dt.kubernetes.container.requests_cpu) },
          from: now()-6h, to: now(), by: { k8s.workload.name, k8s.pod.name, k8s.container.name },
          filter: { k8s.cluster.name == "eks-live" and k8s.namespace.name == "easytrade" }
        | summarize u = sum(arrayAvg(used)), r = sum(arrayAvg(requested)), by: { k8s.workload.name }
        | filter r > 0
        | summarize over_requested = countIf(r > u), reclaimable_total_m = round(sum(if(r > u, r - u, else: 0)), decimals: 0)
        | fieldsAdd k = 1],
    sourceField: k, lookupField: k, fields: { over_requested, reclaimable_total_m }
| sort reclaimable_m desc
| fields workload, requested_m, used_m, used_pct, reclaimable_m, over_requested, reclaimable_total_m, queried_at = now()
```

Averages per container over 6 hours, summed per workload; CPU in millicores. `reclaimable_total_m` adds only the
workloads that request more than they use: one that uses more than it asked for does not offset one that over-asks.

**Show:** Headline "Reserved but never used". Table: Workload | Requested (m) | Used (m) | Used (%) | Reclaimable (m),
5 rows (the top five by reclaimable). Finding: {top workload} requests {requested_m}m and uses {used_m}m, {ratio} times
what it needs; {reclaimable_total_m}m could be handed back across {over_requested} workloads. Bullets: Requests decide
scheduling, not use; The database carries most of it; Same app, starved and bloated; Right-sizing is set from usage over time.

**Reveal:** Lead with the top row: requested against used, and the ratio between them, computed from the two values.
Then the total across the over-requested workloads and the top row's share of it. Explain the mechanism in plain words:
the scheduler places pods by what they request, so a reservation nobody uses is capacity paid for and unavailable to
anything else. Say the unit is millicores — thousandths of a CPU core — and never turn it into money: no row has a price.

Rows with a negative `reclaimable_m` are workloads using more than they requested (a load generator, say). Mention them
only if asked, and as the other kind of mis-sizing, never as savings.

**Staging:**

1. The finding alone on its own line, before any commentary:
   `[top workload] reserves [requested_m]m of CPU and uses [used_m]m — [ratio] times what it needs`
2. Blank line.
3. What kind of problem it is: not a fault, a reservation. Nothing is broken and nothing alerts, which is why it
   lasts: Kubernetes keeps the capacity aside whether it is used or not.
4. The total, `reclaimable_total_m` across `over_requested` workloads, in one sentence.
5. Tie it to the starved step when it ran: the same cluster and the same app, wrong in both directions — one workload
   with too little memory, another reserving many times the CPU it uses. That is what sizing by hand looks like at
   scale. If the starved step did not run, say only this half.

**Objection** — "so just cut the requests": the requests are set from these six hours, and the right figure is set from
usage over a longer window, with peaks; a database's quiet afternoon is not its month-end. The point is that the
evidence for each change is one query away, per workload, which a quarterly review spreadsheet never is.

**Success signal:** User asks how much the cluster could save, or how to right-size the rest.

**Deep link** (label "The database workload in Kubernetes"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.kubernetes/smartscape/workload/K8S_STATEFULSET?detailsId={{DB_STATEFULSET_ID}}&sidebarOpen=false&perspective=Health&detailsTab=Utilization#filtering=Cluster+%3D+%22eks-live%22+AND+Namespace+%3D+%22easytrade%22
```

---

## Beat 4 — From Node to Instance

**Why this step:** The cluster is only the top of the stack, so we follow each of its nodes down to the cloud instance it runs on, and check whether any of those instances has a problem.

**Objective:** User sees every node of the EKS cluster mapped to its EC2 instance — ID, zone and state — with no AWS
console opened, and whether any instance has a problem against it.

**Evidence DQL:**

```dql
smartscapeNodes "K8S_NODE"
| filter k8s.cluster.name == "eks-live"
| fields node = name, node_id = toString(id)
| lookup [smartscapeEdges "*"
          | filter source_type == "K8S_NODE" and type == "runs_on" and target_type == "HOST"
          | fields node_id = toString(source_id), host_id = toString(target_id)],
    sourceField: node_id, lookupField: node_id, fields: { host_id }
| lookup [smartscapeEdges "*"
          | filter source_type == "HOST" and type == "runs_on" and target_type == "AWS_EC2_INSTANCE"
          | fields host_id = toString(source_id), instance_id = toString(target_id)],
    sourceField: host_id, lookupField: host_id, fields: { instance_id }
| lookup [smartscapeNodes "AWS_EC2_INSTANCE"
          | fields instance_id = toString(id), instance = name, ec2_id = aws.resource.id, state = aws.state, zone = aws.availability_zone],
    sourceField: instance_id, lookupField: instance_id, fields: { instance, ec2_id, state, zone }
| lookup [fetch dt.davis.problems, from: now()-24h, to: now()
          | filter dt.davis.is_duplicate == false
          | expand eid = smartscape.affected_entity.ids
          | summarize problems_24h = count(), by: { instance_id = toString(eid) }],
    sourceField: instance_id, lookupField: instance_id, fields: { problems_24h }
| fieldsAdd problems_24h = coalesce(problems_24h, 0)
| fields node, ec2_id, zone, state, problems_24h, queried_at = now()
```

There is no direct node-to-instance relationship: a node runs on a host, and the host runs on the EC2 instance. Two hops.

**Show:** Headline "Every node is a cloud instance". Table: Node | EC2 instance | Zone | State | Problems (24 h),
3-6 rows. Finding: All {nodes} nodes of the cluster run on EC2 instances across {zones} zones, {with problems} with a
problem in the last day. Bullets: Two hops from the cluster to the cloud; Spread across zones; Whether the cloud layer is
clean; The same instance from the Clouds side.

**Reveal:** Lead with the count: every node maps to an instance, from one query, by its EC2 ID — the identifier an AWS
team works with. Say the zones as returned: spread across them is what lets the cluster survive one going away. Then
the health: `state` and `problems_24h` per instance. All running with no problems rules out the cloud layer under this
cluster, and that is a finding, not an absence of one. A node with no instance is said as returned: that node has no
cloud link recorded. Never describe the instances' size or price: no column holds it.

**Success signal:** User asks whether the cloud is the problem, or what a cloud alert would mean for the cluster.

**Deep link** (label "The cluster's nodes in Kubernetes"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.kubernetes/smartscape/K8S_NODE?perspective=Metadata&sort=healthIndicators%3Adescending&sidebarOpen=true#filtering=%22Cluster%22%20=%20%22eks-live%22
```

---

## Beat 5 — Is the Cloud Alert Our Cluster?

**`peak_moment: true`**

**Why this step:** A cloud alert says an EC2 instance is running hot, and the first question on call is whether that instance is one of our cluster's nodes — so we follow the alert to its instance, then check it against the nodes.

**Objective:** User sees a cloud alert followed to its instance, and that instance checked against every Kubernetes
node — ruled in or out from the data, in seconds, without a cloud console.

Two queries, so two turns: the alert and its instance first, then the check against the nodes.

**Evidence DQL — the alert and its instance (first):**

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter event.name == "Amazon EC2 CPU Utilization High" and dt.davis.is_duplicate == false
| sort event.start desc
| limit 1
| expand eid = smartscape.affected_entity.ids
| fieldsAdd eid = toString(eid)
| lookup [smartscapeNodes "AWS_EC2_INSTANCE" | fields eid = toString(id), instance = name, ec2_id = aws.resource.id, zone = aws.availability_zone],
    sourceField: eid, lookupField: eid, fields: { instance, ec2_id, zone }
| fields display_id, status = event.status, started = event.start, ended = event.end,
    open_h = round(toDouble(coalesce(event.end, now()) - event.start) / 3600000000000, decimals: 1),
    instance, ec2_id, zone,
    problem_id = event.id,
    tf_from_ms = toLong(event.start) / 1000000 - 900000,
    tf_to_ms = toLong(coalesce(event.end, now())) / 1000000 + 900000,
    queried_at = now()
```

`limit 1` is the claim here: the latest alert, not all of them.

**Show:** Headline "The cloud alert and its instance". Table: Field | Value, 5 rows (problem, status, open for (h),
instance, EC2 ID). Finding: {display_id} says CPU is high on {instance} ({ec2_id}), {status} for {open_h} hours.
Bullets: What the alert says; The instance it names; The question it leaves open.

**Reveal:** Lead with the alert in plain words: Dynatrace raised a high-CPU problem on one EC2 instance, and the record
names the instance. `status` decides the tense — "open now" only for `ACTIVE`, otherwise when it ran. Then the gap: an
instance name and ID do not say whether this is one of our cluster's nodes, and that is the question that decides who
gets woken. That is the next query.

No rows means no such alert in the last two days: say so, and that the node check in the previous step stands as the
cloud layer's health.

**Evidence DQL — is it one of our nodes:**

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter event.name == "Amazon EC2 CPU Utilization High" and dt.davis.is_duplicate == false
| sort event.start desc
| limit 1
| expand eid = smartscape.affected_entity.ids
| fields instance_id = toString(eid)
| lookup [smartscapeEdges "*"
          | filter source_type == "HOST" and type == "runs_on" and target_type == "AWS_EC2_INSTANCE"
          | fields instance_id = toString(target_id), host_id = toString(source_id)],
    sourceField: instance_id, lookupField: instance_id, fields: { host_id }
| lookup [smartscapeEdges "*"
          | filter source_type == "K8S_NODE" and type == "runs_on" and target_type == "HOST"
          | fields host_id = toString(target_id), node_id = toString(source_id)],
    sourceField: host_id, lookupField: host_id, fields: { node_id }
| lookup [smartscapeNodes "K8S_NODE" | fields node_id = toString(id), node = name, cluster = k8s.cluster.name],
    sourceField: node_id, lookupField: node_id, fields: { node, cluster }
| fields has_host = isNotNull(host_id), is_k8s_node = isNotNull(node_id), node, cluster, queried_at = now()
```

The same two hops as the node step, walked backwards from the alert's instance, across **every** cluster, not only EKS.

**Show:** Headline "Ruled out in one query". Table: Check | Result, 3 rows (monitored host on the instance, a
Kubernetes node on it, which cluster). Finding: The instance with the high CPU {is / is not} a node of any of our
clusters. Bullets: What the check walked; What it means for on call; Where the alert does belong.

**Reveal:** State the verdict from `is_k8s_node`, and only from it. When it is `false`: the instance is a separate
machine — monitored (`has_host`), but not under any cluster — so the cluster is ruled out and this alert goes to
whoever owns that machine, not to the Kubernetes on-call. Say plainly that this is a standalone VM rather than
implying an incident on the platform; ruling it out is the value. When it is `true`: name `node` and `cluster`, and say
the alert is the cluster's — the resource and troubleshoot tracks are where that leads.

**Staging:**

1. The finding alone on its own line, before any commentary:
   `The instance with the high CPU [is / is not] one of our Kubernetes nodes`
2. Blank line.
3. What kind of answer it is: a layer ruled out (or in) from the relationships the platform already holds — alert to
   instance, instance to host, host to node — not from a person cross-checking IDs between two consoles.
4. The check as three short lines from the table, as returned.
5. Back to the tour's idea: the alert was easy; knowing whether it was ours is the part that used to take the time.

**Success signal:** User says the cluster is not involved, or asks who owns the instance.

**Deep link** (label "The cloud alert in Dynatrace"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.davis.problems/problem/{{PROBLEM_ID}}?from={{TF_FROM_MS}}&to={{TF_TO_MS}}
```
