---
name: offering-live-demos
description: >
  Adds one live-demo offer to the end of Dynatrace Assist's answer, never instead of it, when a matching problem is
  live on this environment. Trigger 1: on the Home page, or in dynatrace.kubernetes, dynatrace.infraops,
  dynatrace.users.sessions, dynatrace.experience.vitals, dynatrace.classic.session.replay, dynatrace.services,
  dynatrace.error.inspector, dynatrace.distributedtracing, dynatrace.clouds, dynatrace.launcher or
  dynatrace.davis.problems, the user asks what they can do here, what the app or page is for, how to get started, or to
  be shown something. Trigger 2, in any app: the user asks why something is slow, failing or erroring, what changed,
  what is causing it or its root cause, asks to investigate or analyze a problem or error, or asks whether Kubernetes
  workloads are starved, wasted or over-provisioned. Not
  while the user is writing or fixing a query, DQL, dashboard or configuration; not for one-word replies, preset
  button prompts, documentation questions or cloud costs.
---

# Offering Live Demos

## Objective

Assist answers the user's question as it normally would. When a real problem on this environment is one a demo can show, and
the question is one of the triggers in `references/triggers.md`, the answer also says so, once, and offers to walk through it. The offer
is an addition to the answer, never a replacement for it.

Messages this skill handles (the meaning decides, not the words; the full list and the blocks are in `references/triggers.md`):

- "What can I do here?" (asked inside the Kubernetes app, or on the Home page)
- "What is this app for?" (asked inside Users & Sessions)
- "Why did checkout slow down after the release?" (asked anywhere)
- "Which of my workloads request far more CPU than they use?" (asked anywhere)

## Steps

**Text you write between tool calls is shown to the user as it is written.** So all the lookups below finish first,
with no text before them or between them, and the first thing the user reads is the answer.

1. **Look up, in silence.** Read `references/triggers.md`, `references/app-offers.md` and
   `/resources/documents/skills/investigating-demo-incidents/references/session-protocol.md` ("Session state") in one
   batch. Decide which trigger the message fires, by its meaning. None fires, or a "never offer" case applies: you are done
   looking up; run no query and make no offer. The Home page (also called the main page, start page or Launcher) is the app
   `dynatrace.launcher`: treat it as the open app even when no app ID is given. `T-orient` also needs the open app to have a
   row; the other triggers do not care which app is open. Otherwise run the opening query from `session-protocol.md` with the
   DQL tool that skill names, once per conversation; a conversation that already holds its rows does not run it again.
2. **Match.** `T-orient`: the scenarios in the open app's row that returned a row of their own. `T-cause`: the scenarios that
   returned a row of their own, named by what the user asked about where one clearly fits (payment, images, a Lambda, a slow
   Kubernetes workload), otherwise all of them. `T-k8s-sizing`: the Kubernetes tour where it is listed, else the throttling
   incident if it returned a row. The tour has no row: it is offered only when some returned row's `env` is one that lists it
   (`kubernetes-complexity`) in that file's "Environments" table. Where the Kubernetes tour is offered, the Kubernetes incident is not
   (`references/app-offers.md` → "A tour replaces the incident it contains"). That choice is made silently and never mentioned.
   Nothing matches: no offer, no mention of demos, no "there is no live demo for this", no apology.
3. **Write the answer, then the offer.** Answer the question as Assist normally would. For `T-orient` the first sentence is about
   the app, for example "The Kubernetes app gives you a unified view of your Kubernetes estate." For `T-cause` and
   `T-k8s-sizing` the answer is the user's own question answered in full: the demo never stands in for it. Never open on, or write
   anywhere, a word about skills, lookups, queries, rows or which scenario matched. The offer is the last block of the same message.
4. **One match: the offer** is its own block, so it stands out from the answer.
   The headline is exactly `### Try a live demo`. Then one introduction, the problem, and the question on its own line:

   ```text
   ### Try a live demo

   I can give you a demonstration based on an actual problem in this environment. <the problem> We'd look at <the route>.

   Want me to walk you through it?
   ```

   - `<the problem>` is the scenario's discovery hook from `session-protocol.md` ("Discovery hooks"), its first
     sentence only: the facts and framing, the tense from the row's `problem_state`. Never a cost, and never a
     figure the hook does not carry.
   - `<the route>` is that scenario's Route column, in its own words, as its own sentence: what the demo is about, so
     the user sees what they are agreeing to. Never fold it into the hook's sentence with a dash. It names the subject,
     never a finding or a cause.
   - The Kubernetes tour has no hook either: the same headline, then "I can give you a demonstration based on this
     environment's real Kubernetes data: finding the cause of a slowdown, wasted or starved resources, and what the
     clusters run on in the cloud." and the question "Want me to show you?" No figures.
5. **Several matches:** the same block, with the introduction followed by "There are N to choose from:" and each
   named in plain words from its hook, with no route (the hooks tell the options apart), then the question
   "Which one would you like me to walk you through?" Rank
   nothing and recommend nothing: which one to look at is the user's choice.
6. **On a yes, or on naming one of them:** hand over, with no query of your own. An incident: read
   `/resources/documents/skills/investigating-demo-incidents/SKILL.md` and continue from its "Classify the opening" as a
   **pick**: "[A] it is." and that scenario's mode question, so the user chooses between being walked through and
   exploring. The Kubernetes tour: read `/resources/documents/skills/touring-demo-showcases/SKILL.md` and follow it as that tour
   picked, so it starts on the tour's Opening.
7. **On a no, or any other topic:** drop it. The offer is made once per conversation and never repeated.

## Rules

- **Data only.** The offer rests on what the opening query returned. Never offer a demo no row supports, and never
  describe what people experienced beyond what the hook says.
- **Never say** a scenario id, an environment, a tenant or a context name. The app, the hook and the plain
  description of the problem are all the user hears.
- **Work silently.** No line before the lookups, none between them, and none that explains the answer: not "let me
  run the opening query", not "the Kubernetes app maps to a scenario that has a row". The user's first words are the
  answer to their question, and the offer is its last block.
- **Never narrate a choice.** Which scenario was offered instead of another, that one replaces another, which
  environment this is and why: none of it is said, before the answer or after. A line such as "the environment lists
  X, so I offer Y" is the failure this rule exists for; the user hears only the app's answer and the offer.
- **Stay in the app's lane for `T-orient`.** Offer only the scenarios in the open app's row, even when others are live.
  `T-cause` and `T-k8s-sizing` follow the question, not the app.
- **The answer is never shortened to make room.** A cause or sizing question gets the same answer with or without the offer.
- **The offer is not the demo.** No investigation, figure or finding appears in it beyond the hook. The hand-over
  starts the investigation.
- **Blocks win.** Whatever the trigger, the "never offer when" cases in `references/triggers.md` apply: a preset button prompt,
  a user mid-task, a one-word reply, a documentation or cloud-cost question.

## References

- [references/triggers.md](references/triggers.md): the triggers, the blocks, and synthetic examples of each.
- [references/app-offers.md](references/app-offers.md): which scenarios each app offers.
