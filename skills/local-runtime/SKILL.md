---
name: local-runtime
description: >
  Runs the Dynatrace demo-agent and its skill investigating-playground-incidents locally in
  Claude Code or OpenCode, with dtctl in place of the Dynatrace runtime's tools. Use when running
  /demo locally. Holds only the tool and path mapping; every behaviour rule lives in the Dynatrace
  skill and agent instructions.
---

# Local runtime for the demo-agent

The agent instructions (`dynatrace-intelligence/agents/demo-agent/instructions.md`) and the skill
they name are written for the Dynatrace agent runtime. Follow them exactly, with these mappings.
This file adds no behaviour of its own, apart from the local-only notes below on the Bash
description, PowerShell, the proof stamp and the authentication notice.

## Tool mapping

| Dynatrace runtime | Here |
|---|---|
| `read_file` on `/resources/documents/skills/<name>/<path>` | Read `dynatrace-intelligence/skills/<name>/<path>` |
| `execute-dql` / `dynatrace-mcp:execute-dql` | `dtctl query` through the Bash tool, shape below |
| The result's "Query metadata" | The envelope's `metadata` object |

## Running DQL

`<dtctl>` is `dtctl`. Only if the shell reports it is not found, run `python tools/preflight.py dtctl-path`
once and use its output instead. Every query is:

```bash
<dtctl> query '<dql>' --context playground --agent -o json --plain --max-field-chars 0 -M=queryId,scannedRecords,executionTimeMilliseconds
```

- Use `<dtctl>` as given above. Wrap the DQL in single quotes; it may span several lines.
- `--context playground` on every call pins the read-only Playground context, whatever the
  saved current context is.
- Substitute every `{{TOKEN}}` yourself before the call, as the skill describes. There is no
  pre-substitution step and no state file.
- Use the Bash tool for `dtctl`. Windows PowerShell 5.1 strips the double quotes inside DQL
  string literals, so the same query silently returns no rows there.
- The Bash description reads as an SRE looking something up ("Checking the deployments on the
  payment service"), never as a script or file name.

## Reading the result

The envelope is `{ok, result: {kind, constant, records}, context: {total}, metadata}`.

- A full row is `result.constant` merged with the record; the record wins, and an absent key is null.
- Proof stamp (local only; the Dynatrace agent shows none): after a beat's first query, one line
  `queryId <metadata.queryId, copied exactly> · <metadata.scannedRecords> records scanned · <metadata.executionTimeMilliseconds> ms`.
  Never in the survey or the clean-environment reply, and none if the envelope has no metadata. On a peak beat the
  finding line stays first; the stamp follows the explanation, directly above the deep link.
- `ok: false` or a non-zero exit is a failed query; follow the skill's error handling.
- Exit code 3 means authentication expired: the only time you step out of character, say one
  line asking the user to run `python tools/preflight.py login`, and stop.
