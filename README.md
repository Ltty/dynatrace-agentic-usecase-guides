# Dynatrace Agentic Use Case Guides

A Claude Code plugin for interactive, AI-guided incident investigations on the
[Dynatrace Playground](https://playground.apps.dynatrace.com) — real live data, no fixtures.

## Quickstart

### Codespaces (recommended — zero setup)

1. **Code → Codespaces → Create codespace on master**
   Claude Code, `dtctl`, and Python deps install automatically.

2. **Sign in to Claude** — the Claude Code extension prompts automatically when the Codespace opens.
   Click **Sign in** in the Claude panel (sidebar).
   Do not run `claude login` from the terminal — the terminal OAuth callback won't reach the container.

3. **Authenticate against the Dynatrace Playground** — two steps because dtctl's OAuth
   callback goes to `127.0.0.1:3232` on your local machine, so you need to tunnel that
   port to the Codespace first.

   **Step A — in a local terminal** (not the Codespace):
   ```bash
   gh codespace ssh -- -NL 3232:localhost:3232
   ```
   Leave this running. It forwards local port 3232 → Codespace's dtctl server.

   **Step B — back in the Codespace terminal:**
   ```bash
   dtctl auth login --context playground \
     --environment https://playground.apps.dynatrace.com
   ```
   A browser tab opens. Log in, the callback completes, close the tunnel terminal.
   No account? Free signup: [dynatrace.com/signup/playground](https://www.dynatrace.com/signup/playground/)

4. **Run** — in the Claude Code chat panel:
   ```
   /demo-doctor   # verify everything is wired
   /demo          # start an incident investigation
   ```

### Local (VS Code + Dev Containers)

Clone the repo, open it in VS Code, click **Reopen in Container** when prompted, then follow steps 2–4 above.
Here `claude login` from the terminal works fine — the callback reaches your local machine directly.

---

## Something not working?

```bash
/demo-doctor
```

Reports exactly which piece is missing: Claude auth, dtctl, Playground connectivity, or safety-level config.

---

- **Add a demo:** [docs/AUTHORING.md](docs/AUTHORING.md)
- **Security model:** [docs/SECURITY.md](docs/SECURITY.md)
