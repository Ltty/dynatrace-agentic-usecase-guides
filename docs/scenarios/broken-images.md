# broken-images: stable entity IDs and debugging notes

## Stable entity IDs (safe to hardcode in queries and deep links)

| Name | Entity ID | Type |
|------|-----------|------|
| image-provider-playground in us-east-1 | SERVICE-5A0CD2879D2F37BE | Service (root cause Lambda) |

## What rotates every problem cycle (never hardcode)

problem id / display id, affected-user count, response times and baseline in the problem description,
incident timestamps, commit SHAs, trace ID, session count, countries, durations.

## Resolver notes

Pattern fires daily around 03:04 UTC as a cluster of near-duplicate Davis problems (response time
degradation, LCP increase, user action duration increase). `dt.davis.is_duplicate == false`
selects Davis's merged umbrella instance — its `event.name` is "Multiple application problems".

## The incident shape (verified 2026-10-07 across the last 8 days)

It is a slowdown, not an outage. Every day at about 03:00 UTC a GitHub Actions deploy of the Lambda
(the regression) lands, re-deployed several times — once per affected resource. From then until a
second commit (the fix) lands about 30 minutes later:

- the Lambda's "Resize original product image" step runs on **every** request (resizes == requests,
  about 14,000 per cycle) instead of never — before the deploy, resized images are served from S3;
- the median `Invoke lambda /images/presign.` takes about 4 seconds instead of about 23 ms;
- the Lambda invocations are **not** marked failed, and DynamoDB (about 5 ms) and the S3 existence
  check (about 80 ms) are fast. The time is the resize (about 6 s) plus writing the result to S3.

Things that look like the story but are not stable:

- **A single sampled failed `GET` span** with the exception `SlowDown / "Please reduce your request
  rate."` (about 7 s of retries) exists on some days (seen 2026-10-01 and 2026-10-07) and not on
  others (2026-10-06). The beats must not depend on it. It is a symptom, not the cause.
- **`AccessDeniedException` on `dynamodb:GetItem`** fails thousands of spans every day, but at other
  hours, not in the incident window. The DEM Act 3 kit documents it; it is background noise here.
- **`error.http_5xx_count`** finds a handful of sessions (4 on 2026-10-07). The images return 200, so
  the affected population is measured with per-request RUM data in `user.events` instead (hundreds of
  real-user sessions with an image load over a second, nearly all with replay).

The first beat's problem description quotes the current response time against the baseline; read the
numbers from the result.

## Trace shape (verified 2026-10-07, 24 spans)

The slowest invocation's trace: ingress and frontend requests of about 8.5 s, then the image-provider
`GET` (about 8.2 s) and `Invoke lambda /images/presign.` (about 8.2 s). Inside it: DynamoDB `GetItem` (5 ms),
S3 `HeadObject` (80 ms), then `Resize original product image` (about 6.1 s) containing `Image resizing`
(about 6.0 s), and `S3:PutObject` (about 1.5 s). `render_waterfall.py` anchors on the longest leaf when no
span failed and marks it "most of the time".

## Beat DQL status (all verified live 2026-10-07)

| Query | Records | Notes |
|-------|---------|-------|
| find-problem.dql | 1 | P-2610664 |
| beat-01-problem-summary.dql | 1 | owning_team = Team-UI |
| beat-02-deployment-events.dql | 2 | regression and fix; commit parsed from `event.description` in DQL |
| beat-03-slowdown.dql | 15 | resizes vs requests and p50 per 5 minutes |
| beat-04-slowest-invocations.dql | 5 | producer for the waterfall |
| beat-04-trace-waterfall.dql | 24 | the chained trace |
| beat-05-affected-sessions.dql | 16 | countries; real users with a slow image load, joined to replay |
