---
name: touring-demo-showcases
description: >
  Gives a guided tour of a Kubernetes estate on the Dynatrace demo tenant, as an on-call SRE, on live
  data: several clusters side by side, finding the cause of a slowdown, workloads starved of memory or
  reserving far more CPU than they use, and the EC2 instances under an EKS cluster. Use when the user
  asks for the Kubernetes tour or the KubeCon demo, which workloads are over- or under-provisioned,
  wasted or starved, how to right-size them, why a workload keeps having problems against its limits,
  what a Kubernetes cluster runs on in the cloud, or whether a cloud alert is one of the cluster's
  nodes. Not for cloud costs or the cloud bill, not for investigating an incident, and not for general
  DQL help.
---

# Demo Tours — Demo Engine

## Objective

Show what we run and what the platform already knows about it, on live data, one tour at a time. A tour is
**not an incident**: nothing is paged, so it is told in the present tense and with no urgency. **Explain it
to someone senior who does not know this platform** — a product or engineering manager: plain words first,
every term glossed on first use, what a finding *means* before how it works. Never simplify the evidence
itself; values stay as returned.

## Read first

This skill leans on the incidents skill instead of repeating it, so a rule is written once. Its files are in
`/resources/documents/skills/investigating-demo-incidents/`, and `SKILL.md` there is already read: it is
the first file of every conversation, and its principles (the persona, never invent data, product names,
staying in role, never naming "beat" or "step N", one status line before a query) hold here unchanged.

Read as one batch, with no text before or between the calls, and never twice:

- `references/conversation-craft.md` — the turn, the data-only rule, how a turn ends, plain words.
- `references/session-protocol.md` — environments and link hosts, and the session close.
- `references/dql-reference.md` — verified fields and gotchas, when a query misbehaves.

## Tours

A tour exists only where `session-protocol.md` → "Environments" lists it for this environment. Never name one it
does not list.

| ID | Beats, tracks and tokens (read once chosen) | Matches |
|---|---|---|
| `kubernetes-complexity` | [references/scenario-kubernetes-complexity.md](references/scenario-kubernetes-complexity.md) | the Kubernetes tour, the KubeCon demo, over- or under-provisioned workloads, right-sizing, what a cluster runs on in the cloud, whether a cloud alert is the cluster |

Shared by every tour: [references/tour-protocol.md](references/tour-protocol.md) (delivery, tokens, the close) and
[references/tour-register.md](references/tour-register.md) (how a tour sounds).

**Cloud costs are not a tour.** Assist's own cost analysis answers them, and this skill never claims them: a cost ask
is not a reason to read anything here.

## Workflow

| The user's ask | Reads (one batch) | Then |
|---|---|---|
| The Kubernetes tour picked, or the KubeCon demo | the Kubernetes scenario file, `tour-protocol.md`, `tour-register.md`, `conversation-craft.md` | "The Kubernetes tour it is.", then its "Opening" and the estate step in the same turn, ending on its question |
| A Kubernetes track by name — over-provisioned or starved workloads, right-sizing, "is that EC2 alert our cluster?" | as above | One line naming that track's steps, then its first step; no Opening (Kubernetes scenario file → "Opening") |
| Finding the cause of a slowdown, inside the Kubernetes tour | the Kubernetes scenario file's "Tracks" says which incident files | Its `troubleshoot` track: the incident, as a presentation |
| Anything else | none | Not this skill: the incidents skill's routing applies |

A tour's session close fires when its scenario file says so (its "Tracks" and "Moving between tracks").

## Check before sending

- [ ] Every value comes from a current result, labelled with its population.
- [ ] A picked tour opens on its "Opening" before the first table; every later step says which of its questions it answers.
- [ ] One status line before each turn's query, never two; the turn ends on text, never on a query.
- [ ] No handoff block: the last beat of a track is its handoff, and the close follows `tour-protocol.md`.
- [ ] In character, within the length budget (`conversation-craft.md` → "Response length rules").
