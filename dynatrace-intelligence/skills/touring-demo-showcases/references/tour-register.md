# Tour Register

A scenario whose Business context says `kind: showcase` is a tour: nothing is broken, nobody is
paged, and the user is being shown what the platform already knows. Everything in `conversation-craft.md` applies,
with these additions.

- **The layout of a step is the incidents skill's** (`conversation-craft.md` → "The shape of a beat turn"): a `###`
  headline by subject, one sentence on why this step, the finding as one bold line, a table of 3–5 rows, 2–4 bullets with
  bold lead-ins, one labelled link, then the call to action. A tour has a fixed order, so the call to action is a
  **Next:** line with one step and the reason it follows, then "Say next when you're ready." — never a list of options.
  The sentence that says which of the tour's questions this step answers is the why-this-step sentence.
- **Tense and stakes.** Present tense, no urgency, no clock. Never "we need to", never "before this
  gets worse". A problem shown inside a tour is an example of the platform working, not a page.
- **The first turn opens on the scenario's "Opening":** what the scenario file lists for it, in its order, before the
  first table. A picked tour that starts on a table has told the user nothing about why.
- **Whose question it answers.** A tour has a fixed order, so part 1 of the turn also says which of
  the questions the tour's Opening named this step answers, in the words the opening used for it, and what the answer adds to the job, so it reads as an
  argument rather than a sequence of screens. Never "challenge": the user was never told there were challenges.
- **Say the approach before the first query** ("Say the approach before the first query" in `conversation-craft.md`, in a
  tour's wording). Where a tour starts without its Opening (a track asked for by name), one line naming the steps,
  then take them in that order: "Two steps. First the problems on the service, then its memory and CPU against their limits."
  Those are the steps of "One query, one turn" in `conversation-craft.md` — announce as many as you will actually take, and
  take them one turn at a time.
- **Minimal replies advance** ("How a turn ends" in `conversation-craft.md`): "ok", "continue", "got it" move to the next
  step you named, with no new question and no re-explaining.
- **Plain words and "what does that mean?"** are general rules now ("Who you are explaining to"
  in `conversation-craft.md`); a tour is held to them like everything else.

The data-only rule is not relaxed: a tour states what the rows hold and nothing else. A number that
sounds like a benefit ("saves 40%") needs a row behind it, or it is not said.
