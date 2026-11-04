# lambda-iam-denied: stable entity IDs and debugging notes

Maintainer notes. The agent never reads this file.

Source: the "AWS DevOps Agent integration" step of the *Modern Cloud Observability* golden demo, taken
to incident depth. The showcase (`scenario-cloud-observability.md`) names this same problem in its
beat 3 and counts the agents' notes in beat 4; this scenario walks it to the root cause.

## Stable entity IDs (safe to hardcode in queries and deep links)

| Name | Entity ID | Type |
|------|-----------|------|
| image-provider-live-products in us-east-1 | SERVICE-F4E5246FA8EA27D7 | Service — the DynamoDB side, and the problem's root cause |
| image-provider-live in us-east-1 | SERVICE-42411741F5F4AC50 | Service — the Lambda, where the failing spans are |
| image-provider-live | AWS_LAMBDA_FUNCTION-9365828D44E6A036 | Clouds-app function node |
| image-provider-live | AWS_IAM_ROLE-4EBB0A40DB75D204 | Its execution role |

The function ARN carried by the spans as `cloud.resource_id` is
`arn:aws:lambda:us-east-1:246186168471:function:image-provider-live`; the table is
`arn:aws:dynamodb:us-east-1:246186168471:table/image-provider-live-products`.

**`SERVICE-F4E5246FA8EA27D7` has no spans.** It is the detected DynamoDB-side service; the
`GetItem dynamodb` client spans belong to `SERVICE-42411741F5F4AC50`. A span query or a Distributed
Tracing link built on `{{ROOT_CAUSE_ID}}` returns nothing, which is why the beats use the Lambda
service ID as a literal from the Scope table.

## What rotates every problem cycle (never hardcode)

problem id / display id, affected-user count, the failure rate and bucket counts, the exact window,
the number of agent notes, and the agent's own wording.

## Resolver notes

The survey branch matches `root_cause_entity_id == "SERVICE-F4E5246FA8EA27D7"`. Entity ID, not name:
playground runs its own `image-provider-playground`, and a name match is how `disk-cpu-cascade` leaked
across tenants in testruns 12 and 13.

The cluster also produces `Response time degradation` problems rooted on the *Lambda* service
(`SERVICE-42411741F5F4AC50`). Those are a different story and are deliberately not matched.

## The incident shape (verified 2026-11-04 across the last 7 days)

Fires **daily at about 16:05 UTC**, closes about 16:43, 268–390 affected users on the record.
Non-duplicate instances on 6 of the last 7 days, so the 48-hour survey window catches it reliably.

A new Lambda version is deployed whose IAM inline policy for DynamoDB carries a trailing `/*` on the
resource ARN. The deploy is visible: two `CUSTOM_DEPLOYMENT` events on `SERVICE-42411741F5F4AC50`
from `Dynatrace/opentelemetry-demo-gitops`, one re-deployed several times from about a minute before
the first denial, one about five minutes before the last. **This was missed in the first pass** — a
search of `SDLC_EVENT` and `task.deployment.finished` found only ten-minute ArgoCD noise and the
scenario shipped saying no deploy signal existed. `CUSTOM_DEPLOYMENT` is the event type
`broken-images` already uses for exactly this; check it first next time. A resource ARN ending `/*` addresses what is *under* a table — its indexes — not the
table, so `dynamodb:GetItem` on the table itself is allowed by nothing:

```text
GET (root span, endpoint "invoke") on image-provider-live
  → GetItem dynamodb  →  AccessDeniedException
```

Measured on 2026-11-03, window 15:51–16:59 UTC:

- root spans on the Lambda go **0% → 100% → 0%** across 5-minute buckets, 8,927 failed of 25,881;
- throughput in the failing buckets falls to about a third (4,200 → 1,400 per 5 min). What drives
  that is not in the data — the beats state it and attribute nothing;
- exactly **one** distinct exception, `AccessDeniedException`, message:

  > User: arn:aws:sts::246186168471:assumed-role/image-provider-live/image-provider-live is not
  > authorized to perform: dynamodb:GetItem on resource:
  > arn:aws:dynamodb:us-east-1:246186168471:table/image-provider-live-products because no
  > identity-based policy allows the dynamodb:GetItem action

- the problem description names the endpoint (`GetItem`) and a 100% error rate;
- `team` on the problem is `Team-UI`, while the function's AWS tags say `dt_owner_team:team-unc` and
  `team:Team-Cloud-Services`. Beat 4 states both when asked rather than picking one.

## Two known limits

### 1. The AWS DevOps Agent summary has been unreadable since 2026-10-27

Every note since then is named `… (summary not available)` with a body that says the summary could not
be read and to open the task in the AWS DevOps Agent space. Readable notes ran from 2026-10-06 to
**2026-10-26** (32 investigation + 32 mitigation). Beat 5 is written to handle both and does not
degrade silently.

The last readable mitigation note, 2026-10-26T16:12:09Z, is the scenario's own ground truth:

> **Action** — Manually correct the IAM inline policy 'image-provider-live-dynamodb-read-only' on role
> 'image-provider-live' to remove the trailing /* from the DynamoDB resource ARN, restoring Lambda
> function access to perform dynamodb:GetItem operations on table 'image-provider-live-products'.
>
> **Reasoning** — At 2026-04-22T15:01:27Z, a GitHub Actions Terraform deployment from the
> Dynatrace/opentelemetry-demo-gitops repository re-introduced a broken IAM policy configuration…

Its investigation note additionally measured 17,416 AccessDeniedException errors in the window against
zero in the baseline. **None of this may be said by the agent while the live note carries no summary** —
it is recorded here so a maintainer knows what the beat looks like when the integration is healthy.

Worth chasing on the AWS side. Until it is fixed, beat 5 is thinner than the golden demo's version.

### 2. The broken policy is only visible while the problem is open

`smartscapeNodes` holds current state. Given yesterday's incident window as `from:`/`to:` it still
returned the **corrected** policy, so the trailing `/*` cannot be read back after the fact. Outside the
window beat 4 returns:

```json
{"Action":["dynamodb:GetItem"],"Effect":"Allow","Resource":"arn:aws:dynamodb:us-east-1:246186168471:table/image-provider-live-products"}
```

which is correct, and the beat says so as a finding rather than narrating a `/*` that no row returned.

## Notes against other scenarios

`broken-images` on playground lists this same `AccessDeniedException` as background noise ("fails
thousands of spans every day, but at other hours, not in the incident window"). The two scenarios live
on different tenants and are never offered in the same conversation, but their SKILL.md match phrases
are kept apart on purpose: `broken-images` owns *slow images, slowdowns*, this one owns *access denied,
IAM, permissions, DynamoDB*.
