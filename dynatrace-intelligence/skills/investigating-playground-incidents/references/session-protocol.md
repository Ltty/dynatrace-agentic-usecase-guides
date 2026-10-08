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

Ask me things like:
  • "Root-cause the latest problem"
  • "What changed in the last few hours?"
  • "Are there any open issues right now?"

Or tell me what you're actually looking for.
```

The starters illustrate a kind of question, not a fixed menu.

---

## Session state

Each scenario provides a **primary** and a **fallback** resolver DQL. Run each exactly as the file
gives it, never with fields removed: the later fields are needed, and a trimmed copy costs a second
query. Run the primary; if it returns zero rows, run the fallback; use the first row. If both are
empty, `problem_state` is `no_live_problem`.

Store the result in conversation context (never a file). This is the single source for every
`{{TOKEN}}`:

| Key | Source | Token | Used in |
|---|---|---|---|
| `problem_id` | resolver | `{{PROBLEM_ID}}` | Beat DQL (inside `"..."`), deep links |
| `display_id` | resolver | — | User-facing label |
| `status` | resolver | — | `problem_state` |
| `started`, `ended` | resolver | — | Timeline; `ended` is null while active |
| `duration_min` | resolver | — | Survey; computed in DQL, don't recompute |
| `ended_min_ago` | resolver | — | "how long ago" for a closed problem, in minutes; null while active |
| `affected_users` or `affected_count` | resolver | — | Survey math; the scenario says which (users, or entities) |
| `root_cause`, `description`, `duration_days`, `duration_hours` | resolver | — | The scenario's discovery hook, where it uses them |
| `window_from`, `window_to` | resolver | `{{DQL_FROM}}`, `{{DQL_TO}}` | Beat DQL `from:`/`to:` only, ISO8601 inside `"..."` |
| `tf_from_ms`, `tf_to_ms` | resolver | `{{TF_FROM_MS}}`, `{{TF_TO_MS}}` | Deep-link URLs only, epoch ms |
| `queried_at` | resolver and every beat's first query | — | Elapsed time in the close; never shown in a table |
| runtime values (e.g. `trace_id`) | a prior query's first record | e.g. `{{TRACE_ID}}` | Chained beat DQL |
| `problem_state` | derived | — | Tense and framing |
| `delivery` | conversation | — | `explore` (default) or `walk-through`; see `references/walk-through.md` |
| `beats_completed`, `current_beat` | conversation | — | Progress; a folded-in beat counts as completed |

A resolver row missing any window field is broken — every beat query depends on them.

The discovery hook uses single-brace `{lower_snake_case}` tokens — prose only, a separate namespace
from `{{TOKENS}}`.

**`problem_state`:**

| State | When | Framing |
|---|---|---|
| `live_active` | `status == "ACTIVE"` or `ended` is null | Present tense, real urgency |
| `live_recent` | `status == "CLOSED"` and `ended` set | Past tense, same investigation — "the full picture is still here". Never apologise that it's closed. |
| `no_live_problem` | both resolvers empty | The clean-environment reply, see "Problem survey" |

---

## Problem survey

Triggers on any ask about environment state — "any problems?", "root-cause the latest", "what's
wrong?", "what changed?". **All route to the same output:** findings and entry angles first, beat
loop only once the user picks a direction.

If no scenario returned a problem, the whole answer after the status line is exactly:
"Environment looks clean — nothing I'd page on right now." Nothing in between and nothing after it:
no offer, no question, no suggestions, no scenario or service names, patterns, schedules or timings.

For each scenario in the SKILL.md registry, run its resolver. Then:

1. `revenue_impact = affected_users × avg_order_value_usd`, from the scenario's business context,
   said as "roughly $X". Omit it if the scenario doesn't define `avg_order_value_usd`. Never state a
   failure-rate percentage here — the resolver doesn't return one.
2. Fill the scenario's discovery hook, and say it like a human SRE reporting to a peer, in the right
   tense. For a closed problem, "how long ago" comes from `ended_min_ago` (round to hours above 90
   minutes), never estimated from timestamps.
3. End on 2–3 concrete entry angles (e.g. the deployment, the traces, the customers who hit
   it) — never a yes/no — then one closing sentence, exactly: "Or I can take you through the whole
   thing, start to finish." Naming an angle or a service sets `delivery` to `explore`. Taking the
   offer sets it to `walk-through`: read `references/walk-through.md` and open with its report,
   before any beat. A direct start gets no offer.

Several scenarios found: one line each (name, severity, rough scale), then the offer. If the user
takes it without naming one, ask exactly: "Which one — [first] or [second]?"

In a survey, name only the scenarios that returned a problem, and say nothing about the others: an empty result says nothing about a service. Never write a sentence such as "the payment service and image service are clean", or any sentence that names a service whose scenario returned nothing.

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
Cause:          [what the evidence shows], commit [sha], shipped by [owner]
Goes to:        [owning team, or the host and host group] — they act, we supply the evidence
Evidence:       [problem link], [trace link], [replay link]
Still open:     [what the data does not show]
```

- Every value comes from a result in this conversation, and from the scenario's "Handoff fields"
  table for who it goes to and which population label to use. A row with no such value is left out:
  never "unknown", never "N/A", never a guessed team, and never a sentence saying it is left out. A row keeps the parts that have a source
  ("commit [sha]" without "shipped by [owner]") and is left out when none does.
- `duration` is `duration_days` and `duration_hours` when the resolver returns them, else `duration_min` minutes.
- `Impact` is the problem record's count with its label; add the beat 5 population, with its own label, once that
  beat's query has run.
- The cost is `affected_users × avg_order_value_usd`, only where the scenario defines it.
- `Detected`, `Rate` and `Cause`'s commit come from the beats that return them; a scenario without
  them leaves those rows out.
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
- *Either delivery, on request:* the handoff block, then steps 2–4.

**What it contains.**

1. *Explore only:* the timeline, one sentence per beat, chronological, with the actual values you
   showed.
2. Elapsed time: the latest `queried_at` seen in this conversation minus the survey's, in whole
   minutes. If either is missing, leave the number out and say nothing about it. In a walk-through the number measures the opening report, which
   pulls the whole picture at once.
3. The payoff: "From the first look to the full picture in [X] minutes." followed by the scenario's
   `payoff` sentence, if its business context defines one. Without a measured X, the payoff sentence
   alone; with neither, nothing.
4. The replay link, when the scenario's Handoff fields table has one and the handoff block has not already given it.
5. *Explore:* ask what they'd want to dig into next, naming two or three angles; this replaces the beat's own closing
   question. *Walk-through:* "Happy to go back over any of
   it."

Asked for a recap after the close was already delivered: give a shorter version.
