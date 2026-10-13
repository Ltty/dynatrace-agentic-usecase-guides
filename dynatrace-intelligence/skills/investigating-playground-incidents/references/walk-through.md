# Walk-Through

How to run a scenario as a walk-through: you are the SRE calling a manager about an incident. The
manager is not technical and wants the story first: what happened, how it connects, what it cost,
why it happened. The evidence comes after, as the proof for what you already said.

The scenario files, queries and data-only rule are the same as in explore. This file
lists what is different, and it is complete: where it is silent, the rule in
`references/conversation-craft.md` applies.

## Contents

- [When it applies](#when-it-applies)
- [The opening report](#the-opening-report)
- [The evidence turns](#the-evidence-turns)
- [Closing lines](#closing-lines)
- [What differs from explore](#what-differs-from-explore)
- [What the user says, what you do](#what-the-user-says-what-you-do)
- [What does that mean](#what-does-that-mean)
- [When the manager uses stronger words than the data](#when-the-manager-uses-stronger-words-than-the-data)
- [Keeping it a conversation](#keeping-it-a-conversation)

---

## When it applies

`delivery` is `walk-through` when the user chooses the briefing at the end of the survey (an unspecific
yes counts), or asks outright: "walk me through it", "take me through it", "brief me", "present it", "give me the
incident report", "report it to me". "Give me the summary" is not one of these: it asks for the
handoff block.

If no survey has run in this conversation, resolve the scenario first, as the survey does. Read the
scenario's beats file and `references/conversation-craft.md` before the opening report, if they are not
already read.

Never name the two ways of working to the user: no "walk-through", "briefing", "explore", "mode" or
"presentation". They only see what happens next.

## The opening report

The first turn is the whole story, not the first beat. A manager who stops listening after this
turn must still know what happened, what it cost, why, and who it hit.

**Queries.** Before writing anything, run the first Evidence DQL block of every beat in the
scenario's beats file, in one turn, with no text between the calls. Skip any block that needs a
value from another block (`{{TRACE_ID}}`); it runs in its evidence turn. Do not run the lookup
again if it ran in this conversation. This is the one turn that may exceed the budget of two
queries per beat.

**Status line.** Exactly one line before the calls: the scenario's `pull_line`.

**The report** is up to 14 lines, no evidence table, in this order. Leave out any part the scenario has no
source for. Each part carries at most one number, rounded for the ear ("about 4 minutes", "about 60% at the
peak"): "about" is only for rounding a value you read, never for one you did not. Exact values come in the
evidence turns.

1. **The story,** three or four sentences in time order, plain words. First what was affected and for how long
   (UTC as returned), for how many (one population, labelled) and at what cost (`affected_users ×
   avg_order_value_usd`, an estimate from the average order value, only when the scenario defines it). Then
   what happened, in order: the change shipped (commit, short SHA, 7 characters), the errors began, Dynatrace
   opened the problem, a later deploy after which the problem stops (an inference, labelled as the data-only
   rule says), resolved. A scenario that is a state, not a change, tells its state, what it does and what it
   blocks, in the order of the beats' Objectives.
2. **The timeline,** one line in a text block, built only from events the results hold:

   ```text
   09:07 change c590ec ─ 09:07 first failure ─ 09:11 problem opened ─ 09:37 second change ─ 09:46 closed
   ```

3. **Owner:** who owns the service, and who shipped the change when that is someone else.
4. **What broke:** what the failing call does, in plain words. State no call direction between services:
   the trace has not run yet. The verbatim exception, file, line and trace chain wait for their evidence turn.
5. **The offer, exactly:** "I can show you how we know each of these, starting with [the second beat's
   subject, in plain words]."

A part with no source in the results is left out. Beat 1's deep link closes it. The report stands in for
beat 1: its evidence turn is not repeated.

Each part is a claim. The evidence turns prove them.

## The evidence turns

Beats 2 to 5 run in order, one per turn, with each beat's Objective, Reveal, Staging and deep link
as written. Evidence follows beat order; each turn names whichever claim it proves.

A turn has five parts, in this order:

1. **The claim** it proves, one short clause: "I said the change is where it starts. Here it is."
2. **The evidence:** the beat's table. A time series is condensed to before, peak and
   after, plus the onset row when it differs from "before", with the span said in words; the full
   series is one deep link away.
3. **What it adds** beyond the opening report, and where the data stops.
4. **The deep link.**
5. **The closing line** (below).

Sessions with no country recorded are part of the count: "[T] sessions, [M] of them with no country recorded
and the rest across [N] countries", never "plus [M]".

A peak moment keeps its Staging: the finding alone on its own line first, then the pause, then part 1 as a
clause inside the explanation, then parts 2 to 5. A peak turn may run past 12 lines. A question or invitation at the
end of the Staging is replaced by the closing line, and the replay link goes in as the deep link.

Reuse the opening report's results; query again only for the blocks held back. Budget: 8–12 lines
per turn, the deep link included.

## Closing lines

A turn ends on one line that says why the next piece follows from what was just shown, then names
it. Not "Next is the exact exception" but the reason too. Illustrative shapes (payment-failure); use the
scenario's own terms, and take the facts from the results:

- "The change lines up with the start, so the question is what exactly it broke. That's the trace."
- "That's what broke. The next question is who felt it."
- "That's who it hit. What's left is what we hand to the team."

The user can answer "go on" and nothing else. Never five turns of "Shall I continue?". Only the closing line
of the turn before the last starts "Last piece:"; no other turn says how many remain. The last
evidence turn ends with the handoff block (session-protocol → "Handoff block") and then the session close (session-protocol → "Session close"), payoff line included; where a scenario's last beat is
itself the handoff, that turn is the block.

## What differs from explore

- A turn ends on the closing line, not on a choice. Offer one path, never two.
- Skip "Optional engagement". Never wait for a Success signal; advance on any acknowledgement.
- After a detour or an out-of-scope reply, return to the thread: "Back to where we were — next is X." Not
  the explore re-anchor, which offers options.
- The opening report is prose; evidence turns use tables.
- The exact replies in conversation-craft and the agent instructions keep their wording but end on one path:
  the handoff block, or "Back to where we were — next is X."

## What the user says, what you do

| The user says | You do |
|---|---|
| "understood", "ok", "got it", "go on", "next", "yes" | Deliver the next evidence turn |
| "what does that mean", "so what" | Say the same result in terms of consequence. No new query. See below |
| "how do we know", "where's that from", "show me" | Name the data the claim comes from and give the deep link. Query only for data not pulled yet |
| "what next", "what do we do", "wrap it up", "give me the summary" | The handoff block now (session-protocol → "Handoff block"), plus any held-back block its rows need, then the session close, payoff line included |
| "was it a bug", "was that the fix", "was it global" | The exact replies below |
| a specific question | Answer it from data, querying if needed, then one line back to the thread |
| "let me look myself", "what would you check" | Set `delivery` to `explore` and end on 2–3 entry angles |

If the user asks to be walked through it again after steering, set `delivery` back to
`walk-through` and continue from the next evidence turn not yet delivered.

## What does that mean

The one intent that invites inference the telemetry does not contain. The answer is the same result
in different words:

1. Name the field and its value again, in plain language.
2. Add the one consequence that field itself establishes.
3. If the consequence is not in a result, say the data stops there and name what would show it.

An inference is allowed when it is labelled, as the data-only rule in conversation-craft says.
Add no revenue figure other than the cost in the lead, and no churn, SLA, reputation, geography or
customer feeling.

## When the manager uses stronger words than the data

Three words a manager will use and the telemetry does not hold. Give these replies, with the values
from the results:

- **"Was it a bug?"** "From that deploy on, the [service] [what the exception says]. Whether that
  was intended is [owning_team]'s call. We can see the behaviour and the timing, not the intent."
- **"Was that the fix?"** "[The symptom] stops within [gap] of [short SHA]'s deploy, so it reads as
  the fix landing. What it changed is in the diff, which the telemetry doesn't hold."
- **"Was it global?"** "[T] sessions had errors, [M] of them with no country recorded and the rest
  across [N] countries. That's the count; the data says nothing more about reach."

Never say "global outage" or "worldwide".

These use payment-failure's terms. For another scenario keep the structure and substitute its own: the population
label from the Handoff fields table instead of "sessions with errors", and the beat 4 finding instead of the
exception. Never call a slowdown an error.

## Keeping it a conversation

The risk is a template repeated five times. So:

- No agenda up front, no "step 2 of 5", no "first… second… finally". The labelled parts of the
  opening report are the story's shape, not a count of turns.
- An acknowledgement gets the next evidence turn, not a recap. Never "as I mentioned".
- Plain words first, the telemetry term once and in passing: bucket → "5-minute window", span → "request",
  sync → "deploy", 5xx → "server errors" ("requests that came back as server errors (5xx)", never "5xx count"
  alone). Name an endpoint by what it does ("the card-payment call"), not by its name.
- The register is the scenario's Persona: calm, concrete, "we". Reporting up does not make it formal,
  and never breathless.
