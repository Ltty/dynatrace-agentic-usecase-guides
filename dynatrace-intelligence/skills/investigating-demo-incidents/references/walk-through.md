# Walk-Through

How to run a scenario as a guided walk: you are the SRE taking someone through an incident while they
watch. **Incidents only** — the cloud tour is always a presentation and never reaches this file. They are not making decisions here; they want the answer, and then to be
shown how it was reached. The audience and the register are the same as in explore
(conversation-craft → "Who you are explaining to").

**It opens on the executive summary, then offers the walk, then walks the same beats as explore in the
same order with the user only ever saying "next".** What differs from explore is that nothing is
offered at the end of a turn: no options, no readiness question, one path.

The summary is the answer up front — what happened, what it cost, who it goes to — for someone whose
next meeting is in ten minutes. The walk is then the working, told forwards, each step following from
the last. What this mode must never do is state a finding inside a *step* before the step that
establishes it: the summary says the conclusion once, and the steps earn it in order.

The scenario files, queries and data-only rule are the same as in explore. This file
lists what is different, and it is complete: where it is silent, the rule in
`references/conversation-craft.md` applies.

## Contents

- [When it applies](#when-it-applies)
- [The executive summary, and the report on request](#the-executive-summary-and-the-report-on-request)
- [The steps](#the-steps)
- [Closing lines](#closing-lines)
- [What differs from explore](#what-differs-from-explore)
- [What the user says, what you do](#what-the-user-says-what-you-do)
- [What does that mean](#what-does-that-mean)
- [When the manager uses stronger words than the data](#when-the-manager-uses-stronger-words-than-the-data)
- [Keeping it a conversation](#keeping-it-a-conversation)

---

## When it applies

`delivery` is `walk-through` when the user chooses being walked through at the end of the survey (an
unspecific yes counts), or asks outright: "walk me through it", "take me through it", "present it",
"show me how it was worked out".

**Asking for the artefact is not asking for the walk.** "Give me the incident report", "just give me
the report", "brief me", "summarise it", "give me the summary" ask for something finished, not for a
guided walk: answer with "The report, on request" below, or the handoff block where they asked for a
summary, and do not start stepping.

If no survey has run in this conversation, resolve the scenario first, as the survey does. Read the
scenario file and `references/conversation-craft.md` before the summary, if they are not already read.

Never name the two ways of working to the user: no "walk-through", "briefing", "explore", "mode" or
"presentation". They only see what happens next.

## The executive summary, and the report on request

**The same block, reached two ways.** It is the walk's first turn, before any step. It is also what
someone gets who asks for the artefact without wanting the walk — "give me the incident report", "just
give me the report", "brief me" — at any point in the session. "Give me the summary" and "wrap it up"
ask for the handoff block instead (session-protocol → "Handoff block").

**As the walk's opening it ends on the offer** (part 5 below), and the user's yes starts the steps at
beat 1. Asked for on its own it ends there, with no offer and no stepping.

**It is said once.** The session close at the end produces the handoff block and the report path and
does not re-narrate the story (session-protocol → "Session close"). Two tellings of the same summary in
one session is the repetition this mode is most prone to.

**Queries.** Run the first Evidence DQL block of every beat not already run, in one turn, with no text
between the calls. Skip any block that needs a value from another block (`{{TRACE_ID}}`). Do not run the
survey query again if it ran in this conversation. This is the one turn that may exceed the budget of
two queries per beat.

**Status line.** Exactly one line before the calls: the scenario's `pull_line`.

**The report** is up to 14 lines, no evidence table, in this order. Leave out any part the scenario has
no source for. Each part carries at most one number, rounded for the ear ("about 4 minutes", "about 60%
at the peak"): "about" is only for rounding a value you read, never for one you did not.

1. **The story,** three or four sentences in time order, plain words. First what was affected and for how
   long (UTC as returned), for how many (one population, labelled) and at what cost (the survey row's
   `revenue_usd`, only when the row has it). Then what happened, in order: the change shipped (commit,
   short SHA, 7 characters), the errors began, Dynatrace opened the problem, a later deploy after which
   the problem stops (an inference, labelled as the data-only rule says), resolved. A scenario that is a
   state, not a change, tells its state, what it does and what it blocks, in the order of the beats'
   Objectives.
2. **The timeline,** one line in a text block, built only from events the results hold:

   ```text
   09:07 change c590ec ─ 09:07 first failure ─ 09:11 problem opened ─ 09:37 second change ─ 09:46 closed
   ```

3. **Owner:** who owns the service, and who shipped the change when that is someone else.
4. **What broke:** what the failing call does, in plain words.
5. **The offer, exactly:** "I can show you how we know each of these, starting with [the first beat's
   subject, in plain words]."

Taking the offer starts the walk at beat 1, and every beat still runs: the summary proved nothing, it
only said it. Declining it ends the session at the close.

## The steps

**Every beat runs, in the scenario's own order, one per turn** — beat 1 included. The summary before them
stands in for no beat: it says the conclusion, and the steps are where it is established. The user says
"next" and gets the next step.

The first step opens on the scenario's `approach` (conversation-craft → "Say the approach before the
first query"), so they know the shape, then takes beat 1.

A turn has five parts, in this order:

1. **The link back** — one clause tying this step to the last finding, so the walk reads as one
   argument rather than a sequence of screens: "The median held while the tail ran away, so the
   question is what that container was waiting on." On the first turn this is the approach line
   instead.
2. **The evidence** — the beat's table. A time series is condensed to before, peak and after, plus the
   onset row when it differs from "before", with the span said in words; the full series is one deep
   link away.
3. **What it means** — the beat's Reveal, and where the data stops.
4. **The deep link.**
5. **The closing line** (below).

**Never state a finding before the step that establishes it.** The temptation in this mode is to say
where it ends up and then show the working; that is the shape this delivery used to have and it is
what makes a walk feel like a recital. Each step knows only what the steps before it found.

A peak moment keeps its Staging: the finding alone on its own line first, then the pause, then the
explanation, then parts 2 to 5. A peak turn may run past 12 lines. A question or invitation at the end
of the Staging is replaced by the closing line.

Sessions with no country recorded are part of the count: "[T] sessions, [M] of them with no country
recorded and the rest across [N] countries", never "plus [M]".

Budget: 8–12 lines per turn, the deep link included.

## Closing lines

A turn ends on one line that says why the next piece follows from what was just shown, then names
it. Not "Next is the exact exception" but the reason too. Illustrative shapes (payment-failure); use the
scenario's own terms, and take the facts from the results:

- "The change lines up with the start, so the question is what exactly it broke. That's the trace."
- "That's what broke. The next question is who felt it."
- "That's who it hit. What's left is what we hand to the team."

**Then a short cue, so the user knows the turn is theirs.** "Say next when you're ready." Vary it,
keep it to a few words, and keep it a *statement*: a cue is not a question, and the user should never
have to decide anything to continue. Without one the walk reads as a document being recited — the step
names what comes next and then simply stops, which is what it did before this rule.

Never five turns of "Shall I continue?" — that is the question form, and it asks for a decision the
walk does not need. Only the closing line
of the turn before the last starts "Last piece:"; no other turn says how many remain. The last
step ends with the handoff block (session-protocol → "Handoff block") and then the session close (session-protocol → "Session close"), payoff line included; where a scenario's last beat is
itself the handoff, that turn is the block.

## What differs from explore

- A turn ends on the closing line, not on a choice. Offer one path, never two: explore's option list
  (conversation-craft → "How a turn ends") does not apply here, and neither does its `Requires:`
  reasoning — the walk takes the scenario's recommended order and does not explain why an order is
  forced, because nothing else is on offer.
- Never wait for a Success signal; advance on any acknowledgement.
- After a detour or an out-of-scope reply, return to the thread: "Back to where we were — next is X." Not
  the explore re-anchor, which offers options.
- The report, when asked for, is prose; the steps use tables.
- The exact replies in conversation-craft and the agent instructions keep their wording but end on one path:
  the handoff block, or "Back to where we were — next is X."

## What the user says, what you do

| The user says | You do |
|---|---|
| "understood", "ok", "got it", "go on", "next", "yes" | Deliver the next step |
| "what does that mean", "so what" | Say the same result in terms of consequence. No new query. See below |
| "how do we know", "where's that from", "show me" | Name the data the claim comes from and give the deep link. Query only for data not pulled yet |
| "what next", "what do we do", "wrap it up", "give me the summary" | The handoff block now (session-protocol → "Handoff block"), plus any held-back block its rows need, then the session close, payoff line included |
| "was it a bug", "was that the fix", "was it global" | The exact replies below |
| a specific question | Answer it from data, querying if needed, then one line back to the thread |
| "let me look myself", "what would you check" | Set `delivery` to `explore` and end as the beat loop says — the next step, why it follows, and the readiness cue |

If the user asks to be walked through it again after steering, set `delivery` back to
`walk-through` and continue from the next step not yet delivered.

## What does that mean

The general rule is conversation-craft → "Who you are explaining to": answered in place, in plain words,
no query. Two additions for this mode, where the user is further from the data:

1. Name the field and its value again, in plain language, then the one consequence that field itself
   establishes.
2. If the consequence is not in a result, say the data stops there and name what would show it.

An inference is allowed when it is labelled, as the data-only rule says. Add no revenue figure other
than the cost in the summary, and no churn, SLA, reputation, geography or customer feeling.

## When the manager uses stronger words than the data

Three words a manager will use and the telemetry does not hold. Give these replies, with the values
from the results:

- **"Was it a bug?"** "From that deploy on, the [service] [what the exception says]. Whether that
  was intended is [owning_team]'s call. We can see the behaviour and the timing, not the intent."
- **"Was that the fix?"** "[The symptom] stops within [gap] of [short SHA]'s deploy, so it reads as
  the fix landing. What it changed is in the diff, which the telemetry doesn't hold."
- **"Was it global?"** "[T] sessions had server errors (5xx), [M] of them with no country recorded and the rest
  across [N] countries. That's the count; the data says nothing more about reach."

Never say "global outage" or "worldwide".

These use payment-failure's terms. For another scenario keep the structure and substitute its own: the population
label from the Handoff fields table instead of "sessions with server errors (5xx)", and the beat 4 finding instead of the
exception. Never call a slowdown an error.

## Keeping it a conversation

The risk is a template repeated five times. So:

- No "step 2 of 5" and no "first… second… finally". The approach line names the shape once; after that
  the closing lines carry it, and no turn says how many remain.
- An acknowledgement gets the next step, not a recap. Never "as I mentioned".
- Plain words first, the telemetry term once and in passing: bucket → "5-minute window", span → "request",
  sync → "deploy", 5xx → "server errors" ("requests that came back as server errors (5xx)", never "5xx count"
  alone). Name an endpoint by what it does ("the card-payment call"), not by its name.
- The register is the scenario's Persona: calm, concrete, "we". Reporting up does not make it formal,
  and never breathless.
