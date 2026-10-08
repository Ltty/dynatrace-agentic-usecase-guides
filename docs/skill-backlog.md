# Skill backlog

Changes to `dynatrace-intelligence/skills/investigating-playground-incidents/` and the demo-agent.
Workflow: `.claude/skills/maintaining-dynatrace-skill/SKILL.md`.

## Done in the repo, 2026-10-08 (not uploaded yet; dev tenant upload and evals pending approval)

From testrun-08:
- Payment beat 2 summarizes deploys per commit, oldest first. The old `limit 5` hid the first sync at onset.
- Payment beat 4 groups failures by exception with first/last seen. The chained trace is the earliest failure.
- A result whose row count equals its `limit` may be cut off; never claim absence from it.
- `dql-reference.md` has a logs section: logs carry no span/problem service ID; scope by `k8s.container.name`.

From testrun-08/09:
1. Questions the telemetry can't answer get "That's not in the telemetry…", never "I can't". Eval: `limits-live` (draft).
2. The resolvers return `ended_min_ago` and `queried_at`, and beat 5 returns `queried_at`. The survey's "how long ago" and the close's elapsed time are measured, or left out.
3. The proof stamp shows the last 8 characters of the queryId; the first 8 repeat within a session.
4. The read covers only what results show; an unqueried link is the next step, not a finding.
5. Payment beat 2: first failures seconds before `first_deploy` are normal (sync events are recorded on completion).
6. Beat 3 is marked "Fold in on a jump" in both scenarios, so "pinpoint the problem" still shows the failure-rate step change or the resize flip.
7. Plugin-only rules ported:
   - remediation with no incident (the `instructions.md` reply), fixing the contradiction with `conversation-craft.md`; eval `revert-no-incident`
   - loaded premise; eval `premise`
   - no failure-rate % in the survey; `survey-live` excludes `%`
   - shorter recap on a repeat ask
   - short SHA; null `commit` isn't a cold trail; sessions use `start_time`
   - the full broken-images beat 2 objection; eval `objection-live` (draft)

Branding: "Dynatrace Intelligence" / "Dynatrace Assist", never "Davis" or "CoPilot". Identifiers such as `dt.davis.*` stay. Evals `survey-live` and `handoff-live` check it.

## Done in the repo, 2026-10-08 (from testrun-10 and -11; not uploaded yet)

- Proof stamp: one per turn, for the first query, with the **full queryId copied exactly**. Cutting the last 8 characters produced wrong or short IDs in 8 of 8 stamps; the old first-8 rule was accurate but not useful.
- New rule "Data is the only source of conclusions": counts and nulls exactly as returned, no added geography, intent, validity or cause. Payment beat 4 no longer says "validation regression (rejecting input that should be valid)"; intent is the owning team's call.
- Beat 3 reveal matches the buckets: the first failures fall in the deploy's bucket, the full rate shows in the next.
- Beat 5 (both scenarios): report the row count as returned; a row with no country is reported as such, not counted as a country.
- A chained query is one turn with nothing written between its calls.
- Payment handoff fields: `owning_team` is who to page, `owner` is who shipped it; list both when they differ.
- Eval: `data-only-live` (draft). Not changed: elapsed time varies with how fast the user types; a real measurement stays.

## Done in the repo, 2026-10-08 (walk-through delivery; not run against an agent yet, not uploaded)

- New `references/briefing-mode.md`: the SRE reports the incident to the user as to a manager. Same scenarios, beats and
  proof stamps; the turn ends on a named next step, not a choice; the close is a handoff block with a "Still open" row.
- The survey closes with one fixed sentence offering it. A direct start skips the offer; the clean-environment reply has none.
- A handoff row with no source in the scenario's Handoff fields is left out, never "unknown" or "N/A".
- `instructions.md` carries the offer and the load-bearing rules too, so they don't live only in a reference file.
- Evals: `briefing-dev`, `briefing-meaning-dev`, `briefing-handoff-dev`, `briefing-switch-dev`, `briefing-handoff-live` (draft);
  `survey-dev` and `survey-live` now require the offer.

