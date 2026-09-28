Run preflight checks for the Dynatrace Agentic Guides demo environment.

## Steps

1. Run the check — do this silently, no preamble text:
   ```bash
   cd C:/public/dynatrace/agentic-usecase-guides && python tools/preflight.py check
   ```
   `tools/preflight.py` auto-locates dtctl itself (checks common install dirs even when PATH
   doesn't have it) — don't run a pre-emptive PATH export before this, it's an unneeded extra
   tool call for something the script already handles.

2. Present each result as **✅ pass** or **❌ fail**. For every failure, show the fix command
   directly below the failing check — copy-paste ready, not in a lookup table. Use this shape:

   > ❌ **dtctl not authenticated**
   > Run this to authenticate (a browser tab will open for Dynatrace SSO):
   > ```bash
   > python tools/preflight.py login
   > ```
   > No account yet? Free signup: https://www.dynatrace.com/signup/playground/

   Fix commands per check:

   | Check | Fix command |
   |-------|-------------|
   | dtctl not installed | Not found in any standard location. Use the devcontainer (zero-install), or download the binary from https://github.com/dynatrace-oss/dtctl/releases and add it to PATH. |
   | dtctl doctor (auth) | `python tools/preflight.py login` — opens a browser for Dynatrace SSO. In a Codespace, paste the failed callback URL back when prompted. |
   | safety level ≠ readonly | `dtctl config set-context playground --safety-level readonly` |
   | DQL not reachable | Auth is broken — fix dtctl doctor first, then re-run `/demo-doctor`. |

3. After all checks, add one line for Claude Code auth state:
   - If running inside VS Code / Codespaces with the Claude Code extension, auth is already
     handled by the extension — no action needed.
   - If running in a bare terminal (e.g. after `npm install -g @anthropic-ai/claude-code`),
     remind the user: "If `claude` CLI isn't signed in yet, run `claude login`."

4. On full success, say: **"All checks passed — type `/demo` to see what's happening in the Playground."**

Do not attempt to fix auth automatically. Auth requires a browser and must be initiated by the user.
