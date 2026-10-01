# Comparative analysis: DEM-Demo, log-dtctl-DUAL, and the agentic use-case-guides engine

**Audience:** demo-tooling owners and contributors to this repo.
**Source material:** `DEM-Demo.zip` and `log-dtctl-demo-DUAL.zip`, both placed at the repo root on
2026-10-01 and extracted to a session scratchpad for analysis. Neither zip was extracted into the
repo; the zips themselves are untracked. All `file:line` citations below are kit-relative (e.g.
`dem/REVIEW.md:12`), not scratchpad-absolute.

---

## 1. What the three things are

| | **DEM-Demo** | **log-dtctl DUAL** | **this repo** |
|---|---|---|---|
| Engine | `dem_demo_driver.ps1`, 735 lines | `astroshop_demo_driver.ps1` + `.sh`, ~600 lines each | ~1,070 lines of English prose + 1,606 lines Python |
| Who drives | human presenter, keypress-gated | human presenter, keypress-gated | the model |
| Control flow | PowerShell `while` + `switch` menu | PowerShell / bash `do/while` + `switch` menu | none in code — model-executed prose |
| Storylines | **7 acts, 8 personas** | **6 acts, 4 personas** | **1 scenario, 5 beats, 1 persona** |
| DQL files | 34 (33 wired) | 16 (7 wired) | 8 |
| LLM role | demoed *feature* (Davis CoPilot, 5 call-outs) | demoed *feature* (2 call-outs) | **the engine** |
| Platforms | Windows | Windows + macOS / Linux | Codespaces / devcontainer / local |
| Narrative storage | PS string literals (+ duplicated in 2 markdown docs) | PS + bash string literals (12 hand-synced copies) | `scenario.yaml` prose, single source |
| Read-only enforcement | none — by construction only | none — by construction only | tested hook, 24/24 adversarial cases pass |

**Two clarifications that reframe the comparison:**

`"DUAL"` is not in the kit — zero case-insensitive hits across all 25 files. The label refers to
the dual-platform drivers (`.ps1` + `.sh`, added 2026-09-30), the one structural thing that
distinguishes it from DEM. The two kits share a common lineage: they independently converged on an
`[A]` Assist toggle, a `[B]` browser-link kill switch, `Write-NoBom` helper, `_scratch/` for
runtime files, `Show-Dql` before executing, and the identical `dtctl open intent` `+` → `%20`
fragment workaround (`dem/dem_demo_driver.ps1:86-96`, `dual/astroshop_demo_driver.ps1:86-96`).
That convergence matters — the PowerShell-driver pattern is a twice-iterated local optimum built by
someone who tested it in front of real rooms.

---

## 2. The frame: three users, three optimisation targets

Every comparison point that follows only makes sense inside this frame.

| User | DEM / DUAL | this repo |
|---|---|---|
| **Audience** (prospect in the room) | watches a presenter | **talks to a colleague** |
| **Presenter** (SE / DevRel) | full control; must pre-read the prose | no role — irrelevant |
| **Author** (builds / maintains) | edit a 735-line driver + up to 3 narrative copies | add a folder |

DEM and DUAL are **presentation aids for 1:many stage delivery.** This repo is a **simulated
on-call colleague for 1:1 and self-serve.** Recommending agentic-for-everything — or
script-for-everything — on the strength of this comparison alone would be wrong. They serve
different use cases. The recommendation at the end reflects that.

---

## 3. Where the agentic engine wins

### 3.1 Divergence — the highest-value demo moment

The most valuable thing that can happen during a demo is a question nobody planned for, answered
with live data while the audience watches. Script kits have two options when that happens: the
presenter answers from memory, or they drop to `LAB.md` and hand-type DQL in front of the room.
The agentic engine satisfies it, re-anchors to the investigation, and continues — that behaviour is
specified and tested across six testruns (`skills/demo-engine/SKILL.md:208-243`).

The sharpest illustration: DEM ships objection-handling content that never reaches the terminal.
Every act in `dem/USE-CASES-AND-PERSONAS.md` carries an "Objection to expect" block — for example,
act 2's (`:43`):

> *"'That's a demo app quirk.' It is the single most common real-world antipattern in payment
> integrations. Ask them how their own gateway reports a declined card, and watch the room go quiet."*

And a fairness guardrail (`:107`):

> *"Be fair, not tribal: this compares two configurations, not a verdict on OpenTelemetry the
> standard."*

