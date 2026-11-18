# App Offers

Which live scenarios an open app can offer. An app offers a scenario when the app is where part of that story is
shown: the scenario's own deep links open it, or what the app shows is the evidence. A scenario is offered only when
the opening query returned a row for it on this environment (SKILL.md, step 2).

| Open app | Scenarios offered |
|---|---|
| `dynatrace.kubernetes` | `k8s-cpu-throttling`, `kubernetes-complexity` |
| `dynatrace.infraops` | `k8s-cpu-throttling`, `kubernetes-complexity` |
| `dynatrace.users.sessions`, `dynatrace.experience.vitals`, `dynatrace.classic.session.replay` | `broken-images`, `payment-failure` |
| `dynatrace.services`, `dynatrace.error.inspector` | `payment-failure`, `broken-images` |
| `dynatrace.distributedtracing` | `payment-failure`, `broken-images`, `lambda-iam-denied`, `k8s-cpu-throttling` |
| `dynatrace.clouds` | `lambda-iam-denied`, `kubernetes-complexity` |
| `dynatrace.launcher` (the Home page) | `payment-failure`, `broken-images`, `lambda-iam-denied`, `k8s-cpu-throttling`, `kubernetes-complexity` |
| `dynatrace.davis.problems` | `payment-failure`, `broken-images`, `lambda-iam-denied`, `k8s-cpu-throttling`, `kubernetes-complexity` |

`kubernetes-complexity` is a tour, a showcase with no problem row of its own: it is offered where
`session-protocol.md` lists it for the environment, not by a row. Cloud costs have no offer: Assist's own cost analysis
answers them, so the cost-flavoured apps (`dynatrace.biz.carbon`, `community.cloudsreagents`) carry no row.

**A tour replaces the incident it contains.** `kubernetes-complexity`'s troubleshoot track *is* `k8s-cpu-throttling`.
Where a row lists both and the tour is available, offer the tour and not the incident: offering both makes the user
choose between the same story twice. Where the tour is not listed (playground), the incident is offered as before.

**The Home page offers the whole set.** It is no app's lane, so every live incident and the tour are offered together as a choice
(SKILL.md, "Several matches"), with the tour standing in for the throttling incident.

Adding an app or a scenario: add the row here and the app ID to the SKILL.md description, then run
`python tools/tests/test_app_offers.py`. It fails when a scenario's beat links name an app with no row for that
scenario, when a row names a scenario that does not exist, and when the description and this table disagree.
