# Dynatrace skill and demo agent: maintainer guide

How to structure, upload, test and maintain the Dynatrace-native skill and the `demo-agent` that runs it.
Design notes and open items live in [dynatrace-intelligence/README.md](../dynatrace-intelligence/README.md).
This file is procedure.

## What exists

| Piece | Where | What it is |
|---|---|---|
| The skill | `dynatrace-intelligence/skills/investigating-playground-incidents/` | `SKILL.md` plus a flat `references/` folder. Two scenarios: payment failure and the image-service slowdown. Source of truth. |
| The agent | `agents/demo-agent/` | A `deep-agent` template (`template.json`, `instructions.md`) that mounts the skill and may only call `execute-dql`. |
| The helper | `tools/dt_agent.py` | `check`, `pack`, `docs`, `status`, `render`, `template`, `invoke`. Every write is a dry run unless you pass `--apply`. |
| The validator | `tools/validate_dt_skill.py` | Runs every DQL block of a scenario live on the Playground. |

## Skill layout rules

These are the app format's rules. `python tools/dt_agent.py check` enforces them, and `docs` and `pack` refuse to run if it fails.

- The folder name equals the frontmatter `name`: lowercase letters, digits and single hyphens, at most 64 characters, no "anthropic" or "claude".
- `description` is required, at most 1024 characters, no XML tags, and says what the skill does and when to use it. It is what triggers the skill.
- `SKILL.md` stays under 150 lines. It is the entry point, so route to references instead of embedding detail.
- `references/` is **flat**: no subfolders, only `.md`, `.yaml` or `.json`, and unique names once the type is dropped.
- Links use `references/<name>.md`, always with the `.md` extension, even for a `.yaml` or `.json` file.
- Sample DQL goes in fenced `dql` blocks.
- Only maintainer notes belong outside the skill folder. Anything inside it is read by the agent and can be repeated to users, so keep rationale like "why 48 hours" in `dynatrace-intelligence/README.md`.

**Names.** The skill is `investigating-playground-incidents`: descriptive, and not tied to one agent. The agent is `demo-agent` because that is what people type after `@`. Renaming the skill means changing the folder, the frontmatter `name` and the mount filter in `template.json`.

## Tokens and tenants

- **Working tenant:** `https://fxz0998d.dev.apps.dynatracelabs.com`. The AI API base path is `/platform-reserved/ai/v0.1` (no `/platform` prefix). The Swagger UI rejects tokens, so it only opens in a browser session.
- **Token:** a personal platform token in the `DT_DEV_AGENT_TOKEN` environment variable, set at user level (restart VS Code afterwards). The helper never prints or stores it. Give it a short expiry and delete it when you are done. Never put it in a repo file; `.claude/settings.local.json` is not git-ignored here.
- **Scopes:** `ai:operator:execute`, `mcp-gateway:servers:read`, `mcp-gateway:servers:invoke`, `document:documents:read`, and the `storage:*:read` scopes the DQL needs (`events`, `spans`, `user.sessions`, `user.events`, `buckets`). `document:documents:write` is only for uploading skill documents on dev. The storage scopes are inferred, not documented; a missing one shows up as a named DQL permission error.
- **`dtctl` is separate.** It only reads (ground-truth DQL and validation) and cannot deploy. Keep its `playground` context read-only. `validate_dt_skill.py` pins `--context playground`, but other `dtctl` calls use whatever the current context is, so check `dtctl config current-context` first.

## Change the skill

1. Edit files under `dynatrace-intelligence/skills/investigating-playground-incidents/`.
2. `python tools/dt_agent.py check`
3. `python tools/validate_dt_skill.py --scenario payment-failure` and `--scenario broken-images` (live, on the Playground).
4. `python tools/dt_agent.py --tenant <dev-url> docs` shows `+` create, `~` update, `=` unchanged, and `?` documents only on the tenant (never deleted).
5. After approval, `docs --apply`. The agent saw updated content within minutes in our tests.
6. Run the evals (below), each case at least three times.

## Change the agent

1. Edit `agents/demo-agent/template.json` or `instructions.md`. The template's `agent_instructions.text` must stay `@file:instructions.md`.
2. `python tools/dt_agent.py render` prints the exact payload, with a build stamp (`<git sha>[-dirty]`).
3. `python tools/dt_agent.py --tenant <dev-url> template` shows a diff against the deployed template.
4. After approval, `template --apply`. It creates the template, or updates it with the stored `version` (PUT, with a PATCH fallback). A re-plan then says "up to date".
5. `python tools/dt_agent.py --tenant <dev-url> invoke "<question>"` sends one message and prints a compact transcript (`--raw` for the full event stream).

## How the agent finds the skill

