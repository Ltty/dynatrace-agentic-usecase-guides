# Adding a New Demo

A scenario is two markdown files in the skill, plus a row in its registry table. No engine code changes:
the same skill runs in Dynatrace (`@demo-agent`) and locally (`/demo`), so one scenario serves both.

All paths below are under `dynatrace-intelligence/skills/investigating-playground-incidents/`.

## The contract

```text
references/scenario-<id>.md         # business context, scope, handoff fields, then the beats (evidence DQL, reveal, staging, deep link)
references/session-protocol.md      # the shared survey query gets one scenario branch, the discovery hooks table one row
SKILL.md                            # one row in the Scenarios table
```

The survey reads only the first file for every scenario; the beats file is read once the user picks a
direction. Keep the split, or the survey gets slow and expensive as scenarios are added. `references/` stays
flat: no subfolders, unique names, linked as `references/<name>.md`. Keep `SKILL.md` under 150 lines.

Maintainer-only notes (entity IDs, history, source material) go in `docs/scenarios/`, never in the skill
folder: the agent reads everything in it and would repeat it to the user.

**Read the video transcript before writing beats, if one exists** (`docs/scenarios/payment-failure-source/`
is the example). It is often richer than the step titles in the guide JSON: the payment-failure transcript
revealed a missing beat (which team owns the failing service, already on the problem record) and reframed
what "show me the trace" means (the whole request, confirming the upstream services are clean).

## Step by step

### 1. Copy a scenario and rename it

Start from `scenario-payment-failure.md`. The `<id>` is
`[topic]-[variant]`, e.g. `k8s-oom-kill`.

### 2. Add the scenario to the survey query

There is one survey query for all scenarios, in `references/session-protocol.md` → "Session state". Add a branch to
its `scenario` assignment that recognises your root-cause entity. If the scenario needs a fallback (a different
filter that applies only when the main one finds nothing), give it `pref = 1` through the `pref` expression. The
query returns one row per scenario with the fields the session protocol names; do not add fields the survey does
not use (`description` is read by beat 1). Date arithmetic and any cost figure belong in the query, not in the model.

- Look back `from: now()-48h, to: now()`. Patterns fire on a schedule; this window reliably catches the latest
  occurrence.
- **Filter `dt.davis.is_duplicate == false`, not on `event.name`.** Recurring patterns fire as a cluster of
  near-duplicate problems with overlapping windows and different affected-user counts. Without the filter,
  the newest row is picked arbitrarily and any revenue figure changes every run. The merged problem is
  often named generically ("Multiple application problems"), so an `event.name` filter excludes the one you want.
- The fallback ignores `is_duplicate` and prefers `dt.davis.affected_users_count`; it applies only when no
  non-duplicate row exists for the scenario.

### 3. Write the beats

In `scenario-<id>.md`, one `## Beat N — Title` section each, with: **Requires**, **Why this step**,
**Objective**, **Evidence DQL**, **Reveal**, **Success signal**, **Deep link**, and for a climax
`**peak_moment: true**` plus **Staging**. Optional: an **Objection** paragraph (skeptic pushback and the answer, used only when the user
raises it) and a **Fold in on a jump** note when a beat's evidence is needed even if the user skips it.

**Requires** is the beats whose *findings* this one builds on, or `none`. It is about the argument,
never the query: most of these queries would run in any order, but a reveal that leans on an earlier
finding is incoherent without it. The agent offers every beat whose Requires are complete, so this is
what lets a user steer without the story coming apart — and what lets the agent say plainly when an
order is forced. Beat 1 requires `none`; a beat may only require an earlier beat.
`tools/tests/test_deep_links.py` checks the graph.

**A linear scenario is a legitimate answer.** If every beat requires the one before it, the agent
offers one step at a time and says why that is the only way forward. Do not loosen a real dependency
to manufacture a choice: an option the evidence cannot serve is worse than no option.

**Why this step** and **Objective** are not the same thing, and both are required.

- **Why this step** is one sentence the agent *says*, before the query, naming what the step is for in terms of
  what the scenario is settling: "To know whether the deploy caused this, we need the failure rate either side of
  it." Without it the user is left asking "so what?" at every step.
  `tools/tests/test_deep_links.py` fails a beat that has none.
- **Objective** is for you, the author: what the user ends up seeing. It is never read out.

**A beat with several Evidence DQL blocks runs as several turns** — one query, one finding, one call to action
each (`conversation-craft.md` → "One query, one turn"). A chained pair counts as one. Write the blocks in the
order you want them taken, and put the Staging and the deep link on the last one: they close the beat.

