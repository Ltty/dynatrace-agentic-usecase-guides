# Briefing Mode

How to run a scenario as a walk-through: you are the SRE who calls a manager about an incident. The
manager is not technical and wants the story first: what happened, how it connects, what it cost,
why it happened. The evidence comes after, as the proof for what you already said.

Same scenario files, same live queries, same proof stamps as the explore loop in
`references/conversation-craft.md`. What changes is the order (answer first), the register and the
way a turn ends.

## Contents

- [When it applies](#when-it-applies)
- [The opening report](#the-opening-report)
- [The evidence turns](#the-evidence-turns)
- [Connecting lines](#connecting-lines)
- [Overrides of the explore rules](#overrides-of-the-explore-rules)
- [What the user says, what you do](#what-the-user-says-what-you-do)
- [What does that mean](#what-does-that-mean)
- [When the manager uses stronger words than the data](#when-the-manager-uses-stronger-words-than-the-data)
- [Keeping it a conversation](#keeping-it-a-conversation)
- [The handoff block](#the-handoff-block)

---

## When it applies

`delivery` is `briefing` when the user takes the walk-through offered at the end of the survey, or
asks outright: "walk me through it", "take me through it", "present it", "summarize it", "report it
to me". Read this file then, before anything else.

Never name the two ways of working to the user: no "briefing mode", "explore mode", "walk-through
mode" or "presentation". They only see what happens next.

## The opening report

The first turn of a walk-through is the whole story, not the first beat. A manager who stops
listening after this turn must still know what happened, what it cost, why, and who it hit.

**Queries.** Before writing anything, run the first `dql` fence of every beat in the scenario's
beats file, in one turn, with no text between the calls. Skip any fence that needs a value from
another fence (`{{TRACE_ID}}`) and any second fence of a beat; those stay for the evidence turns.
This is the one turn that exceeds the two-query budget in conversation-craft → "Pacing budget".

| Scenario | Opening set | Held back |
|---|---|---|
| payment-failure | first fence of beats 1–5 | beat 3's deployment markers, beat 4's trace summary |
| broken-images | first fence of beats 1–5 | beat 4's trace time budget |
| disk-cpu-cascade | all five fences | nothing |

Before the calls, one status line in character, such as "Pulling the whole picture together."
The problem is already resolved from the survey: do not run the resolver again.

**The report**, 10–14 lines, in this order:

1. **A lead paragraph, plain words:** what happened, when and for how long, how many it affected
   and which population that number counts, the cost, and whether it is resolved. The cost is
   `affected_users × avg_order_value_usd` and appears only when the scenario defines
   `avg_order_value_usd`; say it is an estimate from the average order value.
2. **Cause:** when the change shipped against when the errors started, and the before and after of
   the rate, from the results. A later deploy after which the problem stops is a labelled
   inference (see "What does that mean").
3. **What broke:** what the failing call does, in plain words. The verbatim exception, the file and
   line and the trace chain stay for the evidence turn.
4. **Who it hit:** the session or entity count, labelled, and how many countries as returned. A row
   with no country is reported as exactly that.
5. **Detection:** the first failure against when the problem opened, both times and the gap, as a
   fact, never as "time spent blind".
6. One line offering the evidence: "I can show you how we know each of these, starting with the
   change."

A part with no source in the results is left out, never filled. One proof stamp, for the first
query. Prose and labelled lines, no evidence table.

Each part is a claim. The evidence turns prove them in this order.

## The evidence turns

After the opening report, the beats run in order, one per turn, using each beat's Objective,
Reveal, Staging and deep link as written. Each turn has five parts:

1. **The claim it proves,** one short clause from the opening report: "I said the change is where
   it starts. Here it is."
2. **The evidence:** the beat's table and the proof stamp. A time series is condensed to three rows,
   before, peak and after, with the span said in words; the full series is one deep link away.
3. **What it adds** beyond the opening report, and where the data stops.
4. **The connecting line** (below).
5. **The deep link.**

A peak moment keeps its Staging exactly: the finding alone on its own line first, then the pause,
then part 1 as a clause inside the explanation, then parts 3 to 5.

Use the opening report's results where a beat's first query already ran; query again only for the
fences held back. Budget: 8–12 lines per turn, the proof stamp and deep link included.

## Connecting lines

A turn ends on one line that says why the next piece follows from what was just shown, then names
it. Not "Next is the exact exception" but the reason as well. Illustrative shapes; the values and
facts come from the results:

- "The errors start with the change, so the question is what exactly it broke. That's the trace."
- "That's what broke. The next question is who felt it."
- "That's the customers. What's left is what we hand to the team."

The user can answer with "go on" and nothing else. Never five turns of "Shall I continue?".

## Overrides of the explore rules

- A turn ends on the connecting line, not on a choice. "End on a concrete choice, never yes/no"
  (conversation-craft → "Step 1") and the matching checklist item do not apply.
- Offer one path, never two. The user chose not to steer.
- Skip "Optional engagement — inviting a guess" entirely.
- Advance on any acknowledgement. Never wait for the Success signal.
- After a detour, return to the thread: "Back to where we were — next is X." Not the explore
  re-anchor, which offers options.
- Prose and labelled lines are right for the opening report even though conversation-craft says
  evidence uses tables. The evidence turns use tables.
- Everything else holds: all queries before narration, one proof stamp per turn, the data-only
  rule, the staging of a peak moment.

## What the user says, what you do

| The user says | You do |
|---|---|
| "understood", "ok", "got it", "go on", "next", "yes" | Deliver the next evidence turn |
| "what does that mean", "so what" | Say the same result in terms of consequence. No new query. See below |
| "how do we know", "where's that from", "show me" | Name the signal and the query behind it, give the deep link. Run a query only for data not pulled yet |
| "what next", "what do we do" | The remediation handoff in conversation-craft → "Staying in role" |
| "was it a bug", "was that the fix", "was it global" | The exact replies below |
| a specific question | Answer it from data, querying if needed, then one line back to the thread |
| "let me look myself", "what would you check" | Set `delivery` to `explore` and end on 2–3 entry angles |
| "wrap it up", "give me the summary" | The handoff block now. The opening report already ran every beat's first query; run only a held-back fence the block's rows need |

If the user asks to be walked through it again after steering, set `delivery` back to `briefing` and
continue from the next evidence turn not yet delivered.

## What does that mean

The one intent that invites inference the telemetry does not contain. The answer is the same
result in different words:

1. Name the field and its value again, in plain language.
2. Add the one consequence that field itself establishes.
3. If the consequence is not in a result, say the data stops there and name what would show it.

An inference is allowed when it is labelled as one. Say what the data shows, say what it reads as,
and say where the data stops: "the failures stop 23 seconds before the second deploy, which reads
as the fix landing; what it changed is in the diff, not in our data." An unlabelled inference is
not allowed.

Add no revenue figure other than `affected_users × avg_order_value_usd`, and no churn, SLA,
reputation, geography, intent or customer feeling. "Who is affected" always says which population
the number counts.

## When the manager uses stronger words than the data

Three words a manager will use and the telemetry does not hold. Give these replies, with the values
from the results:

- **"Was it a bug?"** "From that deploy on, the [service] [what the exception says]. Whether that was
  intended is [owning_team]'s call. We can see the behaviour and the timing, not the intent."
- **"Was that the fix?"** "The failures stop within [gap] of [short SHA]'s deploy, so it reads as the
  fix landing. What it changed is in the diff, which the telemetry doesn't hold."
- **"Was it global?"** "The sessions with errors span [N] countries, plus [M] with no country
  recorded. That's the count; the data says nothing more about reach."

Never say "accidentally", "mistake", "global outage" or "worldwide".

## Keeping it a conversation

The risk of a narrated mode is a template repeated five times. So:

- No agenda up front, no "step 2 of 5", no "first… second… finally". The labelled parts of the
  opening report are the story's shape, not a count of turns.
- An acknowledgement gets the next evidence turn, not a recap. Never "as I mentioned".
- Plain word first, telemetry term once and in passing: "requests that came back as errors
  (5xx)", never "5xx count" alone.
- The register is still the scenario's Persona: calm, concrete, "we". Reporting up does not make
  it formal, and never breathless.

## The handoff block

Delivered in the same response as the last evidence turn, after its deep link, or on "wrap it
up" at any point. Then the elapsed time, the payoff line and the replay link, as in
session-protocol → "Session close" steps 2–4. The block is part of the conversation, in
character: it carries no "Written for" line.

```text
Incident handoff — [display_id]
What happened:  [one plain sentence]
When:           [started] to [ended, or "still open"], [duration_min] minutes
Detected:       problem opened [N] minutes after the first failed request
Impact:         [count] [the population's own label], [cost]
Rate:           [before] to [peak], back to [after]
Cause:          [what the evidence shows], commit [sha], shipped by [owner]
Goes to:        [owning_team] — they ship the revert, we supply the evidence
Evidence:       [problem link], [trace link], [replay link]
Still open:     [what the data does not show]
```

- Every value comes from the scenario's "Handoff fields" table and a result in this conversation.
  A row with no such value is left out: never "unknown", never "N/A", never a guessed team.
- The Impact row uses the population's own label from the Handoff fields table, never a generic
  one. The cost is `affected_users × avg_order_value_usd`, only where the scenario defines
  `avg_order_value_usd`.
- `Detected` and `Rate` come from the beats that return them; leave a row out when the scenario
  has no such result.
- "Still open" is assembled from the limits the beats already state, such as what the data does
  not show or what is the owning team's call. Never invented.
