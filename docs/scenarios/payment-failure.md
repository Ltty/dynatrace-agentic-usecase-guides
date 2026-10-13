# payment-failure: stable entity IDs and debugging notes

## Stable entity IDs (safe to hardcode in queries and deep links)

| Name | Entity ID | Type |
|------|-----------|------|
| astroshop-payment | SERVICE-531CE26849E95EC1 | Service (root cause) |
| astroshop-checkout | SERVICE-5ACC60E0079F8E6D | Service (downstream) |
| Charge endpoint | (filter `endpoint.name == "Charge"`) | The failing endpoint |
| segment | Apy24Rcu0cO | Filter segment used in deep links |

## What rotates every problem cycle (never hardcode)

problem id / display id, affected-user count, exception message text, exception line number,
deployment commit SHA, incident timestamps.

## Resolver notes

The problem fires as a cluster of near-duplicate Davis problems.
`dt.davis.is_duplicate == false` selects Davis's merged umbrella instance — its `event.name`
is "Multiple application problems", not the specific symptom name.
Beat 1 is pinned to `{{PROBLEM_ID}}` (resolved at session start) rather than re-sorting by
timestamp, to avoid stale-count issues when the resolver looks back 48h but beat 1 only
searched 24h.
