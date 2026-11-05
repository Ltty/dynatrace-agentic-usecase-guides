# k8s-cpu-throttling: stable entity IDs and debugging notes

Maintainer notes. The agent never reads this file.

Source: the "K8s troubleshooting agent" step of the *Modern Cloud Observability* golden demo, taken to
incident depth. The showcase (`scenario-cloud-observability.md`) shows this agent at tour depth in its
beat 4; this scenario walks one of its problems from the slow page to the field that was edited.

## Stable entity IDs (safe to hardcode in queries and deep links)

| Name | Entity ID | Type |
|------|-----------|------|
| `[eks-live][easytrade] TradeManagement` | SERVICE-8491B5DDF5BDAB93 | Service, roots the slowdown some days |
| `[eks-live][easytrade] NotMiningBitcoin` | SERVICE-DA275964FAFD97CA | Service, roots it other days |
| EasyTrade | APPLICATION-5DCD0C470BC8680A | Application, roots it other days |
| easytrade-broker-service | K8S_DEPLOYMENT-98DBB38AEB111C5B | The workload whose CPU limit moves |

Cluster `eks-live`, namespace `easytrade`, container `broker-service`.

## What rotates every problem cycle (never hardcode)

problem id / display id, **which of the three entities is the root cause**, affected-user count,
response times and the baseline, the millicore and throttling figures, the window, and the agent's own
wording.

## Resolver notes — this one needed two passes

The branch matches the three entity IDs above **and** `event.category == "SLOWDOWN"`, and the shared
`pref` expression prefers a row whose root cause is a `SERVICE-`.

Both halves were learned the hard way; the first draft had neither and the very first live validation
picked a problem with no spec change behind it.

- **Playground runs its own EasyTrade**, with the same namespace and the same problem names
  ("Easytrade request duration", "High CPU throttling", …) — 123 problems in 7 days. Matching
  `event.name` or `k8s.namespace.name` would leak the scenario onto the Playground exactly as
  `disk-cpu-cascade` leaked in testruns 12 and 13. The demo-live entity IDs return zero rows there.
- **`event.category` is needed** because TradeManagement also roots `Request error rate increase` and
  `Failure rate increase` problems in the same namespace — two of the five rows the first branch
  matched in 48 hours were errors, not slowdowns.
- **`pref` is needed** because the slowdown also fires off-cycle, and those occurrences have no spec
  change behind them. On 2026-11-05 the branch matched both P-26111707 (03:04, service-rooted, with the
  limit change) and P-26111907 (12:08, application-rooted, without it); the newest wins, so the
  validator resolved to the one whose beat 4 returns nothing. Off-cycle occurrences observed so far are
  application-rooted or, once (2026-10-30 10:59), service-rooted with a spec change anyway, so
  preferring `SERVICE-` picks a usable occurrence.

An application-rooted row is still offered when it is the only one, with `pref = 1`; beat 4 then says
the platform recorded no limit change in that window. See "Known limit" below.

## The incident shape (verified 2026-11-05 across the last 7 days)

Fires **daily at about 03:04 UTC**, 15 to 35 minutes, 82–98 affected users, usually with no owning team
on the record. Non-duplicate `Easytrade request duration` on 7 of the last 7 days.

A deployment of EasyTrade changes the broker service's CPU **limit**, and about 25 minutes later changes
it back:

```text
easytrade-broker-service, container broker-service
  03:02  resources/limits cpu  600m -> 300m   (recorded ~5x as the rollout replaces pods)
  03:27  resources/limits cpu  300m -> 600m   (recorded once)
```

Measured on 2026-11-05, 02:45–03:50 UTC, 5-minute intervals:

| Series | Before | During | Note |
|---|---|---|---|
| `limits_cpu` | 600m | **300m** | the only field that moves |
| `requests_cpu` | 150m | 150m | flat all window |
| `cpu_usage` | ~69m | peaks **186m** | never reaches the 300m ceiling |
| `cpu_throttled` | ~9.5 | peaks **863** | tracks the limit exactly |

Service response time in the namespace: BrokerService / NotMiningBitcoin p95 ≈ 1,664 ms against
≈ 100–170 ms for every other service in `easytrade`; p50 stays ≈ 46 ms, which is the signature of
throttling rather than uniform slowness.

### The brief said "requests"; the data says "limits"

The request that commissioned this scenario described "cpu requests change from 600m to 300m". The
change is on `resources/limits`, and `requests_cpu` is flat at **150m** for the whole window — it is
never 600m and never changes. This matters because the two fail differently: a request is a
reservation and affects scheduling and contention; a limit is a ceiling enforced per scheduling slice
and throttles the container regardless of how idle the node is. The evidence — throttling tracking the
ceiling while the node has capacity — is the limit mechanism, so the scenario is written about limits.

## The agent's notes are healthy here

Unlike the AWS DevOps Agent in `lambda-iam-denied`, the Kubernetes troubleshooting agent is producing
full analyses: 260 notes in 30 days, the most recent minutes old at the time of writing. Each note is
~3.7 kB of markdown with these headings:

```text
**Incident Context**          cluster, namespace, workload, entity, category (a table)
**AI Recommendation**
## Root Cause                 one bold sentence, then Supporting Findings with timestamps
## Side Effects Triggered
## What Was Checked (No Issues Found)    memory, node capacity, restart loops
## Solution                   prose plus a full Deployment YAML
### Implementation Steps
```

The note events carry **no Kubernetes dimensions** — only `annotation.problem_ids` and `event.name`
(`✨ Dynatrace AI Analysis`). The workload is in the note body, not in a field, which is why beat 5
joins through the problem record instead of filtering on a workload.

### A showcase bug this scenario found

`scenario-cloud-observability.md` beat 4 extracted its `agent_fix` with
`indexOf(note, "Recommended Fix")`. Across 7 days only **7 of 181** notes contain that string, while
**155** contain `## Solution` — so the showcase was telling users "the note carried no fix section"
while the note held a full Solution with YAML. Fixed on this branch: prefer `## Solution`, fall back to
`Recommended Fix`. Also noted: that beat's `takeFirst(dt.entity.cloud_application.name)` is always
null for the same reason as above.

## Known limit

**An off-cycle occurrence has no spec change behind it.** `pref` makes the resolver avoid those while a
usable one exists in the 48-hour window, but if an application-rooted occurrence is the only row, beat
4 returns nothing and says so. Roughly 1 in 11 non-duplicate occurrences over the last 7 days.
