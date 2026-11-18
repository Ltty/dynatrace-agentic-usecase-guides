# Assist prompt analysis: what people ask, and when "Try a live demo" should appear

Maintainer notes. The agent never reads this file. **Counts only: no prompt, email or user id is recorded here, and none may be.**

The offer skill (`offering-live-demos`) was written with guessed triggers. This is the method for replacing the guesses with
data, and what the first pass found. The tool is `tools/assist_prompts.py`; its tests are `tools/tests/test_assist_prompts.py`.

## Where the prompts are

`dt.system.events`, `event.kind == "GENAI_EVENT"`, `event.type == "GenAI Skill Invocation"`: one event per Assist call, with
`user_input`, `response`, `conversation_id`, `user_id` and the user's email. `client.application_context` is **not** the open app
(it is mostly the Assist app itself). The open app is inside the prompt: an interactive prompt is a template,
`<QUESTION>…</QUESTION>` then `<OPEN-APP>… currently viewing Name (app.id) and it is installed …</OPEN-APP>` (classic apps carry
the bare id). That block is how the real Assist hands our skill its context.

| Tenant | Readable? |
|---|---|
| `demo-live` (Dynatrace employees and partners) | Yes: ~11,000 events and 3,000 conversations in 30 days |
| `playground` (customers and people who are not customers) | **Yes since 2026-11-18** (checked again that day: all 13 event kinds, ~37,800 GenAI events in 30 days). Before that my role saw 2 of 13 kinds and no audit, query-execution or workflow events although queries ran on it: hidden from the role, not missing. Run only after the data-protection sign-off was confirmed, and only as the count-only report. |

## Privacy rules

The prompts belong to other people and the repository is public.

1. Outside the internal tenant everything is aggregated **inside the tenant**: only counts leave it, and a row is shown only when at
   least **10 distinct users** produced it (`report` refuses a lower floor for any tenant but `demo-live`).
2. `fetch` (scrubbed rows to the git-ignored `analysis/` folder, user ids hashed with a per-run salt, no email) works on `demo-live`
   only and refuses every other tenant. Nothing from `analysis/` is committed.
3. No model sees an individual customer's prompt. For a tenant with outside users the most that may reach a model is k-anonymous wording.
4. Analysing customer and prospect prompts on playground needs a data-protection sign-off from that tenant's owner. It was confirmed
   on 2026-11-18, and only the count-only report (floor of 10 users) has been run there.

## How to run it

```bash
python tools/assist_prompts.py report --tenant demo-live --days 30            # all queries, counts only, k = 10
python tools/assist_prompts.py report --tenant demo-live --k 1 --query offer_rate   # internal pilot only
python tools/assist_prompts.py pack [--check]                                 # the same queries as tools/queries/assist-prompts/*.dql
```

The `.dql` files run in a Notebook on any tenant, so an admin who can read the events can run them and send back only the result
tables; that is the route for playground. Queries: `profile`, `open_app`, `intent_totals`, `intent_by_app`, `offer_rate`,
`offer_leaks`, `terms` (words used by many users), `phrases` (wording used by many users).

## What the first pass found (demo-live, 30 days, 2026-10-19 to 2026-11-18)

**Volume.** 10,990 events; 6,217 interactive prompts (the template) from 725 users in 3,039 conversations. The rest is automation
(workflow actions) and development traffic.

**Where people are (open app, interactive prompts):** Home (`dynatrace.launcher`) 1,630 (26%); no app (the full-page Assist) 1,022 (16%);
Problems 752; Dashboards 565; Notebooks 391; classic Dashboards 246; then Logs, Infrastructure & Operations, Settings, Kubernetes
(87 prompts from 18 users) and others under 120 each.

**What they ask (seed rules; first match wins; 6,216 prompts):**

