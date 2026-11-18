#!/usr/bin/env python3
"""
assist_prompts.py — what people ask Assist, grouped, to decide when "Try a live demo" should trigger.

The prompts are other people's text, so the default is to look at counts, never at prompts:

    report   Aggregate queries run inside the tenant. Only counts leave it, and a row is shown only when at
             least K distinct users produced it (K = 10; lower only on the internal demo-live pilot).
    pack     Writes the same queries as .dql files, so a tenant admin can run them in a Notebook and send back
             the result tables. --check fails when the files drift from this module.
    fetch    demo-live only (internal users): scrubbed, pseudonymised rows into a git-ignored folder, for
             developing the parser and the taxonomy. Refuses every other tenant.

Source: dt.system.events, event.kind GENAI_EVENT, event.type "GenAI Skill Invocation". An interactive prompt is
a template: <QUESTION>…</QUESTION> then <OPEN-APP>…currently viewing Name (app.id) and it is installed…</OPEN-APP>.

    python tools/assist_prompts.py report --tenant demo-live --days 30
    python tools/assist_prompts.py pack [--check]
    python tools/assist_prompts.py fetch --tenant demo-live --days 30
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import secrets
import sys
from pathlib import Path

TOOLS = Path(__file__).parent
REPO_ROOT = TOOLS.parent
QUERY_DIR = TOOLS / "queries" / "assist-prompts"
FETCH_DIR = REPO_ROOT / "analysis" / "assist-prompts"

K_FLOOR = 10
INTERNAL_TENANTS = {"demo-live"}
OFFER_MARK = "Try a live demo"
LEAK_WORDS = ["demo-live", "playground", "payment-failure", "broken-images", "lambda-iam-denied",
              "k8s-cpu-throttling", "kubernetes-complexity"]

# Intent seed rules, first match wins. phrases match whole words; stems match anywhere in the text.
# They exist to count and to find what they miss, not to be right: a person reviews the rest.
SEED_INTENTS = [
    # Preset prompts behind an "Ask Assist" button in an app; nobody typed them, so they are not what people ask.
    ("canned_ui_prompt", ["continue"], ["explain what happened in the problem", "provide a detailed explanation of the found vulnerability",
                                       "explain and provide insights on this database execution plan", "explain log"]),
    ("orientation", [
        "what can i do here", "what can i do on this", "what can i do in this", "what can i do with this",
        "what is this app", "what is this page", "what's this app", "what is this for", "what does this app do",
        "what can this app do", "what can this page do", "how do i use this", "show me around",
        "how do i get started", "help me get started", "getting started", "get started", "where do i start",
        "where should i start", "explain this app", "explain this page", "overview of this app"], []),
    ("asks_demo", ["show me a demo", "give me a demo", "is there a demo", "live demo", "demo of", "can i see a demo", "guided tour",
                   "walk me through", "take me through", "show me an example investigation"], []),
    ("assist_capabilities", ["what can you do", "how can you help", "what can you help", "what are you able"], []),
    ("problem_investigation", ["what's wrong", "whats wrong", "what is wrong", "any problems", "open problems",
                                "root cause", "what changed", "why is", "why are", "failing", "outage", "slow"], []),
    ("kubernetes_sizing", ["over-provisioned", "overprovisioned", "right-size", "rightsize", "requests and limits",
                           "cpu throttling", "memory limit", "cpu limit"], ["oomkill"]),
    ("kubernetes", ["kubernetes", "k8s", "pod", "pods", "namespace", "workload", "cluster"], []),
    ("cloud_cost", ["cloud cost", "cloud spend", "cost", "costs", "spend", "bill", "savings"], []),
    ("security", ["security", "compliance"], ["vulnerab", "cve-"]),
    ("logs", ["log", "logs"], []),
    ("dql_query", ["dql", "query", "fetch", "timeseries", "summarize"], []),
    ("authoring", ["dashboard", "notebook", "create a", "build a"], []),
    ("docs_howto", ["how do i", "how to", "documentation", "what is a", "what is the", "explain"], []),
]
OPPORTUNITY_INTENTS = ["orientation", "asks_demo"]

# Which demo a prompt's subject could be answered with. A rule matches when every group has a hit (phrases are whole
# words, stems match anywhere). The kubernetes demos need a Kubernetes word AND a subject word, so "limits" alone is not one.
K8S_WORDS = ["kubernetes", "k8s", "pod", "pods", "container", "containers", "workload", "workloads", "deployment", "deployments",
             "namespace", "eks", "cluster", "clusters"]
CAUSE_PHRASES = ["why is", "why are", "why did", "why does", "why do", "what is causing", "what's causing", "whats causing",
                 "what caused", "what changed", "what went wrong", "find the cause", "figure out why", "investigate", "troubleshoot",
                 "diagnose", "what happened to", "what happened with"]
SYMPTOMS = ["slow", "slower", "slowdown", "latency", "error", "errors", "fail", "fails", "failed", "failing", "failure", "failures",
            "outage", "down", "degraded", "timeout", "timeouts", "crash", "crashing", "broken", "spike", "spiking", "not working", "unavailable"]
DEMO_RULES = [
    # Calibration (demo-live, 2026-11-18): bare subject words were poor triggers, so each rule needs a subject AND a context or symptom.
    ("k8s-resources", [["over-provisioned", "overprovisioned", "under-provisioned", "right-size", "rightsize", "right-sizing", "throttled",
                        "throttling", "oomkilled", "oomkill", "memory limit", "memory limits", "cpu limit", "cpu limits",
                        "requests and limits", "resource requests", "resource limits", "reclaim", "starved", "wasted", "wasting"], K8S_WORDS]),
    ("cloud-to-cluster", [["ec2", "aws resources", "cloud alert", "instance", "instances"],
                          ["kubernetes", "k8s", "node", "nodes", "cluster", "clusters", "eks"]]),
    ("payment-failure", [["payment", "payments", "checkout", "credit card", "card payment", "transaction", "transactions"], SYMPTOMS]),
    ("lambda-iam", [["access denied", "permission denied", "accessdenied", "not authorized", "unauthorized", "forbidden"],
                    ["lambda", "dynamodb", "iam", "role"]]),
    # Cause-seeking: a symptom, asked as "why / what changed / what is causing". The subject word does not matter.
    ("incident-generic", [CAUSE_PHRASES, SYMPTOMS]),
    ("incident-generic", [["root cause", "what's wrong", "whats wrong", "what is wrong", "anything wrong", "any problems", "open problems",
                           "what went wrong", "what changed"]]),
]
FOLLOW_UPS = ["yes", "no", "ok", "okay", "continue", "thanks", "thank you", "sure", "go on", "next", "more"]
# Why a prompt that fits a demo should still not be offered one.
DQL_MARKS = [" | ", "fieldsadd", "summarize ", "| filter"]
STOPWORDS = ["the", "and", "for", "with", "that", "this", "what", "can", "how", "are", "you", "from", "any", "does", "have",
             "not", "where", "all", "which", "there", "one", "but", "would", "could", "should", "when", "about", "only",
             "was", "were", "has", "had", "its", "our", "your", "their", "them", "then", "than", "into", "also", "more",
             "some", "such", "these", "those", "will", "just", "like", "need", "want", "get", "got", "see", "use", "using",
             "please", "tell", "give", "show", "given", "following", "provide", "detailed", "instructions.", "why", "who",
             "is", "it", "in", "on", "of", "to", "do", "me", "my", "we", "us", "be", "or", "an", "at", "as", "by", "if", "so"]


def _q(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def scrub_dql(field: str) -> str:
    """DQL that lowercases and removes what could identify someone: emails, urls, long tokens, numbers, spaces."""
    expr = f"lower({field})"
    # replacePattern takes Dynatrace pattern syntax, not regex: literals are quoted, NSPACE is a run of non-space.
    for pattern, repl in (("[a-z0-9._%+-]+ '@' [a-z0-9.-]+", "<email>"), ("'http' 's'? '://' NSPACE", "<url>"),
                          ("[a-z0-9_-]{16,}", "<id>"), ("[0-9]+", "#"), ("SPACE+", " ")):
        expr = f"replacePattern({expr}, {_q(pattern)}, {_q(repl)})"
    return f"trim({expr})"


def scrub(text: str) -> str:
    """The same scrub in Python, applied again to anything fetched, and what the tests pin down."""
    text = text.lower()
    for pattern, repl in ((r"[a-z0-9._%+-]+@[a-z0-9.-]+", "<email>"), (r"https?://[^ ]+", "<url>"),
                          (r"[a-z0-9_-]{16,}", "<id>"), (r"[0-9]+", "#"), (r"\s+", " ")):
        text = re.sub(pattern, repl, text)
    return text.strip()


def intent_steps() -> list[str]:
    """One small fieldsAdd per rule (a single nested if() over every phrase exceeds DQL's expression limit).
    The first rule that matches names the intent; later rules only look at what is still "other"."""
    steps = [f'| fieldsAdd intent = {_q("other")}']
    for name, phrases, stems in SEED_INTENTS:
        tests = [f"matchesPhrase(q, {_q(p)})" for p in phrases] + [f"contains(q, {_q(s)})" for s in stems]
        steps.append(f'| fieldsAdd intent = if(intent == {_q("other")} and ({" or ".join(tests)}), {_q(name)}, else: intent)')
    return steps


def demo_steps() -> list[str]:
    """demo = which demo the subject could be answered with; blocked = why it should not be offered anyway; fit = the verdict.

    could  = the subject matches a demo (or the user asked for orientation or a demo).
    should = could, and nothing blocks it: not an app button, not a one-word follow-up, not pasted DQL, not cloud cost.
    """
    steps = ['| fieldsAdd demo = "none"']
    for name, groups in DEMO_RULES:
        tests = ["(" + " or ".join(f"matchesPhrase(q, {_q(p)})" for p in group) + ")" for group in groups]
        steps.append(f'| fieldsAdd demo = if(demo == "none" and {" and ".join(tests)}, {_q(name)}, else: demo)')
    steps.append('| fieldsAdd demo = if(demo == "none" and intent == "problem_investigation", "incident-generic", else: demo)')
    follow = ", ".join(_q(w) for w in FOLLOW_UPS)
    dql = " or ".join(f"contains(q, {_q(m)})" for m in DQL_MARKS) + ' or startsWith(q, "fetch ")'
    steps += [
        '| fieldsAdd blocked = "none"',
        '| fieldsAdd blocked = if(intent == "canned_ui_prompt", "app_button", else: blocked)',
        f'| fieldsAdd blocked = if(blocked == "none" and in(q, {{{follow}}}), "follow_up", else: blocked)',
        f'| fieldsAdd blocked = if(blocked == "none" and ({dql}), "pasted_dql", else: blocked)',
        '| fieldsAdd blocked = if(blocked == "none" and intent == "cloud_cost", "cloud_cost_is_assists", else: blocked)',
        '| fieldsAdd blocked = if(blocked == "none" and in(intent, {"dql_query", "authoring"}), "mid_task", else: blocked)',
        '| fieldsAdd fit = if(in(intent, {"orientation", "asks_demo"}), "offer: asked for orientation or a demo",'
        ' else: if(demo != "none" and blocked == "none", "offer: topical",'
        ' else: if(demo != "none", "fits a demo but blocked", else: "no demo fit")))',
    ]
    return steps


def base_dql() -> str:
    """Interactive prompts only (the template), with the question scrubbed and the open app parsed."""
    return "\n".join([
        'fetch dt.system.events, from: now()-__DAYS__d, to: now()',
        '| filter event.kind == "GENAI_EVENT" and event.type == "GenAI Skill Invocation"',
        '| filter contains(user_input, "<QUESTION>")',
        '| parse user_input, "\'<QUESTION>\' DATA:question \'</QUESTION>\'"',
        '| parse user_input, "DATA \'<OPEN-APP>\' DATA:block \'</OPEN-APP>\'"',
        '| parse block, "DATA \'viewing \' DATA \' (\' DATA:app_named \') and it is installed\'"',
        '| parse block, "DATA \'viewing \' DATA:app_bare \' and it is installed\'"',
        '| fieldsAdd open_app = coalesce(app_named, app_bare, "(none)")',
        f'| fieldsAdd q = {scrub_dql("question")}',
        *intent_steps(),
        *demo_steps(),
        f'| fieldsAdd offered = contains(toString(response), {_q(OFFER_MARK)})',
    ])


def _leak_test() -> str:
    head = "substring(toString(response), from: 0, to: 400)"
    return " or ".join(f"contains({head}, {_q(w)})" for w in LEAK_WORDS)


def queries() -> dict[str, str]:
    """name -> DQL. Every query ends in aggregates; none returns the question, the user or the response."""
    b = base_dql()
    return {
        "profile": "\n".join([
            'fetch dt.system.events, from: now()-__DAYS__d, to: now()',
            '| filter event.kind == "GENAI_EVENT" and event.type == "GenAI Skill Invocation"',
            '| fieldsAdd interactive = contains(user_input, "<QUESTION>"), has_app = contains(user_input, "<OPEN-APP>")',
            '| summarize events = count(), conversations = countDistinct(conversation_id), users = countDistinct(user_id),',
            '    interactive_events = countIf(interactive), interactive_conversations = countDistinct(if(interactive, conversation_id)),',
            '    interactive_users = countDistinct(if(interactive, user_id)), with_open_app = countIf(has_app),',
            f'    offers_shown = countIf(contains(toString(response), {_q(OFFER_MARK)}))',
        ]),
        "open_app": b + "\n" + "\n".join([
            '| summarize prompts = count(), users = countDistinct(user_id), conversations = countDistinct(conversation_id), by: { open_app }',
            '| filter users >= __K__',
            '| sort prompts desc',
        ]),
        "intent_totals": b + "\n" + "\n".join([
            '| summarize prompts = count(), users = countDistinct(user_id), by: { intent }',
            '| filter users >= __K__',
            '| sort prompts desc',
        ]),
        "intent_by_app": b + "\n" + "\n".join([
            '| summarize prompts = count(), users = countDistinct(user_id), by: { intent, open_app }',
            '| filter users >= __K__',
            '| sort prompts desc',
            '| limit 80',
        ]),
        "offer_rate": b + "\n" + "\n".join([
            '| filter in(intent, {' + ", ".join(_q(i) for i in OPPORTUNITY_INTENTS) + '})',
            '| summarize opportunities = count(), users = countDistinct(user_id), offers = countIf(offered), by: { open_app }',
            '| filter users >= __K__',
            '| fieldsAdd offer_rate_pct = round(100.0 * offers / opportunities, decimals: 0)',
            '| sort opportunities desc',
        ]),
        "demo_fit": b + "\n" + "\n".join([
            '| summarize prompts = count(), users = countDistinct(user_id), by: { fit, demo, blocked }',
            '| filter users >= __K__',
            '| sort prompts desc',
            '| limit 60',
        ]),
        "demo_fit_by_app": b + "\n" + "\n".join([
            '| filter fit == "offer: topical" or fit == "offer: asked for orientation or a demo"',
            '| summarize prompts = count(), users = countDistinct(user_id), by: { demo, open_app }',
            '| filter users >= __K__',
            '| sort prompts desc',
            '| limit 60',
        ]),
        "offer_leaks": b + "\n" + "\n".join([
            '| filter offered',
            f'| fieldsAdd leaked = {_leak_test()}',
            '| summarize offers = count(), users = countDistinct(user_id), leaks = countIf(leaked)',
            '| filter users >= __K__',
        ]),
        "terms": b + "\n" + "\n".join([
            '| filter intent != "canned_ui_prompt"',
            '| fieldsAdd term = splitString(q, " ")',
            '| expand term',
            '| filter stringLength(term) >= 3 and not contains(term, "<")',
            '| filter not in(term, {' + ", ".join(_q(w) for w in STOPWORDS) + '})',
            '| summarize users = countDistinct(user_id), prompts = count(), by: { term }',
            '| filter users >= __K__',
            '| sort users desc',
            '| limit 150',
        ]),
        "phrases": b + "\n" + "\n".join([
            '| filter stringLength(q) >= 3 and stringLength(q) <= 120',
            '| filter not contains(q, "<email>") and not contains(q, "<url>") and not contains(q, "<id>")',
            '| summarize users = countDistinct(user_id), prompts = count(), by: { pattern = q }',
            '| filter users >= __K__',
            '| sort users desc',
            '| limit 200',
        ]),
    }


def render(name: str, days: int, k: int) -> str:
    return queries()[name].replace("__DAYS__", str(days)).replace("__K__", str(k))


def check_report_allowed(tenant: str, k: int) -> None:
    """A tenant with outside users is only ever seen through counts of at least K_FLOOR users."""
    if tenant not in INTERNAL_TENANTS and k < K_FLOOR:
        raise SystemExit(f"error: {tenant} may only be reported with k >= {K_FLOOR} (got {k})")


def check_fetch_allowed(tenant: str) -> None:
    if tenant not in INTERNAL_TENANTS:
        raise SystemExit(f"error: fetch is for internal tenants only ({', '.join(sorted(INTERNAL_TENANTS))}); "
                         f"{tenant} is aggregate-only: use report or the query pack")


def pack_files(days: int = 30, k: int = K_FLOOR) -> dict[str, str]:
    """File name -> content for the query pack, with the defaults filled in."""
    files = {}
    for number, name in enumerate(queries(), 1):
        header = (f"// assist-prompts / {name}: counts only. Run in a Notebook on the tenant and send back the result table.\n"
                  f"// {days} days, rows shown only for at least {k} distinct users. Change both numbers on the first line and the filter.\n")
        files[f"{number:02d}-{name}.dql"] = header + render(name, days, k) + "\n"
    return files


def _load_preflight():
    spec = importlib.util.spec_from_file_location("preflight", TOOLS / "preflight.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(pf, dql: str) -> list[dict]:
    one_line = " ".join(line.strip() for line in dql.splitlines() if line.strip() and not line.strip().startswith("//"))
    _, out, err = pf.run_dtctl("query", one_line, "-o", "json", "--max-field-chars", "0",
                               "--max-result-records", "60000", "--max-result-bytes", "80000000", timeout=300)
    envelope = pf.parse_envelope(out)
    if not (envelope and envelope.get("ok")):
        raise SystemExit(f"query failed: {(err or out)[:300]}")
    result = envelope.get("result", {})
    if result.get("kind") != "result-file":
        return pf._flatten_records(envelope)
    # A big result is spilled by dtctl to a local JSONL file (constant columns left out). It can hold raw user ids and
    # sits outside the repo, so read it once and delete it.
    path = Path(result["path"])
    constant = result.get("constant", {})
    try:
        with path.open(encoding="utf-8") as handle:
            return [{**constant, **json.loads(line)} for line in handle if line.strip()]
    finally:
        path.unlink(missing_ok=True)


def print_table(rows: list[dict]) -> None:
    if not rows:
        print("  (no rows, or none above the user floor)")
        return
    cols = list(rows[0])
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    print("  " + "  ".join(c.ljust(widths[c]) for c in cols))
    for r in rows:
        print("  " + "  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))


def cmd_report(args) -> int:
    check_report_allowed(args.tenant, args.k)
    os.environ["DTCTL_CONTEXT"] = args.tenant
    pf = _load_preflight()
    names = [args.query] if args.query else list(queries())
    print(f"tenant {args.tenant} | {args.days} days | rows need at least {args.k} distinct users")
    for name in names:
        print(f"\n== {name}")
        print_table(run(pf, render(name, args.days, args.k)))
    return 0


def cmd_pack(args) -> int:
    files = pack_files(args.days, args.k)
    if args.check:
        stale = [n for n, text in files.items() if not (QUERY_DIR / n).exists() or (QUERY_DIR / n).read_text(encoding="utf-8") != text]
        extra = [p.name for p in QUERY_DIR.glob("*.dql") if p.name not in files] if QUERY_DIR.exists() else []
        if stale or extra:
            print(f"query pack out of date: {stale + extra}")
            return 1
        print(f"query pack in step ({len(files)} files)")
        return 0
    QUERY_DIR.mkdir(parents=True, exist_ok=True)
    for stray in QUERY_DIR.glob("*.dql"):
        stray.unlink()
    for name, text in files.items():
        (QUERY_DIR / name).write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {len(files)} files to {QUERY_DIR}")
    return 0


def pseudonym(user_id: str, salt: str) -> str:
    return hashlib.sha256((salt + user_id).encode("utf-8")).hexdigest()[:12]


def cmd_fetch(args) -> int:
    check_fetch_allowed(args.tenant)
    os.environ["DTCTL_CONTEXT"] = args.tenant
    pf = _load_preflight()
    dql = base_dql().replace("__DAYS__", str(args.days)) + "\n" + "\n".join([
        '| fields timestamp, conversation_id, user_id, route = skill, open_app, intent, demo, blocked, fit, q, offered',
        '| sort timestamp asc',
        f'| limit {args.limit}',
    ])
    rows = run(pf, dql)
    salt = secrets.token_hex(16)
    out_dir = FETCH_DIR / args.tenant
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "prompts.jsonl"
    seen: dict[str, int] = {}
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            conv = str(row.get("conversation_id"))
            seen[conv] = seen.get(conv, 0) + 1
            record = {"ts": row.get("timestamp"), "conversation": conv, "user": pseudonym(str(row.get("user_id")), salt),
                      "turn": seen[conv], "route": row.get("route"), "open_app": row.get("open_app"),
                      "intent": row.get("intent"), "demo": row.get("demo"), "blocked": row.get("blocked"), "fit": row.get("fit"),
                      "question": scrub(str(row.get("q") or "")), "offered": row.get("offered")}
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"{len(rows)} rows -> {path} (scrubbed, user ids hashed with a one-run salt, no email; git-ignored)")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    report = sub.add_parser("report", help="aggregate-only report")
    report.add_argument("--tenant", default=os.environ.get("DTCTL_CONTEXT", "demo-live"))
    report.add_argument("--days", type=int, default=30)
    report.add_argument("--k", type=int, default=K_FLOOR, help=f"distinct users a row needs (min {K_FLOOR} outside internal tenants)")
    report.add_argument("--query", choices=list(queries()))
    pack = sub.add_parser("pack", help="write the queries as .dql files")
    pack.add_argument("--days", type=int, default=30)
    pack.add_argument("--k", type=int, default=K_FLOOR)
    pack.add_argument("--check", action="store_true")
    fetch = sub.add_parser("fetch", help="scrubbed rows, internal tenants only")
    fetch.add_argument("--tenant", default="demo-live")
    fetch.add_argument("--days", type=int, default=30)
    fetch.add_argument("--limit", type=int, default=50000)
    args = parser.parse_args(argv[1:])
    return {"report": cmd_report, "pack": cmd_pack, "fetch": cmd_fetch}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