None of this reaches the driver. It is dead prose the presenter must have pre-read.
That is exactly the class of content the agentic architecture deploys situationally, when
the objection actually lands.

### 3.2 Staleness-proofing by design

Both kits independently discovered the same failure mode and wrote it down honestly.

DEM graded its own first version repeatability: **D** (`dem/REVIEW.md:12`):

> *"Every query hardcoded `-24h`. The centerpiece incident would have silently vanished from the
> demo ~6 hours after delivery. Retention is actually 7 days."*

DUAL v1's header states what the original kit claimed vs. what the screen actually showed
(`dual/astroshop_demo_driver.ps1:5-11`):

> *"v1 hardcoded counts from 2026-09-08 and drifted badly out of date (it claimed 5.27M lines /
> 2,008 signal / 620 checkout timeouts while the screen showed 6.08M / 984 / 614, and narrated a
> 90-minute infra cascade that had already aged out of the 7-day retention window)."*

Pattern count decayed 60 → 17 patterns in 14 days.

Our `reveal` describes the *shape* of a finding, never a value (`docs/AUTHORING.md:172-179`), and
the resolver finds the live occurrence from a 48-hour lookback. That said, **live-numbers-not-authored
is not an agentic exclusive** — DUAL v2 fixed the same problem in PowerShell, using `Invoke-Records`
to recompute every narrated figure at run time. What is agentic-exclusive is live numbers in *novel
sentences answering unanticipated questions*.

### 3.3 Enforced read-only

We are the only approach with a mechanism rather than a property. Both script kits are read-only
because their eight `dtctl` call sites happen to be read verbs — nothing prevents a future edit.
Both also ship tenant log content to Davis CoPilot by default (`AssistMode='cli'` at startup), and
DUAL's bash driver `eval`s Python-generated shell (`dual/astroshop_demo_driver.sh:234`, correct
`shlex.quote` at all ~30 emission points, but the safety rests entirely on that discipline holding).
Fine for a public Playground; disqualifying for a customer tenant. If this ever points at customer
data, our hook (`tools/guard_dtctl.py`, 24/24 adversarial test cases passing) is the only
defensible starting point.

### 3.4 Authoring cost

~390 lines across 11 files, no code changes. That claim is currently untested at n>1 (see §6.1).

---

## 4. Where the script kits win — including the headline finding

### 4.1 The credibility inversion

This is the most important finding in the analysis, and it goes against our approach.

The script kits prove liveness *structurally*: `Show-Dql` prints the query, the presenter presses
Enter in front of the room, and `dtctl`'s own unretouched ASCII table appears. The audience watched
it happen. Unfakeable by construction.

We prove liveness by *assertion*: the model narrates *"5 failing traces in 25ms (queryId 01a0e712,
167MB scanned)"* and re-types 3–5 fields into a markdown table. That is richer evidence on paper —
and exactly the class of claim a 2026 audience has been trained to distrust. A sceptic cannot
distinguish a real proof stamp from a fabricated one, and they never see the raw tool output at all.

This is fixable without changing the architecture. It requires a `SKILL.md` beat-loop change: echo
the DQL in a fenced block *before* the Bash call, and present `dtctl`'s table verbatim rather than
re-typing fields into markdown. The proof stamp stays as a supplement, not the primary evidence.

### 4.2 Presenter preflight — the best single idea in either kit

DUAL's `[P]` (`dual/astroshop_demo_driver.ps1:320-344`) runs every act's query and prints
`[LIVE] … N row(s)` or `[EMPTY] … no data in window`, closing with: *"An EMPTY row means that
story has no data right now — skip it."*

A demo that tells you which of its own stories still have live data before you walk into the room.
We have `/demo-doctor`, which checks connectivity and auth, but nothing that verifies story-level
data liveness across all scenarios.

### 4.3 Presenter control surfaces

Things DEM and DUAL have that we have no equivalent of:

- **`[B]` browser-link kill switch** — *"Turn OFF when screen-sharing a fixed layout, recording,
  or testing unattended"* (`dem/dem_demo_driver.ps1:26-27`). Our deep links just open.
- **`[C]` demo clock** — prints current UTC and the next fault window (`dem/dem_demo_driver.ps1:651-665`),
  re-printable mid-demo.
- **Seven curated run orders by buying centre** (`dem/USE-CASES-AND-PERSONAS.md:157-165`) — e.g.
  Business/DX = `2→4→1` (~20 min), SRE/platform = `1→3→2→6` (~28 min). A presenter can make a
  good choice before entering the room.
