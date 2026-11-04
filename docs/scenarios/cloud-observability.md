# cloud-observability: source, verified data and decisions

A showcase, not an incident: the Golden Demo *Modern Cloud Observability* arc with the *Cut Cloud Costs Safely*
Dynatrace Assist conversation folded into its AI-operations part. Tenant: `guu84124` (dtctl context `demo-live`,
read-only). Built and verified live 2026-11-02; updated to the guide's final October 2027 version 2026-11-03.

## Source guides

- *Modern Cloud Observability — October 2027* (Golden Demo, three modules: cloud infrastructure monitoring, cloud
  application observability, Dynatrace Intelligence for cloud operations). Replaces the *— WIP* version the scenario was
  first built from. What changed: part 3 is now Cloud SRE Agents → the K8s troubleshooting agent on the EasyTrade K8s
  High CPU problem → cloud costs in Dynatrace Assist → a four-challenge summary, with workflows (prevent, remediate,
  optimize) as an "Extra" after it. Dropped from the guide: the ServiceNow "Send" click, the Lambda failover walk-through
  and "validate, then close the loop". Part 2's problem card now leads with impact, root cause and the Visual Resolution
  Path, and the AWS DevOps Agent is framed as "Dynatrace context fed to any agent".
- *Cut Cloud Costs Safely* (the CTO asks Dynatrace Assist for 10% off the bill; cost next to utilization; owners).

Mapping to beats:

