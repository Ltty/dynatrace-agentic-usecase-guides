# App Offers

Which live scenarios an open app can offer. An app offers a scenario when the app is where part of that story is
shown: the scenario's own deep links open it, or what the app shows is the evidence. A scenario is offered only when
the opening query returned a row for it on this environment (SKILL.md, step 2).

| Open app | Scenarios offered |
|---|---|
| `dynatrace.kubernetes` | `k8s-cpu-throttling` |
| `dynatrace.infraops` | `k8s-cpu-throttling` |
| `dynatrace.users.sessions`, `dynatrace.experience.vitals`, `dynatrace.classic.session.replay` | `broken-images`, `payment-failure` |
| `dynatrace.services`, `dynatrace.error.inspector` | `payment-failure`, `broken-images` |
| `dynatrace.distributedtracing` | `payment-failure`, `broken-images`, `lambda-iam-denied`, `k8s-cpu-throttling` |
| `dynatrace.clouds` | `lambda-iam-denied`, `cloud-observability` |
| `dynatrace.biz.carbon`, `community.cloudsreagents`, `dynatrace.launcher` | `cloud-observability` |
| `dynatrace.davis.problems` | `payment-failure`, `broken-images`, `lambda-iam-denied`, `k8s-cpu-throttling`, `cloud-observability` |

`cloud-observability` is the cloud tour, a showcase with no problem row of its own: it is offered where
`session-protocol.md` lists it for the environment, not by a row.

Adding an app or a scenario: add the row here and the app ID to the SKILL.md description, then run
`python tools/tests/test_app_offers.py`. It fails when a scenario's beat links name an app with no row for that
scenario, when a row names a scenario that does not exist, and when the description and this table disagree.
