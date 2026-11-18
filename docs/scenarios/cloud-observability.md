# cloud-observability: retired 2026-11-18

Maintainer notes. The agent never reads this file.

The cloud tour (a showcase: the Golden Demo *Modern Cloud Observability* arc with the *Cut Cloud Costs Safely* Assist
conversation folded in) is removed from the skill.

## Why

- **It overrode the FinOps skill.** The tour's description claimed "cut cloud costs, look at cloud spend, save 10% on the
  cloud bill", and the demo-agent's instructions routed every cost ask to it, so Assist ran our conversational script
  instead of `dt-biz-cloud-costs` (Dynatrace-owned, built by the FinOps team). A colleague on the FinOps team reported it while
  documenting the cloud-cost demo: the stock skill's own answer is the stronger demo, and it is not a tour.
- **Its cost track duplicated that skill.** The bill, the untagged share, utilisation next to cost and the ranked action
  list are what `dt-biz-cloud-costs` covers (cost overview, attribution, tag hygiene, AWS compute optimisation).
- **Nothing was worth keeping without the cost job.** Beats 3 and 4 repeat the `lambda-iam-denied` incident, whose beat 6
  already walks the AWS DevOps Agent; the Kubernetes tour shows EKS, AKS and GKE side by side, the node to EC2 link and
  the Kubernetes troubleshooting agent. The tour's argument was the 10% job, and without it there was no spine.

## What replaced it

- Cloud costs are **not** part of this demo. `@demo-agent` redirects a cost ask in character to Assist's own cost
  analysis, with the CTO prompt as the question to ask. On demo-live there is no agent runtime, so a cost question in
  plain Assist reaches `dt-biz-cloud-costs` directly once our skills stop claiming it.
- Don't add a skill or a description that claims cost triggers. If a cloud-cost walk-through is wanted again, wrap the
  FinOps skill's output rather than re-deriving it, and keep the trigger words out of our descriptions.
- The incident scenarios are untouched, including `lambda-iam-denied` (the AWS DevOps Agent problem).

## Restoring it

The scenario file, its probe, the 10% premise and its evals are in git history. Find the deleting commit with
`git log --diff-filter=D -- dynatrace-intelligence/skills/touring-demo-showcases/references/scenario-cloud-observability.md`
and restore from its parent. The deployed documents were removed from demo-live in the same change.
