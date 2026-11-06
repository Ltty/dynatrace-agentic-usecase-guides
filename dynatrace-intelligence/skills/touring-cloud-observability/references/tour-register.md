# Tour Register

A scenario whose Business context says `kind: showcase` is a tour: nothing is broken, nobody is
paged, and the user is being shown what the platform already knows. Everything in `conversation-craft.md` applies,
with these additions.

- **Tense and stakes.** Present tense, no urgency, no clock. Never "we need to", never "before this
  gets worse". A problem shown inside a tour is an example of the platform working, not a page.
- **The first turn opens on the scenario's "Opening":** what the tour is, the four questions it follows, the route and how it
  goes, in that order, before the first table. A picked tour that starts on a table has told the user nothing about why.
- **Whose question it answers.** A tour has a fixed order, so part 1 of the turn also says which of
  the tour's four questions this step answers, in the words the opening used for it, once per step, so it reads as an
  argument rather than a sequence of screens. Never "challenge": the user was never told there were challenges.
- **Say the approach before the first query** ("Say the approach before the first query" in `conversation-craft.md`, in a
  tour's wording). On a cost ask there is no Opening, so one line naming the steps, then take them in that order: "Three steps. First what
  the bill actually says, then utilisation next to it so we only cut what's safe, then who owns what."
  Those are the steps of "One query, one turn" in `conversation-craft.md` — announce as many as you will actually take, and
  take them one turn at a time.
- **Place every finding against the target,** once one has been named. Not "CloudWatch logs cost
  $2,454" but "$2,454 on one line, against a $1,332 working target — this line alone would cover it
  twice". A number with nothing to measure it against is a fact; a number measured against the goal
  is progress, and progress is what makes a tour read as a story instead of a list.
- **Minimal replies advance** ("How a turn ends" in `conversation-craft.md`): "ok", "continue", "got it" move to the next
  step you named, with no new question and no re-explaining.
- **Plain words and "what does that mean?"** are general rules now ("Who you are explaining to"
  in `conversation-craft.md`); a tour is held to them like everything else.

The data-only rule is not relaxed: a tour states what the rows hold and nothing else. A number that
sounds like a benefit ("saves 40%") needs a row behind it, or it is not said.
