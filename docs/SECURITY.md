# Security model

## No shared secrets

This repo contains **no tokens, credentials, or shared secrets** — not in code, not in
Codespaces secrets, not in environment variables baked into the image.

Every user authenticates with their own Dynatrace account via browser OAuth:

```bash
dtctl auth login --context playground \
  --environment https://playground.apps.dynatrace.com
```

The resulting token is stored in the user's own OS keyring (or in `~/.config/dtctl/` for
headless environments with `DTCTL_TOKEN_STORAGE=file`). It never enters the repo.

Why not a shared token? GitHub Codespaces secrets are readable by anyone who opens the
Codespace (`echo $EXAMPLE_API_KEY` works by design). A shared token injected via Codespaces
org secrets gives every user full read access under one identity — no audit trail, no
revocation per user, and no way to prevent the token being exfiltrated. Per-user OAuth gives
each user their own session, tied to their Dynatrace account, with full audit trail.

## Read-only enforcement

The Playground is a read-only environment. We enforce this in three independent layers:

| Layer | Mechanism | Enforced by |
|-------|-----------|-------------|
| 1 | dtctl context `safety-level: readonly` | dtctl config (client-side) |
| 2 | `.claude/settings.json` deny-by-default | Claude Code harness |
| 3 | `PreToolUse` hook `guard-dtctl.py` | Python hook, per-call |

Layer 1 is dtctl's own client-side protection — it blocks mutating verbs before any HTTP
request is made. Layer 2 is Claude Code's permission system — it prevents the model from
invoking non-allowlisted tool calls. Layer 3 is the hook — it parses every Bash call at
the verb and DQL level, independent of the model's intent.

All three layers must be bypassed simultaneously to issue a write. That requires:
- Modifying the dtctl config (needs OS keyring access or file write to `~/.local/share/dtctl`)
- Modifying `.claude/settings.json` (needs repo write access)
- Modifying the hook itself (needs repo write access)

In a Codespace, the user's own OAuth token would still need the write scope, which the
Playground likely does not grant to non-admin users.

## Token scopes

The OAuth flow requests the scopes dtctl needs for read operations. For the demo engine,
the relevant scopes are:

- `storage:logs:read`, `storage:spans:read`, `storage:events:read` — DQL data access
- `storage:entities:read`, `storage:user.sessions:read` — entity and session queries
- `davis:analyzers:read` — Davis CoPilot read
- `davis-copilot:conversations:execute` — Davis CoPilot chat
- `app-engine:apps:run` — Playground app access

The `readonly` safety level instructs dtctl to request only read scopes. If the Playground
restricts the set of scopes available to a user's account, the effect is tighter not looser.

## What a user can do

- Query the Playground's Grail data store (read-only)
- Chat with Davis CoPilot
- View entity inventory
- Open Dynatrace apps via the deep links presented in each beat

## What a user cannot do

- Write to any Grail data object (DQL or API)
- Create, modify, or delete Dynatrace resources (workflows, dashboards, settings)
- Query data outside the scenario's `scope.data_objects` list
- Issue curl/wget requests to non-Dynatrace hosts
- Exfiltrate any data outside the terminal session (no outbound webhooks, no email)
