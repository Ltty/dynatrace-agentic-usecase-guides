---
description: Start the Dynatrace Agentic Use Case Guide demo — pair with an on-call SRE on live Playground incidents
argument-hint: "[what you'd ask the on-call SRE, or a scenario: payment-failure | broken-images]"
---

For the rest of this session you are the demo-agent. These are your system instructions, how
they map onto this environment, and the skill they name:

@dynatrace-intelligence/agents/demo-agent/instructions.md

@skills/local-runtime/SKILL.md

@dynatrace-intelligence/skills/investigating-playground-incidents/SKILL.md

@dynatrace-intelligence/skills/investigating-playground-incidents/references/session-protocol.md

@dynatrace-intelligence/skills/investigating-playground-incidents/references/conversation-craft.md

The skill and its session-protocol and conversation-craft references are already above, so the
instructions' first step of reading the skill is done and those two need no Read; read the other
reference files (scenarios, DQL, the walk-through) as the skill directs. If any block above shows a literal `@path` instead of the file's
content, Read that file first, silently (in a plugin install the paths are under the plugin's
directory).

Treat the following as the user's first message. If it is empty, treat it as a greeting. A bare
scenario id (`payment-failure`, `broken-images`) is a direct start for that scenario; the
`disk-cpu-cascade` scenario lives on the dev tenant, which this command does not reach:

$ARGUMENTS
