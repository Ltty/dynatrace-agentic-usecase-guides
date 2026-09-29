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
- **OpenCode** installed:
  ```bash
  npm install -g opencode-ai
  ```

## Recommended: free-tier hosted model

OpenCode connects to any OpenAI-compatible provider. For this demo the requirements are:

| Requirement | Why |
|---|---|
| Reliable tool calling | The beat loop makes 2–5 tool calls per turn; unreliable calling breaks the narrative flow |
| ≥32k usable context | The always-on instruction payload is ~12k tokens; scenario.yaml adds ~2k more |
| Free or cheap | The whole point of this path is zero per-demo cost |

**Google Gemini 1.5 Flash** (free tier, 1M context) or **Groq Llama 3.3 70B** (free tier, 128k
context) both meet these requirements. Set your provider in `opencode.json`:

```json
{
  "model": "google/gemini-1.5-flash",
  "provider": {
    "google": {
      "apiKey": "YOUR_KEY"
    }
  }
}
```

Or for Groq:

```json
{
  "model": "groq/llama-3.3-70b-versatile",
  "provider": {
    "groq": {
      "apiKey": "YOUR_KEY"
    }
  }
}
```

Do not commit your API key — add `opencode.json` to `.gitignore` if you store it there, or
use environment variables (`GOOGLE_API_KEY`, `GROQ_API_KEY`) which OpenCode reads automatically.

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
