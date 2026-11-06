# Dynatrace Agentic Use Case Guides

Interactive, AI-guided incident investigations on live Dynatrace data — no fixtures. Runs in Claude Code
(as a plugin), OpenCode, and as an agent inside Dynatrace, against the
[Playground](https://playground.apps.dynatrace.com), a dev tenant, or an internal showcase tenant.

## How it works

`/demo` starts a conversation with an on-call SRE. It opens by checking what is actually live in whichever
environment you are pointed at, and lists only that. Pick an incident and it digs in with you on live data:
the page, the change that caused it, the failing requests, who was affected, and a handoff to the owning team.
Every number comes from a query it ran in front of you, and it says where the data stops. Or ask to be walked
through it: you get the whole story first, then each claim proved, ending in a handoff block. Where the
environment has the cloud estate on it, it can also show you how to find money on a cloud bill from real
data — what the bill says, where it concentrates, what is safe to touch, and who owns it.

Locally, the session close also renders an HTML report you can open and forward.

It is the same agent as `@demo-agent` in Dynatrace Assist: two skills and one prompt under
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

OpenCode runs the same demos with a hosted free-tier model instead of Claude Code.
Zero per-demo cost, same skill and scenarios.

**In the devcontainer or a Codespace, OpenCode is pre-installed** and already set to the free bundled model.
Two steps:

1. **Authenticate against the Dynatrace Playground** (once; it needs a browser, so it is not automatic):
   ```bash
   python tools/preflight.py login
   ```
2. **Run:**
   ```bash
   opencode
   /demo-doctor   # verify everything is wired
   /demo          # start an incident investigation
   ```

`dtctl` commands are pre-approved in `opencode.json`, so OpenCode does not ask before each one.
Anything that would change data is denied, and a guard plugin blocks it as well.
Other shell commands still ask.
More in [docs/OPENCODE.md](docs/OPENCODE.md).

**Outside the container**, install OpenCode and the free model first:

```bash
npm install -g opencode-ai
mkdir -p ~/.config/opencode
echo '{"model":"opencode/nemotron-3-ultra-free"}' > ~/.config/opencode/opencode.json
```

Then follow steps 1 and 2 above.

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
