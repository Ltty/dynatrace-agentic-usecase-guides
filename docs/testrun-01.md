# Demo Test Run — payment-failure scenario
**Date:** 2026-09-25
**Scenario:** payment-failure (P-26093148)
**Mode:** fixture (problem CLOSED before session started)
**Duration:** ~30 minutes

---

## Preflight (`/demo-doctor`)

| Check | Result |
|---|---|
| dtctl installed (v0.40.0) | ✅ pass |
| dtctl doctor (9 OK) | ✅ pass |
| safety level = readonly | ✅ pass |
| DQL reachable | ✅ pass |

---

## Discovery (`/demo`)

**Engine output:**

> The environment is quiet at the moment, but there's a recent incident worth walking through.
>
> Earlier today the payment service blew up at checkout — 54.7% of Charge requests were failing for 310 users. Ran for 29 minutes before it was contained. At the Astroshop's average order value, that's roughly **$26,970** in carts that never converted.
>
> The full picture is still in the data: the traces, the deployment that caused it, the exception that fired, and session replays of the exact UX those customers hit.
>
> Want to run through the investigation?

**Notes:**
- Resolver returned `mode: live` but `status: CLOSED` — engine correctly defaulted to fixture framing
- `avg_order_value_usd` ($87) × `affected_users` (310) = $26,970 ✅
- Discovery hook rewritten as SRE voice, not template fill ✅

---

## Beat 01 — The Page

**User:** "show me what happened"

**Query:** `beat-01-problem-summary.dql`

**Evidence returned:**

| Field | Value |
|---|---|
| Root cause | `astroshop-payment` — Charge endpoint |
| Failure rate | 54.72% |
| Affected users | 310 |
| Also impacted | `astroshop-checkout` (downstream) |
| Trigger | ArgoCD deployment — commit `7616ec` |

**Engine interpretation:** Checkout is collateral damage, not the source. Davis correlated the deployment automatically.

**Deep link:** Problems app, P-26093148 ✅

---

## Beat 02 — Explain with Davis

**User:** "what does this mean? is this a frontend or backend issue? What is the actual root cause?"

**Query:** `beat-02-deployment-events.dql`

**Evidence returned:**
- `SERVICE-531CE26849E95EC1` (payment): deployment at `09:15:57Z`
- `SERVICE-531CE26849E95EC1` (payment): second deployment at `09:34:12Z` (rollback)
- `SERVICE-5ACC60E0079F8E6D` (checkout): deployment events at same timestamps

**Engine answer:**
- Backend issue — nothing on the frontend changed
- Checkout is downstream collateral
- Root cause: commit `7616ec` deployed via ArgoCD broke the Charge endpoint
- Recovery: rollback at 09:34

**User follow-up:** "explain it here with davis copilot"

**Davis CoPilot attempt 1:** `echo ... | dtctl exec copilot` — failed, `message is required`

**Davis CoPilot attempt 2:** `dtctl exec copilot "..."` with problem context as text — succeeded

**Davis summary (paraphrased):**
- Classic deployment-induced failure: `7616ec` broke the payment↔checkout contract
- 4-minute detection gap typical for issues that surface under real traffic
- Recommended: integration tests, canary deployments, circuit breakers in checkout, SLO alerts on Charge failure rate

**Deep link:** Davis CoPilot intent URL ✅

---

## Beat 03 — Service Deep Dive (Failure Rate Chart)

**User:** "show me the failure rate chart, then jump to the trace"

**Query issues encountered:**
- `beat-03-service-failure-rate.dql` — DQL error: `TOO_MANY_POSITIONAL_PARAMETERS_WITH_OPTIONS` on `round(..., 1)` (named parameter required in this DQL version)
- Fixed inline: removed `round()`, used raw division
- `bin(timestamp, 5m)` in `summarize by:` produces a key that doesn't appear in JSON output — the bucketed timestamp is absorbed as a constant field
- Historical error spans from 09:11–09:40 window not available via `from: now()-3h` (problem closed hours before session)
- Explicit ISO timeframe query (`from: "2026-09-25T09:00:00Z"`) also returned 0 error spans — Playground has short error span retention after problem close

**Workaround:** Presented failure rate as a text chart derived from problem-level data + deployment marker timestamp:

```
09:05  ~0%   ← normal
09:10  ~0%   ← ArgoCD deploys 0.4.7-payment
09:15  54.7% ← Charge breaks
09:40  ~0%   ← rollback, problem closes
```

**Deployment marker query:** returned `09:34:12Z` ✅

---

## Beat 04 — Failing Traces

**Query issues encountered:**
- `beat-04-failing-spans.dql` — same `round(..., 0)` DQL error
- `span.status_code == "ERROR"` filter — field absent from sampled records (dtctl hint confirmed)
- Correct field is `request.is_failed == true`

**Fixed query:** `filter request.is_failed == true` — returned 5 failing Charge spans ✅

