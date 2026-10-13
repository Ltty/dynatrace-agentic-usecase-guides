# Demo Test Run 13 — payment-failure, user-steered (`/demo`, explore delivery)

**Date:** 2026-10-08
**Runtime:** `/demo` — `demo-agent` instructions + `investigating-playground-incidents` skill, mapped onto
Claude Code by `skills/local-runtime/SKILL.md` (dtctl in place of `execute-dql`). Companion to
[testrun-13-guided.md](testrun-13-guided.md): same incident, but the user picked every step and the walk-through
was never requested.
**Model:** Sonnet 5.5
**Scenario:** payment-failure (P-2610781)
**Mode:** `live_recent` (problem CLOSED; started 2026-10-08 09:11:00 UTC, ended 09:46:00 UTC; resolver ran 11:31:34 UTC)
**Delivery:** `explore` throughout
**Elapsed (first payment query → last evidence query):** 3 minutes 19 seconds (11:32:06 → 11:35:25 UTC). Derived from
the timestamps embedded in the queryIds (UUIDv7), checked against the one `queried_at` that was returned (beat 5:
11:32:38.414 against 11:32:38.393 from its queryId). The handoff turn ran no query, so the clock stops at the last
evidence query.
**Entry path:** `/demo` (empty, greeting) → "what's going on?" (survey, three findings) → "payment" (problem record) →
"Show me impacted customers" (sessions) → "what happened before 09:11" (deployments) → "let's have a look at the
failure rates to confirm if the commit was the issue" (failure rate + markers) → "I want to see the actual
exception based on the traces" (exception + trace) → "let's write the handoff" → this file request

The values marked **verify** are the ones I summed or derived by hand. Everything else was read from a result.

---

## What this run tests

Run 13 (guided) tests the walk-through. This run is the other half: a user who knows what they want and jumps
around. It checks front-running (customers before the change), a user asking the agent to "confirm" a cause, and
the session close when the last evidence turn is not the sessions beat.

---

## Startup and survey

- Empty message treated as a greeting; the skill's greeting used verbatim ✅
- **User:** "what's going on?" → status line exactly "Checking for open issues." ✅
- `python tools/preflight.py dtctl-path` printed `dtctl`; every query used it bare with `--context playground` ✅
- Three primary resolvers ran in parallel; the disk-cpu primary returned zero rows and the **file's fallback ran
  whole** ✅ (no resolver, fallback or empty result mentioned to the user)

| | payment-failure | broken-images | disk-cpu-cascade |
|---|---|---|---|
| Problem | P-2610781, CLOSED | P-2610759, CLOSED | P-26092140, ACTIVE |
| Impact (problem record) | 350 affected users | 273 affected users | 2 affected entities |
| Duration | 35 min | 34 min | 23 days 13 hours (still open) |
| Ended | 106 min ago, said "about 2 hours" | 474 min ago, said "about 8 hours" | — |

- Payment: "roughly $30,450" (350 × $87, **verify**). Images framed as a slowdown with no revenue figure. Host framed
  as still open ✅
- One line per finding, then a pick question and the exact closing sentence "Or I can take you through the whole
  thing, start to finish." ✅ The user picked "payment", so the walk-through was never taken up.
- Run 12 and 13 (guided) point still open: disk-cpu is documented as dev-tenant only and surfaced on `playground`
  through the fallback, with `root_cause` absent. The survey line named the `/data` disk from the problem
  description.

---

## Turn 1 — "payment" (problem record)

**Query:** `fetch dt.davis.problems` pinned to the problem ID. One row.

| Field | Value |
|---|---|
| Root cause | astroshop-payment, Charge endpoint |
| Affected users | 350 (problem record) |
| Owning team | Team-Financial-Services |
| Window | 09:11:00 → 09:46:00 UTC |