- **In-act skip/diverge is impossible.** Inside an act, the beat sequence is hard-coded; only
  Ctrl+C exits. Our engine supports arbitrary divergence (`SKILL.md:208-243`); theirs demands it
  all goes in the presenter's head.

### 4.4 Honest negatives as evidence

DEM deliberately runs a rage-click probe it knows returns nothing interesting — *"max clicks on any
element = 2, mean = 1.006. The 'real users' here are a scripted load generator, and bots don't get
frustrated. That is the correct answer, not a broken query."* (`dem/dem_demo_driver.ps1:514-519`).
It also volunteers that the mobile crash is injected via `ChaosEngine.triggerCrash` because *"a
customer reading the stack will spot it, so say it first."*

That is an enormous trust move — "our demo is honest about what the demo is" — and we have no
concept of it. Our `reveal` is always a positive finding.

### 4.5 Breadth — the sharpest competitive gap

- DEM: 7 acts — synthetic monitoring, RUM→Lambda→IAM cross-cloud tracing, session replay as
  queryable data, OneAgent vs pure OTel, DPL log clustering, mobile DEM (crashes, ANRs, app start).
- DUAL: 6 acts — DPL log clustering, DevOps (flagd crash-loop), Security (RBAC denial audit trail),
  Business Ops (checkout timeout, payment error reframed as conversion loss).
- **Us: 1 scenario.**

We cover roughly 8% of their total storyline surface. A field org choosing a demo tool today picks
the script kits on coverage alone and would be right to. The content is the scarce asset — not
either engine.

---

## 5. Failure classes agentic adds

A script's bugs are finite and testable. A prompt's failure modes are a distribution. The testrun
record in `docs/` names these concretely:

- **testrun-03** (`docs/testrun-03.md`): *"Trailing tool call makes text invisible in VSCode Focus
  view (blocking UX issue). Happened four times this session."*
- **testrun-04**: the ordering fix was applied correctly and the model still wrote *"No response
  requested."* instead of narrating. Separately, a stale session count from a three-day-old
  occurrence, stated as current fact.
