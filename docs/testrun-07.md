# Demo Test Run 07 — broken-images scenario

**Date:** 2026-10-01
**Scenario:** broken-images (P-261012)
**Mode:** live_recent (problem CLOSED; started 03:04 UTC, ended 03:39 UTC; session started ~11:43 UTC)
**Duration:** ~20 minutes
**Entry path:** Survey (two scenarios) → user chose image service → blast radius (beat-01) →
failing spans + trace waterfall (beat-02) → affected sessions (beat-03) → ad-hoc deployment
investigation (out-of-scenario, user-driven)

---

## Preflight

Not run explicitly this session. `/demo` ran both resolvers silently at entry.

---

## Discovery (`/demo`)

**Trigger:** "are there any open issues"

**Resolver output:** Two scenarios both `live_recent`:
- broken-images: P-261012, CLOSED, 269 affected users, 03:04–03:39 UTC (8h prior)
- payment-failure: P-261045, CLOSED, 333 affected users, 09:07–09:43 UTC (2h prior)

**Engine output (paraphrased):**

> Two incidents hit today, both closed: payment service failures for 333 users ~2 hours ago
> (~$29K in abandoned carts), and image service degradation for 269 users ~8 hours ago.
> Asked which to dig into.

**Notes:**

- Survey triggered correctly on "are there any open issues" ✅
- Both scenarios presented with correct live data; revenue impact computed for payment-failure ✅
- broken-images has no `avg_order_value_usd` in its `business_context` — revenue impact not
  computed for image scenario (no number to misstate) ✅
- Past-tense `live_recent` framing for both ✅
- Ended on a choice between scenarios, not yes/no ✅
- User chose broken-images via "What happened to the image service?" ✅

---

## Beat 01 — The Page

**User:** "What happened to the image service?"

**Query:** `beat-01-problem-summary.dql` — ran cleanly, 1 record ✅

**Evidence returned:**

| Field | Value |
|---|---|
| Problem | P-261012 |
| Root cause | image-provider-playground in us-east-1 |
| Affected users | 269 |
| Owning team | Team-UI |
| Also affected | astroshop-frontend, ingress, Astroshop synthetic, binoculars check |
| Response time | ~6.21s vs 24.58ms baseline (25,183% deviation) |

**Narration quality:**
- Davis characterised as response time degradation, not outage — service responding at 7s,
  not crashing ✅
- Owning team named (Team-UI) ✅
- Cascaded impact (frontend, ingress, synthetic) explained as knock-on, not root cause ✅
- Deep link: Davis problem detail ✅

---

## Beat 02 — The Failing Calls (peak moment)

**User:** "Why did the lambda get that slow?"

**Queries:**

- `beat-02-failing-spans.dql` — ran cleanly, 1 record ✅
- `beat-03-trace-waterfall.dql` (chained, `TRACE_ID=49c0148bf7fb63d6773b314400d58607`) — ran
  cleanly, 22 spans, ASCII waterfall rendered ✅
- Verbatim CLI table also fetched (`-o table --plain`) ✅

**Evidence — failing span:**

| Field | Value |
|---|---|
| Endpoint | invoke |
| Exception type | SlowDown |
| Exception message | "Please reduce your request rate." |
| Exception file | `@aws-sdk/core/dist-cjs/submodules/protocols/index.js:72` |
| Duration | 7019ms |

**Evidence — waterfall (condensed):**

```
astroshop ingress          3039ms  ✓   page request completed fine
  frontend GET /api/images 7129ms  ✗   image fetch sub-request fails
    image-provider Lambda  7019ms  ✗   Lambda fails
      DynamoDB:GetItem        5ms  ✓
      S3:HeadObject          50ms  ✓
      Image resizing       5999ms  ✗   ← retry loop here
      S3:PutObject          927ms  ✓
```

**Initial root cause stated:** DynamoDB rate throttling — Lambda hit DynamoDB capacity limits,
AWS SDK retried until timeout.

**Narration quality:**
- Exception message landed verbatim before commentary ✅
- Peak moment staging followed: exception first, then explanation, then waterfall ✅
- Waterfall condensed to key hops; causality (frontend OK, image path broken) stated explicitly ✅
- Deep link: Distributed Tracing / failing spans on image-provider ✅

**Issue — root cause incomplete:** The `SlowDown` exception was identified as the proximate
mechanism (AWS SDK retry loop), but the engine did not query for deployment events on the
image-provider service. The broken-images scenario has no deployment beat, so the upstream
cause (a code regression that introduced the throttle-triggering behaviour) was not surfaced.

User was later shown a root cause from another SRE agent describing a GitHub Actions deployment
regression. Engine acknowledged the gap, re-queried, and updated the diagnosis ✅ (see
"Ad-hoc deployment investigation" below).

---

## Beat 03 — The Humans (peak moment)

**User:** "yes, I want to see the users"

**Query:** `beat-04-affected-sessions.dql` — ran cleanly, 6 records ✅

**Evidence:**

| Country | Sessions | With replay |
|---|---|---|
| CZ | 1 | 1 |
| IE | 1 | 1 |
| JP | 1 | 1 |
| KR | 1 | 1 |
| MX | 1 | 1 |
| US | 1 | 1 |

6 sessions, 6 countries, 100% replay coverage.

**Narration quality:**
- 100% replay rate flagged as the key finding, not the session count ✅
- Replay framed concretely: which images loaded, which showed broken placeholder, whether
  users gave up or kept shopping ✅
