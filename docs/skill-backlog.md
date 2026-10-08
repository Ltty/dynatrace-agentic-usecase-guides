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

## Open

- Recap-on-repeat has no eval case (it needs a full live session).
- The `-live` cases stay drafts until the agent exists on the Playground tenant.
- The old plugin edition (`scenarios/`, `skills/demo-engine/`) got only the beat 2/4 DQL fixes, for the A/B. It is retired in Phase 3, so nothing else is mirrored.

Deliberately dropped: payment beat 5's "310 error events" line (a hardcoded value that changes every cycle) and `urgency_phrase` (nothing uses it).
