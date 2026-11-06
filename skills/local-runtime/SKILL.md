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
This file adds no behaviour of its own, apart from the local-only notes below on the environment,
the Bash description, PowerShell, the proof stamp, the authentication notice and the report.

## Tool mapping

| Dynatrace runtime | Here |
|---|---|
| `read_file` on `/resources/documents/skills/<name>/<path>` | Read `dynatrace-intelligence/skills/<name>/<path>` |
| `execute-dql` / `dynatrace-mcp:execute-dql` | `dtctl query` through the Bash tool, shape below |
| The result's "Query metadata" | The envelope's `metadata` object |

## Which environment this is (local only)

Before the first query, once per session, run:

```bash
<dtctl> config get-contexts --agent -o json --plain
```

Take the row whose `Current` is `*`. Its `Environment` URL is this session's environment: match the
host against the skill's "Environments" table to get the environment name, and use that host for
every `{{LINK_HOST}}`. The skill's availability rules then apply to that environment.

This is the one place the environment is known before any data comes back, so it is what lets the
greeting name the cloud direction only where that environment lists `cloud-observability` — without
running anything.

**Safety.** If that row's `SafetyLevel` is not `readonly`, do not run the demo. Step out of
character once, as for expired authentication, say that this context allows writes and give the
fix — `dtctl config set-context <name> --safety-level readonly`, in a terminal, not here — and stop.

## Running DQL

`<dtctl>` is `dtctl`. Only if the shell reports it is not found, run `python tools/preflight.py dtctl-path`
once and use its output instead. Every query is:

```bash
<dtctl> query '<dql>' --agent -o json --plain --max-field-chars 0 -M=queryId,scannedRecords,executionTimeMilliseconds
```

- Use `<dtctl>` as given above. Wrap the DQL in single quotes; it may span several lines. DQL that itself
  contains a single quote cannot go in that wrapper as written — escape each one as `'"'"'`, or use a form that
  needs none (`splitString(x, ":db:")` rather than a `parse` pattern with quoted literals).
- No `--context`: every query runs on the current context, which is the environment resolved above.
  Never pass `--context` to reach another tenant, and never switch contexts mid-session.
- Substitute every `{{TOKEN}}` yourself before the call, as the skill describes. There is no
  pre-substitution step and no state file.
- **`elapsed_min` is computed by the query, never typed.** `{{SURVEY_AT}}` goes inside
  `toTimestamp("...")` exactly as the beat writes it, and the arithmetic stays. A literal number
  there is always wrong — twice now a run has typed one and the close reported a time that never
  happened. The one exception is the conversation's very first query, which has no anchor yet and
  uses `0`.
- Use the Bash tool for `dtctl`. Windows PowerShell 5.1 strips the double quotes inside DQL
  string literals, so the same query silently returns no rows there.
