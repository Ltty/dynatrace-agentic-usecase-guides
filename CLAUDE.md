# Dynatrace Agentic Use Case Guides

<!--
CONFIRMED WORKING (verified in a fresh session): these two lines make demo-engine/SKILL.md
and dynatrace-playground/SKILL.md show up as their own separate "Contents of ... (project
instructions, checked into the codebase)" blocks at session start, with zero visible Read
call — the same silent-injection mechanism CLAUDE.md's own content uses. This is what lets
.claude/commands/demo.md skip an explicit "read these files" step entirely (see its own
"Your operating rules are already loaded" section) — that step used to cost two visible
Read rows before the very first word of the greeting.

If you ever see the literal "@skills/..." text unexpanded in a session's context instead of
the skill content itself, this has broken (client/version change) — restore the explicit
Read instruction in .claude/commands/demo.md as a fallback until it's fixed.
-->
@AGENTS.md
@skills/demo-engine/SKILL.md
@skills/dynatrace-playground/SKILL.md
