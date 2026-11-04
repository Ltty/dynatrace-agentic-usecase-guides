# Scenario: Lambda Denied by IAM (Outage) — Context and Beats

Read once the user has picked a scenario. The survey query and the discovery hooks are in `references/session-protocol.md`.
Reveals describe the *shape* of a finding, never its values. Counts, failure rates, user numbers, the window and the agent's own wording rotate every cycle — read them from the live result.

## Contents

- [Business context](#business-context)
- [Scope](#scope)
- [Handoff fields](#handoff-fields)
- [Beat 1 — The Page](#beat-1--the-page)
- [Beat 2 — The Failing Window](#beat-2--the-failing-window)
- [Beat 3 — What the Failures Say](#beat-3--what-the-failures-say) (peak)
- [Beat 4 — The Permission](#beat-4--the-permission)
- [Beat 5 — What the Agent Found](#beat-5--what-the-agent-found)

---

## Business context

| Field | Value |
|---|---|
| `service_name` | "image provider" |
| `symptom` | "product images failing on the storefront" |
| `pull_line` | "Pulling the problem, the failing requests, the exception behind them, the function's permissions and the agent's notes together." |

This is an **outage, not a slowdown**: the requests return an error, they are not merely late. No `avg_order_value_usd` is defined: no revenue figure, and none is to be estimated from the affected users.

The root cause entity is the DynamoDB side of the call; the requests that fail run on the Lambda. Both are named below, and they are not interchangeable.

## Scope

**Data objects:** `dt.davis.problems`, `spans`, `smartscapeNodes`, `events`

**Stable IDs** (demo-live entities):

| Name | ID |
|---|---|
| image-provider-live-products in us-east-1 (root cause, the DynamoDB side) | `SERVICE-F4E5246FA8EA27D7` — resolves as `{{ROOT_CAUSE_ID}}` |
| image-provider-live in us-east-1 (the Lambda service, where the failing spans are) | `SERVICE-42411741F5F4AC50` |
| image-provider-live (the function, Clouds app) | `AWS_LAMBDA_FUNCTION-9365828D44E6A036` |
| image-provider-live (its execution role) | `AWS_IAM_ROLE-4EBB0A40DB75D204` |
| The AWS DevOps Agent's notes | `events` where `annotation.source == "aws_devopsagent"` |

`{{ROOT_CAUSE_ID}}` has **no spans of its own**: the DynamoDB client spans belong to the Lambda service. Span queries and any Distributed Tracing filter use the literal Lambda service ID above; built on `{{ROOT_CAUSE_ID}}` they return nothing.

## Handoff fields

Two populations coexist — always say which one a number counts.

| Value | Source |
|---|---|
| `owning_team` | Survey row (beat 1 shows it) |
| `Goes to` | `owning_team`, with the function's own AWS owner tags beside it when beat 4 returns different ones |
| Affected users (problem record) | survey row `affected_users` |
| Failed requests on the Lambda | Beat 2 — `failed`, against `requests` |
| The exception, verbatim | Beat 3 — `exception_type` and `message` |
| The role and the policy | Beat 4 — `role_arn`, `policy_name`, `document` |
| What to change | Beat 5 — the agent's own recommendation, when the note carries one |

---

## Beat 1 — The Page

**Why this step:** Before we chase a cause we need the blast radius: what is failing, for how many, and whose service it is.

**Objective:** User grasps the blast radius: a storefront-facing image call is failing outright, how
many users it reached, how far it spread, and who owns it.

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
    description    = event.description,
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

**Reveal:** Three values carry this beat — the rate, the users and the team. The query returns more than that;
don't put the whole row on screen. `description` names the endpoint that failed and the rate it reached —
quote both; a rate at or near 100% is the finding, because it means every call, not a share of them. Say which
population `affected_users` counts: the problem record's. Then `also_affected`, read as a chain rather than a
list — it runs from the DynamoDB-side service in `root_cause` out through the Lambda to the storefront
frontend, the ingress and a synthetic image check, which is the distance from the call that broke to the shop
page someone is looking at. Name `owning_team` last, as the one thing here that is a person rather than a
number.

**Success signal:** User names the image provider, or asks what the failing call was.

**Deep link** (label "Problem in Dynatrace"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.davis.problems/problem/{{PROBLEM_ID}}?from={{TF_FROM_MS}}&to={{TF_TO_MS}}
```

---

## Beat 2 — The Failing Window

**Why this step:** A problem record says something broke; to know whether it drifted or switched we need the requests themselves, minute by minute.

**Objective:** User sees the failure arrive and leave as a step rather than a slope, with the clean
traffic either side of it in the same table.

**Evidence DQL:**

```dql
fetch spans, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter dt.entity.service == "SERVICE-42411741F5F4AC50"
| filter request.is_root_span == true
| summarize requests = count(), failed = countIf(request.is_failed == true), by: { bucket = bin(start_time, 5m) }
| fieldsAdd failure_rate_pct = round(100.0 * failed / requests, decimals: 1)
| sort bucket asc
| fields bucket, requests, failed, failure_rate_pct,
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

The window is the problem's, padded 15 minutes each side, so the clean buckets either side come back in the
same result.

**Reveal:** Give the shape, not every row: clean before, the rate it climbs to and how many buckets it holds
there, clean after, with the clock times of the first and last failing bucket. A rate that goes from zero to
its ceiling inside one or two buckets is a switch being thrown, not a resource filling up or a dependency
degrading — which is what rules out load, saturation and a slow backend before we have spent a query on any
of them. Throughput in the failing buckets is its own number: state it as returned and leave what drove it to
the owning team, since nothing here says whether callers retried, backed off, or were served elsewhere.

**Success signal:** User asks what the failing requests return, or what changed at that minute.

**Deep link** (label "Requests on the function"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.distributedtracing/explorer?filter=dt.smartscape.service+%3D+SERVICE-42411741F5F4AC50&tf={{TF_FROM_ISO}}%3B{{TF_TO_ISO}}&v=requests
```

All requests, not only the failing ones: the step is only visible with the clean traffic beside it.

---

## Beat 3 — What the Failures Say

**`peak_moment: true`**

**Why this step:** A failure rate says how much broke, never why — for that we read what the failing requests themselves threw.

**Objective:** User reads the root cause off the exception: one error, repeated on every failure, naming
the identity, the action and the resource it was refused.

**Evidence DQL:**

```dql
fetch spans, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter dt.entity.service == "SERVICE-42411741F5F4AC50"
| filter request.is_root_span == true and request.is_failed == true
| expand span.events
| filter span.events[span_event.name] == "exception"
| summarize failures = count(), first_seen = min(start_time), last_seen = max(start_time),
    by: { exception_type = span.events[exception.type], message = span.events[exception.message] }
| sort failures desc
| fields exception_type, message, failures, first_seen, last_seen,
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

`expand span.events` first, then bracket access — `span.events[exception.type]` on an unexpanded array returns nothing.

**Reveal:** Quote `message` verbatim; it is the whole finding and paraphrasing it loses the three things that
matter. Say how many distinct exceptions came back: **one** row means a single cause, not a flaky dependency
or a pile of unrelated errors. An authorization error is not a failure of the thing being called — DynamoDB
answered, and what it answered was no. So the table is fine, the function is fine, and what is wrong is what
the function is allowed to do. The message names three things, and all three get read out, in plain words as well as verbatim: the
**identity** the function runs as (AWS calls it an execution role — the set of permissions the function
borrows while it runs), the **action** it tried, and the **resource** it tried it on, written as an ARN, which
is AWS's full address for one thing in one account and region. Assume none of that is known. Whether the
permission was always missing or was taken away is not in this result.

**Success signal:** User names the permission, the IAM role or the policy as the thing to look at.

**Staging:**

1. The finding alone on its own line, before any commentary:
   `[exception_type] on [failures] failed requests — [the action] on [the resource], refused`
2. Blank line.
3. What kind of problem it is: a permission, not a fault. Nothing is broken, overloaded or unreachable; the
   call is being denied. That is a configuration change somewhere, and it is instant rather than gradual —
   which is the step in beat 2.
4. The message quoted in full, as returned.
5. The three names it hands us — identity, action, resource — and that the role is the one thing of the three
   we can read in Dynatrace right now.

**Deep link** (label "The failed requests"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.distributedtracing/explorer?filter=dt.smartscape.service+%3D+SERVICE-42411741F5F4AC50+AND+request.is_failed+%3D+true&tf={{TF_FROM_ISO}}%3B{{TF_TO_ISO}}&v=requests
```

---

## Beat 4 — The Permission

**Why this step:** The exception named an identity, an action and a resource, and the policy that is supposed to join them is in Dynatrace with everything else about the function.

**Objective:** User sees the function's execution role and its inline policies as the cloud provider holds
them, and compares the DynamoDB grant against the ARN the exception named — without opening AWS.

**Evidence DQL:**

```dql
smartscapeNodes "AWS_IAM_ROLE"
| filter id == toSmartscapeId("AWS_IAM_ROLE-4EBB0A40DB75D204")
| parse aws.object, "JSON:o"
| fieldsAdd role_name = o[configuration][roleName], role_arn = o[configuration][arn]
| expand policy = o[configuration][rolePolicyList]
| fieldsAdd policy_name = policy[policyName], doc = toString(policy[policyDocument])
| fieldsAdd is_dynamodb = contains(doc, "dynamodb:")
| fields role_name, role_arn, policy_name, is_dynamodb,
    document = if(is_dynamodb, doc, else: ""),
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
| sort is_dynamodb desc, policy_name asc
```

Smartscape holds the role as it is **now**. There is no history here: during an open problem this is the
configuration that is failing, and after it closes this is whatever replaced it.

**Reveal:** The role in the result is the one the exception named — say so by matching `role_arn` to the
identity in beat 3's message. List the policy names so the shape is visible: an inline policy is a grant
attached to this role and nothing else, and there is one per thing the function touches, each scoped to its
own resources. Then the DynamoDB one: read its `Action` and its `Resource` out of
`document`, and hold the `Resource` next to the ARN the exception quoted.

- **They differ** — the grant is written against something other than the table the function asks for; state
  both strings exactly as returned and let the difference be the finding. A resource ARN that ends `/*`
  addresses the things *under* a table, not the table, so a grant written that way allows nothing on the
  table itself.
- **They match** — say that as plainly: the grant is correct in the configuration we can read right now, so
  it was not correct during the window, and it has since been changed back. When it changed, and by what, is
  not in Dynatrace; beat 5 is where that comes from.

Never describe a `/*`, or any other difference, that the returned `document` does not contain.

`primary_tags` and `tags:aws` on the function carry owner tags of their own. When the user asks who owns it
and those differ from beat 1's `owning_team`, state both as returned; which one is right is the owners' call.

**Success signal:** User asks what changed the policy, or who changed it.

**Deep link** (label "The function in the Clouds app"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.clouds/smartscape/functions?perspective=health&detailsId=AWS_LAMBDA_FUNCTION-9365828D44E6A036&sidebarOpen=false&tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}
```

---

## Beat 5 — What the Agent Found

**Why this step:** Dynatrace can show the denial and the grant, but not the deploy that changed it — that history lives in the cloud account, which is where the AWS DevOps Agent was sent with this problem's context.

**Objective:** User sees the hand-off close: Dynatrace correlated the incident, triggered the AWS DevOps
Agent with it, and the agent's findings came back onto the same problem record rather than into a separate
tool.

**Evidence DQL:**

```dql
fetch events, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter annotation.source == "aws_devopsagent"
| expand pid = annotation.problem_ids
| lookup [fetch dt.davis.problems, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
          | filter root_cause_entity_id == "{{ROOT_CAUSE_ID}}"
          | fields pid = event.id, display_id],
    sourceField: pid, lookupField: pid, fields: { display_id }
| filter isNotNull(display_id)
| fieldsAdd d = toString(event.description), has_summary = not contains(event.name, "summary not available")
| fieldsAdd h = indexOf(d, "#### ")
| fieldsAdd kind = if(contains(event.name, "Mitigation"), "Mitigation Recommendations", else: "Investigation Results")
| summarize notes = count(), on_problems = countDistinct(display_id), last_at = max(timestamp),
    summary = takeFirst(if(has_summary and h >= 0, substring(d, from: h + 5, to: h + 505), else: "")),
    by: { kind, has_summary }
| sort has_summary desc, kind asc
| fields kind, has_summary, notes, on_problems, last_at, summary,
    queried_at = now(), elapsed_min = round(toDouble(now() - toTimestamp("{{SURVEY_AT}}")) / 60000000000, decimals: 0)
```

The notes attach to several records of the same cluster, which is why `on_problems` can exceed one and why
the lookup matches on the root cause rather than on `{{PROBLEM_ID}}` alone.

**Reveal:** The agent wrote `notes` notes in two kinds — an investigation and a mitigation — onto this
incident's records, `last_at` minutes after it started. State what that chain is: Dynatrace saw it, named the
root cause, and handed the agent the context; the agent worked the AWS side, where CloudTrail and the deploy
history are, and wrote back here. One problem record, every investigation on it, and from here it can go on to
a ticket or a coding agent with the evidence attached.

- **`has_summary` is true** — quote `summary` as the agent's own words, attributed to it, and say plainly it
  is a recommendation for the owning team to review, not a change anyone has made. If it names a deploy, a
  repository or a time, those are the agent's findings from AWS, not Dynatrace's: attribute them that way.
- **`has_summary` is false** — the notes are on the record but their summary is not readable from here; say
  exactly that, say how many there are and when, and point at the AWS DevOps Agent task as where the findings
  are. Never infer what the note said from beats 3 and 4.

**Objection** — "so it fixed it?": no. The agent investigated and recommended; the role is still whatever
beat 4 returned. Everything an agent does here is written down and attributed, with a human deciding whether
to apply it.

**Success signal:** User asks what to do about it, or who to send it to.

**Deep link** (label "The agent's notes on the problem"):

```text
https://{{LINK_HOST}}/ui/apps/dynatrace.davis.problems/problem/{{PROBLEM_ID}}?from={{TF_FROM_MS}}&to={{TF_TO_MS}}
```
