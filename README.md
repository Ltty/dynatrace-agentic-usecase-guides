# Dynatrace Agentic Use Case Guides

A Claude Code plugin for interactive, AI-guided incident investigations on the
[Dynatrace Playground](https://playground.apps.dynatrace.com) — real live data, no fixtures.

## Two modes

`/demo` opens a mode menu on every session:

- **[A] Investigate with me** — conversational 1:1. Ask anything, the engine digs in live.
  Best for self-serve exploration or walk-through with a single person.
- **[B] Presenter mode** — stage-ready 1:many. Fixed beat order, DQL shown before each run,
  raw dtctl table as the evidence. The user advances with `n`; off-script questions are
  answered inline and the step resumes. Best for demos to a room or a screenshare audience.

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
Zero per-demo cost, same skills and scenarios.

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

- **Add a demo:** [docs/AUTHORING.md](docs/AUTHORING.md)
- **Security model:** [docs/SECURITY.md](docs/SECURITY.md)
- **OpenCode setup:** [docs/OPENCODE.md](docs/OPENCODE.md)
