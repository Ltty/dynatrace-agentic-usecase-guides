# Narrative review

Verdicts for each scenario against the selected set in `AUTHORING.md` → "The narrative standard".
A verdict is not a read-through: it names what the file satisfies, what it does not, and the line
that fails.

Reviewed 2026-11-04 against the fifteen selected principles. Two of them are owned centrally and
the scenarios inherit them rather than restating them:

- **Anchoring** is a global rule (`conversation-craft.md` → "Act: all queries first, then
  narration"). Scenarios are judged on whether their Reveals comply.
- **Goal Gradient** is scoped to showcases (`conversation-craft.md` → "Showcase register"). An
  incident with no target legitimately has none — except where the scenario does have a threshold,
  which is the disk case below.

Each scenario file also opens with "Reveals describe the *shape* of a finding, never its values",
which is why no file states a figure. That is deliberate and is not counted against Anchoring.

---

## Summary

| Principle | `payment-failure` | `broken-images` | `disk-cpu-cascade` |
|---|---|---|---|
| Anchoring | pass | pass (fixed: beat 2 led on a row count) | pass, strongest |
| Goal Gradient | n/a — no target exists | partial: baseline named once, never carried forward | **was a miss — fixed** |
| Serial Position | pass for beats; `commit` mid-table | pass for beats; null-owner caveat buried in a cell | **Contents fixed**; peak deliberately not last |
| Storytelling | pass; **beat 5 stands alone** | pass; **beat 5 stands alone** | pass, strongest; beat 3 disconnected by instruction |
| Curiosity Gap | pass | pass, strongest | pass — gaps name limits, not next beats |
| Progressive Disclosure | pass | front-loads impact dimensions never reused | **was self-contradictory — fixed** |
| Loss Aversion | **miss — see below** | n/a, no figure | n/a, no figure; risk framing used at the peak |
| Curse of Knowledge | fixed (5xx) | fixed (baseline) | fixed (I/O wait) |

---

## Fixed in this pass

- **`disk-cpu-cascade`: "I/O wait" was never glossed**, and the beat's whole argument depends on the
  reader knowing that high I/O wait is the mechanism a full disk would normally show. The beat asked
  the user to conclude something from the *absence* of a signal it never explained. Now glossed on
  first use.
- **`disk-cpu-cascade`: the file contradicted itself.** Its own preamble says percentages rotate and
  must be read live; the Handoff table hard-coded "lower than 3%" and "above 95%". The table now
  names the field instead of the values.
- **`disk-cpu-cascade`: thresholds existed and nothing measured against them.** Beats 2 and 3 stated
  the disk percentage and the CPU figures with nothing to compare them to, while beat 1 had already
  quoted the thresholds that triggered the problem. Both now state the figure against the threshold.
  This is the one place in the three incident scenarios where a gradient was available and unused.
- **`disk-cpu-cascade`: the peak was unmarked in Contents**, while both sibling files mark theirs.
- **`broken-images`: "auto-detected baseline"** was Dynatrace vocabulary asserted in beat 1's opening
  sentence, where the user has least footing, and the beat's claim rests on accepting it. Reworded to
  say what the baseline is.
- **`broken-images`: beat 2 opened on a row count** ("Typically two rows"), the exact anti-pattern
  the Anchoring rule names. It now leads with the deploy gap.
- **`payment-failure`: 5xx unglossed** in the beat 5 Reveal, in a file that glosses it correctly in
  its own Handoff table.

## Open, and why they are not one-line fixes

- **Beat 5 stands alone in both `payment-failure` and `broken-images` — and it has to.** Checked on
  the Playground: `user.sessions` carries no service field (57 fields, the only entity is the RUM
  application) and spans carry no session id (95 fields, none session-linking). There is no join, so
  the beat cannot be scoped to the scenario's service by any query. **Resolved by saying so**: both
  beats now state that these are sessions that hit an error in the window, that the data does not
  attribute them to this service, and that the replay is what closes the gap. The disconnection was
  always real; what was wrong was implying otherwise.
- **`payment-failure` defines `avg_order_value_usd` and no beat ever uses it.** The figure does reach
  the user — the survey hook and the handoff block both carry `revenue_usd` — so it is not unused,
  but nothing between the opening and the handoff refers to the cost again. The Loss Aversion verdict
  is "miss within the beats", not "defined and discarded".
- **`broken-images` front-loads three impact dimensions in beat 1** (frontend, ingress, synthetic
  check) that no later beat returns to, and beat 5 then explicitly excludes synthetic. Detail arrives
  early, is never used, and is filtered out.
- **`disk-cpu-cascade`'s peak is not the last beat.** Sanctioned — its last beat is the handoff
  summary — but the consequence stands: the recency slot goes to a recap rather than the high point.

## Deliberate deviations, recorded so they are not "fixed" later

- `disk-cpu-cascade` beat 3 is **forbidden** from connecting to beat 2: the data does not show I/O
  wait as the mechanism, and the refusal to offer one is the beat's content.
- `broken-images` never says "failing" or "erroring" — it is a slowdown, which is why the file has no
  error framing to hang Loss Aversion on.
- All three state the shape of a finding rather than its values, so figures in the files would be
  stale by construction.
