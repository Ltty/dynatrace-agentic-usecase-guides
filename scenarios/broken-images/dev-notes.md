# broken-images: stable entity IDs and debugging notes

## Stable entity IDs (safe to hardcode in queries and deep links)

| Name | Entity ID | Type |
|------|-----------|------|
| image-provider-playground in us-east-1 | SERVICE-5A0CD2879D2F37BE | Service (root cause Lambda) |

## What rotates every problem cycle (never hardcode)

problem id / display id, affected-user count, exception message text, exception line number,
incident timestamps, trace ID, session count, countries.

## Resolver notes

Pattern fires daily ~03:04 UTC as a cluster of near-duplicate Davis problems (response time
degradation, LCP increase, user action duration increase). `dt.davis.is_duplicate == false`
selects Davis's merged umbrella instance — its `event.name` is "Multiple application problems".

Resolver verified 2026-10-01: returns P-261012 (CLOSED, 269 affected users).

## Exception shape (observed 2026-10-01, may rotate)

The current exception is `SlowDown / "Please reduce your request rate."` from the AWS SDK
(`@aws-sdk/core/dist-cjs/submodules/protocols/index.js:72`). This is a DynamoDB rate-throttle.

The DEM Act 3 kit documents `AccessDeniedException / dynamodb:GetItem` — that exception may
have rotated. Always read the live exception text from spans; don't assume either shape.

## Trace shape (verified 2026-10-01)

22 spans in a representative failing trace. Key structure:
- Top-level page request (astroshop frontend): ~3039ms, OK — the page itself loaded
- Image fetch sub-request (frontend GET): ~7129ms, FAIL
  - image-provider Lambda: ~7019ms, FAIL (SlowDown exception)
    - 4 internal Lambda sub-calls: all OK, ≤927ms
    - 1 failing Lambda sub-call: ~7018ms, FAIL (the DynamoDB retry loop)
      - 3 more sub-calls: all OK, ≤6960ms

The Lambda spends its entire execution time in DynamoDB retry attempts before failing.

## Beat DQL status (all verified live 2026-10-01)

| Query | Records returned | Notes |
|-------|-----------------|-------|
| find-problem.dql | 1 | P-261012, 03:04 UTC |
| beat-01-problem-summary.dql | 1 | owning_team = Team-UI |
| beat-02-failing-spans.dql | 1 | Only 1 failing span captured per incident cycle |
| beat-03-trace-waterfall.dql | 22 | Full trace; render_waterfall.py condenses to ~5 key rows |
| beat-04-affected-sessions.dql | 6 | 6 countries, all sessions have replay |

## Note on span count

beat-02 returns only 1 failing span for today's incident cycle, despite Davis reporting
~269 affected users. The Lambda instrumentation captures sampled spans; the user-impact
count comes from RUM/session data, not span count. This is expected — don't try to explain
the discrepancy in the beat reveal, just show what the span says.
