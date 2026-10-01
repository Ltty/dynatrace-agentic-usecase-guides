# Running on OpenCode

OpenCode is a zero-cost alternative to Claude Code for running the Agentic Guides.
You bring your own model; the skills, scenarios, and tools work unchanged.

## Prerequisites

- **Node 20+** (already in the devcontainer)
- **Python 3.11+** (already in the devcontainer)
- **dtctl** authenticated against the Playground — same as for Claude Code:
  ```bash
  python tools/preflight.py login
  ```

**In the devcontainer**, OpenCode and the global model config are set up automatically by
`post-create.sh` — no manual steps needed. Skip to "Running a demo" below.

## Install (outside devcontainer)

```bash
npm install -g opencode-ai
```

Then write the global model config — the model must live in `~/.config/opencode/opencode.json`,
not in the project-level `opencode.json` (which handles instructions and permissions only):

```bash
mkdir -p ~/.config/opencode
cat > ~/.config/opencode/opencode.json <<'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "model": "opencode/nemotron-3-ultra-free"
}
EOF
```

`opencode/nemotron-3-ultra-free` is a free bundled model available on OpenCode's platform —
no API key required, no external provider account needed. It has strong instruction following
and reliable tool calling, which are the two properties this demo engine depends on most.

### Alternative: bring your own API key

If you prefer a different model, set it in the global config instead. Provider API keys go
in the global config too — never in the project-level `opencode.json`, which is committed to
the repo. Using environment variables is cleanest:

```bash
export GROQ_API_KEY="your-key"   # or GOOGLE_API_KEY, OPENAI_API_KEY, etc.
```

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "groq/llama-3.3-70b-versatile"
}
```

## Experimental: Ollama (local, truly zero-cost)

Ollama works, but on hardware with ≤8GB VRAM the experience degrades noticeably. The
always-on instruction payload is ~12k tokens. Ollama's default `num_ctx` is 2048 — the skill
will be **silently truncated** if you don't raise it.

Minimum config:

```json
{
  "model": "ollama/qwen2.5-coder:7b",
  "provider": {
    "ollama": {
      "baseUrl": "http://localhost:11434",
      "options": {
        "num_ctx": 32768
      }
    }
  }
}
```

Use a model with verifiable tool-calling support (Qwen2.5-Coder, Mistral-Nemo, Llama3.1 8B).
Expect that persona adherence and the role guardrails degrade first — the engine's behavioural
rules are the longest section and are cut earliest when context fills. If the agent breaks
character or stops running queries, raise `num_ctx` further or switch to a hosted model.

On 6GB VRAM: 7–8B Q4 models fit but have only ~60–70% of the instruction payload in active
context. Budget at least one tuning pass before presenting to an audience.

## Running a demo on OpenCode

```bash
opencode                   # opens the TUI
/demo-doctor               # verify preflight
/demo                      # start the investigation
```

The same slash commands work as in Claude Code. The guard hook fires on every bash tool call
via `.opencode/plugin/guard-dtctl.ts`, which shells out to `tools/guard_dtctl.py`.

## Known differences from Claude Code

| Behaviour | Claude Code | OpenCode |
|---|---|---|
| Skills loaded at startup | `@import` in CLAUDE.md — silent | `instructions` array in opencode.json — same effect |
| Permission enforcement | `settings.json` deny-by-default | `opencode.json` permission globs |
| Hook mechanism | PreToolUse Python hook | TypeScript plugin shelling to the same Python |
| Agent mode env var | `CLAUDECODE=1` set by harness | not set — `--agent` flag on dtctl calls still works |
| ASCII waterfall | renders in Claude Code terminal | should render identically (same piped Python script) |
