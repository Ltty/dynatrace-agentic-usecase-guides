---
description: (Temporary) Run the demo on the Dynatrace skill and demo-agent instructions, for comparison with /demo
argument-hint: "[what you'd ask the on-call SRE]"
---

For this session, the instructions loaded from `skills/demo-engine/SKILL.md` and
`skills/dynatrace-playground/SKILL.md` do not apply. Do not use `/demo` flows, `.demo-state`
files, `preflight.py resolve` or `load-queries`.

Silently, with no text before or between the calls, read:

1. `dynatrace-intelligence/agents/demo-agent/instructions.md` — your system instructions.
2. `skills/local-runtime/SKILL.md` — how those instructions map onto this environment.

Then follow the instructions, starting with reading the skill they name. Treat the following
as the user's first message; if it is empty, treat it as a greeting:

$ARGUMENTS
