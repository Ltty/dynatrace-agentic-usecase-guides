# Tour Protocol

How the cloud tour (`cloud-observability`) starts, settles its target, runs and closes. It is a tour, not an incident:
no problem record, and never walked through. The core files stay in force: the greeting, environments, survey and
session close in `session-protocol.md`, and all of `conversation-craft.md`, both in `/resources/documents/skills/investigating-demo-incidents/references/`.
What is below is added to them, not instead of them.

## The cloud tour

`cloud-observability` is a showcase: a tour of what we run, not an incident. It has no problem record, so the
survey's problem branch cannot find it. Its availability, and the figures the tour opens with, come from a
probe run when the cost track starts. The opening itself carries no figures.

- **The probe** is beat 5's bill query, ending with:

  ```text
  | filter total_usd > 0
  | fieldsAdd env = "demo-live", scenario = "cloud-observability"
  ```

  A row means the showcase is available, and carries `total_usd`, `untagged_usd`, `untagged_pct` and
  `target_usd` for the opening line and the proposal. No row means
  it is not available: say nothing about it.
- **When to run it:** the turn the cost track starts, as its first query — not on the greeting and not on the
  survey. Where the runtime already knows the environment lists the showcase (the local adapter reads it from
  the CLI), beat 5's own bill query serves: the probe's `filter total_usd > 0` is an availability test, and
  availability is already settled. Run the probe form only where the environment is unresolved. It is the heaviest read in the scenario, so it waits until the user has asked for the bill. The
  greeting names the cloud direction without numbers; the numbers are this query's job.
- **If it returns nothing,** this environment has no bill: say so plainly once ("there's no cloud spend
  imported here") and offer what the environment does have. Never leave the user waiting on a tour that
  cannot run.
- **Reuse its result.** The probe is beat 5's own first query, so beat 5 does not run it again. Its
  `queried_at` sets `{{SURVEY_AT}}` only if it was the conversation's first query — the survey usually
  ran first, and then that one holds.
- **A question *about* the cloud line** ("what do you mean, where 10% of it is?") is answered first,
  in two sentences, and the turn then **starts the first step** — it does not end on a question. The
  user asked what you meant; showing them is the answer. An instruction ("show me the bill", "cut
  cloud costs") starts the same way.
- **Setting the target.** The user often brings their own number, or none. Settle it before the
  tour, in one turn, and settle it against the bill rather than against an opinion — run the bill
  query first, then answer from it. **The bill is always stated before the question is asked**: a
  goal means nothing until the user knows what it is a share of.
  - **No number** ("let's look at my cloud costs", "let's optimise the cloud spend"): state what the
    bill is and what the untagged share means, then ask, once:

    ```text
    The cloud bill is $[total_usd] over the last 30 days of charges, and $[untagged_usd] of it —
    [untagged_pct]% — carries no team tag, so nobody is being asked to reduce it.

    Do you have a savings goal in mind, or shall I propose one?
    ```

    A vague answer ("you propose", "whatever you think") is a yes to your proposal. This is the step
    that was missing: proposing 10% before asking takes the decision away from the user, and the
    number then sounds arbitrary rather than offered.
  - **Proposing one:** 10% of `total_usd`, as your own assumption, with the reason it is that and not
    more: it is the share you can point at line by line.
  - **A number the evidence can cover:** take it. Say what it comes to in dollars and start.
  - **A number the evidence does not reach** ("cut it in half", "30%"): never call it unrealistic,
    never refuse it, and do not argue about what is achievable. The point of this track is the
    *method*, and the method is the same whatever the number — say so, then show it:

    ```text
    30% is $[their figure]. The way you find it is the same either way — let me show you, and we'll
    see how far the data gets us.
    ```

    Where you want to say what the evidence currently reaches, say it as a floor rather than a
    counter-offer:

    ```text
    Half the bill is $[half]. What I can point at right now is $[largest line] on the biggest line
    and $[monitor-first dollars] in databases nobody is measuring. Past that I'd be guessing at what
    is safe to cut, and guessing is what gets a database shrunk that shouldn't be.

    I'd start at 10% — $[target_usd] — because I can show you where every dollar of it is. If that
    lands we'll know a lot more about where the rest might come from.
    ```

    The difference between the two numbers is a limit of the evidence, not a judgement about the
    user's ambition. Say it that way, and keep working to **their** number: it is the goal, and what
    you can evidence is how far you got. Both go in the findings block and in the report — their
    figure as the goal, yours as what the evidence reached, and the difference in "Still open".
    Never quietly replace theirs with yours.
- **One delivery: a presentation.** A showcase is never walked through and never asks which way to run it. It is
  always the step-by-step guide, with a call to action after every step. Nothing reads `delivery` for a showcase,
  and the incidents skill's `walk-through.md` does not apply to one. The user steers by asking, as they always can; they are
  not asked to choose a format first.
- **No `problem_state`.** Its remaining tokens come from its own beats (the scenario file → "Tokens"): beat 3's
  problem fills `{{PROBLEM_ID}}` and the window.
- **Tense:** present, no urgency. A problem shown in beat 3 is part of the tour, not a page.
- **Handoff block:** the showcase's last beat is its handoff (the cost action list), so the handoff block in the incidents skill's `session-protocol.md` is not used.
- **Session close:** as in the incidents skill's `session-protocol.md` ("Session close"), and it fires when the **track** the user walked is complete (the scenario file →
  "Tracks"), not when beat 6 runs.
  - After `estate`: the payoff line names the four questions the tour answered, in one sentence ("one view of the
    three clouds, one problem with its cause and impact, agents working it with that context, and where the 10% is").
  - After `cost`: the payoff line is the answer to the question you opened with — what the bill is, what the working
    10% comes to, and which lines carry it — and the cost action list is the handoff.
    When the tour opened on its premise ("take 10% off the cloud bill without breaking anything"), the payoff line answers it
    in the data's terms, both halves of it: how far the evidence gets toward the 10%, and what *without breaking anything* came
    to — what not to touch, and what cannot be judged yet. Never a plain yes or no the rows do not hold: "the data gets us this
    far, and here is what stands between us and the rest" is a complete answer, and the honest one when the lines are small.
  The way out offers what is left *inside the scenario*: the other track, the "Extra" (the workflows that prevent,
  remediate and optimize), a beat the user skipped, or a view from its "Other views" table.
