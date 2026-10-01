Run preflight checks for the Dynatrace Agentic Guides demo environment.

## Steps

1. Run the check — do this silently, no preamble text:
   ```bash
   python tools/preflight.py check
   ```
   `tools/preflight.py` auto-locates dtctl itself (checks common install dirs even when PATH
   doesn't have it) — don't run a pre-emptive PATH export before this, it's an unneeded extra
   tool call for something the script already handles.

2. Present each result as **✅ pass** or **❌ fail**. For every failure, show the fix command
   directly below the failing check — copy-paste ready, not in a lookup table. Use this shape:

   > ❌ **dtctl not authenticated**
   > Run this to authenticate:
   > ```bash
   > python tools/preflight.py login
   > ```
   > No account yet? Free signup: https://www.dynatrace.com/signup/playground/

   Fix commands per check:

   | Check | Fix command |
   |-------|-------------|
   | dtctl not installed | Not found in any standard location. Use the devcontainer (zero-install), or download from https://github.com/dynatrace-oss/dtctl/releases and add to PATH. |
   | dtctl doctor (auth) | `python tools/preflight.py login` — opens a browser for Dynatrace SSO. In VS Code Desktop or local Dev Containers, sign-in completes automatically. In a browser Codespace, sign in via the noVNC desktop (port 6080). |
   | safety level ≠ readonly | `dtctl config set-context playground --safety-level readonly` |
   | DQL not reachable | Auth is broken — fix dtctl doctor first, then re-run `/demo-doctor`. |

3. Run the scenario liveness check — silently, in the same block as step 1:
   ```bash
   python tools/preflight.py preflight
   ```
   Present results with the same ✅/❌ shape. Each line is one published scenario:
   - ✅ **payment-failure** — P-261038 ACTIVE, 333 users (live_active)
   - ❌ **flagd-rbac** — EMPTY, no live problem in the last 48h

   If the liveness check itself fails (DQL not reachable, registry missing), show:
   - ❌ **scenario liveness** — DQL not reachable — fix auth (step 2) then re-run

5. After all checks, add one line for Claude Code auth state:
   - If running inside VS Code / Codespaces with the Claude Code extension, auth is already
     handled by the extension — no action needed.
   - If running in a bare terminal (e.g. after `npm install -g @anthropic-ai/claude-code`),
     remind the user: "If `claude` CLI isn't signed in yet, run `claude login`."

6. On full success, say: **"All checks passed — type `/demo` to see what's happening in the Playground."**

Do not attempt to fix auth automatically. Auth requires a browser and must be initiated by the user.
