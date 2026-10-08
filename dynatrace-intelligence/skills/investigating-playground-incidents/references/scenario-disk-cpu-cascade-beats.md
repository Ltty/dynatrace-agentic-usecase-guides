# Scenario: Disk / CPU Cascade — Beats

Read once the user has picked a direction from the survey. Resolver, scope, and handoff fields:
`references/scenario-disk-cpu-cascade.md`. Reveals describe the *shape* of a finding, never its values.
Timestamps, percentages, and version strings rotate every cycle — read them from the live result.

## Contents

- [Beat 1 — The Page](#beat-1--the-page)
- [Beat 2 — The Disk](#beat-2--the-disk)
- [Beat 3 — The CPU](#beat-3--the-cpu)
- [Beat 4 — The Platform Victim](#beat-4--the-platform-victim)
- [Beat 5 — The Handoff](#beat-5--the-handoff)

---

## Beat 1 — The Page

**Objective:** User grasps the blast radius: the `/data` disk is the root cause Dynatrace Intelligence
named, CPU saturation on the same host is listed as affected, and the problem record also lists the platform's
own agent failing to update.

**Evidence DQL:**

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter event.id == "{{PROBLEM_ID}}"
| sort timestamp desc
| limit 1
| fields
    display_id,
    status        = event.status,
    started       = event.start,
    root_cause    = root_cause.smartscape_entity[name],
    affected      = smartscape.affected_entities,
    impact_level  = dt.davis.impact_level,
    description   = event.description,
    queried_at    = now()
```

**Reveal:** Dynatrace Intelligence named the `/data` disk as the root cause — not the host and not the CPU. The
host `frontend-high-cpu` is listed as affected. Quote the disk threshold and the CPU threshold from
`description`, and say how many entities the problem covers. The description also lists an OneAgent update
failure: name the blocked version only if the description shows it, and say it is confirmed in beat 4. Say
what the record shows, not why: how the three relate is for the next beats to test.

**Success signal:** User names the disk, or asks why CPU is high, or asks about the OneAgent failure.

**Deep link:**

```text
https://fxz0998d.dev.apps.dynatracelabs.com/ui/apps/dynatrace.davis.problems/problem/{{PROBLEM_ID}}?from={{TF_FROM_MS}}&to={{TF_TO_MS}}
```

---

## Beat 2 — The Disk

**Objective:** User sees the free space on `/data` over the whole window and confirms it is critically low — not a
spike, a sustained floor.

**Evidence DQL:**

```dql
timeseries
    { free_pct = avg(dt.host.disk.free), avail_bytes = avg(dt.host.disk.avail) },
    by: { dt.entity.disk },
    from: "{{DQL_FROM}}", to: "{{DQL_TO}}",
    filter: dt.entity.disk == "DISK-2B3DB86FA32F6CE1"
| fieldsAdd
    buckets      = arraySize(free_pct),
    free_pct_min = round(arrayMin(free_pct), decimals: 2),
    free_pct_max = round(arrayMax(free_pct), decimals: 2),
    avail_mb_min = round(arrayMin(avail_bytes) / 1048576, decimals: 1),
    avail_mb_max = round(arrayMax(avail_bytes) / 1048576, decimals: 1)
| fields dt.entity.disk, interval, timeframe, buckets, free_pct_min, free_pct_max, avail_mb_min, avail_mb_max, queried_at = now()
```

One row: the series is summarised in DQL (min and max across all buckets, and the bucket size in `interval`).

**Reveal:** If `free_pct_min` and `free_pct_max` are equal or nearly so, the free space has not moved across the
whole window: a floor, not a spike. State the percentage, the megabytes available, and how many buckets of what
size that covers (the window is as long as the problem has been open). The disk was already at that level when
the window opened, so the data shows that it stayed full, not how it filled. Say where the data stops: what wrote
to the disk is not in these metrics.

**Success signal:** User asks what filled the disk, or how long it has been this way, or asks to see the CPU.

**Deep link:**

```text
https://fxz0998d.dev.apps.dynatracelabs.com/ui/apps/dynatrace.infraops/explorer?entityId=HOST-A2BABAD05D401471&tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}
```

---

## Beat 3 — The CPU

**Objective:** User sees the CPU and I/O wait on the host over the same window, and what that does and does not
say about how the CPU relates to the disk.

**Evidence DQL:**

```dql
timeseries
    { cpu = avg(dt.host.cpu.usage), iowait = avg(dt.host.cpu.iowait) },
    by: { host.name },
    from: "{{DQL_FROM}}", to: "{{DQL_TO}}",
    filter: host.name == "frontend-high-cpu"
| fieldsAdd
    buckets    = arraySize(cpu),
    cpu_min    = round(arrayMin(cpu), decimals: 1),
    cpu_avg    = round(arrayAvg(cpu), decimals: 1),
    cpu_max    = round(arrayMax(cpu), decimals: 1),
    iowait_avg = round(arrayAvg(iowait), decimals: 4),
    iowait_max = round(arrayMax(iowait), decimals: 4)
| fields host.name, interval, timeframe, buckets, cpu_min, cpu_avg, cpu_max, iowait_avg, iowait_max, queried_at = now()
```

One row, summarised in DQL. Both metrics are in percent.

**Reveal:** Report what the two series show, from the row: CPU usage is saturated across the window (state the
min, average and max), and I/O wait is close to zero (state its average and max). Read it as it is: the data
does **not** show I/O wait as the way the full disk affects the CPU. What it shows is two conditions on the same
host, which Dynatrace Intelligence grouped into one problem with the disk as root cause and the CPU as affected.
Do not explain the CPU load by the disk, and do not offer a mechanism. What is using the CPU is not in these
metrics; the next step for that is the host's process view.

**Objection** — "high CPU could be a workload spike, not the disk": agree it is not shown to come from the
disk. It is not a spike either: the minimum across the window is also saturated. Beat 4 shows the one effect the
data does tie to the disk, in its own words.

**Success signal:** User asks what is using the CPU, or whether the disk causes it, or asks about the OneAgent
failure.

**Deep link:**

```text
https://fxz0998d.dev.apps.dynatracelabs.com/ui/apps/dynatrace.infraops/explorer?entityId=HOST-A2BABAD05D401471&tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}
```

---

## Beat 4 — The Platform Victim

**`peak_moment: true`**

**Objective:** User sees that Dynatrace's own OneAgent tried to auto-update and failed, with the failure message
naming the full disk — the monitoring platform itself is affected by the condition it reports.

**Evidence DQL:**

```dql
fetch events, from: "{{DQL_FROM}}", to: "{{DQL_TO}}"
| filter host.name == "frontend-high-cpu"
| filter matchesPhrase(event.name, "OSAgent auto update failure") or matchesPhrase(event.description, "NotEnoughDiskSpace")
| summarize
    failures   = count(),
    first_seen = min(timestamp),
    last_seen  = max(timestamp),
    by: { event.description }
| sort last_seen desc
| fieldsAdd queried_at = now()
```

One row per distinct failure message (each carries a from-version and a target version), newest first. No `limit`:
the totals below are sums over every row. The target version moves as newer releases appear, so the problem
`description` can quote an older target than the newest event: the newest row here is the one to state, and if it
differs from beat 1, say the target moved.

**Reveal:** OneAgent has tried to update repeatedly and each attempt failed with `NotEnoughDiskSpace`. The total
is the sum of `failures` over all rows, from the earliest `first_seen` to the latest `last_seen`; quote the
version strings of the newest row exactly as `event.description` has them, and say how many different target
versions there were (the row count). The failure message itself names the disk space as the reason; that is the one link
between the disk and another symptom that the data states in so many words. The agent keeps reporting, but its own
update has not gone through since `first_seen`.

**Success signal:** User asks what version is blocked, or what happens if OneAgent stays outdated, or asks how to
fix it.

**Staging:**

1. The finding alone on its own line, before any commentary:
   `OneAgent update blocked — NotEnoughDiskSpace ([from_version] → [to_version])`
2. Blank line.
3. What kind of finding it is: the monitoring agent's own update is failing for the reason the problem names as
   root cause. Not a separate incident — the same `/data` disk.
4. The three facts on the same host, from live values, as a list, not a chain of arrows (the data does not show the
   CPU following from the disk):

   ```text
   /data disk:      [free_pct]% free ([avail_mb] MB), flat since the window opened
   frontend-high-cpu CPU:  [cpu_avg]% average, I/O wait [iowait_avg]%
   OneAgent update: [total failures] failed attempts since [earliest first_seen], NotEnoughDiskSpace
   ```

5. State it plainly: one root cause in the problem record, and the update failure says in its own message that
   the disk is full. Whether freeing space also brings the CPU down is not something the data shows.

**Deep link:**

```text
https://fxz0998d.dev.apps.dynatracelabs.com/ui/apps/dynatrace.infraops/explorer?entityId=HOST-A2BABAD05D401471&tf={{TF_FROM_MS}}%3B{{TF_TO_MS}}
```

---

## Beat 5 — The Handoff

**Objective:** User has everything needed to act: the root cause, what the data shows on the host, the blocked
OneAgent version, and the one step the data supports.

**Evidence DQL:**

```dql
fetch dt.davis.problems, from: now()-48h, to: now()
| filter event.id == "{{PROBLEM_ID}}"
| sort timestamp desc
| limit 1
| fields
    display_id,
    started        = event.start,
    status         = event.status,
    root_cause     = root_cause.smartscape_entity[name],
    affected_count = arraySize(smartscape.affected_entities),
    description    = event.description,
    queried_at     = now()
```

`queried_at` is for the session close's elapsed time, not for the table.

**Reveal:** Summarise from the live data and the earlier beats: the root cause entity, the host, how long the
problem has been open (the resolver's `duration_days` and `duration_hours`; still open if the status says so), `affected_count`, and
the blocked OneAgent version from beat 4. The data supports one action: free space on `/data`, which is what the
update failure's message asks for. Say plainly that the data does not show whether that also resolves the CPU
saturation. The record has no owner, so hand off by host name and host group; do not name a team.

**Success signal:** User confirms they know what to do, or asks for the handoff block.

**Deep link:**

```text
https://fxz0998d.dev.apps.dynatracelabs.com/ui/apps/dynatrace.davis.problems/problem/{{PROBLEM_ID}}?from={{TF_FROM_MS}}&to={{TF_TO_MS}}
```
