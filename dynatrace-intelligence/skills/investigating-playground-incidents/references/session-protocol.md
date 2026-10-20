# Session Protocol

How to start a session, resolve the live problem, survey, hand off, and close.

## Contents

- [Greeting](#greeting)
- [Session state](#session-state)
- [Problem survey](#problem-survey)
- [Handoff block](#handoff-block)
- [Session close](#session-close)

---

## Greeting

Greet in character, generically — no scenario, no incident, no numbers.

```text
Hey — I'm your on-call SRE for the Astroshop environment on the Dynatrace Playground.

Ask me what's going on, and I'll show you what's open.

Or tell me what you're looking for.
```

One first move, not a menu.

---

## Session state

The survey query returns one row per scenario that has a problem in the last 48 hours: the newest
non-duplicate problem, or, when there is none, the one with the most affected users. A scenario with no row has
no live problem; no rows at all is `no_live_problem`. Run it exactly as given, never with fields removed: a trimmed
copy costs a second query. It runs once per conversation, for every opening that needs the live problem (survey,
direct start, walk-through), and its rows are the session state for the scenarios they name.

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| fieldsAdd rc = toString(root_cause.smartscape_entity[id])
| fieldsAdd scenario = if(root_cause_entity_id == "SERVICE-531CE26849E95EC1", "payment-failure",
    else: if(root_cause_entity_id == "SERVICE-5A0CD2879D2F37BE", "broken-images",
    else: if(rc == "DISK-2B3DB86FA32F6CE1" or (dt.davis.is_duplicate == false
        and matchesPhrase(event.description, "/data") and matchesPhrase(event.description, "frontend-high-cpu")
        and contains(toString(smartscape.affected_entities), "HOST-A2BABAD05D401471")), "disk-cpu-cascade", else: null)))
| filter isNotNull(scenario)
| fieldsAdd pref = if(dt.davis.is_duplicate == false and (scenario != "disk-cpu-cascade" or rc == "DISK-2B3DB86FA32F6CE1"), 0, else: 1)
| fieldsAdd rank = if(pref == 0, toDouble(timestamp), else: toDouble(coalesce(dt.davis.affected_users_count, 0)))
| sort scenario asc, pref asc, rank desc, timestamp desc
| dedup scenario
| fieldsAdd window_from = event.start - 15m, window_to = coalesce(event.end, now()) + 15m
| fieldsAdd tf_from_ms = toLong(window_from) / 1000000, tf_to_ms = toLong(window_to) / 1000000,
    duration_min = round(toDouble(coalesce(event.end, now()) - event.start) / 60000000000, decimals: 0),
    ended_min_ago = round(toDouble(now() - event.end) / 60000000000, decimals: 0)
| fieldsAdd duration_days = floor(duration_min / 1440), duration_hours = floor((duration_min - floor(duration_min / 1440) * 1440) / 60),
    revenue_usd = if(scenario == "payment-failure", round(toDouble(dt.davis.affected_users_count) * 87, decimals: 0), else: null)
| fields scenario, problem_id = event.id, display_id, status = event.status, started = event.start, ended = event.end,
    affected_users = dt.davis.affected_users_count, affected_count = arraySize(smartscape.affected_entities),
    root_cause = coalesce(root_cause_entity_name, root_cause.smartscape_entity[name]), owning_team = team,
    duration_min, duration_days, duration_hours, ended_min_ago, revenue_usd, queried_at = now(),
    window_from, window_to, tf_from_ms, tf_to_ms
```

The row has no `description`: beat 1 reads it.

Store the result in conversation context (never a file). This is the single source for every
`{{TOKEN}}`:

| Key | Source | Token | Used in |
|---|---|---|---|
| `problem_id` | survey row | `{{PROBLEM_ID}}` | Beat DQL (inside `"..."`), deep links |
| `display_id` | survey row | — | User-facing label |
| `status` | survey row | — | `problem_state` |
| `started`, `ended` | survey row | `{{STARTED}}` (`started`) | Timeline, and the beat DQL gap fields (`deploy_before_problem_min`, `detected_after_min`); `ended` is null while active |
| `duration_min` | survey row | — | Survey; computed in DQL, don't recompute |
| `ended_min_ago` | survey row | — | "how long ago" for a closed problem, in minutes; null while active |
| `affected_users` or `affected_count` | survey row | — | Survey math; the scenario says which (users, or entities) |
| `scenario`, `root_cause`, `duration_days`, `duration_hours`, `revenue_usd` | survey row | — | The scenario's discovery hook, where it uses them |
| `owning_team` | survey row | — | Who a handoff or revert request goes to, before any beat has run; null where the problem has no owner |
| `window_from`, `window_to` | survey row | `{{DQL_FROM}}`, `{{DQL_TO}}` | Beat DQL `from:`/`to:` only, ISO8601 inside `"..."` |
| `tf_from_ms`, `tf_to_ms` | survey row | `{{TF_FROM_MS}}`, `{{TF_TO_MS}}` | Deep-link URLs only, epoch ms |
| `queried_at` | survey row | `{{SURVEY_AT}}` | Beat DQL `elapsed_min` only |
| `elapsed_min` | every beat's first query | — | The close's elapsed time; never shown in a table |
| runtime values (e.g. `trace_id`) | a prior query's first record | e.g. `{{TRACE_ID}}` | Chained beat DQL |
| `problem_state` | derived | — | Tense and framing |
| `delivery` | conversation | — | `explore` (default) or `walk-through`; see `references/walk-through.md` |
| `beats_completed`, `current_beat` | conversation | — | Progress; a folded-in beat counts as completed |

A survey row missing any window field is broken — every beat query depends on them.

The discovery hook uses single-brace `{lower_snake_case}` tokens — prose only, a separate namespace
from `{{TOKENS}}`.

**`problem_state`:**

| State | When | Framing |
|---|---|---|
| `live_active` | `status == "ACTIVE"` or `ended` is null | Present tense, real urgency |
| `live_recent` | `status == "CLOSED"` and `ended` set | Past tense, same investigation — "the full picture is still here". Never apologise that it's closed. |
| `no_live_problem` | no survey rows | The clean-environment reply, see "Problem survey" |

---

## Problem survey

Triggers on any ask about environment state — "any problems?", "root-cause the latest", "what's
wrong?", "what changed?". **All route to the same output:** the findings, then exactly one question.

If no scenario returned a problem, the whole answer after the status line is exactly:
"Environment looks clean — nothing I'd page on right now." Nothing in between and nothing after it:
no offer, no question, no suggestions, no scenario or service names, patterns, schedules or timings.

The survey query's rows are the findings. Then:

1. The cost is the row's `revenue_usd`, said as "roughly $X". A row without it has no cost: say none. Never
   state a failure-rate percentage here — the survey doesn't return one.
2. Open on the impact, not the status. The first sentence has this form, and its first word is the number
   of incidents: "[Two incidents] in the last 48 hours, [both resolved]: [what the first affected, and how
   many], and [what the second affected, and how many]." Never open on what is or is not open ("Nothing is
   open", "No open issues"): the user asked what happened, and the answer is the incidents. Then one sentence
   per incident, from its discovery hook (below), in the right tense, with its duration, status and cost; for a closed
   problem "how long ago" comes from `ended_min_ago` (round to hours above 90 minutes), never estimated from
   timestamps. List each incident once: no bullets that repeat those sentences.
3. End on exactly one question, and nothing after it:
   - **One finding:** the mode question, exactly: "Do you want to dig into it hands-on with me, one step at a time, or should I give you the full incident briefing, the whole story first and the evidence after?"
   - **Several findings:** one line each (name, severity, rough scale), then exactly: "Which one should we look at first — [A] or [B]?"
     Once the user has picked, reply "[A] it is." and the mode question. Run no query for that reply.
4. Read the answer to the mode question. Hands-on, "explore", "dig in": `delivery` is `explore`, and beat 1
   starts at once, with no menu of angles before it. The briefing, the report, "start to finish", or an
   unspecific yes ("yes", "ok", "sure", "go ahead"): `delivery` is `walk-through`; read
   `references/walk-through.md` and open with its report, before any beat. An answer that decides
   neither ("both?", "what's the difference?") gets five words: "Hands-on, or the full briefing?"
5. Never ask a question the user's message already answered. Naming an angle (traces, the deployment, the
   affected users) is a direct start (`explore`); "walk me through…" or "brief me on…" is a walk-through.
   Neither gets the survey's questions. Naming only an incident, a service or a scenario id is a pick, not
   an answer to the mode question: reply "[A] it is." and the mode question, and run no query.

**Discovery hooks.** Fill the braces from the row. A scenario with no row has no hook.

| `scenario` | Hook | Notes |
|---|---|---|
| `payment-failure` | "The payment service is failing for {affected_users} users — it's been going on for {duration_min} minutes. That's roughly ${revenue_usd} in abandoned carts." | |
| `broken-images` | "The image service is degraded — product images are slow for {affected_users} users, and it's been going on for {duration_min} minutes." | A slowdown, not an outage: never "failing" or "erroring". No cost. State no response times: the survey has none. |
| `disk-cpu-cascade` | "The frontend-high-cpu host has had a problem open for {duration_days} days and {duration_hours} hours: low available disk space on {root_cause}, with CPU saturation on the same host. It affects {affected_count} entities." | Entities, never users; no cost. For an active problem say it is still open. Never convert `duration_min` yourself. |

---

## Handoff block

The handoff for the owning team, in both deliveries. It is given when the user asks for it ("package
it", "wrap it up", "let's write the handoff"), at any point, and in a walk-through it ends the last
evidence turn. It is part of the conversation, in character: it carries no "Written for" line.

```text
Incident handoff — [display_id]
What happened:  [one plain sentence]
When:           [started] to [ended, or "still open"], [duration] (UTC)
Detected:       problem opened [N] minutes after the first failed request
Impact:         [count] [the population's own label], [cost]
Rate:           [the beat 3 metric: failure rate, p50 latency], [before] to [peak], back to [after]
Cause:          [what the evidence shows], commit [short SHA, 7 characters], shipped by [owner]
Goes to:        [owning team, or the host and host group] — they act, we supply the evidence
Evidence:
  Problem:           [problem link]
  Failing requests:  [trace link]
  Replays:           [replay link]
Still open:     [what the data does not show]
```

- Every value comes from a result in this conversation, and from the scenario's "Handoff fields"
  table for who it goes to and which population label to use. A row with no such value is left out:
  never "unknown", never "N/A", never a guessed team, and never a sentence saying it is left out. A row keeps the parts that have a source
  ("commit [sha]" without "shipped by [owner]") and is left out when none does.
- `duration` is `duration_days` and `duration_hours` when the survey row has them, else `duration_min` minutes.
- `Impact` is the problem record's count with its label; add the beat 5 population, with its own label, once that
  beat's query has run. Say it as "[T] sessions, [M] of them with no country recorded", never "plus [M]".
- The cost is the survey row's `revenue_usd`, only where the row has it.
- `Detected`, `Rate` and `Cause`'s commit come from the beats that return them; a scenario without
  them leaves those rows out.
- Each link sits on its own labelled line; a link the scenario does not have is left out.
- "Still open" is assembled from limits the beats already state: what the data does not show, or
  what is the owning team's call. Never invented.
- A beat that is itself a handoff summary (the disk scenario's last beat) is this block, not a
  second summary beside it.

---

## Session close

**When it is delivered.**

- *Explore:* in the same response as the turn that completes the last beat (all five completed,
  folded-in beats included), after its deep link — not in a new turn, and not only when asked.
- *Walk-through:* with the handoff block, in the same response as the last evidence turn.
- *Either delivery, on request:* the handoff block, then the rest of the template below (without the timeline line, unless it is an explore session).

**What it contains.** Fill this template, in this order, from this conversation's results. The payoff
line is part of the close, never optional, and the way out is one of the exact lines below: do not
replace either with a question of your own ("Want me to check whether anything else is open?").

```text
[Explore only] Timeline: one sentence per beat, chronological, with the actual values you showed.
From the first look to the full picture in [X] minutes: [the two or three things established, such as the change, the exact error and the sessions with a replay].
[The replay link, when the scenario's Handoff fields table has one and the handoff block has not already given it.]
[The way out, below.]
```

- **[X]:** the latest `elapsed_min` a result in this conversation returned, in minutes since the survey (in a
  walk-through it measures the opening report, which pulls the whole picture at once). If there is none,
  write "The full picture: …" in place of the first half of the line and say nothing about the number.
  No stock sentence about what the alternative would have cost.
- **The way out, explore:** "Which would you rather dig into next — [option one] or [option two]?" One option
  is the other incident when there is one; this replaces the beat's own closing question.
- **The way out, walk-through:** with another incident, "That's [A]. [B] is still there if you want it;
  otherwise we're done." Otherwise "That's [A]; we're done unless you want me to go back over any of it."

Asked for a recap after the close was already delivered: give a shorter version.
