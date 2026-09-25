Run preflight checks for the Dynatrace Agentic Guides demo environment.

## Steps

1. Read `tools/preflight.py` to understand what it checks.
2. Run: `python tools/preflight.py check`
3. Present each check result as a clear pass ✅ or fail ❌ with a one-line fix instruction on failures.

## Key fix instructions for failures

- **dtctl not found**: The devcontainer setup installs it. Locally: see https://github.com/dynatrace-oss/dtctl
- **Auth / OAuth session expired**: `dtctl auth login --context playground --environment https://playground.apps.dynatrace.com`
- **Safety level not readonly**: `dtctl config set-context playground --safety-level readonly`
- **DQL not reachable**: Usually an auth problem — fix auth first, then retry.

## On success

Show: "All checks passed — you're ready. Type `/demo` to see what's happening in the Playground."

Do not attempt to fix auth automatically. Auth requires a browser and must be initiated by the user.

Note: `dtctl` must be on PATH. If running locally (not in the devcontainer), add it:
`export PATH="$PATH:$HOME/.local/bin"` or `export PATH="$PATH:$LOCALAPPDATA/dtctl"` on Windows.