- Genuine open question posed: did the UI give visual feedback, or did images silently fail? ✅
- Deep link: Error Inspector — affected sessions ✅

---

## User follow-up — population discrepancy (6 vs 269)

**User:** "now you said 6 users? in the beginning you said 269. Did you make a mistake?"

**Engine response:** Correctly explained two distinct populations without prompting:
- **269** — Davis `affected_users_count`: everyone who experienced the slowdown during the
  incident window (slow or eventually-resolved images)
- **6** — `user.sessions` where `error.http_5xx_count > 0`: sessions that received a hard 5xx,
  meaning the Lambda exhausted retries and returned an error

Both numbers accurate; they measure different populations. Engine did not conflate them ✅

---

## Ad-hoc deployment investigation (out-of-scenario, user-driven)

### Round 1 — "show me the exact commit"

**Engine initial response:** Stated there was no commit to show — the degradation was a
DynamoDB capacity issue, not a code regression. **This was incorrect.** Engine stopped at the
mechanism without querying for deployment events.

### Round 2 — external root cause presented

**User provided** a root cause from another SRE agent:
> "A GitHub Actions deployment of the image-provider-live Lambda function introduced a
> regression causing severe response time degradation — from 28ms baseline to ~5.4 seconds
> (19,178% deviation). Impacted 367 users."

**Engine response:** Acknowledged the gap, queried deployment events on
SERVICE-5A0CD2879D2F37BE ✅

**Deployment events found:** 7 `CUSTOM_DEPLOYMENT` events from `Github Actions for Image lambda
deployment`, starting at **03:02 UTC** (2 minutes before Davis fired at 03:04). However, the
`commit` and `git_url` fields were **null** on all 7 records.

**Engine stated:** "No path to the commit — commit and git_url fields came back null."

### Round 3 — user pointed to event.description

**User:** "but it's a grail event. it's in the event.description field in dynatrace"

**Engine:** Queried again with `event.description` included. Found on the first deploy:

> "Image processing problem trigger from [PR](https://github.com/Dynatrace/opentelemetry-demo-gitops/commit/16b26d41d0848cf1d9cd1814a4924d2cbcb81b22)"

Commit `16b26d41`, `Dynatrace/opentelemetry-demo-gitops` ✅

### Round 4 — "show me the commit"

Engine fetched the GitHub commit and surfaced the one-liner:

```diff
- if (exists !== true) {
+ if (exists !== 'true') {
```

`image-provider/src/src/getProductImage.js`, inside `ensureTargetImage()`. Boolean `true`
changed to string `'true'` — `true !== 'true'` is always `true` under strict equality, so
the "image is missing" branch fires on every call. Lambda ran the full resize operation on
every request instead of returning a cached result. That's the 6 seconds.

---

## Issues to Fix

### 1. broken-images scenario is missing a deployment beat

The scenario has beats for blast radius, failing spans/waterfall, and affected sessions — but
no beat for deployment events. Payment-failure has `beat-02-deployment-events.dql`; broken-images
has nothing equivalent. Without it, the investigation naturally terminates at the proximate
mechanism (SlowDown exception) without surfacing the upstream code regression.

**Fix:** Add a deployment beat (`beat-02-deployment-events.dql`) to broken-images, analogous
to payment-failure's beat-02. The `event.description` field must be included in the query
since `commit` and `git_url` fields are null on the GitHub Actions deployment events for this
service.

### 2. commit/git_url fields null on GitHub Actions deployment events

The GitHub Actions pipeline for image-provider registers the commit reference in
`event.description` as a markdown link, not in the dedicated `commit` / `git_url` fields that
payment-failure's `beat-02-deployment-events.dql` relies on. A future scenario query for this
service must include `event.description` or the commit is not recoverable from the event record
alone.

### 3. Engine stated "no path to commit" incorrectly

When `commit` and `git_url` came back null, the engine concluded the commit was unreachable
and required a user push to check `event.description`. The engine should not assume a null
`commit` field means no commit reference exists — description fields should be checked before
declaring the trail cold.

---

## What Worked Well

- Survey triggered correctly on "are there any open issues"; two scenarios presented cleanly ✅
- Past-tense `live_recent` framing for both scenarios in the survey ✅
- Beat-01: owning team (Team-UI) named from live data; Davis characterised correctly as
  degradation (not outage) ✅
- Beat-02: exception message landed verbatim; peak moment staging followed; waterfall causality
  (frontend OK, image path broken) stated explicitly ✅
- Beat-03: 100% replay rate surfaced as the hook; replay framed concretely, not as a footnote ✅
- 6 vs 269 population discrepancy explained clearly and correctly without prompting ✅
- When challenged on root cause, engine acknowledged the gap honestly and re-queried rather
  than defending the incorrect diagnosis ✅
- GitHub commit fetched and characterised correctly: type mismatch, business-logic regression,
  one-character revert ✅

---

## First Run of broken-images Scenario

This is the first full test of the broken-images scenario end-to-end. The scenario structure
works for the three scripted beats. The missing deployment beat is the primary gap — without
it, the investigation produces a technically accurate but incomplete root cause. The fact that
the engine updated its diagnosis when challenged is correct behaviour; the goal for the next
iteration is to surface the deployment evidence within the scripted beat loop rather than
requiring user correction.
