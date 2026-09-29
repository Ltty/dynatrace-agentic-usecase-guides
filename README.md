# Dynatrace Agentic Use Case Guides

A Claude Code plugin for interactive, AI-guided incident investigations on the
[Dynatrace Playground](https://playground.apps.dynatrace.com) — real live data, no fixtures.

## Quickstart

### VS Code Desktop with Dev Containers (fully automatic sign-in)

1. Clone the repo, open it in VS Code, click **Reopen in Container** when prompted.
   Claude Code, `dtctl`, and Python deps install automatically.

2. **Sign in to Claude** — run `claude login` from the terminal.
   The OAuth callback reaches your local machine directly; sign-in completes automatically.

3. **Authenticate against the Dynatrace Playground:**
   ```bash
   python tools/preflight.py login
   ```
   A browser tab opens; sign in once, and it completes with no further steps.
   No account? Free signup: [dynatrace.com/signup/playground](https://www.dynatrace.com/signup/playground/)

4. **Run** — in the Claude Code chat panel:
   ```
   /demo-doctor   # verify everything is wired
   /demo          # start an incident investigation
   ```

### Codespaces (sign-in via in-container browser)

1. **Code → Codespaces → Create codespace on master**
   Claude Code, `dtctl`, Chromium, and Python deps install automatically.

2. **Forward port 6080** (the noVNC desktop) — VS Code shows it in the Ports panel.
   Open the forwarded URL in your local browser.
   Default VNC password: `changeme` (set in `.devcontainer/devcontainer.json`).

3. **Sign in to both Claude and the Dynatrace Playground** — inside the noVNC desktop,
   open a terminal and run:
   ```bash
   bash tools/login-in-container.sh
   ```
   Chromium opens inside the container; OAuth callbacks resolve on the container's own
   loopback without any port-forwarding needed.

   **Important:** run this from the noVNC desktop terminal, not from VS Code's integrated
   terminal. VS Code's integrated terminal intercepts browser opens and forwards them to your
   local machine, where the OAuth callback can't reach the container.
   No account? Free signup: [dynatrace.com/signup/playground](https://www.dynatrace.com/signup/playground/)

5. **Run** — in the Claude Code chat panel:
   ```
   /demo-doctor   # verify everything is wired
   /demo          # start an incident investigation
   ```

---

## Something not working?

```bash
/demo-doctor
```

Reports exactly which piece is missing: Claude auth, dtctl, Playground connectivity, or safety-level config.

---

- **Add a demo:** [docs/AUTHORING.md](docs/AUTHORING.md)
- **Security model:** [docs/SECURITY.md](docs/SECURITY.md)
