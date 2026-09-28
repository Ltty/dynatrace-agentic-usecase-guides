Run preflight checks for the Dynatrace Agentic Guides demo environment.

## Steps

1. Run the check — do this silently, no preamble text:
   ```bash
   cd C:/public/dynatrace/agentic-usecase-guides && python tools/preflight.py check
   ```
   `tools/preflight.py` auto-locates dtctl itself (checks common install dirs even when PATH
   doesn't have it) — don't run a pre-emptive PATH export before this, it's an unneeded extra
   tool call for something the script already handles.

2. Present each result as **✅ pass** or **❌ fail** with a one-line fix on failures:

| Check | Fix if failing |
|-------|---------------|
| dtctl installed | Not found anywhere preflight.py checks. Windows: `$env:PATH += ";$env:LOCALAPPDATA\dtctl"` then restart terminal. Or run the devcontainer. |
| dtctl doctor | Run: `dtctl auth login --context playground --environment https://playground.apps.dynatrace.com` |
| safety level = readonly | Run: `dtctl config set-context playground --safety-level readonly` |
| DQL reachable | Auth problem — fix auth first |

3. On full success, say: **"All checks passed — type `/demo` to see what's happening in the Playground."**

Do not attempt to fix auth automatically. Auth requires a browser and must be initiated by the user.
