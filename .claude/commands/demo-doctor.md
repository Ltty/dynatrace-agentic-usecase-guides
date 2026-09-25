Run preflight checks for the Dynatrace Agentic Guides demo environment.

## Steps

1. **Set PATH first** — dtctl may not be on PATH in a fresh session. Run this before anything else:
   ```bash
   # Windows (run in Bash tool):
   export PATH="$PATH:/c/Users/$USERNAME/AppData/Local/dtctl"
   # Linux/Mac:
   export PATH="$PATH:$HOME/.local/bin"
   ```
   The preflight script also auto-searches common install locations, so this is a belt-and-suspenders step.

2. Run the preflight check:
   ```bash
   cd C:/public/dynatrace/agentic-usecase-guides && python tools/preflight.py check
   ```

3. Present each result as **✅ pass** or **❌ fail** with a one-line fix on failures:

| Check | Fix if failing |
|-------|---------------|
| dtctl installed | Windows: `$env:PATH += ";$env:LOCALAPPDATA\dtctl"` then restart terminal. Or run the devcontainer. |
| dtctl doctor | Run: `dtctl auth login --context playground --environment https://playground.apps.dynatrace.com` |
| safety level = readonly | Run: `dtctl config set-context playground --safety-level readonly` |
| DQL reachable | Auth problem — fix auth first |

4. On full success, say: **"All checks passed — type `/demo` to see what's happening in the Playground."**

Do not attempt to fix auth automatically. Auth requires a browser and must be initiated by the user.