- Read stated first, "checkout is listed as affected, but the root cause points at payment" ✅ (run 12's "checkout
  calls payment" overreach did not recur)
- The ArgoCD sync on the payment pod in the description was called "a lead, not yet a cause" ✅
- Stamp, deep link and a two-way choice at the end ✅

## Turn 2 — "Show me impacted customers" (front-run to sessions)

**Query:** `user.sessions` with `error.http_5xx_count > 0` by country, no limit. 16 rows.

- 160 sessions with 5xx, 148 with replay (**verify** both sums). US 39/39, no country 17/5, NL 15/15, AU 14/14,
  CN 12/12, then smaller rows.
- The 12 sessions without replay are all in the no-country row (**verify**: 17 − 5) ✅
- Said "16 rows: 15 countries plus one row with no country", never "16 countries" ✅
- Said plainly that the 160 sessions are a different population from the 350 users ✅
- Finding alone on its own line before the table; replay made concrete with the "did the UI tell them?" question ✅
- Ended on "we still don't know what broke these checkouts", then the choice ✅

## Turn 3 — "what happened before 09:11" (deployments)

| Commit | First deploy (UTC) | Syncs |
|---|---|---|
| c590ec | 09:07:14 | 10 |
| dcca03 | 09:37:18 | 2 |

- c590ec landed "about 4 minutes" before the problem opened (09:07:14 vs 09:11:00 is 3 min 46 s) ✅
- Owner `team-astroshop` vs service owner Team-Financial-Services named as two different names ✅
- dcca03 called a second commit, "not yet shown to be a second regression" ✅
- Said the failures-start-with-it check had not been run yet ✅

## Turn 4 — "have a look at the failure rates to confirm if the commit was the issue"

**Queries (2, parallel):** Charge failure rate per 5-minute bucket; deployment markers.

| Bucket (UTC) | Failures / calls | Rate |
|---|---|---|
| 09:00 | 0 / 59 | 0% |
| 09:05 | 12 / 61 | 19.7% |
| 09:15 | 28 / 60 | 46.7% |
| 09:30 | 33 / 54 | 61.1% |
| 09:35 | 11 / 58 | 19% |
| 09:40 onward | 0 per bucket | 0% |

- The user asked to "confirm" the commit as the cause. The reply called it **a timing match** and said the telemetry
  shows when, not why ✅ (data-only rule held under a leading ask)
- Described as a ramp, not a step ✅ (run 13 guided issue 7 applies to the beats file, not to the agent)
- Said 5-minute buckets can't place the first failure inside the 09:05 bucket ✅

## Turn 5 — "I want to see the actual exception based on the traces" (peak)

**Queries (2, chained, no text between):** exceptions over the window, then the per-service summary for trace
`4cb4b105bd18c87e58c3eedec8c7f3eb` (`toUid()` used).

Exception: Sorry, we cannot process American Express credit cards. Only Mastercard or Visa are accepted.

- `/usr/src/app/charge.js` line 77, 150 failed spans (a span count, not users), one distinct message ✅
- Exception alone on its own line, blank line, then the chain and the sentence that one call originates the failure ✅

```text
ingress → frontend → checkout → payment   failed (origin: payment)
checkout also called: cart, catalog, currency, shipping, quote, flagd — all clean
```

- First failure 09:07:06 (8 s before c590ec's sync event), last 09:36:55 (23 s before dcca03's), problem opened
  09:11:00. The detection gap was stated as a fact, not as time spent blind ✅
- Intent left to Team-Financial-Services ✅ (the "validation regression" overreach from runs 10 and 11 did not recur)

## Turn 6 — "let's write the handoff" (session close)

Delivered as a handoff block for Team-Financial-Services and team-astroshop: status, root cause, both commits, the
exception, 150 failed spans, failure-rate before/after, 350 users (problem record), 160 sessions (different
population), the $30,450 estimate with its arithmetic, then what the data does and doesn't show, and one ask.

- Populations labelled in every row ✅; dcca03 not called the fix ✅
- **Issue 1 (user-flagged):** the close ended "I can't give a measured page-to-root-cause time here, so I'm leaving
  the number out". That is a narrated omission and "I can't". The skill says drop "in [X] minutes" without a
  measured X; it does not say to announce it. The user asked for it removed.
- **Issue 2:** the elapsed time could not be computed. The close step is "last beat's `queried_at` minus the
  resolver's `queried_at`", but only the sessions query returns `queried_at`, and here sessions was turn 2. A user
  who steers has no reason to end on beat 5. Suggest returning `queried_at` from every beat's main query, or
  stating that the close takes the latest `queried_at` seen.
- **Issue 3:** no "Written for:" line on the handoff, as in run 12. Same open decision (run 12 issue 9).

---

## Wrap-up: what Dynatrace did for us

This is the summary I would give a manager who picks up the phone after the page. It covers the stretch from "look
into payment" to the recap.

> **Payment checkouts failed for 35 minutes today. We had the cause, the change behind it, the exact error and the
> customers it hit in about three and a half minutes of querying.**
>
> Between 09:11 and 09:46 UTC, card payments failed in checkout. Dynatrace's problem record counted 350 affected
> users, roughly $30,450 in abandoned carts at the scenario's $87 average order, and it named the failing service
> and the team that owns it, Team-Financial-Services, without anyone having to ask around.
>
> **What changed.** One deployment event, commit c590ec by team-astroshop, landed at 09:07:14 UTC. The payment
> charge call went from 0 failures in 59 calls (09:00 window) to 12 in 61 within the next window, and climbed to 61.1%
> by 09:30. After a second commit, dcca03, at 09:37:18, the next window and every one after it show 0 failures. What
> either commit changed is in the diff and for the owning team to read.
>
> **What exactly broke.** The trace names it: the payment service itself rejects the request with "Sorry, we cannot
> process American Express credit cards. Only Mastercard or Visa are accepted." at `charge.js` line 77. In the
> same request, cart, catalog, currency, shipping, quote and flagd were all clean. One service originates the failure
> and everything upstream relays it.
>
> **Who it hit.** 160 customer sessions saw server errors, from 15 countries plus 17 sessions with no country
> recorded, and 148 of the 160 have a session replay. The replay shows what a customer saw at checkout, which no
> metric can.
>
> **How fast.** Dynatrace opened the problem about four minutes after the first failed request (09:07:06 vs 09:11:00).

### How it was done

One platform answered five different kinds of question, with no tool switching and no log grepping:

| Question | Where the answer came from | Evidence query |
|---|---|---|
| What is broken, how big, who owns it? | The problem record | 1 |
| Who did it hit? | Real-user sessions with replay | 1 |
| What changed? | Deployment events on the same services | 1 |
| Did the change line up with the failures? | Request spans, failure rate per window | 2 |
| What exactly failed? | Exception and trace across the whole request | 2 |

- 7 evidence queries plus 4 at the survey (**verify**): about 10.9 million records scanned and 221 ms of total
  execution time across the evidence queries (**verify**: sum of the seven stamps).
- A closed problem, 2 hours old, was fully investigable. The data was all still there ("the full picture is still
  here").
- The deployment events, the problem, the trace and the user sessions all lined up on the same timeline without
  anyone joining them by hand.
- Everything the telemetry could not say was said as such: what the commits changed, whether the card rule was
  intended, and whether dcca03 was the fix. Those go to the owning team.

---

## What worked well

- Greeting, survey, exact status line, no resolver or fallback mentions ✅
- All tool calls before narration in every turn; every turn ended on text ✅
- The user jumped to customers first; the agent followed, re-anchored on "we still don't know what broke these
  checkouts" and folded nothing in that wasn't needed ✅
- A leading "confirm the commit" ask answered with a timing match and the limits of the data ✅
- Populations kept apart (350 users, 150 failed spans, 160 sessions) and the null-country row never counted as a
  country ✅
- Proof stamps carried the full queryId in every evidence turn ✅
- Persona held: "we", no "Davis"/"CoPilot", walk-through never named ✅

---

## Proof-stamp queryIds (for verification)

| Query | queryId |
|---|---|
| Payment resolver (survey) | `01a11b48-6ff8-7497-acb1-524a16e9f03d` |
| Image resolver (survey) | `01a11b48-7733-7807-b639-2c43b099bfa9` |
| Disk-cpu primary (survey, empty) | `01a11b48-7f11-79b4-87d1-f438f954f501` |
| Disk-cpu fallback (survey) | `01a11b48-a065-7f86-ae72-bbe5fd06df32` |
| Problem record | `01a11b48-ec61-7beb-bf9e-3f8e98df9960` |
| Sessions with 5xx | `01a11b49-6979-79c6-b32e-03033d4ae78e` |
| Deployments | `01a11b49-c008-7723-ba9b-6e5539afe747` |
| Charge failure rate | `01a11b4a-5889-7ee7-b679-c0108f08e8e9` |
| Deployment markers | `01a11b4a-625e-7556-a355-a8103df9a01d` |
| Exceptions | `01a11b4b-dab3-71b7-b8ec-faac434d9c38` |
| Trace summary | `01a11b4b-f3d8-7818-8ce3-9c118d59bd36` |
