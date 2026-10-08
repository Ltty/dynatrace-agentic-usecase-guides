# Dynatrace Agentic Use Case Guide — Skill Edition

The single source of the SRE-persona incident investigation: one skill and one agent prompt, run both
inside Dynatrace (`@demo-agent`) and locally (`/demo` in Claude Code or OpenCode, through
[`skills/local-runtime`](../skills/local-runtime/SKILL.md)). Same live Playground data, same beat structure.

Procedures (layout rules, deploying, testing, adding a scenario): [docs/DYNATRACE-SKILL.md](../docs/DYNATRACE-SKILL.md). This file holds design notes and open items.

---

## What this is

- **One `SKILL.md`** — the entry point and dispatch layer.
- **Reference `.md` files** — the conversation rules, DQL gotchas, and each scenario's resolver and beats.
- **Native DQL execution** — in Dynatrace the runtime runs queries through `execute-dql`; locally the
  adapter maps the same call onto `dtctl query`.

The first version of this demo was a Claude Code plugin with its own engine, scenario YAML and Python
tooling (`preflight.py` state files, a waterfall renderer). It was retired once this skill ran locally
too; the history is in git and `docs/comparative-analysis.md`.

## Files

```text
dynatrace-intelligence/
└── skills/
    └── investigating-playground-incidents/   — folder name must equal the frontmatter `name`
        ├── SKILL.md                          — entry point, principles, scenario registry, workflow, checklist
        └── references/                       — flat: no subfolders, unique names, linked as references/<name>.md
            ├── session-protocol.md           — greeting, session state + token table, survey, close
            ├── conversation-craft.md         — beat loop, divergence, staying in role, pacing rules
            ├── briefing-mode.md              — the walk-through delivery: turn shape, intent table, handoff block
            ├── dql-reference.md              — verified field names, gotchas, chained queries
            ├── scenario-payment-failure.md        — persona, business context, scope, handoff fields, resolvers
            ├── scenario-payment-failure-beats.md  — the 5 beats with DQL, reveals, staging, deep links
            ├── scenario-broken-images.md          — same shape, for the image-provider slowdown
            ├── scenario-broken-images-beats.md    — the 5 beats for the slowdown
            ├── scenario-disk-cpu-cascade.md       — same shape, for the dev-tenant disk and CPU problem
            └── scenario-disk-cpu-cascade-beats.md — the 5 beats for the disk and CPU problem
```

Every scenario runs in two deliveries: the user explores with the SRE as a peer (default), or the SRE
reports the incident to them as to a manager and ends with a handoff block. The survey offers the second
once, after the entry angles. `briefing-mode.md` is the only file that knows about it; scenarios author
nothing extra, but the handoff block draws on their Handoff fields table, so a scenario with no owner or no
user count must say so there.

The survey reads only each scenario's resolver file; the beats file is read once the user picks
a direction. Adding a scenario means adding both files and a row in the SKILL.md registry.

The layout is the one `dt-app deploy` expects. It turns each file into an `ai-agent-resource` document named `/skills/<skill-name>/SKILL.md` or `/skills/<skill-name>/references/<name>.md`. SKILL.md stays under 150 lines, and reference links always use the `.md` extension.

## Where this runs

The skill needs a tool that executes DQL against the Playground. Every number it states comes
from a live query, and there is no fixture fallback.

| Surface | Works? | Why |
|---|---|---|
| Dynatrace agent runtime (Assist, `@demo-agent`) | Yes — the target | DQL through the MCP gateway tool `execute-dql` |
| Claude Code, OpenCode (`/demo`) | Yes | `skills/local-runtime` maps `execute-dql` to `dtctl query` on the read-only `playground` context |
| Claude API (Skills upload) | No | Skill containers have no network access |
| claude.ai | Only with network access and a DQL tool | Network access varies by user/admin settings |

Because the Dynatrace runtime has no bash or scripts, DQL is this skill's deterministic layer:
date math, epoch conversion, and trace condensing live in the queries, not in the model's prose.

**One codebase.** A rule, a DQL gotcha or a scenario change is edited here once and both runtimes get it
— for example, the GitHub Actions deploy rule (`commit` is null; parse the SHA from `event.description`)
matters to broken-images in both. The local runtime reads these repo files; `@demo-agent` reads the
uploaded documents, so upload after every change (`docs/DYNATRACE-SKILL.md`).

## Security posture

Locally, three independent read-only layers apply (the `readonly` dtctl context, the permission
allow-list, and the guard hook). The Dynatrace runtime replaces them with DQL's platform-level read-only
constraint. See `docs/SECURITY.md` for both.

## Verification

The strong practice in this repo is *no query ships unexecuted*. Before loading the skill:

```bash
# Runs both resolver DQLs, then all beat DQLs, including the chained trace summary.
python tools/validate_dt_skill.py --scenario payment-failure
python tools/validate_dt_skill.py --scenario broken-images
```

Also open one deep link with substituted values and confirm the Dynatrace app loads the right view.

## Current scope

- **Engine:** complete — session protocol, beat loop, divergence, persona, pacing, data-only conclusions.
- **payment-failure scenario:** complete — resolver DQLs and all 5 beats with DQL inline.
- **broken-images scenario:** complete — ported as a latency investigation, rebuilt against
  live data. The incident repeats every day: after a deploy around 03:00 UTC the Lambda resizes
  every image on every request until a fix lands about 30 minutes later. A single sampled failed
  `GET` span with a `SlowDown` throttle exists on some days only, so the beats do not depend on
  it.

## Resolver notes (maintainers only)

Kept out of the skill on purpose: the agent reads the scenario files and would repeat them to the user.

- `now()-48h`: payment-failure fires about twice a day and broken-images once a day (around 03:04 UTC), so 48 hours always spans at least one occurrence.
- `±15m` window padding catches the culprit deploy just before onset, a clean baseline, and the recovery after the fix.
- The fallback resolver drops `is_duplicate` and takes the largest-impact problem instead, for cycles where the near-duplicate problems weren't merged.
- The resolvers hardcode Playground service IDs, so on any other tenant the survey reports a clean environment.

## Open items

- **Liveness proof stamp:** locally it comes from the dtctl envelope's `metadata` (`queryId`,
  `scannedRecords`, `executionTimeMilliseconds`). Whether the Dynatrace runtime exposes these
  fields is unknown. Do not fabricate them; decide after the first live test.
- **Deep links (broken-images):** the deployment-management and error-inspector links
  haven't been opened against a live problem yet.

Agents run DQL through the MCP gateway tool `execute-dql` (server `dynatrace-mcp`, type
`dtp-mcp-gateway`), so SKILL.md names it as `dynatrace-mcp:execute-dql`. An agent that has no MCP
server has no tools at all and cannot run the DQL in this skill.

No separate AI call in beat 2: inside Dynatrace Assist or `@demo-agent` the agent already is
Dynatrace Intelligence, so beat 2 gives the causal read itself.

Naming: all Dynatrace AI is "Dynatrace Intelligence" and the chat interface is "Dynatrace Assist".
The skill never says "Davis" or "CoPilot"; `dt.davis.*` fields and app IDs in links are identifiers
and stay as they are.

## Format

Follows Anthropic's Agent Skills format, which Dynatrace's skill documentation links to:
[overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) and
[authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).
Before changing the skill, check the best-practices checklist. Then run
`tools/validate_dt_skill.py` and `docs/dt-skill-evals.md`.
