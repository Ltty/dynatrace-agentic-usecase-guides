# Dynatrace Agentic Use Case Guide — Skill Edition

A port of the [Claude Code plugin](../README.md) to the Dynatrace agentic skill format.
Same SRE-persona incident investigation, same live Playground data, same beat structure —
restructured to run inside Dynatrace without a local CLI, Python tooling, or Claude Code.

---

## What this is

The Claude Code plugin drives the investigation through `dtctl` (a local CLI), Python scripts
(`preflight.py`, `render_waterfall.py`), and Claude Code's hook/slash-command machinery.

This skill edition replaces all of that with:

- **One `SKILL.md`** — the entry point and dispatch layer.
- **Five reference `.md` files** — the engine prose, DQL queries, scenario data.
- **Native DQL execution** — the Dynatrace runtime runs queries directly; no CLI, no envelope parsing.

The content is the same. The plumbing is gone.

## Files

```
dynatrace-skill/
├── SKILL.md                              — entry point, role, principles, workflow, checklist
└── references/
    ├── session-protocol.md               — resolver contract, session state, survey, session close
    ├── conversation-craft.md             — beat loop, divergence, staying in role, pacing rules
    ├── dql-reference.md                  — verified field names, gotchas, chained queries
    ├── waterfall-rendering.md            — condensed call-tree recipe for beat 4
    └── scenario-payment-failure.md       — persona, resolver DQLs, business context, 5 beats
```

## What changed from the Claude Code plugin

| Plugin | Skill edition | Why |
|---|---|---|
| `preflight.py resolve` (Python, 100+ lines) | Resolver DQL with `fieldsAdd` timestamp arithmetic | Keeps date math in the data layer, not the model |
| `preflight.py load-queries` (pre-substitution) | Agent substitutes `{{TOKENS}}` inline at beat time | No pre-loading needed without a state file |
| `render_waterfall.py` (247 lines, span tree) | Condensing recipe in prose | The `staging` instruction already constrains to 3–4 rows |
| `guard_dtctl.py` + `settings.json` (hook enforcement) | Platform read-only + skill instructions | DQL `fetch` has no write path; behavioural guardrails remain instruction-only |
| `.demo-state.<id>.json` (on-disk state) | Conversation context only | No filesystem in the Dynatrace runtime |
| `/demo` slash command | Natural-language entry (survey on request) | The two-stage greeting/survey design already works without a slash command |
| Two `SKILL.md` files (`@import`ed) | One `SKILL.md` + reference files | Matches the skill skeleton format |

## Security posture

The Claude Code plugin enforces three independent read-only layers; the Dynatrace runtime
replaces them with DQL's platform-level read-only constraint. See `docs/SECURITY.md` →
"Dynatrace runtime" for the full comparison.

## Verification

The strong practice in this repo is *no query ships unexecuted*. Before loading the skill:

```bash
# Runs both resolver DQLs from scenario-payment-failure.md, then all beat DQLs,
# including the chained waterfall block.
python tools/validate_dt_skill.py --scenario payment-failure
```

Also open one deep link with substituted values and confirm the Dynatrace app loads the right view.

## Current scope

- **Engine:** complete — session protocol, beat loop, divergence, persona, pacing.
- **payment-failure scenario:** complete — resolver DQLs and all 5 beats with DQL inline.
- **broken-images scenario:** not yet ported.

## Open items

- **Liveness proof stamp:** the plugin shows `queryId / scannedRecords / executionTimeMs` from
  the dtctl envelope. Whether the Dynatrace runtime exposes these fields is unknown. Do not
  fabricate them; decide after the first live test.
- **Davis CoPilot call (beat 2):** inside Dynatrace the agent may already *be* CoPilot, making
  the call circular. See the note in beat 2 of `scenario-payment-failure.md`.
- **Real Dynatrace skill spec:** the skeleton format used here was user-supplied. Confirm
  frontmatter fields, reference-file loading semantics, and any size constraints with the owning
  team before final packaging.