| Group | Share | Note |
|---|---|---|
| Not matched by any rule | 51% | needs the clustering step |
| Canned prompt behind an app button | 19% | 1,162 prompts, 366 users; **one** preset ("explain the problem, why it happened and how to fix it", in Problems) is 13% of everything |
| DQL and query building | 6.5% | |
| Logs | 5% | |
| Docs and how-to | 5% | |
| Kubernetes | 3.5% | plus 0.2% sizing (over-provisioned, limits) |
| Problem investigation | 2.8% | |
| Dashboards and notebooks authoring | 2.4% | |
| Cloud cost | 2.4% | |
| Security | 2.0% | |
| Asks for a demo | 0.7% | 45 prompts, 28 users |
| **Orientation ("what can I do here")** | **0.3%** | 20 prompts, 5 users, mostly our own tests |

**Exact wording is almost never shared.** Only 5 phrases were used by 10 or more users, and all are app buttons or "continue". So
typed questions cannot be grouped by phrase; the vocabulary report (words used by 10+ users) is the aggregate-safe way to find
groups: DQL, query, filter, fetch; user, session, journey (app-generated analysis prompts); problem, root, cause; logs; dashboard;
host, oneagent; and Kubernetes at only 47 users.

**Home is not asking about itself.** Of 1,630 Home prompts, 61% are unmatched typed questions, then DQL (120), docs (114), logs
(84), problem investigation (73), Kubernetes (58), authoring (54), cloud cost (52), security (44). Only 11 are orientation or a
demo request. The 1,022 no-app prompts are 71% canned.

**Our offer today (baseline).** 11 offers in 30 days. Of 65 orientation or demo-request prompts, 10 (15%) got an offer: Kubernetes
7 of 20 (two users, our testing), Home 2 of 11, Problems 0 of 3 (it is in the table), Notebooks 0 of 7 and Dashboards 0 of 3 (not in
the table). **4 of the 11 offers began with environment or scenario text** (the leak fixed on 2026-11-18; re-measure).

## Playground (30 days to 2026-11-18, count-only report, every row at least 10 distinct users)

Same template and the same parser. **9,926 interactive prompts from 1,561 users in 3,299 conversations** (demo-live: 6,217 / 725).
Our offer is not deployed there, so offers shown are 0 and the 13 orientation prompts are the unserved baseline.

**Where people are.** Home (`dynatrace.launcher`) **5,157 prompts (52%)** from 512 users; no app 1,155; Problems 654; Dashboards 600;
Notebooks 530; Logs 201; Infrastructure & Operations 139; Services 138; Smartscape 136; Distributed Tracing 119; Kubernetes 97
(44 users); Clouds 65.

**What they ask (seed rules, 9,922 prompts):**

| Group | Share | Note |
|---|---|---|
| Not matched by any rule | 52% | |
| DQL and query building | 14.8% | the largest typed topic; no demo of ours addresses it |
| Canned prompt behind an app button | 11% | 1,094 prompts; the Problems "explain the problem" preset is 736 prompts from 406 users |
| Logs | 5.2% | |
| Kubernetes | 4.5% | plus 0.2% sizing: **462 prompts, ~126 users** |
| Docs and how-to | 4.5% | |
| Dashboards and notebooks authoring | 2.6% | |
| Problem investigation | 2.2% | |
| Security | 1.2% | |
| Cloud cost | 1.1% | must not trigger |
| Asks for a demo | 0.2% | 16 prompts, 15 users |
| **Orientation** | **0.1%** | 13 prompts, 12 users, all on Home |

**Home on playground (5,157):** 55% unmatched typed questions, **21% DQL (1,078 prompts, 121 users)**, Kubernetes 318 (57 users), logs
283, docs 207, authoring 114, security 85, problem investigation 78, cloud cost 74. Orientation and demo requests together are
well under 1%.