| Guide step | Beat |
|---|---|
| Clouds app: AWS / Azure / GCP on one page | 1 The Estate |
| EC2/Lambda details, related resources, Smartscape topology | 2 One Function in Depth (image-provider-live, as in the guide's part 2) |
| image-provider-live service, service map, problem card, impact, AWS DevOps Agent findings | 3 What Runs on It |
| Cloud SRE Agents app; K8s troubleshooting agent on the EasyTrade K8s High CPU problem (spec change, fix recommendation) | 4 Agents on the Problem |
| Assist: CTO asks for 10%; bill first, then utilization; spend breakdown; largest line; untagged spend | 5 The Bill and the Target |
| Databases: low CPU but no free memory; no utilization data; owners per team (cost guide) | 6 Cost Next to Utilization |
| Summary: the four challenges | The framing paragraph and the session close's payoff line |
| Extra: launchpad, EBS remediation (prevent), Lambda region failover (remediate), auto-optimize | Extra — Workflows That Act (on request, after the close) |

Left out, and why:

- **Idle NAT gateway** (cost guide): the only NAT gateway with traffic metrics (`nat-01293787cc0dc1b3b`, 0 GB in 14 days)
  is not on the last 30 days of the bill, and the two that are (`nat-0611dc1c0fd53195d`, `nat-0d4d1f30583e4617b`) have no
  metric series. The join the guide implies cannot be made from the data.
- **Cache suspension savings** ("cuts their cost by about two thirds"): no ElastiCache utilization metric exists, and
  serverless caches cannot be stopped like an instance. A savings percentage would be invented.
- **"$624 to $1,396 a month" savings range**: an LLM estimate in the guide, not a value any query returns. Beat 5 gives the
  target and the lines; which lines close the gap is the owners' call.
- **Session Replay, onboarding screenshot, VMware dashboard and VM, compare-costs week, Visual Resolution Path**: UI
  steps with no DQL evidence the agent can show. Users & Sessions (the guide's Astroshop 12-hour filter), the VMware
  dashboard and VM, and the Clouds services explorer (where Assist is opened) are in the scenario's "Other views" table;
  the Visual Resolution Path is on beat 3's problem page.
- **The guide's `my.demo.now` problem pages** ("image provider failure", "EasyTrade High CPU Slowdown"): curated pages,
  not the live problem. Beat 3 links the live problem; beat 4 links Cloud SRE Agents, since a second problem link would
  need a second problem token.
- **The guide's cost figures** ($12,762, $1,276, "about 35% each", $928 for CloudWatch logs): values from the day the guide
  was written. The skill reads them live.
- **The staged change behind beat 4.** The `easytrade-k8s-deployment-trigger` workflow (`fad33b35-…`, Event-triggered, 88
  runs in 7 days) matches the 88 `Deployment spec change` events in `easytrade` that flip `broker-service`'s CPU limit
  between 600m and 300m: the "too strict optimization" is the demo's own chaos. The skill states the change as the
  platform recorded it and says nothing about who made it, as the data in the beat does not show it.

## Stable IDs

| Name | ID |
|---|---|
| image-provider-live Lambda (Clouds app node) | `AWS_LAMBDA_FUNCTION-9365828D44E6A036` |
| Same Lambda, span-side entity | `AWS_LAMBDA_FUNCTION-A538594598C37291` (do not use; join on ARN) |
| image-provider-live in us-east-1 (service) | `SERVICE-42411741F5F4AC50` |
| image-provider-live-products in us-east-1 (service) | `SERVICE-F4E5246FA8EA27D7` |
| AWS account | `246186168471` |
| Workflows | k8s agent `1e4e7449-…`, EBS remediate low storage `dd59f7b0-…`, failover Lambda `4df6c4b4-…`, Cost & Carbon Optimization: Calculation `9f1eb5e4-…`; no longer queried: DevOps Agent investigation `6b7f3d61-…`, ServiceNow enrichment `8f4a965b-…` |
| Agent notes (`annotation.source`) | `aws_devopsagent`, `SRE Agent`, `Dynatrace AI Workflow` (the k8s agent: 124 of the 129 five-minute windows with its notes in 7 days also hold a `k8s-troubleshooting-agent` run) |

## Verified values on 2026-11-02 (they rotate; never put them in the skill)

- Resources: AWS 2,675 (65 types), Azure 289 (29), Google Cloud 193 (14). A per-cloud region count was dropped: GCP
  returned 44 distinct values, which reads as zones, not regions.
- Lambda: nodejs22.x, 512 MB, 10 s timeout, last modified 2026-11-02T04:31:46Z. Tags disagree on ownership:
  `team` = Team-Cloud-Services, `dt_owner_team` = team-unc. The problem record's `team` is Team-UI.
- Service: 1.14 M root requests in 24 h, 0.82% failed, p50 23 ms, p95 56 ms.
- Problems: two daily non-duplicate patterns. About 04:04 UTC, root cause image-provider-live (no DevOps Agent notes);
  about 16:05 UTC, root cause image-provider-live-products, with two AWS DevOps Agent notes (investigation and
  mitigation) — both "summary not available" in the last 7 days except one investigation and one mitigation summary.
  Beat 3 prefers the annotated one. P-2611219: 332 affected users (problem record).
- Workflows, 7 days, final states: k8s-troubleshooting-agent 198, failover Lambda 84, ServiceNow enrichment 14, DevOps
  Agent investigation 11; all SUCCESS, all Event-triggered. Without `state.is_final` the counts double.
- 2026-11-03, agents over 7 days: Kubernetes troubleshooting agent 223 problems / 223 notes; SRE Agent 28 / 60; AWS DevOps
  Agent 11 / 22. Beat 4's EasyTrade problem: P-2611822 "Easytrade request duration" (SLOWDOWN), 03:03–03:35 UTC,
  91 affected users; `broker-service` CPU limit 600m → 300m at 03:01 UTC (2 minutes before). The agent's note names that
  change as the root cause but gives it as 04:10:21Z — the event is the record.
- 2026-11-03, the extra's workflows over 7 days: EBS remediate low storage 56 of 63 succeeded (Event), failover Lambda 84 of
  84 (Event), Cost & Carbon Optimization: Calculation 336 of 336 (Schedule).
- Bill, last 30 days of charges: $14,122; target $1,412; untagged $7,605 (54%). Compute $6,063, Management and
  Governance $4,478. Largest line CloudWatch `PutLogEvents` $2,415. Teams: team-demoability $5,801, team-unc $709,
  `demoability` $8 (a second spelling of the tag).
- Databases: 18 with no utilization data ($321); sf-live-postgres 3.8% CPU / 121 MB free and
  astroshop-live-productcatalog-db 5.7% / 38 MB ("low CPU, no memory headroom"); pure-otel-live 5.9% / 2,992 MB.

## Open

- **Deep links not opened in a browser.** `validate_dt_skill.py --scenario cloud-observability --links` prints them; the
  Clouds, problem and workflow URLs are copied from the guide, the cost-explorer one is the guide's 90-day URL changed to
  30 days. Open each and judge it against its label (AUTHORING step 4).
- **Where the agent runs.** The deployed `demo-agent` runs DQL on its own tenant; this scenario works only where it is
  deployed on `guu84124`. On the Playground, `/demo` reaches it through `--context demo-live` (local-runtime).
  Contributors need a read-only `demo-live` context: `dtctl config set-context demo-live --environment
  https://guu84124.apps.dynatrace.com --safety-level readonly`, then `dtctl auth login --context demo-live`.
- **Evals drafted, not run.** `run_dt_evals.py` and `local_agent.py` have a `demo-live` tenant; draft cases
  `cloud-tour-opening-demo-live`, `cloud-cost-demo-live` and `cost-pricing-demo-live`. Run with
  `python tools/run_dt_evals.py --local --tenant demo-live --include-draft` (needs `ANTHROPIC_API_KEY`), then promote the
  ones that pass to ready. A case for the "do not shrink" peak is still missing.
- **Playground not checked** for cost or cloud data (token expired during the build).