- Window every query with `from: "{{DQL_FROM}}", to: "{{DQL_TO}}"`, never `now()-Nh`: these are the incident
  window from the survey row (15 minutes of padding each side), so the query works however long ago it closed.
  A showcase has no incident window and uses relative windows instead.
- **Never write a tenant's host, or an entity id the survey resolves, into a link or a query.** A scenario can run
  on more than one environment, and a literal host sends the user to the wrong one. The full token list, all of
  which `test_deep_links.py` knows:

  | Token | What it is |
  |---|---|
  | `{{LINK_HOST}}` | the environment's host — **every** deep link starts `https://{{LINK_HOST}}/` |
  | `{{PROBLEM_SEGMENTS}}` | the problem link's segment parameter, empty outside the environment that has one |
  | `{{ROOT_CAUSE_ID}}` | the root-cause entity, from the survey row, instead of a hardcoded `SERVICE-…` |
  | `{{PROBLEM_ID}}`, `{{TF_FROM_MS}}`, `{{TF_TO_MS}}`, `{{TF_REL_H}}`, `{{TF_FROM_ISO}}`, `{{TF_TO_ISO}}` | the problem and its window, in each app's own format |
  | `{{DQL_FROM}}`, `{{DQL_TO}}`, `{{SURVEY_AT}}`, `{{TRACE_ID}}` | query windows, the elapsed anchor, and a chained value |

  An auxiliary id that the survey does *not* resolve (a second service, a host) stays literal, in the Scope
  table, with a row per environment.
- Never use `limit` where the beat's claim is about *everything* (all deploys, all distinct exceptions, the
  total sessions). Aggregate instead: `summarize … by:` per commit or per exception, oldest first, with
  `first_seen` / `last_seen`. A `sort desc | limit 5` once hid the deploy that caused the incident.
- Return few columns; select exactly what the beat needs.
- DQL must never contain INGEST, INSERT, UPDATE, DELETE, PUT or WRITE; the guard hook rejects it.
- A **chained** query takes a value from another query's first record (a trace ID, say): say so in the beat,
  name the field, and use `toUid("{{TRACE_ID}}")` for `trace.id`.

**Verify every field name against the live Playground; trust nothing from a spec or a past run.** The verified
gotchas (`start_time` not `timestamp`, `toDouble(duration)`, named `round(x, decimals: 1)`, bracket access after
`expand span.events`, `toUid()` on `trace.id`, deployment events, user sessions, logs) are in
`references/dql-reference.md`. Add each new one there, with the reason.

**Write `Reveal` as the shape of the finding, never its values.** Exception messages, commit SHAs, line
numbers, counts and teams rotate every problem cycle. "The failing spans carry a specific exception — quote it
verbatim" stays true; "the exception is X" is stale the next time the pattern fires. The agent reads the value
at run time. A reveal also states only what the returned fields show. Say what the data says, and say where
the data stops ("whether it was intended is the owning team's call"); never a cause, intent or geography that
no returned field contains.

**Success signal** is recognition, not compliance: "user names the failing service", not "user clicks next".

**Deep links** matter as much as queries: each beat should let the user open the real Dynatrace view of what
they just found in the terminal.

### 4. Peak moments

A climax (the finding that *is* the answer) or an emotional payoff (making the human impact concrete) gets
`peak_moment: true` and a **Staging** list: land the finding on its own line before commentary, pause, explain
what kind of finding it is, then the concrete next action. The skill's rule for the shared rhythm is in
`references/conversation-craft.md` → "Peak moments".

### 5. Business context and handoff

In `scenario-<id>.md`: `service_name`, optional `avg_order_value_usd` (omit it and the survey
reports no revenue figure rather than an invented one; the survey query computes `revenue_usd` from it). The
discovery hook is a row in the "Discovery hooks" table in `session-protocol.md`, with single-brace tokens
(`{affected_users}`, `{duration_min}`, `{revenue_usd}`). Only reference values the survey row supplies. If the problem record carries no clean rate, describe severity qualitatively and let a beat's query
carry the exact number.

**The hook opens on what a person using the product met, not on the component that broke.** "Shoppers
couldn't pay — card payments failed at checkout" rather than "the payment service was failing": a viewer
who does not know the architecture cannot size the second one. Keep it to scenario knowledge, never a
measured claim the survey row does not carry.

**Its `Route` cell** is a short closing clause naming what the investigation is *about* — "a cloud
permission, and whatever the AWS DevOps Agent made of it" — so the user can choose between incidents on
something other than a user count. It names the subject, never a finding, a cause or a count, and is
phrased openly enough that a beat returning no rows does not contradict it. `test_deep_links.py` fails a
hook row with an empty Route.

