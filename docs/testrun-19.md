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

| Scenario | Environment | Explore | Presentation | Closed run? |
|---|---|---|---|---|
| `k8s-cpu-throttling` | demo-live | 2 (one pre-fix, one post-fix) | 1 | yes, both |
| `lambda-iam-denied` | demo-live | 1 | 1 | yes |
| `payment-failure` | demo-live | 1 | 1 | yes |
| `broken-images` | playground | 1 | — | yes |
| `cloud-observability` | demo-live | n/a — presentation only by design | 1 | yes |

**Every scenario now has at least one run driven all the way to its close**, on both tenants, with the
handoff block in the console and an HTML report rendered. Evidence links per render, after the
fixes: payment-failure 4, lambda-iam-denied 5, cloud-observability 6, broken-images 4,
k8s-cpu-throttling 3.

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

## Findings 8 to 10, from the second pass

| # | Finding | Outcome |
|---|---|---|
| 8 | **The showcase handed over one link out of seven, by specification.** Its handoff block spelled Evidence as a single hardcoded line, `Cost explorer: [this beat's deep link]`. Since that block is what the report's `evidence` list is built from, every showcase render carried 0–2 links where incidents carried 3–5. The asymmetry sat in the renders for two days and read as a report problem; it was a scenario problem | **Fixed and verified.** Evidence is now every labelled link the session gave. The render went from **2 links to 6** (`20261104T132205Z` vs `20261105T162112Z`) |
| 9 | **The turn ending was described twice, in two positions.** Part 5 of the beat turn was "the readiness cue", inside the narration sequence, while the tail rule placed it after the deep link. One run cued-stamped-linked-cued; another put its options before the stamp and ended on the link, which the same file forbids. Opposite faults from identical rules | **Fixed.** Four narration parts that explicitly stop, and the tail owns stamp, link and ending. `SKILL.md`'s checklist brought in line |
| 10 | **The heaviest query in the framework.** The showcase's service step scanned 6.83 GB over 24 hours — more than the entire cost track, which had been tuned down to 2.07 GB to avoid exactly this | **Fixed.** 6 hours scans 1.67 GB for the same reading; at ~48,000 requests an hour it is never empty. Adding a service-id filter alongside the ARN measured 6.84 GB — marginally *worse*, no pruning. The ARN filter stays: that join is the step's point |

## Beat 4 of `lambda-iam-denied`, verified on live data

The beat rebuilt after the 70-poll watcher proved the broken grant is never readable now reads as
specified: *"This view is a snapshot of the role as it is now, so a grant that was wrong for half an
hour and then restored would not appear here"*, with the match framed as evidence — *"The configuration
that is running now is not the one that was running at 16:02"* — and the inference labelled.

## Second pass: runs that audit themselves

Three runs were given the scenario and told to self-drive to the close, then to report a critical audit
of their own transcript. Self-driven, so the user side is not independent — but the audits found things
a watched run did not, because the agent can see its own whole transcript at once.

| # | Finding | Outcome |
|---|---|---|
| 11 | **The status line rule was stated twice, in two scopes.** `SKILL.md` said "exactly one status line before the first query"; `conversation-craft.md` says "before the step's query". A run wrote one on turn 1 and none on turns 2–5, following the first and failing the second. Third instance today of one rule with two homes | **Fixed.** One before *every* turn's query, never more than one, in both places |
| 12 | **The close said "in 0 minutes".** A walk-through pulls every query at once, so `elapsed_min` is legitimately 0 — and the report header then printed "0 minutes" beside a 14-minute incident | **Fixed.** Under a minute is said as "under a minute" |
| 13 | **A label promised what it does not open.** `"The agent's analysis on the problem"` linked this session's record while the notes sat on a sibling record in the cluster, with no caveat in `Still open` | **Fixed.** Relabelled, and the beat must now say which record carries the notes |
| 14 | **The hook was restated as an observation** — "shoppers saw it as missing images". The hook's plain-language framing is scenario knowledge and may be said; what people *experienced* is not in any field | **Fixed.** Guard added beside the hook rules; the replay is what shows that |

Both runs also hit a schema rejection from the payload example I had corrected minutes earlier — they
had read the stale version. No action: the example and the schema now agree.

## Still owed

- The rest of the matrix: two more runs of each scenario in each mode.
- Nothing on the handoff block: **verified**. See below.
- `window` has a documented mapping now but has never been populated in a render.
- Browser verification of the deep links on `demo-live` and `playground`.
