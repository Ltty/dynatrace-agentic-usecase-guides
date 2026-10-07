# demo-agent

A Dynatrace `deep-agent` that runs the skill `investigating-playground-incidents` (payment failure and the
image-service slowdown) as an on-call SRE on the Dynatrace Playground.

| File | Purpose |
|---|---|
| `template.json` | The AI API payload: model, `execute-dql` as the only tool, the skill mount, platform control off |
| `instructions.md` | The agent's instructions, inlined into `agent_instructions.text` when rendered |

```bash
python tools/dt_agent.py render                                      # the exact payload, offline
python tools/dt_agent.py --tenant <url> template                     # dry run: diff against the tenant
python tools/dt_agent.py --tenant <url> template --apply             # create or update (ask first)
python tools/dt_agent.py --tenant <url> invoke "any open issues?"    # smoke test
```

The token comes from `DT_DEV_AGENT_TOKEN`. Scopes, mount rules, deploy flow and the move to an app-shipped
agent are in [docs/DYNATRACE-SKILL.md](../../../docs/DYNATRACE-SKILL.md).
