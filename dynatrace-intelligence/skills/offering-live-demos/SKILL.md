---
name: offering-live-demos
description: >
  Adds one live-demo offer to Dynatrace Assist's answer when the user opens a Dynatrace app and asks what
  they can do there, what the app is for, how to get started or to be shown something, and a matching problem
  is live on this environment. Use when the open app is one of dynatrace.kubernetes, dynatrace.infraops,
  dynatrace.users.sessions, dynatrace.experience.vitals, dynatrace.classic.session.replay, dynatrace.services,
  dynatrace.error.inspector, dynatrace.distributedtracing, dynatrace.clouds, dynatrace.launcher or
  dynatrace.davis.problems, and the question is about the app
  itself ("What can I do here?", "What is this app for?", "Show me what this can do"). Not for questions about
  the user's own data in the app, and not for writing code or DQL.
---

# Offering Live Demos

## Objective

Assist answers "what can I do here?" with the app's features. When a real problem on this environment is one the
app can show, the answer also says so, once, and offers to walk through it. The offer is an addition to the
answer, never a replacement for it.

Example questions this skill handles:

- "What can I do here?" (asked inside the Kubernetes app)
- "What is this app for?" (asked inside Users & Sessions)
- "Show me what this can do." (asked inside Clouds)
- "How do I get started?" (asked inside Services)

## Steps

**Text you write between tool calls is shown to the user as it is written.** So all the lookups below finish first,
with no text before them or between them, and the first thing the user reads is the answer.

1. **Look up, in silence.** Read `references/app-offers.md` and
   `/resources/documents/skills/investigating-demo-incidents/references/session-protocol.md` ("Session state") in one
   batch. The open app has no row: you are done looking up. Run no query and make no offer. Otherwise run the opening
   query from `session-protocol.md` with the DQL tool that skill names, once per conversation; a conversation that
   already holds its rows does not run it again.
2. **Match.** The scenarios offered are the row's scenarios that returned a row of their own. The tour has no
   row: it is offered only when some returned row's `env` is one that lists it (`kubernetes-complexity`) in that
   file's "Environments" table. Where the Kubernetes tour is offered, the
   Kubernetes incident is not (`references/app-offers.md` → "A tour replaces the incident it contains"). Nothing matches: no offer, no mention of demos, no "there is no live demo for this", no apology.
3. **Write the answer, then the offer.** Open on the answer to the user's question, as Assist normally would: the first
   sentence is about the app, for example "The Kubernetes app gives you a unified view of your Kubernetes estate."
   Never open on, or write anywhere, a word about skills, lookups, queries, rows or which scenario matched. The offer
   is the last block of the same message.
4. **One match: the offer** is its own block, so it stands out from the app's feature answer.
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
- **Stay in the app's lane.** Offer only the scenarios in the open app's row, even when others are live.
- **The offer is not the demo.** No investigation, figure or finding appears in it beyond the hook. The hand-over
  starts the investigation.
- Questions about the user's own data in the app are not this skill's: answer them as Assist normally would.

## References

- [references/app-offers.md](references/app-offers.md): which scenarios each app offers.
