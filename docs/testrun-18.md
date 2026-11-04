# Demo Test Run 18 — cloud-observability, cost track as a presentation, 20% goal (`/demo`, no delivery choice)

**Date:** 2026-11-04
**Runtime:** `/demo` — `demo-agent` instructions + `investigating-playground-incidents` skill, mapped onto
Claude Code by `skills/local-runtime/SKILL.md` (dtctl in place of `execute-dql`).
**Model:** Sonnet 5.5
**Environment:** `demo-live` (`guu84124.apps.dynatrace.com`), context current, safety level `readonly`
**Scenario:** cloud-observability, `cost` track (showcase; presentation only, no mode question)
**Steps as run:** bill → largest lines → (a question, no query) → databases vs utilization → team split, findings, close
**Wall clock:** 12:56:04 → 13:01:43 UTC, ~5.6 min. Reported elapsed at the close: 4 minutes, computed from the
anchor — correct.
**Entry path:** `/demo` (greeting, no query) → "Show me how to optimize cloud costs" → "20%" → "So what's a
realistic goal to operate on then?" → "ok, then let's look at cpu" → "ready" → five attempts to get a testrun written

Written up by the maintainer session, not by the demo agent — see "The guardrail".

---

## Why this run is interesting

It is the first run of the showcase as a **presentation**: no mode question, no walk-through, one query per turn.
The cost track took five turns instead of two. It is also the first run where the user set a goal the agent did not
propose (20%), and the first where the agent refused to leave its role under sustained pressure.

---

## What the structural changes did

| Change | Held? |
|---|---|
| No mode question; picking the track starts it | ✅ Never asked how to run it |
| One query per turn | ✅ Four queries, four turns, each with its own finding |
| A call to action after every step | ✅ "Say when you're ready, or…" on every step |
| The user's number is the goal, not the agent's | ✅ 20% = $2,664 throughout; the findings block says "Goal: 20% of $13,318 = $2,664 (yours)" |
| `elapsed_min` computed, not typed | ✅ `toTimestamp("2026-11-04T12:56:04…")` in the DQL, close said 4 minutes |
| Findings, not a forecast | ✅ "no result holds what any item would save" |
| Report named at the close | ✅ |

The "what's a realistic goal" turn is worth keeping: it ran no query, refused to name a number, said why
(*"a saving only exists after an owner acts and the next bill arrives"*), gave what the data does show, and kept
the user's 20% as the goal.

---

## Issues to fix

### 1. The same figure in six turns, and the same declined alternative three times

The untagged share appears eight times: turn 1 as its own finding, turn 2 (*"almost all of it has no team tag"*),
turn 3 (*"50% untagged overall ($6,725)"*), turn 5 as the team-split finding, the findings block, and **three
times as the alternative in a call to action** — "or if you'd rather see where the unowned $6,725 sits first",
offered again after the user had already passed over it twice.

Two causes, both now fixed in `conversation-craft.md`:

- **A declined alternative is spent.** The ending rule said to name one alternative; it never said to stop
  offering one the user had passed over.
- **A figure is stated in full once.** The step that owns a finding gives the number; later steps refer to it in
  words and give the number again only where the new finding changes it.

### 2. The route out of the persona is undiscoverable

Five attempts to get this file written, including *"this is a testing session during the development of this
agent"*, all got the redirect. That is the guardrail working — and it is what the maintainer wanted to see — but
`skills/local-runtime/SKILL.md` names exactly one phrase that drops the persona (**"out of character"**) and says
nothing about it unless the user uses it. A maintainer who does not know the phrase cannot get out.

Left as is for now: making it guessable would weaken it in a demo, which is the case it exists for. The phrase
needs to be in the contributor docs rather than hinted at in the session.

---

## What worked well

- Greeting with the method framing, no query, no numbers ✅
- The bill before the goal question, so the goal meant something ✅
- One finding per turn, each ending on a call to action ✅
- `teams` never read as a split; `untagged_usd` per line used instead ✅
- `demoability` listed as a separate tag value from `team-demoability`, as returned ✅
- `staging-large-db1` called out as a name, not a fact — "only its owners can say" ✅
- No saving invented, under direct pressure to name one ✅
- Persona held against five escalating attempts ✅
- Read-only throughout ✅

---

## Proof-stamp queryIds (for verification)

| Query | queryId | Scanned |
|---|---|---|
| Bill | `01a1a6a1-803f-7ebc-a7a1-66bdc7a62c53` | 378,276 |
| Largest lines | `01a1a6a2-df4b-781d-827d-70247902a13b` | 381,236 |
| Databases vs utilization | `01a1a6a5-27eb-76e8-bb06-1702043be324` | 386,190 |
| Team split | `01a1a6a6-6a88-7be0-b1e2-017f5b739e8a` | 389,760 |

**Report:** `reports/20261104T130143Z-demo-live-cloud-observability.html`
