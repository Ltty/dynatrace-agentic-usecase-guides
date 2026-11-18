# Demo Test Run 20 — the Kubernetes tour, and the cloud tour's removal

**Date:** 2026-11-17 to 2026-11-18
**Runtime:** in-session subagents playing `demo-agent` against the repo's own files
(`docs/DYNATRACE-SKILL.md` → "Test" → in-session evals), `dtctl` for data. Skill selection was tested by subagents
playing a neutral Assist that picks from the skills' descriptions.
**Model:** Sonnet 5.5
**Environment:** `demo-live` (`guu84124`), `readonly`.
**Prompted by:** adding the KubeCon booth demo as a tour, then a colleague's report that our cost skill overrode
`dt-biz-cloud-costs`.

Every value below was read from a result or from a file in the repo.

---

## Coverage, stated honestly

Not the three runs per case the evals call for: one pass, with reruns only where a fix needed proving.

| Case | Runs | Outcome |
|---|---|---|
| `k8s-tour-opening-demo-live` | 2 (second after the cost removal) | pass, pass |
| `offer-kubernetes-demo-live` (two turns) | 1 | pass |
| `k8s-tour-cloud-alert-demo-live` (two turns) | 1 | pass, after the case was corrected |
| `k8s-tour-handoff-demo-live` (two turns) | 2 | fail (one narration line, not reproduced), pass |
| `k8s-tour-resources-demo-live` (three turns) | 3 | **fail (routing)**, pass but wrong shape (closed early), pass |
| `cost-redirect-demo-live` | 1 | pass |
| Skill selection, Assist picking by description | 3 prompts, 1 run each | pass ×3 |

**Not covered:** one full `/demo` session through all three tracks and the close, the troubleshoot track past its first
step, any run of the cases three times, the real Assist UI, and the tour's links opened in a browser.

---

## Findings

| # | Finding | Where it came from | Outcome |
|---|---|---|---|
| 1 | **A starved-workload question went to the throttling incident**, not the tour: the agent read the incident and concluded the service was *not* starved from a 48-hour window the 30-day data contradicts | resources run 1 | Fixed: the incident's Matches no longer claim limits and sizing; the tour's routing names a workload's memory or CPU against its limits. Rerun passed. |
| 2 | **The resources track ended on the full session close** (handoff block, wrap-up) instead of bridging to another track. The shared `tour-protocol.md` said a close fires when a track completes; the Kubernetes file said otherwise | resources run 2 | Fixed: the shared file defers to each tour, the Kubernetes file says a finished track ends on its bridge, and the case now asserts it. Rerun passed. |
| 3 | The cloud-alert case expected the verdict on turn 1, but the step has two queries, so the agent correctly split it | cloud-alert run 1 | Case corrected: name on turn 1, verdict on turn 2. |
| 4 | An explicit `davis` exclusion matched the word inside `dynatrace.davis.problems` in every problem link | cloud-alert, handoff | Case files only: the runner's default list already covers product naming. |
| 5 | One handoff run narrated "Running the estate query." before its answer | handoff run 1 | Not reproduced on the rerun. Left under observation. |
| 6 | **Our evals could not have caught the override.** None asserted that a cost question leaves our skills alone; a colleague found it by using Assist | her report | The tour and the cloud-cost routing are removed. `cost-redirect-demo-live` and the selection check are the new guard. |

Data findings that shaped the beats (detail in `docs/scenarios/kubernetes-complexity.md`): the script's "29,000
millicores" for the database is `timeseries sum()` adding samples inside each bucket (500m is the truth); the
calculation service's 6-hour memory average (66% of the limit) would contradict "no headroom", so the beat reads 30 days
of hourly maxima (82% average, 311 of 721 hours above 90%).

---

## Owed

- Run each tour case three times and read the rate.
- One full `/demo` session: all three tracks and the close, through the troubleshoot track's last step.
- Open the five tour links in a browser; the StatefulSet link for easytrade-db is inferred, not copied.
- The reporter's retry of their prompt in plain Assist after the deploy, and the Kubernetes offer from the Clouds app.
