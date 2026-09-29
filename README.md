# Dynatrace Agentic Use Case Guides

A Claude Code plugin for interactive, AI-guided incident investigations on the
[Dynatrace Playground](https://playground.apps.dynatrace.com) — real live data, no fixtures.

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

---

## Something not working?

```
/demo-doctor
```

Reports exactly which piece is missing and how to fix it.

---

- **Add a demo:** [docs/AUTHORING.md](docs/AUTHORING.md)
- **Security model:** [docs/SECURITY.md](docs/SECURITY.md)