- **testrun-01 / -02**: DQL field-name mismatches that showed up only at run time — `round(x,1)`
  positional error, `span.status_code == "ERROR"` (correct value is lowercase `"error"`),
  `matchesPhrase(useraction.errors,…)` (field doesn't exist), `session.hasSessionReplay` (field
  doesn't exist), `--max-field-chars 0` invalid on `exec copilot`.

Every regression was fixed by adding more prose. `skills/demo-engine/SKILL.md:386-451` is now a
66-line "What you must never do" list, several items being verbatim patches for a named testrun.
That is the architecture's cost curve, and it is open-ended in a way a `switch` statement is not.

Related: ~12k tokens of instruction at session start — 2.8× the entire scenario content payload.
`docs/OPENCODE.md:58-86` states that under context pressure *"persona adherence and the role
guardrails degrade first — the engine's behavioural rules are the longest section and are cut
earliest when context fills."*

The soft guardrails (persona, scope adherence, no-remediation) are prompt-only.
`docs/guardrail-probes.md` is a 225-line template with every response block still reading
`[paste engine output]` — zero recorded verification of any role-guardrail scenario.

---

## 6. Recommendation

**Agentic is the right architecture. Neither engine is the deliverable — the content is.**

### 6.1 The strategic line

**Two delivery modes over one content library.** Scenario folders are the single source of truth.
The agentic engine is one reader; a thin Enter-gated scripted mode (replayable, projector-safe,
presenter-controlled) is a second reader for stage use. The content does not care which driver
reads it. That resolves the 1:many vs 1:1 mismatch rather than pretending it doesn't exist.

This claim — "adding a scenario is a folder, no engine changes" — is currently untested beyond a
single scenario. Before investing in content at scale, port **one** scenario (DUAL's flagd
crash-loop → RBAC chain is the cleanest two-beat causal chain) and treat it as the real test.
If it lands with zero changes under `skills/`, `commands/`, or `tools/`, the thesis holds.

### 6.2 Don't retire the script kits

For a cold room, a fixed slot, 1:many, on a projector, they are better today and will stay better
for that mode. Our engine's natural home is the prospect driving it themselves, asynchronously, with
no SE present — a larger market and a worse stage act.

### 6.3 Steal these, in priority order

1. **Presenter preflight across all scenarios** — a `/demo-doctor --scenarios` or
   `python tools/preflight.py preflight` that resolves every published scenario and prints
   `[LIVE]` / `[EMPTY]` per storyline before the session. Highest value per line of work.
2. **Fix the credibility inversion** — echo the DQL before the Bash call, present `dtctl`'s table
   verbatim. Prompt-only change in `SKILL.md`, no code.
3. **`objections` field on the beat schema** — port DEM's "Objection to expect" blocks so the
   engine can surface them situationally rather than the presenter having to pre-read them.
4. **`negative_evidence` beat concept** — a query whose empty or boring result *is* the finding,
   with pre-framing prose. DEM's rage-click probe and single-row fleet query are the model.

### 6.4 Content port order

All DQL is live-tested and comes with documented field-name gotchas. Two caveats carry across:
every DUAL persona query matches on English log substrings (`contains(content, "American Express")`)
forced by null entity attributes on raw container logs (`dual/astroshop_demo_findings.md:50`);
DEM hardcodes entity IDs in 11 of 34 queries with no resolution-by-name. Both must become
resolver-backed on the way in.

| Port | Source | Why first |
|---|---|---|
| Log analytics / DPL clustering (acts 1–2) | DUAL | different surface, retention-proof — reads the live window |
| flagd crash-loop → RBAC denial (acts 3–4) | DUAL | clean two-beat causal chain; real test of §6.1 |
| AmEx conversion-loss (act 6) | DUAL | strongest business persona; overlaps `payment-failure` — merge rather than duplicate |
| Broken images: RUM → Lambda → IAM (act 3) | DEM | cross-cloud trace pivot, dynamic trace discovery already implemented |
| Mobile DEM: crash / ANR / app start (act 7) | DEM | wholly uncovered surface |
| Session replay as queryable data (act 4) | DEM | wholly uncovered surface |

---

## 7. Engineering blockers found during this analysis

**These are not in scope for this document** — they are recorded here so nothing is lost.
All seven require code or schema changes; none belong in a documentation-only pass.

1. **The validator fails on the only shipped scenario.** `scenarios/payment-failure/scenario.yaml:47`
   has `root_cause_service_id` (consumed by the resolver fallback at `tools/preflight.py:276`)
   but `scenarios/_schema/scenario.schema.json:69-81` sets `additionalProperties: false`. Running
   `python tools/validate_scenarios.py` today produces:
   ```
   ERROR: Schema violation: Additional properties are not allowed
          ('root_cause_service_id' was unexpected) (path: resolve.problem)
   RESULT: validation failed
   ```
   Fix: add `root_cause_service_id` to the schema's `resolve.problem` properties.

2. **One global `.demo-state.json` vs. a multi-scenario survey.** `STATE_PATH` is a single constant
   (`tools/preflight.py:31`) while `commands/demo.md:61-62` resolves every published scenario with
   `--write` in parallel. Last writer wins; `load-queries` then hands scenario B scenario A's
   timeframe. Fix: make it per-scenario — `.demo-state/<id>.json`.

3. **Hardcoded `PAYMENT_FAILURE_PROBLEM` placeholder** (`tools/preflight.py:348`) — scenario
   content baked into the engine tool. Fix: emit `PROBLEM_ID`, keep old key as an alias.

4. **`scenarios/_template/` is schema-invalid.** Still declares `fallback: fixtures/problem.json`
   (`:28`) and uses the dead `{{PROBLEM_ID}}` placeholder in its deep link (`:53`). The validator
   deliberately skips `_template` (`validate_scenarios.py:346`), so a copied template passes
   static validation and ships a broken link. Fix: stop skipping it and fix the template.

5. **Resolver / beat-1 lookback disagree.** `queries/find-problem.dql:12` looks back 48h;
   `queries/beat-01-problem-summary.dql:6` looks back 24h and re-selects with
   `sort timestamp desc | limit 1` instead of pinning to the resolved problem id. Fix: pin to id.

6. **`/demo status` and `/demo recap` read fields never written.** `commands/demo.md:224-227`
   expects beat progress from `.demo-state.json`, but mid-session writes are forbidden
   (`skills/demo-engine/SKILL.md:132-135`). Fix: track in context only and remove the file read,
   or allow a limited write.

7. **Orphaned third copy of the guard.** `.claude/hooks/guard-dtctl.py` is referenced by nothing
   and diverges (prints block reason to stdout; `tools/guard_dtctl.py:54` uses stderr). The
   `commands/` ↔ `.claude/commands/` directory is also byte-for-byte duplicated (243 + 40 lines).
   Fix: delete `.claude/hooks/guard-dtctl.py`, pick one canonical command location.
