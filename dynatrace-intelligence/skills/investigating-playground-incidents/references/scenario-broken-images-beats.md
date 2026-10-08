# Scenario: Broken Images (Slowdown) — Beats

Read once the user has picked a direction from the survey. Resolver, scope, and handoff fields:
`references/scenario-broken-images.md`.

Reveals describe the *shape* of a finding, never its values. Commit SHAs, timestamps, latencies,
user and session counts, and countries rotate every cycle — read them from the live result.

## Contents

- [Beat 1 — The Page](#beat-1--the-page)
- [Beat 2 — The Deploy](#beat-2--the-deploy)
- [Beat 3 — The Slowdown](#beat-3--the-slowdown)
- [Beat 4 — The Slow Trace](#beat-4--the-slow-trace) (peak)
- [Beat 5 — The Humans](#beat-5--the-humans) (peak)

---

## Beat 1 — The Page

**Objective:** User grasps the blast radius: the image-provider Lambda is the root cause, it's a
response-time degradation rather than an outage, how many users are affected, and who owns it.

**Evidence DQL:**

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter event.id == "{{PROBLEM_ID}}"
| fields
    display_id,
    status         = event.status,
    started        = event.start,
    affected_users = dt.davis.affected_users_count,
    root_cause     = root_cause_entity_name,
    owning_team    = team,
    also_affected  = affected_entity_names,
    impact_level   = dt.davis.impact_level,
    description    = event.description,
    queried_at     = now()
```

**Reveal:** Dynatrace Intelligence classifies it as a slowdown — `description` states the current response time
against the auto-detected baseline for the image provider; quote both numbers. The frontend,
the ingress, and a synthetic image-loading check are listed as affected; `impact_level`
spans application, services, and synthetic. Name `owning_team` explicitly — it's the only
owner on record, since the deploy events carry none.

**Success signal:** User names the image provider or the Lambda, or asks why it's slow.

**Deep link:**

```text
https://playground.apps.dynatrace.com/ui/apps/dynatrace.davis.problems/problem/{{PROBLEM_ID}}?from={{TF_FROM_MS}}&to={{TF_TO_MS}}
```

---

## Beat 2 — The Deploy

**Objective:** User connects the slowdown to a specific commit, and sees both deploys on the
timeline.

**Evidence DQL:**

```dql
fetch events, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter event.type == "CUSTOM_DEPLOYMENT"
| filter dt.entity.service == "SERVICE-5A0CD2879D2F37BE"
| parse event.description, "LD \"(\" LD:git_url \")\""
| parse git_url, "LD \"/commit/\" ALNUM:commit"
| summarize
    first_deploy = min(timestamp),
    last_deploy  = max(timestamp),
    deploys      = count(),
    by: { commit, git_url }
| sort first_deploy asc
| fieldsAdd queried_at = now()
```

These GitHub Actions events leave `commit` and `gitUrl` null; the query parses both from the
markdown link in `event.description` and collapses the repeated re-deploys of one commit.

**Reveal:** Typically two rows. The first commit lands a few minutes before the problem
`started` (beat 1) and is re-deployed several times — that's the regression. The second
lands shortly before the problem ended and is not a second regression; whether the slowdown
stops around it is for beat 3, and what it changed is in the diff, not the telemetry. Both
descriptions read alike, so tell them apart by timing, not text. State both SHAs, the
`git_url` of the first, and the gap between its `first_deploy` and the problem start.

**Objection** — "a few minutes apart doesn't prove causation": agree that a gap that short is
suggestive, not proof. The proof is whether the Lambda's behaviour changed at exactly that
deploy and went back around the later deploy — the next beat shows it per request; offer to go
there.

**Success signal:** User identifies the deploy as the trigger, or asks what that commit changed.

**Deep link:**

```text
https://playground.apps.dynatrace.com/ui/apps/dynatrace.deployment.management/deployments?filter=dt.entity.service%3DSERVICE-5A0CD2879D2F37BE&tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}
```

---

## Beat 3 — The Slowdown

**Objective:** User sees what changed in the Lambda's behaviour at the deploy: it started
resizing the image on every request, and latency jumped with it.

**Fold in on a jump:** if the user jumps to beat 4, run this query in the same turn and show the
flip in one line. It is the evidence that ties the deploy to the slowdown.

**Evidence DQL:**

```dql
fetch spans, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter dt.entity.service == "SERVICE-5A0CD2879D2F37BE"
| filter in(span.name, "Invoke lambda /images/presign.", "Resize original product image")
| summarize
    requests = countIf(span.name == "Invoke lambda /images/presign."),
    resizes  = countIf(span.name == "Resize original product image"),
    p50_ms   = round(percentile(if(span.name == "Invoke lambda /images/presign.", toDouble(duration)), 50) / 1000000, decimals: 0),
    by: { bucket = bin(start_time, 5m) }
| sort bucket asc
| fieldsAdd queried_at = now()
```

**Reveal:** Before the regression deploy, `resizes` is zero — resized images are served from
S3. From the deploy's bucket on, `resizes` equals `requests`: every single image request runs
the full resize pipeline, and `p50_ms` jumps from tens of milliseconds to seconds. After the later
deploy, resizes fall back to zero and latency recovers. State the actual before/after p50 and
the buckets where it flips — that flip lines up with both commits.

**Success signal:** User connects the resizes to the deploy, or asks where the time goes.

**Deep link:**

```text
https://playground.apps.dynatrace.com/ui/apps/dynatrace.services/explorer/services?detailsId=SERVICE-5A0CD2879D2F37BE&perspective=performance&problemId={{PROBLEM_ID}}&tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}
```

---

## Beat 4 — The Slow Trace

**`peak_moment: true`**

**Objective:** User sees one slow image request end to end: where the seconds go, and what
is *not* slow.

**Evidence DQL — slowest Lambda invocations (run first):**

```dql
fetch spans, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter dt.entity.service == "SERVICE-5A0CD2879D2F37BE"
| filter span.name == "Invoke lambda /images/presign."
| fieldsAdd duration_ms = round(toDouble(duration) / 1000000, decimals: 0)
| sort duration_ms desc
| limit 5
| fields start_time, trace_id = trace.id, duration_ms, failed = request.is_failed, queried_at = now()
```

**Evidence DQL — the trace's time budget (chained; substitute `trace_id` from the first
record above):**

```dql
fetch spans, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter trace.id == toUid("{{TRACE_ID}}")
| fieldsAdd duration_ms = round(toDouble(duration) / 1000000, decimals: 0)
| summarize duration_ms = max(duration_ms), first_start = min(start_time),
    by: { service = dt.service.name, span_name = span.name }
| filter duration_ms >= 50 or contains(span_name, "DynamoDB")
| sort first_start asc
| fields service, span_name, duration_ms
```

One row per operation in call order; sub-50 ms noise is dropped except DynamoDB, which shows
it is fast.

**Reveal:** The Lambda invocations themselves are not marked failed — this is latency, not an error. Inside the
Lambda, the DynamoDB lookup and the S3 "check if image for screen size exists" take
milliseconds; then "Resize original product image" takes almost the whole request — the
resizing itself plus writing the result back to S3. The S3 check runs, and the resize happens
anyway: the cache stopped short-circuiting. Say that as the read, and point at beat 2's commit
for the code-level confirmation — don't state what the diff contains.

Don't claim there are no errors anywhere. If the user asks about errors, query the failing spans for the window: a single sampled failed `GET` span may be there, with a throttle exception ("SlowDown: Please reduce your request rate.") after about 7 seconds of retries. Quote the exception verbatim; it is a symptom of the resizes, not a separate cause.

**Success signal:** User names the resize step as where the time goes, or asks why the cache
check doesn't skip it.

**Staging:**

1. The finding alone on its own line, before any commentary:
   `Resize original product image — [duration_ms] ms of a [Lambda duration_ms] ms request`
2. Blank line.
3. What kind of problem it is: latency from work that shouldn't happen on every request, not
   an error and not a slow dependency — DynamoDB is at single-digit milliseconds.
4. The trace as a short chain plus one line for the fast steps:

   ```text
   frontend /api/images/… → image-provider Lambda → Resize original product image   [slow]
   fast: DynamoDB GetItem, S3 HeadObject check — milliseconds
   ```

   Build both lines from the rows the query returned.
5. Tie it back: the check for a cached image runs, the resize runs anyway, every request since
   the deploy.

**Deep link:**

```text
https://playground.apps.dynatrace.com/ui/apps/dynatrace.distributedtracing/explorer?filter=dt.smartscape.service+%3D+SERVICE-5A0CD2879D2F37BE+AND+endpoint.name+%3D+invoke&tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}
```

---

## Beat 5 — The Humans

**`peak_moment: true`**

**Objective:** User understands who felt it: real shoppers in many countries waiting seconds
for product images, each with a replay of exactly what they saw.

**Evidence DQL:**

```dql
fetch user.events, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter characteristics.has_request == true
| filter contains(url.full, "/api/images/")
| filter dt.rum.user_type == "real_user"
| filter toDouble(duration) > 1000000000
| summarize slow_loads = count(), worst_ms = round(max(toDouble(duration)) / 1000000, decimals: 0),
    by: { session_id = dt.rum.session.id, country = geo.country.iso_code }
| lookup [fetch user.sessions, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
          | fields session_id = dt.rum.session.id, has_replay = characteristics.has_replay],
    sourceField: session_id, lookupField: session_id, prefix: "s."
| summarize
    sessions    = count(),
    with_replay = countIf(s.has_replay == true),
    slow_loads  = sum(slow_loads),
    worst_ms    = max(worst_ms),
    by: { country }
| sort sessions desc
| fieldsAdd queried_at = now()
```

Sessions with at least one image load over 1 s, real users only (the synthetic monitor is
excluded). Don't use `error.http_5xx_count` here: the images return 200, so a 5xx filter finds
almost nobody. No `limit` — the total is the sum of `sessions` across all rows, and it is a
different population from the problem's affected users; label each. `queried_at` is for the
session close's elapsed time, not for the table.

**Reveal:** Real-user sessions across many countries hit image loads of several seconds, and
nearly all have replay. State the actual session total, the number of rows as returned (one per
country value; a row with no country is reported as exactly that), the top rows, and the worst
load time. Don't add geography the rows don't contain. The point isn't the number — each one is a
recording of a shopper whose image took seconds to load.

**Success signal:** User asks about the experience, what shoppers saw, or opens a replay.

**Staging:** After the numbers, make replay concrete: open one and watch which product images
appeared, which stayed blank, and whether the shopper waited, scrolled on, or left. Ask: "for a front-end problem, what did the user actually see?" — and invite the user to
open a replay via the deep link. The DQL can't answer that; the replay can.

**Deep link:**

```text
https://playground.apps.dynatrace.com/ui/apps/dynatrace.error.inspector/error-explorer?tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}&problemId={{PROBLEM_ID}}&perspective=impact&sort=affected_users%3Adescending
```
