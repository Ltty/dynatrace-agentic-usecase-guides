---
name: offering-live-demos
description: >
  Adds one live-demo offer to Dynatrace Assist's answer when the user opens a Dynatrace app and asks what
  they can do there, what the app is for, how to get started or to be shown something, and a matching problem
  is live on this environment. Use when the open app is one of dynatrace.kubernetes, dynatrace.infraops,
  dynatrace.users.sessions, dynatrace.experience.vitals, dynatrace.classic.session.replay, dynatrace.services,
  dynatrace.error.inspector, dynatrace.distributedtracing, dynatrace.clouds, dynatrace.biz.carbon,
  community.cloudsreagents, dynatrace.launcher or dynatrace.davis.problems, and the question is about the app
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

1. **Answer the question first**, as Assist normally would. Everything below only adds to that answer.
2. **Find the open app in `references/app-offers.md`.** No row for it: stop. Run no query, make no offer, and say
   nothing about demos.
3. **Run the opening query once per conversation** and keep its rows: read
   `/resources/documents/skills/investigating-demo-incidents/references/session-protocol.md` ("Session state") and run
   its query with the DQL tool that skill names. A conversation that already holds the rows does not run it again.
4. **Match.** The scenarios offered are the row's scenarios that returned a row of their own. The cloud tour has no
   row: it is offered only when some returned row's `env` is one that lists `cloud-observability` in that file's
   "Environments" table. Nothing matches: say nothing about demos. No "there is no live demo for this", no apology.
5. **One match: add the offer after the answer** as its own block, so it stands out from the app's feature answer.
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
   - The cloud tour has no hook, so its block is the same headline, then "I can give you a demonstration based on this
     environment's real cloud data: how to bring the cloud bill down." and the question "Want me to show you?" No figures.
6. **Several matches:** the same block, with the introduction followed by "There are N to choose from:" and each
   named in plain words from its hook, with no route (the hooks tell the options apart), then the question
   "Which one would you like me to walk you through?" Rank
   nothing and recommend nothing: which one to look at is the user's choice.
7. **On a yes, or on naming one of them:** hand over, with no query of your own. An incident: read
   `/resources/documents/skills/investigating-demo-incidents/SKILL.md` and continue from its "Classify the opening" as a
   **pick**: "[A] it is." and that scenario's mode question, so the user chooses between being walked through and
   exploring. The cloud tour: read `/resources/documents/skills/touring-cloud-observability/SKILL.md` and follow it.
8. **On a no, or any other topic:** drop it. The offer is made once per conversation and never repeated.

## Rules

- **Data only.** The offer rests on what the opening query returned. Never offer a demo no row supports, and never
  describe what people experienced beyond what the hook says.
- **Never say** a scenario id, an environment, a tenant or a context name. The app, the hook and the plain
  description of the problem are all the user hears.
- **Work silently.** Once this skill is loaded, write nothing before the answer: no word about skills, files, lookups
  or queries. The user's first words are the answer to their question, and the offer is its last paragraph.
- **Stay in the app's lane.** Offer only the scenarios in the open app's row, even when others are live.
- **The offer is not the demo.** No investigation, figure or finding appears in it beyond the hook. The hand-over
  starts the investigation.
- Questions about the user's own data in the app are not this skill's: answer them as Assist normally would.

## References

- [references/app-offers.md](references/app-offers.md): which scenarios each app offers.