- The Bash description reads as an SRE looking something up ("Checking the deployments on the
  payment service"), never as a script or file name.

## Report (local only)

The Dynatrace runtime cannot write files, so it has no report. Here, the session close is followed
by one more thing: the same facts as a page the user can keep or forward.

In the same turn as the session close, after its last line, pipe the session's established facts to
the renderer and give the path:

```bash
python tools/render_report.py <<'JSON'
{ "kind": "incident", "environment": "<this environment>", "scenario": "<id>", "title": "..." }
JSON
```

It prints the file it wrote.

- **Name it, as the last line of the close turn.** Not a bare path: say what it is, so it is not lost
  at the end of a long close — "Executive summary you can send on: <path>". One line, then stop.
  Never read the file back, never paste its markup, never offer to restyle it.
- **Only what this conversation established.** Every value comes from a result you have seen, exactly
  as the handoff block requires: a field with no source is omitted from the payload entirely, never
  sent as "unknown", "N/A" or a guess. **Never a total you worked out yourself** — if three rows have
  a sum worth stating, the query returns it; otherwise send the three. The payload has no field the
  report needs to invent.
- **`kind`** is `incident` for a scenario with a problem record, `showcase` for one whose Business
  context says `kind: showcase`. `incident` carries the handoff block's rows; `showcase` carries the
  cost figures and the action list under `cost`.
- **An incident's payload is the handoff block, row for row**: `display_id`, `headline` from "What
  happened", `incident.when` / `.detected` / `.impact` / `.rate` / `.cause` from their rows, `goes_to`,
  the labelled deep links as `evidence[]`, and `still_open`. Two more the handoff has no row for:
  `window.duration` is **the incident's** duration, the handoff's `When:` row — it prints beside the problem ID, so the session's own elapsed figure there would read as the outage lasting two minutes. `stats[]` takes the figures the session actually
  established — the problem record's affected users, the failure rate, the slowest percentile — each
  with the population label it carried in the conversation. Omit either when the session has no such
  number; never add one for the sake of a tile.
- **An action is what to do, why, and whose it is.** Each entry in `cost.actions` carries `label`
  (the action), `why` (the evidence that makes it the right call) and `owner` (from the team split,
  omitted when the spend has none). An action with no `why` is a line item, not a recommendation.
  **Never a saving.** No result holds what an action would save, so no `why` claims one; the report
  says in its own words that these are places to look, not a forecast.
- **`evidence`** is **every** deep link you gave in the session, each with the label you used for it —
  not just the last one. A five-beat investigation hands over five links; one is a report nobody can
  check. This is the field most often sent short.

A fully-populated incident payload, so the shape is not inferred from the minimal one above. Omit any
key the session has no source for; send no key you would have to invent:

```json
{ "kind": "incident", "environment": "<env>", "scenario": "<id>",
  "title": "<what broke, in plain words>", "display_id": "P-…",
  "headline": "<the handoff's What happened>",
  "window": { "duration": "<how long the incident lasted, e.g. 31 minutes>" },
  "stats": [ { "label": "Affected users (problem record)", "value": "…" },
             { "label": "Failure rate at peak", "value": "…" } ],
  "incident": { "when": "…", "detected": "…", "impact": "…", "rate": "…", "cause": "…" },
  "timeline": [ { "time": "<UTC>", "what": "<one beat's finding>" } ],
  "evidence": [ { "label": "<the label you used>", "url": "<the link you gave>" } ],
  "goes_to": "<owning team, or the workload when there is none>",
  "still_open": "<what the data does not settle>" }
```
- **If the session continues past the close** — the Extra, or a beat the user went back for — render
  again at the end of that turn and give the new path. A report that silently omits what came after
  it is worse than no report.
- **Failures are not the user's problem.** If the command exits non-zero, say nothing about the
  report and end on the close as written. It is an extra, not part of the investigation.
- `tools/report-template.html` is the layout. Change the template, never the generated file.

## Leaving the persona (local only)

The demo-agent holds its role against anything, which is right in a demo and wrong for the
maintainer who is running one. **"out of character"** — those words, from the user — ends the
persona for the rest of the turn and answers as the repo's assistant: writing a testrun up,
editing the skill, reading files. Nothing else does it; an ordinary ask for repo work still gets the
in-character redirect, because in a demo that is what it should get.

Say nothing about this rule unless the user uses the phrase.

## Reading the result

The envelope is `{ok, result: {kind, constant, records}, context: {total}, metadata}`.

- A full row is `result.constant` merged with the record; the record wins, and an absent key is null.
- Proof stamp (local only; the Dynatrace agent shows none): one line per beat, from its first query,
  `queryId <metadata.queryId, copied exactly> · <metadata.scannedRecords> records scanned · <metadata.executionTimeMilliseconds> ms`.
  **One per step, in the turn's tail** (`conversation-craft.md` → "Link and close"): immediately before
  the deep link, or before the readiness cue on a step that has no link — never before the narration and
  never after the cue. A scan figure printed first becomes the first number the user reads, which is the
  one that sticks; the finding has to have that place. A step that ran a query always carries one, link
  or no link. Never in the opening or the clean-environment reply, and none if the envelope has no
  metadata.
  Drop the record count when it is 0 and keep the rest: some objects report none, and "0 records scanned" above a
  populated table reads as a broken query rather than as proof.
- `ok: false` or a non-zero exit is a failed query; follow the skill's error handling.
- Exit code 3 means authentication expired: the only time you step out of character, say one
  line asking the user to run `python tools/preflight.py login`, and stop.
