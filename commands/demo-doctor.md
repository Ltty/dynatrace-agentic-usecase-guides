# /demo-doctor

Run preflight checks for the Dynatrace Agentic Guides demo environment.
Use this before starting any demo, and whenever something seems broken.

## What it checks

1. dtctl installed and reachable
2. OAuth session valid (or prompts to re-authenticate)
3. Context set to `playground` with `safety-level: readonly`
4. DQL query reachable against `dt.davis.problems`
5. Available scenarios from `scenarios/registry.yaml`

## Instructions

Run:

```
python tools/preflight.py check
```

Then present the results clearly:

- Show each check as a pass ✅ or fail ❌ with a one-line fix instruction on failures.
- If auth is missing, show the exact command to run: `dtctl auth login --context playground --environment https://playground.apps.dynatrace.com`
- If the safety level is not `readonly`, show: `dtctl config set-context playground --safety-level readonly`
- If all checks pass, show: "All checks passed — run `/demo` to see available demos."

Do not attempt to fix auth automatically. Auth requires a browser window and must be initiated by the user.
