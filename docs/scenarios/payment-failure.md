# payment-failure: stable entity IDs and debugging notes

## Stable entity IDs (safe to hardcode in queries and deep links)

| Name | Entity ID | Type |
|------|-----------|------|
| astroshop-payment (playground) | SERVICE-531CE26849E95EC1 | Service (root cause) |
| astroshop-payment (demo-live) | SERVICE-E9CB57C5D00C3626 | Service (root cause) — this scenario runs on both tenants |
| astroshop-checkout | SERVICE-5ACC60E0079F8E6D | Service (downstream) |
| Charge endpoint | (filter `endpoint.name == "Charge"`) | The failing endpoint |
| segment | Apy24Rcu0cO | Filter segment used in deep links — **playground only**; demo-live has none, so `{{PROBLEM_SEGMENTS}}` is empty there |

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

## The Assist prompt, retired as a deep link (2026-11-05)

Beat 2 used to link `dynatrace.davis.copilot/ask-question` with an "Explain what happened in the problem
…" prompt, labelled "Explain with Dynatrace Intelligence". Testrun 14 found it opens the assistant
rather than a view, and `docs/AUTHORING.md` step 5 fails a link that opens a chat; relabelling it was a
compromise that left the checklist and the scenario disagreeing. Beat 2 now links the problem record,
where the deploy events are correlated. The intent URL, if anyone wants it by hand:

```text
https://<host>/ui/intent/dynatrace.davis.copilot/ask-question#%7B%22prompt%22%3A%22Explain%20what%20happened%20in%20the%20problem%20with%20id%20<problem-id>%2C%20why%20it%20happened%2C%20and%20actionable%20steps%20to%20remediate%20it.%22%2C%22execute%22%3Atrue%7D
```
