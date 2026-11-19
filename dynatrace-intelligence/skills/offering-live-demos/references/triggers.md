# Triggers

When the "Try a live demo" block may be added to an answer. The answer always comes first and in full; the offer is its last block,
made at most once per conversation, and only when `SKILL.md` step 2 finds a live scenario to offer.

| Id | The user is… | Where | What is offered |
|---|---|---|---|
| `T-orient` | asking what they can do here, what this app or page is for, how to get started, or to be shown something or given a demo | the Home page and the apps in `references/app-offers.md` | the open app's row there |
| `T-cause` | trying to find the cause of something that is wrong: asking why it is slow, failing or erroring, what changed, what is causing it, its root cause, or asking you to investigate, analyze or explain a problem, failure or slowdown | any app | the live incidents: one named, several as a list; the Kubernetes tour in place of the throttling incident where the tour exists |
**Kubernetes sizing is not a trigger here.** A question about starved, wasted or over-provisioned workloads, right-sizing, throttling or
limits belongs to the Kubernetes tour, whose own description claims it: Assist answers it in the tour's format, which is the demo. Two
skills claiming the same question made the agent pick the tour and skip the offer, so this skill leaves it alone.

A trigger is a **meaning**, not a keyword. "Why is checkout slow since the release?" and "can you work out what is making the cart
fail" are both `T-cause`; a question that merely contains the word "error" is not.

## Never offer when

- **The prompt is a preset button.** A canned prompt behind an app's "ask Assist" button ("explain what happened in this problem…",
  "explain this vulnerability", "explain this execution plan", "explain this log") was not typed: the user started a task with a click.
- **The user is mid-task:** writing, fixing or explaining a query or DQL, building a dashboard or notebook, configuring something.
- **The message is a reply**, not a question: "yes", "no", "ok", "continue", "thanks".
- **The question is about documentation** or how a product feature works.
- **The question is about cloud costs.** Assist's own cost analysis answers it; never route it to a demo.
- **An offer was already made** in this conversation, or the user said no to one.

## Examples (synthetic)

These are written for this file; none is a real prompt. They are the test material for a trigger and are read as examples of the
meaning above, not as phrases to match.

### T-orient

Offer:

- What can I do here?
- What is this page for?
- How do I get started with this app?
- Show me what this can do.
- Is there a demo I can look at?

Do not offer:

- What is the difference between a host and a process group?
- Explain this problem. (a preset button)
- What can I do about the high CPU on this host? (a cause question; `T-cause` decides)
- Can you do a demo of dashboards? (no live demo fits: the offer rests on a live row)
- Thanks, that helps.

### T-cause

Offer:

- Why did response time on the checkout service jump this morning?
- What changed in the last hour that could be making the login service fail?
- Can you work out what is causing the errors on the product pages?
- Something is slow in production since the deploy. What is going on?
- What is the root cause of the failures I am seeing on the payment flow?
- Can you investigate the slowdown on the cart service?

Do not offer:

- Analyze the output of this query for me. (mid-task)
- Why does this query return no rows? (mid-task)
- Write a query that shows the slowest endpoints. (a task, not a cause)
- Why is the sky blue? (not about the environment)
- What is a root cause analysis in Dynatrace? (documentation)
- Why are my cloud costs higher this month? (cloud costs)
