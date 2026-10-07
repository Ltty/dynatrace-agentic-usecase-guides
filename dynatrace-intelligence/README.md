# Dynatrace Agentic Use Case Guide — Skill Edition

A port of the [Claude Code plugin](../README.md) to the Dynatrace agentic skill format.
Same SRE-persona incident investigation, same live Playground data, same beat structure —
restructured to run inside Dynatrace without a local CLI, Python tooling, or Claude Code.

Procedures (layout rules, deploying, testing, adding a scenario): [docs/DYNATRACE-SKILL.md](../docs/DYNATRACE-SKILL.md). This file holds design notes and open items.

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

```text
dynatrace-intelligence/
└── skills/
    └── investigating-playground-incidents/   — folder name must equal the frontmatter `name`
        ├── SKILL.md                          — entry point, principles, scenario registry, workflow, checklist
        └── references/                       — flat: no subfolders, unique names, linked as references/<name>.md
            ├── session-protocol.md           — greeting, session state + token table, survey, close
            ├── conversation-craft.md         — beat loop, divergence, staying in role, pacing rules
            ├── dql-reference.md              — verified field names, gotchas, chained queries
            ├── scenario-payment-failure.md        — persona, business context, scope, handoff fields, resolvers
            ├── scenario-payment-failure-beats.md  — the 5 beats with DQL, reveals, staging, deep links
            ├── scenario-broken-images.md          — same shape, for the image-provider slowdown
            └── scenario-broken-images-beats.md    — the 5 beats for the slowdown
```

The survey reads only each scenario's resolver file; the beats file is read once the user picks
a direction. Adding a scenario means adding both files and a row in the SKILL.md registry.

The layout is the one `dt-app deploy` expects. It turns each file into an `ai-agent-resource` document named `/skills/<skill-name>/SKILL.md` or `/skills/<skill-name>/references/<name>.md`. SKILL.md stays under 150 lines, and reference links always use the `.md` extension.

## Where this runs

The skill needs a tool that executes DQL against the Playground. Every number it states comes
from a live query, and there is no fixture fallback.

| Surface | Works? | Why |
|---|---|---|
| Dynatrace agent runtime (Assist, `@demo-agent`) | Yes — the target | DQL through the MCP gateway tool `execute-dql` |
| Claude Code | Use the plugin edition instead | `dtctl` provides DQL there; see below |
| Claude API (Skills upload) | No | Skill containers have no network access |
| claude.ai | Only with network access and a DQL tool | Network access varies by user/admin settings |

Because the Dynatrace runtime has no bash or scripts, DQL is this skill's deterministic layer:
date math, epoch conversion, and trace condensing live in the queries, not in the model's prose.

**Two editions, maintained separately.** Skills don't sync across surfaces. This directory is
the Dynatrace-runtime edition; the Claude Code edition is the plugin (`skills/`, `commands/`,
`scenarios/`). A new DQL gotcha or scenario change must be applied to both — for example, the
GitHub Actions deploy rule (`commit` is null; parse the SHA from `event.description`) matters
to broken-images in both editions.

## What changed from the Claude Code plugin

| Plugin | Skill edition | Why |
|---|---|---|
| `preflight.py resolve` (Python, 100+ lines) | Resolver DQL with `fieldsAdd` timestamp arithmetic | Keeps date math in the data layer, not the model |
| `preflight.py load-queries` (pre-substitution) | Agent substitutes `{{TOKENS}}` inline at beat time | No pre-loading needed without a state file |
| `render_waterfall.py` (247 lines, span tree) | Per-service trace summary in DQL | `summarize … by: { service }` returns ~10 ordered rows; no tree building in the model |
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
# Runs both resolver DQLs, then all beat DQLs, including the chained trace summary.
python tools/validate_dt_skill.py --scenario payment-failure
python tools/validate_dt_skill.py --scenario broken-images
```

Also open one deep link with substituted values and confirm the Dynatrace app loads the right view.

## Current scope

- **Engine:** complete — session protocol, beat loop, divergence, persona, pacing.
- **payment-failure scenario:** complete — resolver DQLs and all 5 beats with DQL inline.
- **broken-images scenario:** complete — ported as a latency investigation, rebuilt against
  live data. The plugin edition's reveals (DynamoDB `SlowDown` throttle, failing spans) no
  longer match the Playground: current cycles have no exceptions and no failed spans, and the
  time goes into an image resize that runs on every request after the deploy.

## Resolver notes (maintainers only)

Kept out of the skill on purpose: the agent reads the scenario files and would repeat them to the user.

- `now()-48h`: payment-failure fires about twice a day and broken-images once a day (around 03:04 UTC), so 48 hours always spans at least one occurrence.
- `±15m` window padding catches the culprit deploy just before onset, a clean baseline, and the recovery after the fix.
- The fallback resolver drops `is_duplicate` and takes the largest-impact problem instead, for cycles where Davis didn't merge the near-duplicate problems.
- The resolvers hardcode Playground service IDs, so on any other tenant the survey reports a clean environment.

## Open items

- **Liveness proof stamp:** the plugin shows `queryId / scannedRecords / executionTimeMs` from
  the dtctl envelope. Whether the Dynatrace runtime exposes these fields is unknown. Do not
  fabricate them; decide after the first live test.
- **Deep links (broken-images):** the deployment-management and error-inspector links are
  carried over from the plugin and haven't been opened against a live problem yet.

Agents run DQL through the MCP gateway tool `execute-dql` (server `dynatrace-mcp`, type
`dtp-mcp-gateway`), so SKILL.md names it as `dynatrace-mcp:execute-dql`. An agent that has no MCP
server has no tools at all and cannot run the DQL in this skill.

Davis CoPilot is not used: inside Assist or `@demo-agent` the agent is the copilot, so beat 2 gives
the causal read itself.

## Format

Follows Anthropic's Agent Skills format, which Dynatrace's skill documentation links to:
[overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) and
[authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).
Before changing the skill, check the best-practices checklist. Then run
`tools/validate_dt_skill.py` and `docs/dt-skill-evals.md`.