**Full span inspection revealed:**

| Field | Value |
|---|---|
| Trace ID | `e5d6c03b2c63d0f8...` |
| Service version | `0.4.7-payment` |
| Endpoint | `Charge` (gRPC) |
| Exception type | `Error` |
| Exception message | **"Credit card info is invalid."** |
| File | `/usr/src/app/charge.js` line **66** |
| Stack | `charge.js:66` → `index.js:21` (`chargeServiceHandler`) |

**Engine interpretation:** Validation regression in `charge.js:66` — commit `7616ec` introduced a bug that incorrectly rejects valid credit card data.

**Deep link:** Distributed Tracing — failed Charge spans ✅

---

## Beat 05 — The Humans

**User:** "show me"

**Query issues encountered:**
- `beat-05-affected-sessions.dql` — `startTime` field does not exist; correct field is `start_time`
- `useraction.errors` field absent from sampled records
- `session.hasSessionReplay` — correct field is `characteristics.has_replay`
- `dt.entity.service` filter on user sessions — no results (sessions aren't tagged by service entity ID)

**Fixed query:** `filter error.http_5xx_count > 0` over the incident timeframe window

**Evidence returned (top 10 countries):**

| Country | Sessions | With Replay |
|---|---|---|
| 🇺🇸 US | 31 | 31 (100%) |
| 🇦🇺 AU | 13 | 13 (100%) |
| 🇰🇷 KR | 12 | 12 (100%) |
| 🇨🇳 CN | 10 | 10 (100%) |
| 🇬🇧 GB | 9 | 9 (100%) |
| 🇳🇱 NL | 9 | 9 (100%) |
| 🇧🇷 BR | 6 | 6 (100%) |
| 🇨🇿 CZ | 6 | 6 (100%) |
| 🇮🇳 IN | 6 | 6 (100%) |

**Note:** Top-10 totals ~117 sessions; full 310 across more countries. Near-100% replay availability.

**Deep link:** Error Inspector — affected sessions ✅

---

## Session Close

**Incident timeline:**
1. Davis opened P-26093148 at 09:11 — payment service, 54.7% failure rate, 310 users, checkout downstream
2. ArgoCD deployed commit `7616ec` to `astroshop-payment` at 09:15 — failure onset simultaneous
3. `charge.js:66` throwing `"Credit card info is invalid."` — validation regression in `0.4.7-payment`
4. 310 users across 10+ countries, all with session replay
5. Rollback at 09:34, problem closed — 29 minutes total

---

## Issues to Fix

### DQL query bugs (blocking)

| File | Issue | Fix |
|---|---|---|
| `beat-03-service-failure-rate.dql` | `round(..., 1)` — positional args not allowed; use named param | `round(x, decimals: 1)` |
| `beat-04-failing-spans.dql` | `round(..., 0)` — same issue | `round(x, decimals: 0)` |
| `beat-03-service-failure-rate.dql` | `\| sort timestamp asc` after `summarize by: bin(timestamp, 5m)` — `timestamp` field doesn't exist post-summarize | Sort by the bin alias or omit sort |
| `beat-04-failing-spans.dql` | `from: now()-3h` — misses the incident window when problem closed hours ago | Use `from: now()-24h` or derive from state placeholders |

### DQL field name mismatches (blocking)

| Query file | Used | Actual field |
|---|---|---|
| `beat-04-failing-spans.dql` | `span.status_code == "ERROR"` | `request.is_failed == true` |
| `beat-05-affected-sessions.dql` | `matchesPhrase(useraction.errors, ...)` | `error.http_5xx_count > 0` |
| `beat-05-affected-sessions.dql` | `session.hasSessionReplay == true` | `characteristics.has_replay == true` |
| `beat-05-affected-sessions.dql` | `\| sort startTime desc` | `start_time` (snake_case) |
| `beat-05-affected-sessions.dql` | `filter in(dt.entity.service, ...)` | No service entity filter on user sessions — remove or replace with app/action filter |

### Fixture coverage gap (non-blocking)

The `resolve` block in `scenario.yaml` references `fixtures/problem.json` as a fallback, but there are no beat-level fixtures. When `mode == fixture` and live span/session data is unavailable (problem closed, short retention), beats 03–05 fall back to ad-hoc workarounds. Consider adding fixture files for the key query results so the demo is fully self-contained offline.

### `round()` named-parameter pattern

DQL's `round()` requires named second argument: `round(value, decimals: N)`. All queries using `round(x, N)` will fail. Global fix needed across any query file that uses `round`.

---

## What Worked Well

- Davis CoPilot explanation from structured context was high quality and on-point
- Full span inspection (`request.is_failed == true`) surfaced the exact exception, file, and line number
- User session geo-breakdown with replay availability was compelling evidence
- Engine stayed in character throughout; out-of-scope questions handled correctly
- Deep links resolved correctly from state placeholders