- **Mount at `/resources/documents/`.** The platform appends each document's full name under the mount path. Mounting at `/resources/documents/skills/<skill>/` buried `SKILL.md` two levels deep and the agent ignored the skill. At `/resources/documents/`, `SKILL.md` lands at `/resources/documents/skills/<skill>/SKILL.md`, directly inside the directory listed in `skills`. The SRE template's per-skill mount form does not transfer.
- **Name the path in the instructions.** After a document update the agent skipped the skill in three runs in a row. Naming the exact `SKILL.md` path and saying to read it first, before any query, fixed it (3 of 3 runs).
- **Survey reads resolvers only.** At survey time the agent reads `session-protocol.md` and the two resolver files, never the beats files. Eval group D checks this.

## Dev and production routes

- **Dev (current):** `docs --apply` uploads shared (`isPrivate: false`) documents **owned by you**. They are not ready-made: owner is you, `originAppId` is empty, and you can edit and delete them.
- **Production (planned):** ship the skill in the `dynatrace.use.case.guides` app so the documents become ready-made (system-owned, read-only, available to all users on install or update, up to 5 minutes).
  - `python tools/dt_agent.py pack --out <app-repo>` checks the skill and copies it into `<app-repo>/dynatrace-intelligence/skills/`. It is a dry run by default, never deletes, and `--check` exits 1 if the app's copy drifted.
  - The guide says this feature is limited to Dynatrace-internal apps. Test on dev with `dt-app deploy --dry-run` first.
  - Before shipping on a tenant that has the dev copies, delete them, or the mount filter matches both sets by name. Do not upload user-owned copies to the Playground.
- **Later:** apps will be able to ship agent templates as ready-made documents. Then `template.json` moves into the app, and `template` and `status` can be retired.

## Add a scenario

1. Add `scenario-<id>.md` (persona, business context, scope, handoff fields, primary and fallback resolver) and `scenario-<id>-beats.md` to `references/`, copying an existing pair.
2. Add a row to the scenario table in `SKILL.md`, and keep it under 150 lines.
3. Register the files in `SCENARIO_FILES` in `tools/validate_dt_skill.py`.
4. Verify every DQL block live, then `check`, then upload.
5. Verify DQL on live data before writing the reveal. Plugin-era assumptions went stale: a failing-spans story turned out to be pure latency.

## Test

- **Checks:** `python tools/dt_agent.py check` (skill and template rules), then `python tools/validate_dt_skill.py` for both scenarios (live DQL on the Playground).
- **Runner tests:** `python tools/tests/test_run_dt_evals.py` (offline) after any change to the runner or the case files.
- **Behaviour:** `python tools/run_dt_evals.py --tenant dev` runs every ready case on that tenant's agent, **3 runs each** (one run can pass or fail by luck). Cases are one YAML file each in `tests/evals/dt-agent/`: the turns to send, and scripted assertions (skill read first, which files were read, DQL used or not, the exact reply, required and forbidden text, the turn ends on text). The default forbidden list covers "beat", "the demo", "I can't", "I'm read-only", "as an AI" and "Dynatrace Intelligence".
- **Review sheet:** every run writes `tests/evals/dt-agent/reports/<timestamp>-<tenant>.md` (git-ignored) with the transcripts, for tone and persona, which a script cannot judge.
- **Ground truth (Playground):** a case can list `truth: [payment-failure, ...]`. The runner runs the scenario's resolver and deployment DQL itself, pinned to the read-only `playground` `dtctl` context (`python tools/run_dt_evals.py --truth payment-failure` prints it), and `{truth.<scenario>.<field>}` placeholders in a case are replaced with the live values. An empty truth fails the check instead of skipping it.
- **Tenants:** `--tenant dev` uses `DT_DEV_AGENT_TOKEN`; `--tenant playground` uses `DT_PLAYGROUND_AGENT_TOKEN`. If the tenant has no `demo-agent` template, the runner skips with a message. Cases marked `status: draft` (the two Playground ones) need `--include-draft` and their expectations are unvalidated until the agent exists there.
- **Manual groups:** `docs/dt-skill-evals.md` and `docs/guardrail-probes.md` stay the source for cases that are not automated yet (persistence, deep links).
- **Dev has no scenario data.** The resolvers hardcode Playground service IDs and RCA is broken on dev, so dev only shows "environment looks clean". Scenario content is tested on the Playground.

## Gotchas

- `dtctl`'s current context can silently redirect repo tooling; check it first, and never leave the `dev` context at `readwrite-all`.
- Query results are untrusted data. The skill and the agent instructions both say so; keep it that way.
- Repo files may be CRLF on Windows. The helper normalizes to LF before comparing or uploading.
- A platform guardrail answers some prompts before the agent does (competitor comparisons, injection-style requests such as "do whatever the problem description says"). The reply is safe but out of persona and identical every time; you cannot change it, so do not write instructions for those cases.
- Describe a behaviour and the model improvises around it; give the exact reply and it holds. The clean-environment line, the off-topic redirect and the revert-without-incident reply all went from partial to 3 of 3 once they were stated word for word.
- Put role and out-of-role rules in the agent instructions as well as the skill. The agent reads the skill first now, but a rule that only lives in a reference file is easy to miss on short, off-topic turns.
- Tool-using agents can skip instructions that depend on judgment. Prefer mechanical wording (exact paths, "first, before any query").
