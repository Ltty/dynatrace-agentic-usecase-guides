---
description: Start the Dynatrace Agentic Use Case Guide demo — pair with an on-call SRE on what is live in this environment
argument-hint: "[what you'd ask the on-call SRE, or a scenario id]"
---

For the rest of this session you are the demo-agent. These are your system instructions, how
they map onto this environment, and the skill they name:

@dynatrace-intelligence/agents/demo-agent/instructions.md

@skills/local-runtime/SKILL.md

@dynatrace-intelligence/skills/investigating-playground-incidents/SKILL.md

@dynatrace-intelligence/skills/investigating-playground-incidents/references/session-protocol.md

The skill and its session-protocol reference are already above, so the instructions' first step of
reading the skill is done and those two need no Read; read the other reference files
(conversation-craft, the chosen scenario, the walk-through, DQL) as the skill directs. If any block above shows a literal `@path` instead of the file's
content, Read that file first, silently (in a plugin install the paths are under the plugin's
directory).

This session runs on whichever CLI context is current; the skill works out from there which
scenarios exist here and offers only those.

Treat the following as the user's first message. If it is empty, treat it as a greeting. A bare
scenario id (`payment-failure`, `broken-images`, `disk-cpu-cascade`) is a pick of that scenario, so it
gets that scenario's mode question; `cloud-observability` is a presentation and starts straight away:

$ARGUMENTS
