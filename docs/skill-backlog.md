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
2. The resolvers return `ended_min_ago` and `queried_at`, and every beat's first query returns `queried_at` (testrun-13, below). The survey's "how long ago" and the close's elapsed time are measured, or left out.
3. The proof stamp shows the last 8 characters of the queryId; the first 8 repeat within a session. Superseded: the full queryId is copied exactly (testrun-10/11, below).
4. The read covers only what results show; an unqueried link is the next step, not a finding.
5. Payment beat 2: first failures seconds before `first_deploy` are normal (sync events are recorded on completion).
6. Beat 3 is marked "Fold in on a jump" in both scenarios, so "pinpoint the problem" still shows the failure-rate rise or the resize flip.
7. Plugin-only rules ported:
   - remediation with no incident (the `instructions.md` reply), fixing the contradiction with `conversation-craft.md`; eval `revert-no-incident`
   - loaded premise; eval `premise`
   - no failure-rate % in the survey; `survey-live` excludes `%`
   - shorter recap on a repeat ask
   - short SHA; null `commit` isn't a cold trail; sessions use `start_time`
   - the full broken-images beat 2 objection; eval `objection-live` (draft)

Branding: "Dynatrace Intelligence" / "Dynatrace Assist", never "Davis" or "CoPilot". Identifiers such as `dt.davis.*` stay. Evals `survey-live`, `handoff-live` and `walk-through-opening-live` exclude Davis and CoPilot.

## Done in the repo, 2026-10-08 (from testrun-10 and -11; not uploaded yet)

- Proof stamp: one per turn, for the first query, with the **full queryId copied exactly**. Cutting the last 8 characters produced wrong or short IDs in 8 of 8 stamps; the old first-8 rule was accurate but not useful.
- New rule "Data is the only source of conclusions": counts and nulls exactly as returned, no added geography, intent, validity or cause. Payment beat 4 no longer says "validation regression (rejecting input that should be valid)"; intent is the owning team's call.
- Beat 3 reveal matches the buckets: the first failures fall in the deploy's bucket, the full rate shows in the next.
- Beat 5 (both scenarios): report the row count as returned; a row with no country is reported as such, not counted as a country.
- A chained query is one turn with nothing written between its calls.
- Payment handoff fields: `owning_team` is who to page, `owner` is who shipped it; list both when they differ.
- Eval: `data-only-live` (draft). Not changed: elapsed time varies with how fast the user types; a real measurement stays.

## Done in the repo, 2026-10-08 (walk-through delivery; testruns 12 and 13; not uploaded)

- The walk-through (`references/walk-through.md`): the survey offers it once; taking it gives one opening report with the
  whole story (what, how long, how many, cost where defined, cause with before and after, owner, what broke, who it hit,
  detection), built from the first query of every beat. Evidence turns then prove each claim and end on a line that says
  why the next piece follows. The handoff block carries `Detected`, `Rate` and the cost, and is available at any point.
- Testrun-13 fixes: `queried_at` from every beat's first query, the close using the latest one ("From the first look to
  the full picture in X minutes"), omissions made silently, intent words in both directions, UTC times, no part-of-day
  words, the opening report standing in for beat 1 with an owner part, payment beat 3's marker query skipped when beat 2
  ran.
- Shared with explore: "the fix" is a labelled inference everywhere; payment beat 3 no longer promises a step change (the
  image `resizes` flip stays one); no call direction before the trace; resolver DQL runs as written.
- The disk-cpu fallback requires the dev host ID among the affected entities, so a Playground survey no longer lists it
  (testruns 12 and 13).
- Consolidation after three audits: one home per rule (voice and exact replies in the agent instructions, the data-only rule
  in conversation-craft, the handoff block and close in session-protocol); `mode` renamed `problem_state`; templates are
  scenario- and tense-neutral (`symptom`, `payoff`, `Goes to` per scenario); `dql-reference.md` holds DQL facts only;
  maintainer rationale moved to the README.
- Evals: the runner forbids "Dynatrace Intelligence" only as self-identification, so no walk-through case sets
  `forbid: false`; `explore-close-dev` (draft) covers the close; `walk-through-*` cases replace `briefing-*`.

## Done in the repo, 2026-10-20 (best-practice review and execution cost; not uploaded, evals not run)

Review against the skill-authoring best practices, then a pass to cut thinking time and tokens without losing determinism.

- **Contradictions fixed:** one opening-report length (14 lines); checkout is "listed as affected", not "downstream", in the
  payment context (read before any trace); "let me look myself" ends on exactly two angles; beat 5 (payment, images) no
  longer ends on a quiz question; one label for the beat 5 population ("sessions with server errors (5xx)"); no hardcoded
  retry time in the images beat 4.
