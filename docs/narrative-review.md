# Narrative review

Verdicts for each scenario against the selected set in `AUTHORING.md` → "The narrative standard".
A verdict is not a read-through: it names what the file satisfies, what it does not, and the line
that fails.

**Feedforward was the one selected principle no incident had ever satisfied.** It was written into
`conversation-craft.md` inside the *Showcase register*, so only the cloud tour stated its approach before
querying; every incident went straight into beat 1 with the user not knowing the shape. Fixed 2026-11-05
for all five by promoting the rule to the general beat loop and giving each scenario an `approach` row.
Recorded as one row rather than five sections because it was one omission.

The openings had the matching problem and it is the same principle pair: they named the component that
broke ("the image provider was erroring") rather than what a person met ("product images aren't loading
in the shop"). That is Curse of Knowledge at the one turn where the user has least footing, and it is now
the hooks' first clause.

Reviewed 2026-11-04 against the fifteen selected principles. `lambda-iam-denied` was added later the
same day and reviewed on arrival; its verdict is the last column and its own section below. Two of them are owned centrally and
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

| Principle | `payment-failure` | `broken-images` | `disk-cpu-cascade` | `lambda-iam-denied` | `k8s-cpu-throttling` |
|---|---|---|---|---|---|
| Feedforward | **was a miss — fixed** | **was a miss — fixed** | **was a miss — fixed** | **was a miss — fixed** | **was a miss — fixed** |
| Anchoring | pass | pass (fixed: beat 2 led on a row count) | pass, strongest | pass for beats 1–4; beat 5 leads on a note count, sanctioned below | pass — beat 3's staging leads on usage against the ceiling, not a series count |
| Goal Gradient | n/a — no target exists | partial: baseline named once, never carried forward | **was a miss — fixed** | n/a — no target exists | n/a — no target; the limit is a threshold, and beat 3 places usage against it |
| Serial Position | pass for beats; `commit` mid-table | pass for beats; null-owner caveat buried in a cell | **Contents fixed**; peak deliberately not last | **was a miss — fixed**: beat 1 returned nine fields with the owner mid-row | pass; beat 1's reveal names three values and leaves the row off screen |
| Storytelling | pass; **beat 5 stands alone** | pass; **beat 5 stands alone** | pass, strongest; beat 3 disconnected by instruction | **was a gap — fixed**: the chain named no cause for the change it was built on | pass, strongest: page -> which service -> why -> what changed -> what to set |
| Curiosity Gap | pass | pass, strongest | pass — gaps name limits, not next beats | pass — beats 2 and 3 both end on a gap the next beat opens | pass — beats 2 and 3 each end on the question the next answers |
| Progressive Disclosure | pass | front-loads impact dimensions never reused | **was self-contradictory — fixed** | pass — five beats, one query each | pass — five beats, one query each |
| Loss Aversion | **miss — see below** | n/a, no figure | n/a, no figure; risk framing used at the peak | n/a, no figure by design | n/a, no figure; the cost framing is the tuning that backfired |
| Curse of Knowledge | fixed (5xx) | fixed (baseline) | fixed (I/O wait) | **was the worst miss — fixed** (role, ARN, inline policy, `/*`) | **the main risk — addressed**: throttling, limits vs requests, slices |

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

---

## `lambda-iam-denied`, reviewed on arrival 2026-11-04

### Fixed before it shipped

- **Curse of Knowledge was the worst of it.** The scenario is built on AWS identity vocabulary and
  the first draft assumed all of it: *execution role*, *ARN*, *inline policy* and the trailing `/*`
  all appeared unglossed, in the two beats the whole argument rests on. A reader who does not already
  know what an ARN is cannot judge whether the one in the policy matches the one in the exception —
  which is the entire finding of beat 4. All four are now glossed in plain words on first use, and
  beat 3 says explicitly to assume none of it is known.
- **Beat 1 returned nine fields and said to state them.** Serial Position and Chunking both fail on a
  nine-row table, and `owning_team` — the only value in it that is a person — sat in the middle. The
  Reveal now names the three values that carry the beat, says not to put the whole row on screen, and
  moves the owner to last.

- **The argument had no cause in it.** Beats 2 and 3 established that a permission changed at a
  specific minute, and the scenario then went straight to the hand-off without naming what changed
  it — because the first pass concluded no deploy signal existed in Dynatrace. It does: two
  `CUSTOM_DEPLOYMENT` events, one landing about a minute before the first denial. Storytelling asks
  that each reveal connect to the one before, and the one connection the whole scenario needed was
  missing. Beat 5 now names the commit, and beat 4 no longer claims the platform holds no history of
  the change. Found by an eval run, not by the review — the review read the file against itself and
  the file was internally consistent and wrong.

### Deliberate deviations, recorded so they are not "fixed" later

- **The peak is beat 3, not beat 4 or 5.** Beat 4 was drafted on the assumption that it would show the
  broken grant during a live window. It never does — 70 one-minute polls across the 2026-11-04
  incident returned the correct policy every time, because Smartscape is a configuration snapshot
  and the grant is wrong for 39 minutes. Had the peak been placed there it would have landed on
  nothing, on every run. Beat 5's commit is the more dramatic reveal, but a commit is a correlation
  the user is told to confirm in the repository; the exception is the only beat that states the
  cause outright.
- **Beat 5's first number is a count of notes, not an impact figure.** Anchoring says the first number
  in a turn is the impact. Beat 5's subject *is* the notes — the impact was established in beats 1 and
  2 and is not restated. Said at all, a second impact figure here would be the repetition testrun 18
  objected to in the cost track.
- **Peak-End puts the recency slot on the handoff, not the peak** — the same shape as
  `disk-cpu-cascade`, and here the last beat is a real payoff (the hand-off closing) rather than a
  recap.
- **No Loss Aversion framing and no cost figure.** The scenario has no `avg_order_value_usd` and the
  affected users are the problem record's. Inventing exposure from them would be the kind of number
  the data does not hold.

### Open

- **Beat 5 is thinner than the story it is modelled on**, and will stay that way while the AWS DevOps
  Agent writes notes with no readable summary (since 2026-10-27, see
  `docs/scenarios/lambda-iam-denied.md`). The beat is honest about it rather than silent, but a
  reader meeting the scenario for the first time meets the degraded path.

---

## `k8s-cpu-throttling`, reviewed on arrival 2026-11-05

The lesson from `lambda-iam-denied` was applied before writing rather than after: the review there
found that the scenario assumed its own vocabulary, so this one was written with the glosses in place.

### What the standard changed while writing

- **Curse of Knowledge is the whole difficulty of this scenario.** Its argument cannot be followed
  without knowing that a CPU *limit* is enforced in short slices, that throttling means being stopped
  mid-work rather than being short of CPU, and that a *request* is a different field that fails a
  different way. All three are glossed where they first appear, and beat 3's staging step 3 exists
  only to say "not a shortage — being cut off" in plain words. The scenario would otherwise read as
  three numbers with no meaning.
- **Anchoring put the right number first.** Beat 3 returns four series, and the tempting opening is
  how many or how high the throttling went. The staging leads instead with usage against the ceiling,
  because that pair is the finding and throttling alone reads as "it needed more CPU", which is the
  opposite of what happened.
- **Framing, in its literal form.** The beat states the absolute (millicores used) and the share it
  implies (well under the ceiling) because the share is what carries the meaning, and the absolute
  alone invites the wrong fix.

### Deliberate deviations, recorded so they are not "fixed" later

- **Beat 2 deliberately proves a negative.** Its point is that the *other* services in the namespace
  are normal, which is what rules out the node and the cluster. A reader skimming will see a table of
  services and wonder why the slow one is not simply shown alone; the neighbours are the evidence.
- **The peak is beat 3, not beat 4.** Naming the edited field is the more concrete reveal, but it only
  means anything once the mechanism is established, and beat 4 degrades to nothing on an off-cycle
  occurrence. The lesson from the sibling scenario is not to place the peak on a beat that sometimes
  returns no rows.
- **Beat 5 compares the agent's conclusion to ours rather than just quoting it.** That is not padding:
  an agent that agrees with evidence the user has already seen is checkable, which is the only reason
  to trust the part they cannot check.

### Open

- **The root cause entity rotates between three entities**, one of them an application. Beat 1 states
  it as returned, so the scenario reads correctly either way, but the user sees a different root cause
  named on different days and nothing explains why. Explaining it would mean telling them how Dynatrace
  picks, which is not in any returned field.
- **Off-cycle occurrences have no spec change**, so beat 4 can return nothing even though `pref` makes
  the resolver avoid them. The beat says so honestly; the arc is weaker on those runs.

