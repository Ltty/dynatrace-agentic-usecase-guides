# Demo Test Run 19 — the sanity-check matrix: every scenario, both modes

**Date:** 2026-11-05
**Runtime:** in-session subagents playing `demo-agent` against the repo's own files
(`docs/DYNATRACE-SKILL.md` → "Test" → in-session evals), `dtctl` for data.
**Model:** Sonnet 5.5
**Environments:** `demo-live` (`guu84124`), and `playground` for `broken-images` via `DTCTL_CONTEXT`.
Both `readonly`.
**Prompted by:** a full sanity check and housekeeping request, with two direction changes — one audience
for both modes, and presentation opening on the executive summary.

Every value below was read from a result or from a file in the repo.

---

## Coverage, stated honestly

The brief asked for three runs of each scenario in each mode. This run is **not** that: it is the first
pass, roughly one run per scenario per mode, with `k8s-cpu-throttling` run twice in explore because it
was the control for the fixes.

| Scenario | Environment | Explore | Presentation |
|---|---|---|---|
| `k8s-cpu-throttling` | demo-live | 2 (one pre-fix, one post-fix) | 1 |
| `lambda-iam-denied` | demo-live | 1 | — |
| `payment-failure` | demo-live | — | 1 |
| `broken-images` | playground | 1 | — |
| `cloud-observability` | demo-live | n/a — presentation only by design | 1 |

The remaining runs are owed. What this pass bought was seven findings, five of them fixed the same day,
and one retraction.

---

## Findings

| # | Finding | Where it came from | Outcome |
|---|---|---|---|
| 1 | **The turn ended twice** — readiness cue, then proof stamp, then deep link, then a second cue — on *every* turn of one run, and not once in another, from identical rules | k8s explore run 1 vs lambda explore | **Fixed.** The ending is now the final element after the link; part 4 of the turn shape names the next step and explicitly does not cue. Verified in k8s explore run 2: one ending per turn, including at the option pivot. |
| 2 | **No proof stamp at all** on one turn | lambda explore turn 1 | Not reproduced in later runs. Left under observation. |
| 3 | A table rendered with an empty header row (`\| \| \|`) | lambda explore turn 1 | Cosmetic, not acted on. |
| 4 | **Explore never printed the handoff block.** The close attached it to the walk-through and to an explicit request only, so a self-explore session ended with a timeline, a payoff line and a report path — and no owning team | the k8s explore close, read against `session-protocol.md` → "Session close" | **Fixed.** The handoff block is unconditional in both deliveries, and is named as the source of the report's `evidence` list. |
| 5 | Reports carry one evidence link | — | **Retracted; my error.** `grep -c` counts lines and the template emits the list on one line. Counted properly: `payment-failure` 5, `lambda-iam-denied` 4–5, `k8s-cpu-throttling` 3. No renderer fault. The real residue is that `window` is empty in all nine renders and the showcase reports are the thin ones (0–2 links). |
| 6 | **`payment-failure` shipped a deep link its own checklist fails.** Beat 2 opened `dynatrace.davis.copilot/ask-question` — an Assist prompt, not a view. `AUTHORING.md` step 5 fails a link that opens a chat; testrun 14 caught *this* link doing it, and relabelling it then left the checklist and the scenario contradicting each other | payment presentation run | **Fixed.** Beat 2 links the problem record, where the deploy events are correlated. The intent URL is preserved in `docs/scenarios/payment-failure.md`. Its label also collided with beat 1's and is differentiated. |
| 7 | **An internal field name said out loud:** "The route is where the request time actually went" | broken-images survey on playground | **Fixed.** The bookkeeping rule covered beat numbers; it now covers `Route`, `Requires`, `approach`, `pull_line` and the rest. |

### Scale observation, not a defect

