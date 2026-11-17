# kubernetes-complexity: source, stable IDs and what moved since the script

Maintainer notes. The agent never reads this file.

Source: the KubeCon NA 2026 booth demo, "Complexity reduced": the launchpad `2250b42c-7c72-4194-8cff-9242770b29f9`
on demo-live, its presenter script and three recorded walk-throughs, all in
`kubernetes-complexity-source/` (kept locally and git-excluded, not in the repo). The event's SharePoint links (videos, the .docx
script) are left out of the copied launchpad on purpose.

The demo is one opening and three tracks. Two of them (resources, cloud) are new beats in
`touring-demo-showcases/references/scenario-kubernetes-complexity.md`. The third (troubleshoot) **is**
`k8s-cpu-throttling`: the tour hands into that incident rather than copying its beats, and the incident's agent step
gained a first query for the workflow run (script step 1c).

## How the script maps to the tour

| Script | Tour |
|---|---|
| Opening: the complexity wall, read the tiles | Opening + beat 1, the estate per cluster with its distribution |
| 1a–1d: problem, spec change, workflow run, agent report | `troubleshoot` track = `k8s-cpu-throttling`, its five beats |
| 2a: calculationservice problems, then Assist on its limits | Beat 2, two queries |
| 2b: Assist on over-requested CPU in easytrade | Beat 3 (peak) |
| 3a: eks-live nodes to EC2 instances | Beat 4 |
| 3b: Assist on the AWS layer, then the EC2 CPU alert | Beat 4's health columns, then beat 5 (peak) |
| Handoff rows | "Moving between tracks" |
| Close: complexity collapses | The close, payoff line in the scenario file |

The script's Assist questions are not typed into Assist: the agent *is* Assist (or `/demo`), so each one is a beat
whose query the agent runs itself.

## Stable entity IDs (demo-live)

| Name | Entity ID |
|---|---|
| easytrade-calculationservice | K8S_DEPLOYMENT-EC6A3214218AE471 |
| easytrade-db (a StatefulSet, not a Deployment) | K8S_STATEFULSET-96920965601CF900 |
| eks-live | K8S_CLUSTER-5B4F62B146DD4A5E |
| cloud-alerts-live-high-cpu-vm | AWS_EC2_INSTANCE-D1B36E2AF2B30145 |
| k8s-troubleshooting-agent workflow | 1e4e7449-b32a-32e3-8bb8-0e2319f23daf (queried by title, so playground needs no row) |

The eks-live nodes were recreated on 2026-11-13, so their instance IDs are new: the launchpad's
`AWS_EC2_INSTANCE-576F7B2F3AEBA822` is a node that no longer exists. Beat 4 finds them by traversal for that reason.

## What moved between 21 Oct (script) and 17 Nov (live check)

| Script says | Live on 17 Nov | Consequence |
|---|---|---|
| Scale: 4 clusters, 10 nodes, 46 namespaces, 122 deployments, 278 pods | 4, 10, 46, 125, 286 | Read live, never quoted |
| Nightly slowdown at about 02:05 UTC | About 03:04 UTC (P-26116748, 101 users) | The incident reads it live already |
| calculationservice: 4 "Multiple infrastructure problems", none recent | 20 non-duplicate problems in 30 days: OOM kills, memory close to limits, restarts, the latest 13 Nov | Beat 2 summarises by kind, never by one name |
| calculationservice working set about 22 of 25 MiB (88%, 6 h) | About 16 MiB over 6 h, but over 30 days: peak 24.9 MiB, average 82%, 311 of 721 hours at 90%+ of the limit | Beat 2 uses 30 days of hourly maxima, not a 6-hour average |
| "CPU should not be the issue" | CPU average 1% of its 100m limit, 4 hours near it, but one hourly peak at 99m | The reveal compares hours near the limit, not peaks |
| easytrade-db 30m of 500m, 470m reclaimable | Same | Hero row holds |
| EC2 alert P-261012632, opens and closes daily | P-26115952, active since 14 Nov 22:35 | Tense from `status`, never assumed |
| Alert instance `i-07986e2614029a55b` | `i-09d1cd6c4444ebd6d`, same name | Instance read from the problem |

## Why the bloated query does not use `sum()`

The second walk-through has Assist answering "requesting 29,000 millicores while it is using 1,7000" for a database that
requests 500m. That is what `timeseries sum()` on 1-minute data in 5-minute buckets returns: it adds the samples inside
each bucket (verified: 2,493m for easytrade-db). Beat 3 averages per container series, then sums per workload. The
gotcha is in `dql-reference.md` → Metrics.

## Left out on purpose

- GKE (has a GCP instance link) and AKS (its nodes are not linked to Azure VMSS VMs): the cloud track is EKS only, as
  in the script. Beat 5's node check walks every cluster, so the verdict holds for all of them.
- demo-kspm: no cloud link.
- The Clouds app tiles (script 3a): no beat reads them; "EC2 instances in Clouds" is an Other view.
- The GitOps pull-request path: wired in the workflow, unverified, off in the nightly runs. The tour never promises it.

## Not verified

- The two Kubernetes-app workload links (beats 2 and 3): the Deployment route is copied from the launchpad, the
  StatefulSet route (`smartscape/workload/K8S_STATEFULSET`) is inferred from it. Open both before calling the links done.
- The Other view into the Clouds VM list.
