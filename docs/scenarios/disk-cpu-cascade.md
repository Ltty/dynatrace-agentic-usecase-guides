# disk-cpu-cascade — maintainer notes

Not read by the agent (it lives outside the skill folder). The scenario is in
`dynatrace-intelligence/skills/investigating-playground-incidents/references/scenario-disk-cpu-cascade*.md`.

## Where it runs

The `dev` tenant (`fxz0998d.dev.apps.dynatracelabs.com`), host group `cloud-alerts-demo`. The Playground runs the
same demo under different IDs (host `HOST-EBC5983479603BE2`, problem `P-26092140`, whose record has no root cause), so
the beats and links, which hardcode the dev IDs, would not work there. The fallback resolver therefore requires the dev
host ID among the affected entities (`contains(toString(smartscape.affected_entities), "HOST-A2BABAD05D401471")`), and
returns nothing on the Playground, so a Playground survey does not list it. Before that guard it did (testruns 12 and
13). The local `/demo` pins `--context playground` and cannot reach it; `@demo-agent` on the dev tenant can. Validate it with
`python tools/validate_dt_skill.py --scenario disk-cpu-cascade` (the validator picks the `dev` context from
`SCENARIO_CONTEXT`); `python tools/preflight.py preflight` skips it.

The `dev` dtctl context is `readwrite-all`. Use it only for `dtctl query`; the guard hook rejects anything else.

## How it differs from the first draft (validated live 2026-10-08)

| Draft | Live result | Now |
|---|---|---|
| Resolver filters `root_cause_entity_id` | Field absent on dev; root cause is `root_cause.smartscape_entity`, only on the newest platform-analysed record, and its id needs `toString()` | Resolver filters on `toString(root_cause_id)` |
| `affected_users` | `dt.davis.affected_users_count` absent | `affected_count` = `arraySize(smartscape.affected_entities)` (2) |
| Resolver window `now()-30d` | Scanned 22.9 GB per run | `now()-48h` (1.5 GB), like the other scenarios; the problem is refreshed continuously while active |
| `dt.host.disk.avail.percent` | Doesn't exist (zero series) | `dt.host.disk.free` (percent) and `dt.host.disk.avail` (bytes) |
| `by: { dt.entity.host }` | Not a dimension; one tenant-wide series (about 24% CPU) | `by: { host.name }` |
| Beat 4 `dt.entity.host == "HOST-…"` | Events have no such field: 0 rows | `host.name == "frontend-high-cpu"`, grouped per failure message |
| "CPU is high because of I/O wait" | I/O wait averages 0.0002% (max 0.0035%) over all 26 days; CPU min 94.2%, avg 99.3% | Beat 3 reports both and says the data does not show the mechanism |
| "Something filled this disk" | Free space is constant (0.76%, 77.5 MB) from the first bucket | Beat 2 says the data shows it stayed full, not how it filled |
| "All three symptoms resolve from one fix" | Not shown by the data | Beats 4 and 5 state only what the failure message says |
| Beat 3 titled "The Fill Rate" | It is about CPU | Renamed "The CPU" |
| "Davis named…" | Branding | "Dynatrace Intelligence" |
| Hook states "OneAgent can't update itself" and "no user-facing requests are failing" | The second is not in the data | Hook uses only resolver fields |

Other facts, as of 2026-10-08:

- The problem has been ACTIVE since 2026-09-12 06:07 UTC (about 26 days, `duration_min` 37,609 at validation).
  Two non-duplicate records exist for it (`P-2609144538`, platform RCA, with the root cause; `P-260916957`, a refreshed
  copy without it). The resolver's root-cause filter is what keeps it off the second one.
- OneAgent update failures on this host: 16 events over 8 distinct target versions, 2026-09-13 to 2026-10-08, all
  `NotEnoughDiskSpace` from `1.348.0.20260901-163918`. The problem `description` quotes an older target
  (`1.349.0.20260914-171338`) than the newest event (`1.350.0.20261001-181022`).
- The problem record has no owner field, so the handoff has no team.
- Deep links point at the dev tenant. The `dynatrace.infraops/explorer?entityId=` links are carried over from the
  draft and have not been opened.
- The greeting in the skill says "Astroshop"; on the dev tenant that wording is generic.