The showcase's beat 3 scanned **50,480,746 records** — 24 hours of spans on the image function. That is
the heaviest query in the framework by a wide margin; the cost track's bill query was deliberately tuned
from 12.7 GB down to 2.07 GB to avoid exactly this. The beat needs the service's real behaviour, so
this is recorded rather than changed.

---

## What the runs confirm is working

**The one-audience register.** Glossing on first use, in every scenario: "the time the slowest 1 in 20
requests exceeds", "an IAM role, the set of permissions it holds while it runs", "a security group,
which is the firewall rule set around it", "the ingress (the entry point for web traffic)", "DynamoDB,
the database holding product records". Meaning before mechanism, consistently.

**The data-only rule under pressure.** "A gap of two minutes is suggestive, not proof." The broker pair
returning identical figures called "one finding, not two" rather than double-counted. The showcase
saying its own estate count "says nothing about how any of it is doing" — declining the oversell at the
one point where a tour invites it.

**`Requires` earning its place.** Where one beat is unlocked the runs explain the forced order — "Until
we see where the time goes, the CPU numbers have nothing to be compared against" — instead of
manufacturing a menu. Where two are unlocked, both appear with a recommendation and a reason.

**Presentation's new opening.** Both presentation runs opened on the executive summary: the story in
time order, the timeline text block, owner, what broke, then the offer. Neither began stepping
unasked.

**The clearest causal demonstration of the session** was `broken-images`: resizes going from 0 to
essentially every request at the 04:00 bucket, median 22 ms → 3,953 ms, flipping back at the second
commit, then one slow request broken down to "Resize original product image — 6,216 ms of an 8,042 ms
request" with the shopper's browser waiting 9,670 ms. All of it still labelled as timing, not as the
diff.

---

## The handoff fix, verified

k8s explore run 2 reached its close after the fix and printed the block in the console:

```text
Incident handoff — P-26111707
What happened:  EasyTrade was slow for 94 people after the CPU limit on the broker-service container was cut from 600m to 300m.
When:           2026-11-05 03:04 to 03:35, 31 minutes (UTC)
Impact:         94 affected users (problem record)
Rate:           95th percentile 1664 ms on BrokerService and NotMiningBitcoin (the same 1927 root spans), against 169.8 ms on the next service down
Cause:          'cpu' in 'resources/limits' for container 'broker-service' changed from '600m' to '300m' at 03:02 UTC, restored to '600m' at 03:27 UTC
Goes to:        easytrade-broker-service in the easytrade namespace on eks-live, no owning team on the record
Evidence:       [three labelled links]
Still open:     Why the limit was cut, what the EasyTrade 1.1.1 version change did, and the right ceiling
```

Then the timeline, the payoff line, the way out, and
`reports/20261105T153708Z-demo-live-k8s-cpu-throttling.html`.

The console handover is the whole gain. The report was **not** affected: both the pre-fix and post-fix
renders carry three evidence links, which is further confirmation that finding 5 was a measurement
error and not a defect. The post-fix render carries two stat tiles where the pre-fix one carried three
— run variance, not a consequence of the change.

## The second close: `broken-images` on playground

Reached a complete close on the other tenant, with a four-link handoff block, and rendered
`reports/20261105T153736Z-playground-broken-images.html` — the first report ever produced on
`playground`. Checked for host leakage: **zero** occurrences of the demo-live host, every link on
`playground.apps`, and the playground-only `segments` parameter present. The environment registry and
`{{LINK_HOST}}`/`{{PROBLEM_SEGMENTS}}` resolve correctly per tenant.

Four stat tiles, each carrying its population label, and the two populations kept apart in the prose:
"This is a different population from the 363 affected users on the problem record… nothing in the data
ties a session to this function, so they aren't a count of the slowdown's victims."

## Still owed

- The rest of the matrix: two more runs of each scenario in each mode.
- Nothing on the handoff block: **verified**. See below.
- `window` has a documented mapping now but has never been populated in a render.
- Browser verification of the deep links on `demo-live` and `playground`.
