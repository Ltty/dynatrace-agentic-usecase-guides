# Dynatrace Agentic Use Case Guides

Interactive, AI-guided incident investigations on the
[Dynatrace Playground](https://playground.apps.dynatrace.com) — real live data, no fixtures. Runs in Claude Code
(as a plugin), OpenCode, and as an agent inside Dynatrace.

## How it works

`/demo` starts a conversation with an on-call SRE for the Astroshop environment. Ask what's going on, pick an
incident, and the SRE digs in with you on live data: the page, the change that caused it, the failing
requests, who was affected, and a handoff to the owning team. Every number comes from a query it ran in front
of you, and it says where the data stops.

It is the same agent as `@demo-agent` in Dynatrace Assist: one skill and one prompt under
[dynatrace-intelligence/](dynatrace-intelligence/), run locally through `dtctl`.

## Quickstart

### Codespaces

1. **Code → Codespaces → Create codespace on master**
   Claude Code, `dtctl`, and Python deps install automatically.

2. **Sign in to Claude** — click **Sign in** in the Claude Code panel (sidebar).

3. **Authenticate against the Dynatrace Playground:**
   ```bash
   python tools/preflight.py login
   ```
   A browser window opens for Dynatrace SSO. After signing in the browser shows a
   "can't connect" page — copy that URL and paste it into the terminal prompt.
   No account? Free signup: [dynatrace.com/signup/playground](https://www.dynatrace.com/signup/playground/)

4. **Run** — in the Claude Code chat panel:
   ```
   /demo-doctor   # verify everything is wired
   /demo          # start an incident investigation
   ```

### Local (VS Code + Dev Containers)

Clone the repo, open in VS Code, click **Reopen in Container**, then follow steps 2–4 above.
`claude login` from the terminal works here — the callback reaches your local machine directly.

### OpenCode (free-tier alternative)

OpenCode lets you run the same demos with a hosted free-tier model instead of Claude Code.
Zero per-demo cost, same skill and scenarios.

1. **Install OpenCode and configure the free bundled model:**
   ```bash
   npm install -g opencode-ai
   mkdir -p ~/.config/opencode
   echo '{"model":"opencode/nemotron-3-ultra-free"}' > ~/.config/opencode/opencode.json
   ```
2. **Authenticate against the Dynatrace Playground** (same as above):
   ```bash
   python tools/preflight.py login
   ```
3. **Run:**
   ```bash
   opencode
   /demo-doctor   # verify everything is wired
   /demo          # start an incident investigation
   ```

   In the devcontainer, steps 1 and 2 happen automatically — just run `opencode`.

---

## Something not working?

```
/demo-doctor
```

Reports exactly which piece is missing and how to fix it.

---

- **Add a scenario:** [docs/AUTHORING.md](docs/AUTHORING.md)
- **Change the skill or agent:** [docs/DYNATRACE-SKILL.md](docs/DYNATRACE-SKILL.md)
- **Security model:** [docs/SECURITY.md](docs/SECURITY.md)
- **OpenCode setup:** [docs/OPENCODE.md](docs/OPENCODE.md)
