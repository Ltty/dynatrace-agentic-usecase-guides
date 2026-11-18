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
| `playground` (customers and people who are not customers) | **Not with the current role.** My role there sees 2 of 13 event kinds in `dt.system.events` and no audit, query-execution or workflow events from the last 2 hours although queries ran on it, so the events are hidden from that role rather than missing. |

## Privacy rules

The prompts belong to other people and the repository is public.

1. Outside the internal tenant everything is aggregated **inside the tenant**: only counts leave it, and a row is shown only when at
   least **10 distinct users** produced it (`report` refuses a lower floor for any tenant but `demo-live`).
2. `fetch` (scrubbed rows to the git-ignored `analysis/` folder, user ids hashed with a per-run salt, no email) works on `demo-live`
   only and refuses every other tenant. Nothing from `analysis/` is committed.
3. No model sees an individual customer's prompt. For a tenant with outside users the most that may reach a model is k-anonymous wording.
4. Analysing customer and prospect prompts on playground needs a data-protection sign-off from that tenant's owner. Nothing was run there.

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

## What this changes

- **Orientation-only triggers can reach about 1% of traffic.** The current design is right but thin: a rewrite of its wording will
  not move the volume.
- The reachable demo-relevant groups are **Kubernetes plus sizing (~3.7%)** and **problem investigation (~2.8%)**, as topical
  triggers. Cloud cost (2.4%) must not trigger: Assist's own cost skill owns it.
- About a fifth of volume is app buttons, not questions. Offering a demo there would interrupt a task the user started with one click,
  so it is out unless the data later says otherwise.
- Half the prompts are still unclassified; the next pass clusters them (aggregate-only on playground).

## Not yet done

Clustering the unmatched half; the trigger table (`offering-live-demos/references/triggers.md`) and its evals; playground (access,
sign-off); re-measuring seven days after the next deploy.
