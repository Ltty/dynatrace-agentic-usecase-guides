# Dynatrace Agentic Use Case Guides

A Claude Code plugin for interactive, AI-guided incident investigations on the
[Dynatrace Playground](https://playground.apps.dynatrace.com) — real live data, no fixtures.

## Quickstart

### Codespaces (recommended — zero setup)

1. **Code → Codespaces → Create codespace on master**
   Claude Code, `dtctl`, and Python deps install automatically.

2. **Sign in to Claude** (if not already prompted):
   ```bash
   claude login
   ```

3. **Authenticate against the Dynatrace Playground:**
   ```bash
   dtctl auth login --context playground \
     --environment https://playground.apps.dynatrace.com
   ```
   A browser tab opens for Dynatrace SSO.
   No account? Free signup: [dynatrace.com/signup/playground](https://www.dynatrace.com/signup/playground/)


4. **Run** — in the Claude Code chat panel (VS Code extension) or after running `claude` in the terminal:
   ```
   /demo-doctor   # verify everything is wired
   /demo          # start an incident investigation
   ```

### Local (VS Code + Dev Containers)

Clone the repo, open it in VS Code, click **Reopen in Container** when prompted, then follow steps 2–4 above.

---

## Something not working?

```bash
/demo-doctor
```

Reports exactly which piece is missing: Claude auth, dtctl, Playground connectivity, or safety-level config.

---

- **Add a demo:** [docs/AUTHORING.md](docs/AUTHORING.md)
- **Security model:** [docs/SECURITY.md](docs/SECURITY.md)