## Done in the repo, 2026-10-08 (from testrun-12; walk-through red line; not run against an agent yet, not uploaded)

- The walk-through now opens with the whole story (what, how long, how many, cost where defined, cause with before and after,
  what broke, who it hit, detection), built from the first query of every beat run in one turn. The beats become the proof,
  each turn opening with the claim it proves and ending on why the next piece follows. Time series condense to before, peak, after.
- Handoff block gains `Detected` and `Rate`, and the cost on the `Impact` row. It works at any point, not only after beat 5.
- A manager's stronger words get exact replies: "was it a bug", "was that the fix", "was it global".
- Fixed in both deliveries: "the fix" is a labelled inference (payment beats 2-4, image beats 2-3, `dql-reference.md`);
  payment beat 3 no longer promises a step change (the rate ramps; the image `resizes` flip is a real step and stays);
  "checkout calls payment" is not said before the trace (payment beat 1, the `SKILL.md` example, `conversation-craft.md`);
  payment beat 4 states detection time.
- Resolver DQL runs exactly as written in the file; a trimmed copy cost a second query.
- Evals: `briefing-opening-live`, `briefing-inference-live` (drafts); `briefing-dev` and `briefing-handoff-live` tightened.

## Open

- **`disk-cpu-cascade` appears in a Playground survey** (testrun-12). Its primary filters
  `toString(root_cause_id) == "DISK-2B3DB86FA32F6CE1"`; the fallback replaces that with
  `matchesPhrase(event.description, "/data") and matchesPhrase(event.description, "frontend-high-cpu")`, which has no entity,
  host-group or tenant predicate, so any problem whose description holds both phrases matches on any tenant. It also drops
  the root-cause filter, so the newest record can lack a root cause, hence the null `root_cause` in the run. To fix: run the
  fallback once on the Playground, see which entity fields the matched record carries, and filter on one of them.
- **Detection gap is computed by the model** from two timestamps (payment beat 4). If testrun-13 shows it wrong, move it into the DQL.

- **Walk-through delivery is untested.** Run `python tools/run_dt_evals.py --tenant dev` after the dev upload and read the
  review sheet for register: whether five turns read as one conversation or one template cannot be scripted.
- **Eval runner's global `FORBIDDEN` list contains `dynatrace intelligence`**, which the skill tells the agent to say in beat 1.
  Latent in `handoff-live`; the `briefing-*` cases set `forbid: false` to get past it, which also turns off the narration checks
  for them. Narrow the pattern to the self-reference it was meant to catch.
- `commands/demo.md`'s `argument-hint` lists only two scenarios; `disk-cpu-cascade` is missing.

- **Survey narrates scenarios that returned nothing** (found 2026-10-08, dev tenant, where only `disk-cpu-cascade` is live).
  Session-protocol now says to name only scenarios that returned a problem, and `survey-dev` passes 3/3 on a fresh
  conversation. After a declined request (`recovery`) the agent still said "the payment and image service resolvers came
  back clean" or "both look clean" in 2 of 3 runs, which an empty resolver does not show. `recovery` now fails on
  "payment" or "image" in its survey reply, so it shows red until this is fixed. Next try: put the rule in
  `instructions.md` as well as the skill (rules that live only in a reference file get missed on later turns).
- Run 3 of `recovery` also failed for a reason the review sheet doesn't state; read the runner's failure text first.

- Recap-on-repeat has no eval case (it needs a full live session).
- The `-live` cases stay drafts until the agent exists on the Playground tenant.
- The old plugin edition (`scenarios/`, `skills/demo-engine/`) got only the beat 2/4 DQL fixes, for the A/B. It is retired in Phase 3, so nothing else is mirrored.

Deliberately dropped: payment beat 5's "310 error events" line (a hardcoded value that changes every cycle) and `urgency_phrase` (nothing uses it).
