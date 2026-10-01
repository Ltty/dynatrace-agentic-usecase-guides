# Security model

## No shared secrets

This repo contains **no tokens, credentials, or shared secrets** — not in code, not in
Codespaces secrets, not in environment variables baked into the image.

Every user authenticates with their own Dynatrace account via browser OAuth:

```bash
python tools/preflight.py login
```

This runs `dtctl auth login --safety-level readonly` under the hood.
dtctl starts a local HTTP callback server on a port it picks at runtime and opens a browser.
In a browser Codespace that browser runs inside the container (via the `desktop-lite` feature),
so the OAuth redirect reaches dtctl directly and sign-in completes automatically.
In VS Code Desktop the port is forwarded onto the laptop's localhost, which also works.
As a last resort, the login wizard can accept a pasted callback URL — `tools/preflight.py`
extracts the real port from the authorization URL and replays the callback there directly.

The resulting token is stored per-user in `~/.local/share/dtctl/oauth-tokens/`
(controlled by `DTCTL_TOKEN_STORAGE=file` in `devcontainer.json`). It never enters the repo.

Why not a shared token? GitHub Codespaces secrets are readable by anyone who opens the
Codespace (`echo $EXAMPLE_API_KEY` works by design). A shared token injected via Codespaces
org secrets gives every user full read access under one identity — no audit trail, no
revocation per user, and no way to prevent the token being exfiltrated. Per-user OAuth gives
each user their own session, tied to their Dynatrace account, with full audit trail.

### Non-interactive auth (CI and automation)

If `DTCTL_CLIENT_ID` and `DTCTL_CLIENT_SECRET` are set when `preflight.py login` is called,
the wizard uses the OAuth client-credentials grant instead — no browser at all.
This is opt-in, never committed, and intended for CI pipelines:

```bash
export DTCTL_CLIENT_ID=dt0s02.EXAMPLE
export DTCTL_CLIENT_SECRET=dt0s02.EXAMPLE.SECRET
export DTCTL_ACCOUNT_URN=urn:dtaccount:00000000-0000-0000-0000-000000000000
export DTCTL_TOKEN_STORAGE=file
python tools/preflight.py login
```

The client-credentials grant issues no refresh token (RFC 6749 §4.4.3).
Re-run the command when the token expires.

If you already have dtctl authenticated on another machine, you can also export and import
a token with `dtctl config set-credentials`; see `dtctl config --help`.

## Read-only enforcement

The Playground is a read-only environment. We enforce this in three independent layers.
The specific mechanism for layers 2 and 3 differs by harness, but the guarantee is the same.

### Claude Code

| Layer | Mechanism | Enforced by |
|-------|-----------|-------------|
| 1 | dtctl context `safety-level: readonly` | dtctl config (client-side) — harness-independent |
| 2 | `.claude/settings.json` deny-by-default | Claude Code permission system |
| 3 | `PreToolUse` hook (`tools/guard_dtctl.py`) | Python hook, per-call |

### OpenCode

| Layer | Mechanism | Enforced by |
|-------|-----------|-------------|
| 1 | dtctl context `safety-level: readonly` | dtctl config (client-side) — harness-independent |
| 2 | `opencode.json` permission globs | OpenCode permission system |
| 3 | `.opencode/plugin/guard-dtctl.ts` (shells to `tools/guard_dtctl.py`) | TypeScript plugin, per-call |

**Layer 1 is the only layer that is truly harness-independent.** Layers 2 and 3 are
reimplementations for each harness, both backed by the same underlying Python script
(`tools/guard_dtctl.py`) for verb+DQL enforcement. The OpenCode path's read-only guarantee
was added in the `opencode-port` branch and should be verified with a full demo run before
treating it as equivalent to the Claude Code path.

All three layers must be bypassed simultaneously to issue a write. That requires:
- Modifying the dtctl config (needs OS keyring access or file write to `~/.local/share/dtctl`)
- Modifying the harness permission config (`settings.json` or `opencode.json`) — needs repo write access
- Modifying the guard script itself (`tools/guard_dtctl.py`) — needs repo write access

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

Hard limits (enforced by the three layers above — cannot be prompted away):
- Write to any Grail data object (DQL or API)
- Create, modify, or delete Dynatrace resources (workflows, dashboards, settings)
- Issue curl/wget requests to non-Dynatrace hosts

Soft limits (enforced by the engine skill prompt — can be overridden by a sufficiently
creative user prompt, but not by accident):
- Query data outside the scenario's `scope.data_objects` list
- Exfiltrate data by asking the engine to summarise and send it somewhere
- Pull the engine out of the SRE persona (product comparisons, cost/billing, demo mechanics)
- Get the engine to attempt or promise a remediation action (revert, code edit, restart, page)

---

## Dynatrace runtime (skill edition)

The `dynatrace-skill/` folder ports the engine to Dynatrace's native agentic skill format.
The security posture in that runtime differs from the Claude Code plugin.

### What stays the same

- **DQL has no write path.** The `fetch`-based DQL that all beat queries use cannot ingest,
  insert, update, or delete data. Ingest is a separate API, not accessible through query
  execution. This is a platform property — not asserted by the skill, and not bypassable by
  prompt.
- **Behavioural guardrails** (staying in role, declining remediation requests, refusing product
  comparisons) are instruction-only in both runtimes. `docs/guardrail-probes.md` covers
  manual verification.

### What changes

The Claude Code plugin enforces three independent layers:

| Layer | Claude Code plugin | Dynatrace runtime |
|---|---|---|
| 1 | dtctl `safety-level: readonly` (client-side) | **Gone** — no dtctl |
| 2 | `.claude/settings.json` verb allowlist (harness) | **Gone** — no harness hook |
| 3 | `guard_dtctl.py` PreToolUse hook (per-call) | **Gone** — no hook mechanism |

In the Dynatrace runtime, layer 1 is replaced by the platform's own execution constraint
(DQL fetch → read-only). Layers 2–3 have no equivalent; the data-object scope list in
`scenario-payment-failure.md` is instruction-only, not enforced.

### Honest summary

The Dynatrace runtime relies on one hard constraint (DQL read-only by design) and instruction-
level guardrails for everything else. This is weaker than the Claude Code plugin's three-layer
model. For a read-only, bounded investigation on Playground data, the platform constraint is
the load-bearing layer; the harness layers in the plugin provided defence-in-depth against
misuse of the dtctl CLI that doesn't apply here.
