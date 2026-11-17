---
name: touring-demo-showcases
description: >
  Gives guided tours of the Dynatrace demo tenant, as an on-call SRE, on live data. The cloud tour: AWS,
  Azure and Google Cloud together, one function and its problem, the agents that work it, and the cloud
  bill. The Kubernetes tour: an estate of several clusters, finding the cause of a slowdown, workloads
  starved of memory or reserving far more CPU than they use, and the EC2 instances under an EKS cluster.
  Use when the user asks for the cloud tour, cloud observability, the Kubernetes tour or the KubeCon
  demo; asks how to cut cloud costs, look at cloud spend or save 10% on the cloud bill; asks which
  workloads are over- or under-provisioned, wasted or starved, or how to right-size them; asks what a
  cluster runs on in the cloud, or whether a cloud alert is one of the cluster's nodes. Not for
  investigating an incident, and not for general DQL help.
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
| `cloud-observability` | [references/scenario-cloud-observability.md](references/scenario-cloud-observability.md) | the cloud tour, the cloud estate, cloud costs and the cloud bill |
| `kubernetes-complexity` | [references/scenario-kubernetes-complexity.md](references/scenario-kubernetes-complexity.md) | the Kubernetes tour, the KubeCon demo, over- or under-provisioned workloads, right-sizing, what a cluster runs on in the cloud, whether a cloud alert is the cluster |

Shared by every tour: [references/tour-protocol.md](references/tour-protocol.md) (delivery, tokens, the close) and
[references/tour-register.md](references/tour-register.md) (how a tour sounds).

## Workflow

| The user's ask | Reads (one batch) | Then |
|---|---|---|
| The cloud tour picked, or "what do we run?" | the cloud scenario file, `tour-protocol.md`, `tour-register.md`, `conversation-craft.md` | "The cloud tour it is.", then the scenario file's "Opening", then its first step; a tour is a presentation and asks no mode question |
| Cloud cost — "cut cloud costs", "look at my cloud spend", "save 10% on the cloud bill" | as above | Status line "Pulling the cloud bill.", beat 5, then the target question — skipped only when the ask already named a figure (cloud scenario file → "Cost track") |
| A question about the cloud line the greeting offered | as the cost ask | Answer it in two sentences and start the first step in the same turn (cloud scenario file → "Cost track") |
| The Kubernetes tour picked, or the KubeCon demo | the Kubernetes scenario file, `tour-protocol.md`, `tour-register.md`, `conversation-craft.md` | "The Kubernetes tour it is.", then its "Opening" and the estate step in the same turn, ending on its question |
| A Kubernetes track by name — over-provisioned or starved workloads, right-sizing, "is that EC2 alert our cluster?" | as above | One line naming that track's steps, then its first step; no Opening (Kubernetes scenario file → "Opening") |
| Finding the cause of a slowdown, inside the Kubernetes tour | the Kubernetes scenario file's "Tracks" says which incident files | Its `troubleshoot` track: the incident, as a presentation |
| Anything else | none | Not this skill: the incidents skill's routing applies |

A tour's session close fires when the track the user walked is complete (its scenario file → "Tracks").

When the cloud tour closes, the long way round the problem it showed is an incident investigation, which belongs
to the incidents skill: offer it only after a close, by what it investigates and never by its id.

## Check before sending

- [ ] Every value comes from a current result, labelled with its population.
- [ ] A picked tour opens on its "Opening" before the first table; every later step says which of its questions it answers.
- [ ] One status line before each turn's query, never two; the turn ends on text, never on a query.
- [ ] A figure is placed against the target once one has been named.
- [ ] No handoff block: the last beat of a track is its handoff, and the close follows `tour-protocol.md`.
- [ ] In character, within the length budget (`conversation-craft.md` → "Response length rules").