- **One survey query** (`session-protocol.md` -> "Session state") replaces three main/backup lookup pairs. `dedup` picks the main
  row, or the fallback when there is none, in DQL. Checked live: same problem ids as the old lookups on the Playground
  (payment, images) and on dev (disk, via the fallback branch, 5 days 1 hour). Survey steps drop from five sequential model steps
  to three.
- **One file per scenario:** the lookup file and the beats file are merged; the survey reads `session-protocol.md` only, and a
  scenario file is read once the scenario is chosen. Discovery hooks moved into the protocol; the persona is stated once in
  SKILL.md; unused `user_action` and `Duration` lines are gone. Local `/demo` preloads SKILL.md and session-protocol only and
  uses bare `dtctl` (the path helper is a fallback).
- **Arithmetic moved into DQL:** `revenue_usd`, `duration_days/hours` (survey); `deploy_before_problem_min` (beat 2),
  `detected_after_min` (payment beat 4), `elapsed_min` (every beat's first query, from `{{SURVEY_AT}}`), and beat 5 totals
  (`total_sessions`, `no_country`, `countries`, top five rows) instead of summing 16 rows by hand. This closes the "detection
  gap is computed by the model" item. New tokens: `{{STARTED}}`, `{{SURVEY_AT}}`.
- **Less text:** "Optional engagement", the four-class table, the duplicated off-topic and cost replies, the second payment
  Wrong/Right example and the repeated survey paragraph are gone. SKILL.md has a turn table (reads, status line, ending per
  opening) in place of the checklist exceptions.
- **Measured** (characters / 4, before the first reply): survey 13.6k -> 6.9k tokens; hands-on payment session 16.8k -> 13.7k.
- Tools follow the layout: `validate_dt_skill.py` uses the survey query narrowed to the scenario as its resolver, and
  `preflight.py` and `run_dt_evals.py` (ground truth) use it too. Survey evals now assert that no scenario file is read.
  All three scenarios validate live (8, 7 and 6 blocks pass); offline tests pass.
- Beat 1 keeps its own query: it needs `description`, which the survey row leaves out on purpose (the row does carry `owning_team`).

## Open

- **In-session evals after the 2026-10-20 restructuring (1 run each, subagent plays the agent, Sonnet):** 11 of 11 pass:
  `survey-live`, `survey-dev`, `opening-pick-id-live`, `opening-pick-live`, `opening-shortcut-live`,
  `walk-through-opening-live`, `walk-through-evidence-live` (six turns, ends on the handoff block and close),
  `explore-close-live` (seven turns, close with a measured "4 minutes"), `data-only-live`, and `handoff-live` after a fix.
  - `handoff-live` first failed: the revert request ran a query for the owning team, which only beat 1 returned. The
    pre-change skill skipped that query and named the deploy owner (team-astroshop) as who it goes to, which is the wrong
    team per the Handoff fields. Fixed by adding `owning_team` to the survey row; the rerun names Team-Financial-Services,
    lists both teams and runs no query.
  - Not run: `offtopic`, `cost` (instructions changed by one phrase), `clean-environment` (needs a clean tenant),
    the images and disk walk-throughs, `limits-live`, `premise`, `injection`, and the model comparison (Haiku, Sonnet, Opus).
    One run each is not the 3-run bar the dev runner uses. A subagent writes no text between tool calls, so the status line
    is not checked here.
- **Deep links are still templates** in the beats. Building them with `concat()` in each beat's first query would save the
  model the URL assembly; not done because it adds fields to every result.
- **Dev tenant:** one trivial query hung until timeout during the restructuring and worked again minutes later (token refresh
  suspected); the dev validation passed on retry.
- **Deployed to dev, 2026-10-08 (template v12, 11 documents); first `@demo-agent` runs.** Dev evals, 3 runs each, across
  four rounds: cost, greeting, injection, offtopic, revert-no-incident and vendor pass 3/3 every time. The rest moved
  between rounds with 3-run noise; what stays broken, and why:
  - **The agent token lacks the metrics read scope** (`storage:metrics:read`). The disk scenario's `timeseries` beats
    (2 and 3) return a permission error on the agent, although `dtctl` reads them fine on dev. The agent then says "I can't
    show you the free-space trend" in most walk-through runs, and `walk-through-handoff-dev` runs a query it should not
    need. Add the scope to `DT_DEV_AGENT_TOKEN`, then re-run before judging those cases or tuning the skill further.
  - **Invented proof stamps: decided, dropped.** The Dynatrace agent's query results often carry no `queryId`, and the agent
    wrote patterned ids despite the rule. If it is not in the data, it does not exist: the stamp is gone from the shared skill
    and the agent instructions, and survives only as a local-only line in `skills/local-runtime/SKILL.md`, where `dtctl`
    always returns the metadata.
  - **The survey names scenarios that returned nothing** ("the payment service and image service are clean"): accepted. It
    comes from the dev tenant, where only the disk scenario is live, so two of three resolvers are always empty; it will not
    happen where the scenarios are live. `survey-dev` and `recovery` stay red until then; the rule stays in place.
  - One `HTTP 500` ("technical error") from the platform in the third round; transient.
  - `explore-close-dev` is a draft and has not run.
- **In-session evals, payment flows on the Playground (subagent plays the agent):** 8 runs of the 3- and 4-turn flows: opening
  report 3 of 4, handoff block 3 of 4, manager's-words replies 2 of 3, survey 1 of 1. All failures had one cause: 2 of 8
  agents narrated while reading the skill files, before the status line. The status line was exact in every run, the
  `queryId`s were real, the three exact replies held, and no run leaked "the other scenarios are clean" or listed the disk
  scenario. Fixed (the status line is the first thing written); 4 fresh survey runs after the fix pass 4 of 4. Also fixed:
  "160 sessions plus 17 with no country" double-counted (the 17 are in the 160), and "downstream" before a trace. Still
  unexamined: the walk-through's later evidence turns (beats 2 to 5) have not been run through this route.
- **In-session evals, second round (evidence turns, explore to the close, images; 5 flows plus 5 fresh surveys):**
  - Passing: explore through all five beats to the close with a measured "2 minutes" (X1); the walk-through's evidence turns
    with the strict no-repeat-query assertions, the exception on its own line, and the handoff block (E2); the images
    walk-through without errors, cost or a `Detected` row (M1, apart from the missing commit below).
  - Fixed after the round: the pre-status-line narration was still there in 2 of 5 flows, so the reads are now one parallel
    batch (survey re-check: 5 of 5 pass, none mention resolvers, 1 of 5 still narrates about the rule itself); the images
    report named no commit and the block printed a 40-character SHA (now the short SHA); "plus 17 with no country"
    double-counted (verbatim phrase now); "not time spent blind" was echoed to the user (rule rephrased); a survey that asked
    "which one?" itself made a later "payment" read as taking the walk-through (the survey now ends on the offer).
  - Still open: 1 of 5 narrates about the rule itself before the status line (the stamp slip is moot: the stamp is gone); the scorer counts only direct `dtctl query` commands, so a
    query hidden behind a shell variable would not count toward `no_dql`/`requires_dql`.
- **Opening redesign (one question per turn; the growth.design cheatsheet applied to the narration), in-session, 13 runs:**
  - Working: the survey ends on exactly one question (11 of 11); "which one" then "[A] it is" plus the mode question, no
    query; a bare "yes" gives the briefing; a first message that already decides gets neither question (2 of 2); the report
    leads with the story in time order and a one-line timeline; the trace turn closes "Last piece: …"; the ending names what
    this incident established and offers the other incident or a clean stop. After the "first word is the number of
    incidents" rule, 3 of 3 surveys open on the impact (4 of 6 opened on "Nothing is open" before it).
  - Open: planning narration before the queries, now in 2 of 3 surveys ("Now the three primary resolvers in parallel.") and 1
    in 4 of the longer flows; it echoes the skill's own words (resolver, primary), so renaming those terms in the skill is the
    next thing to try. A survey sometimes quotes an error-rate percentage (forbidden; asserted from now on). Dev is not
    synced with any of this.
- **Local eval harness built, not yet run against a model** (`run_dt_evals.py --local`, `tools/local_agent.py`): the
  harness logic, the dtctl path on both tenants and the write guard are tested; the first model call needs
  `ANTHROPIC_API_KEY`. Run `--local --include-draft` for the payment and image cases, then compare against the dev agent.
- **`explore-close-dev` and the new `queried_at` queries** need a live run: a steered user who finishes all five beats gets the
  close with a measured elapsed time.
- **Detection gap is computed by the model** from two timestamps (payment beat 4). Correct in both testrun-13 runs; move it
  into the DQL if it drifts.
- **Survey narrates scenarios that returned nothing** (found 2026-10-08, dev tenant, where only `disk-cpu-cascade` is live).
  Session-protocol says to name only scenarios that returned a problem, and `survey-dev` passes 3/3 on a fresh
  conversation. After a declined request (`recovery`) the agent still said "the payment and image service resolvers came
  back clean" or "both look clean" in 2 of 3 runs, which an empty resolver does not show. `recovery` fails on "payment" or
  "image" in its survey reply, so it shows red until this is fixed. Next try: put the rule in `instructions.md` as well as
  the skill (rules that live only in a reference file get missed on later turns).
- Run 3 of `recovery` also failed for a reason the review sheet doesn't state; read the runner's failure text first.
- Recap-on-repeat has no eval case (it needs a full live session).
- The `-live` cases stay drafts until the agent exists on the Playground tenant.
- The old plugin edition (`scenarios/`, `skills/demo-engine/`) got only the beat 2/4 DQL fixes, for the A/B. It is retired in
  Phase 3, so nothing else is mirrored.

Deliberately dropped: payment beat 5's "310 error events" line (a hardcoded value that changes every cycle) and
`urgency_phrase` (nothing uses it).
