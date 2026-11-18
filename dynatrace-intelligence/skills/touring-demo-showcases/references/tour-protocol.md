# Tour Protocol

How a tour runs and closes. Every tour in this skill is a showcase, not an incident: no problem record to answer,
and never walked through. The core files stay in force: the greeting, environments, survey and session close in
`session-protocol.md`, and all of `conversation-craft.md`, both in `/resources/documents/skills/investigating-demo-incidents/references/`.
What is below is added to them, not instead of them. What one tour does differently — how it starts, what its tracks
close on — is in that tour's own scenario file.

## Every tour

- **One delivery: a presentation.** A showcase is never walked through and never asks which way to run it. It is
  always the step-by-step guide, with a call to action after every step (the **Next:** line, `tour-register.md`). Nothing reads `delivery` for a showcase,
  and the incidents skill's `walk-through.md` does not apply to one. The user steers by asking, as they always can; they are
  not asked to choose a format first.
- **Availability.** A tour has no survey row. It exists where `session-protocol.md` → "Environments" lists it for this
  environment, and nowhere else: never name a tour the environment does not list.
- **No `problem_state`.** Its tokens come from its own beats (the scenario file → "Tokens"): a beat that returns
  `problem_id`, `tf_from_ms` and `tf_to_ms` fills the problem link.
- **Tense:** present, no urgency. A problem shown inside a tour is part of the tour, not a page.
- **Handoff block:** a tour's last beat of a track is its handoff, so the handoff block in the incidents skill's
  `session-protocol.md` is not used.
- **Session close:** as in the incidents skill's `session-protocol.md` ("Session close"), and **when it fires is each tour's own
  rule** (its scenario file → "Tracks" and "Moving between tracks"): a tour of several tracks may close only when the
  visitor is done. Never close a track the tour says should bridge onward. The payoff
  line is the tour's own, in its scenario file. The way out offers what is left *inside the tour*: another track, a
  beat the user skipped, or a view from its "Other views" table.

  **The layout of the close** is the incidents skill's (`session-protocol.md` → "Session close"): the last step's own
  reply, then `### What we hand over` with the findings block, then `### Where that leaves us` with two or three
  bullets and nothing else, then the way out as one line. The bullets are the tour's own (its scenario file says
  which). No paragraph over three sentences.
- **An incident inside a tour.** Where a tour shows a problem that the incidents skill also investigates, that
  investigation is the incidents skill's: read its scenario file and follow it. The tour's scenario file says when —
  only after a close, or as one of its tracks.