**Shared wording.** Besides the app buttons, several questions were used by 12 to 23 different users each (a response-time question
about a demo service, "how does Dynatrace determine the root cause of a problem", "observability score", "slowest database query
executions"), plus "yes" and "continue". They look like suggested or guided prompts that many people clicked, not free typing, which is
worth confirming with the Assist team before reading them as demand.

**Vocabulary (10+ users):** dynatrace, DQL, query, filter, fetch, fields, summarize (people pasting or writing DQL), service, logs,
dashboard, problem, host, error. Kubernetes terms are far down.

**What exists to offer on playground.** Only the incidents: `payment-failure`, `broken-images`, `lambda-iam-denied`,
`k8s-cpu-throttling`. The Kubernetes tour is demo-live only, so a Kubernetes trigger there offers the throttling incident.

## Which prompts could and should get "do you want a demo?" (every interactive prompt, scored)

The question is asked of each prompt, not of a topic. **Could**: a demo's subject matches what the person asks. **Should**: could,
and nothing blocks it. Blocks: an app button (nobody typed it), a one-word follow-up ("yes", "continue"), pasted DQL (they are
mid-task), cloud cost (Assist's own cost skill answers it). Orientation and demo requests are offered in any app. The rules are in
`tools/assist_prompts.py` (`DEMO_RULES`, `demo_steps`), the verdicts in the queries `demo_fit` and `demo_fit_by_app`.

**Rule verdicts, all interactive prompts, 30 days:**

| | demo-live (6,216) | playground (9,926) |
|---|---|---|
| Would get an offer (could and should) | 355 (5.7%) | 313 (3.2%) |
| Fits a demo but blocked | 66 (1.1%) | 93 (0.9%), mostly pasted DQL |
| No demo fit | 5,832 (94%), of which 1,134 are app buttons | ~9,465 (95%) |

**Calibration (demo-live only; playground prompts were never read by a model).** 261 unique prompts, drawn by rule verdict and
shuffled, labelled by an independent model judge that did not see the rule labels (one judge, one pass, so a measured opinion, not user
behaviour). Weighted back to the 4,491 unique typed prompts:

- The judge says **about 756 could use a demo (17%) and about 511 should be offered one (11%)**: more than the rules' 310.
- **Precision of the rules is 41%** (52% for "could"); **recall is 25%**. They are noisy on the wrong subjects and blind to the right ones.
- By rule: incident-generic 64% should; payment-failure 48%; Kubernetes resources 36% (but only 20% agreed on *which* demo); cloud-to-cluster
  33%, on 6 prompts; **Lambda and IAM 8%** (the words match unrelated questions); orientation and demo requests only **10%** (43% could):
  the words "demo" and "tour" mostly appear in unrelated prompts.
- What the rules miss (9 of 100 sampled prompts they rejected were should-offers) is almost all **incident-generic**: someone asking
  why something is wrong, slow or failing, in words my keyword rules did not cover.
- Strata of 25 or fewer prompts carry a wide margin (about 20 points); Kubernetes, cloud-to-cluster and images are too small to separate from noise.

**What this means for the triggers.** The reliable pattern is not a subject word but an **intent to find the cause of something that is
wrong** (why is it slow or failing, what changed, root cause, analyse this error or slowdown), asked as a question and not as a task.
Subject words (Lambda, IAM, "demo") are poor triggers. Demo-fit is about 11% of typed prompts, so the realistic reach is a few hundred
prompts a month per tenant, not the 0.1 to 0.3% that orientation questions give.

## What this changes (both tenants agree)

- **Orientation-only triggers reach about 0.1 to 0.3% of traffic** (demo-live 0.3%, playground 0.1%). The current design is right but
  thin: rewording it will not move the volume. Home is where the people are (26% on demo-live, 52% on playground), and they are not
  asking Home about itself.
- The reachable demo-relevant groups are **Kubernetes plus sizing (3.7% demo-live, 4.7% playground)** and **problem investigation
  (2.8% and 2.2%)**, as topical triggers. Cloud cost (2.4% and 1.1%) must not trigger: Assist's own cost skill owns it. DQL (6.5% and
  14.8%) is the biggest typed topic and nothing we offer addresses it.
- 11 to 19% of volume is app buttons, not questions (the Problems "explain the problem" preset alone is 13% on demo-live). Offering a
  demo there would interrupt a task the user started with one click, so it is out unless the data later says otherwise.
- About half the prompts are unclassified on both tenants; the next pass clusters them with the vocabulary report (aggregate-only on playground).
- The offer skill is not on playground, so there it has no baseline of its own; the throttling incident is the only Kubernetes
  demo that exists there.

## Not yet done

Clustering the unmatched half; the trigger table (`offering-live-demos/references/triggers.md`) and its evals; the app-repo change
that would put the skill on playground; re-measuring seven days after the next deploy (demo-live) and after the app-repo change
ships (playground).