Hook and route live in `session-protocol.md`, never in the scenario file: the survey answers without
opening one (`tests/evals/dt-agent/survey-live.yaml` → `reads_exclude`).

**`approach`** is a row in the scenario's own Business context: one line in the SRE's voice proposing how
they would work it ("Here's how I'd work it: start with who it hit, then what changed on the service just
before, …"), said once as beat 1 opens and never recited again. It is the Feedforward principle below, and
`test_deep_links.py` fails an incident scenario without one. It is **not** `pull_line`, which is a status
line shown while queries run.

The **Handoff fields** table says which beat provides each value the agent needs to hand an incident to its
owner (owning team, commit and link, populations, replay link). If the owning team and the deploy owner
differ, say which is who. The row `Goes to` says who the handoff goes to: the team, or the host when there is no
team. The **Business context** table carries a `symptom` (a short phrase for what is failing) and, optionally,
`avg_order_value_usd`; without it a scenario gets no cost line. It also carries a `pull_line`: the one status
line the walk-through shows while it pulls the first query of every beat, naming what those queries fetch.

### 6. Register, validate, evaluate

1. Add the row to the Scenarios table in `SKILL.md` and the files to `SCENARIO_FILES` in
   `tools/validate_dt_skill.py` (the same dict feeds `run_dt_evals.py` and `preflight.py preflight`).
   List the environments its data exists on in `SCENARIO_ENVIRONMENTS` in `tools/preflight.py`, and add
   the same row to `session-protocol.md` -> "Environments" — `tools/tests/test_environments.py` fails if
   the two disagree. The validator then uses that environment, `preflight.py preflight` skips the
   scenario where it does not belong, and the opening never names it there.

   Its branch in the opening query must carry a predicate only that tenant's entities satisfy, and must
   stamp the environment into the `"env:scenario"` key. Match on entity id, never on entity name:
   playground and demo-live both run Astroshop, and a name match is how `disk-cpu-cascade` leaked onto
   the Playground in testruns 12 and 13. A scenario on more than one environment needs one Stable-IDs
   row per environment, and `--environment` becomes required when validating it.
2. `python tools/dt_agent.py check` — layout rules; `python tools/tests/test_deep_links.py` — every beat has a
   labelled deep link that uses only known tokens and a **Why this step** line.
3. **The narrative pass.** Read the scenario against "The narrative standard" below and write a verdict into
   `docs/narrative-review.md`: which principles it satisfies, which it does not, and the line that fails. A
   read-through is not a pass. Nothing automated can judge this, which is why it is a step rather than a test —
   and why the three incident scenarios each carry findings nobody had noticed until somebody did it.
4. `python tools/validate_dt_skill.py --scenario <id> [--environment <env>]` — runs the opening query (narrowed to the scenario) and **every** beat query live,
   including chained ones, and fails on a bad field name or `round()` call. Do not call a scenario done
   until it passes clean.
5. `python tools/validate_dt_skill.py --scenario <id> --links` prints each beat's label and its URL with the live
   problem's values. Open every one for a problem that has ended and judge it against its label: a link that opens a
   chat, an empty view (an app that falls back to its default last-30-minutes window) or an error fails. A link
   matching the beats file is not a pass (testruns 10 and 11 marked the Assist link as one; testrun 14 found it opens
   the assistant). Each app writes its own time-range format: copy the URL from the app, never from another app's link.
6. `python tools/preflight.py preflight` — the scenario shows as live, or as SKIP when its data lives on another
   tenant.
7. Upload and evaluate: `docs/DYNATRACE-SKILL.md`. Add an eval case under `tests/evals/dt-agent/` for any new
   behaviour. Run a full `/demo` session and write it up as a `docs/testrun-NN.md`.

## The narrative standard

`psychology-cheat-sheet.pdf` in this folder (growth.design, *Psychology of Design*, 106 principles) is
the standard every scenario is written against. It is not applied wholesale, for two reasons.

Read literally it contradicts itself — Hick's Law says cut the options, Group Attractiveness says
present them together — so an author needs a short list with a rule attached, not a reading list.
And several of its principles work by making a decision *less* rational. This demo is evidence-led;
using those on someone watching it would cut against the rule everything else rests on, and once
noticed would discredit every number said before. So they are excluded by name, not by omission.

**Do not use:** Scarcity, Social Proof, Decoy Effect, Bandwagon, Sunk Cost, Variable Reward,
Temptation Bundling, Hawthorne.

**The selected set.** Most of these name something the skill already does; naming it is what makes it
reviewable.

| Principle | The rule it becomes |
|---|---|
| Feedforward | State the approach before the first query, so the user knows the shape before it starts — the scenario's `approach` row, said once at beat 1 |
| Goal Gradient | Once a target is named, place every finding against it — "$2,454 against a $1,332 target" |
| Storytelling Effect | A scenario has an order and an argument; each Reveal connects to the one before |
| Chunking, Miller's Law | 3–5 fields per table, findings grouped |
| Peak-End Rule | `peak_moment` staging and the close decide how the session is remembered |
| Serial Position | In a list, what matters most goes first or last, never buried in the middle |
| Curiosity Gap | The opening names a gap without closing it ("where 10% of it is") |
| Anchoring | The first number in a turn is the impact figure, never a row count |
| Loss Aversion | Unowned spend is exposure, not a missed gain — "$6,725 nobody is accountable for" |
| Framing | Give the absolute and the share when the share carries the meaning |
| Reactance | Which incident to investigate is never recommended or ranked — the bullets are the choice. Inside an investigation a next step is proposed once; the other option gets no comment and no second attempt |
| Progressive Disclosure | Beats exist so the estate is not dumped in turn one |
| Curse of Knowledge | "What does that mean?" is answered in plain words, no product vocabulary assumed |
| Labor Illusion | The proof stamp shows the work behind the answer |
| Provide Exit Points | The close's way out is a real exit, not a hook to keep going |

Five of these change what the agent *says* and are therefore also stated in
`references/conversation-craft.md`: Feedforward, Goal Gradient, Anchoring, Reactance, Curse of
Knowledge. The rest are authoring guidance and stay here, out of the runtime context.

**Reviewing a scenario against it** means a written verdict, not a read-through: which principles it
satisfies, which it does not, and the line that fails. `docs/narrative-review.md` holds the current
verdicts.

## Showcase scenarios

A showcase shows a capability instead of resolving an incident (`scenario-cloud-observability.md` is the example). It
uses the same file layout, beats, reveals, deep links and data-only rule, with these differences:

- **No survey branch.** The user asks for it; the survey never finds or names it. Add the opening phrases to SKILL.md's
  opening table instead.
- **Tracks, when a showcase has more than one story in it.** A `## Tracks` section maps each arc to its beats
  and what it closes on, so entering in the middle walks one arc forward rather than backwards through another.
  The session close fires when the track's beats have all run, in whatever order they ran.
- **One delivery, and no `Requires:`.** A showcase is a presentation: no `mode_question`, no `pull_line`,
  and `references/walk-through.md` does not apply to it — no executive summary, no on-request report. It is
  always guided step by step, with a call to action after every step. Because nothing is ever offered, its
  beats declare no `Requires:`; `## Tracks` carries the ordering instead, and
  `tools/tests/test_deep_links.py` exempts showcases from the beat-graph check.
- **Its own tokens.** A "Tokens" section says which beat result fills each token: beat 1's `queried_at` is
  `{{SURVEY_AT}}`, and a beat that returns `problem_id`, `tf_from_ms` and `tf_to_ms` fills the problem link. Windows
  are relative (`now()-24h`, `now()-7d`), since there is no incident window.
- **Its own handoff.** The last beat is the handoff (an action list with owners); the Handoff fields table says where
  each row comes from.
- **Register it** in `SHOWCASES` in `tools/validate_dt_skill.py` as well as `SCENARIO_FILES`; the validator then skips
  the survey and harvests the tokens from the beat results, for both the live run and `--links`.
- **Extras** (optional): a `## Extra — <title>` section after the last beat, for a guide part that is offered after the
  close and is not part of the tour itself. It has its own evidence DQL, reveal and labelled deep link; the validator
  runs its query and `test_deep_links.py` counts its link.

## What the agent guarantees

It reads your two files and runs your queries. It will:

- add no scenario knowledge it did not read from them, and state no value it did not read from a result;
- never modify the Playground (read-only context, guard hook, permission allow-list);
- narrate your Reveal as its own read of the evidence in the same turn, attached to a next step, never
  withheld until the user guesses and never a dead end;
- offer the deep link at the end of each beat, and follow the user's detours before re-anchoring on what is
  still unknown;
- when the user asks to be walked through it, deliver the same beats in the same order, one per turn,
  each following from the last, with nothing offered and the user only ever saying "next" — and close
  with a handoff block built only from your Handoff fields table. A value the table has no source for is
  left out of the block, so say plainly there when a scenario has no owning team or no user count. The
  condensed one-turn report still exists but only when asked for by name (`walk-through.md` → "The
  report, on request");
- show no query ID: local `/demo` adds a proof stamp from the dtctl envelope, the Dynatrace agent shows none.

It will not guarantee that entity IDs stay stable if the Playground is reset, and it does not parse a failure
rate out of the problem description text: take exact rates from an evidence query.
