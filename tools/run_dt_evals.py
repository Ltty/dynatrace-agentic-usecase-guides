#!/usr/bin/env python3
"""
run_dt_evals.py — Run the demo-agent behaviour cases and write a review sheet.

Cases live in tests/evals/dt-agent/*.yaml. Each case runs several times (agents are not
deterministic), every turn is checked with scripted assertions, and a Markdown review sheet
with the transcripts is written for the things a script cannot judge (tone, persona).
Scenario cases compare the agent's numbers with ground truth: the runner runs the resolver
and deployment DQL itself on the read-only Playground dtctl context.

Usage:
    python tools/run_dt_evals.py --list
    python tools/run_dt_evals.py --truth payment-failure
    python tools/run_dt_evals.py --tenant dev [--case greeting,cost] [--runs 3] [--workers 3]
    python tools/run_dt_evals.py --tenant playground

Tokens: DT_DEV_AGENT_TOKEN (dev) and DT_PLAYGROUND_AGENT_TOKEN (playground); never printed.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CASES_DIR = REPO_ROOT / "tests" / "evals" / "dt-agent"
REPORTS_DIR = CASES_DIR / "reports"
AGENT = "demo-agent"
TENANTS = {
    "dev": ("https://fxz0998d.dev.apps.dynatracelabs.com", "DT_DEV_AGENT_TOKEN"),
    "playground": ("https://playground.apps.dynatrace.com", "DT_PLAYGROUND_AGENT_TOKEN"),
}
FORBIDDEN = [
    r"\bbeats?\b", r"step \d+ of \d+", r"\bthe demo\b", r"\bas an ai\b", r"\bI can'?t\b",
    r"\bI'?m read-only\b", r"\bI am read-only\b", r"dynatrace intelligence",
]
TRUTH_RE = re.compile(r"^\{truth\.([a-z_]+)\.([a-z0-9_]+)\}$")


def load_module(name: str):
    path = Path(__file__).parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Events and assertions (pure functions, covered by tools/tests/test_run_dt_evals.py)
# ---------------------------------------------------------------------------

def summarize(events: list[dict]) -> dict:
    """Reduce an event stream to the facts the assertions need."""
    calls = [(e["tool_call"]["name"], e["tool_call"].get("args") or {})
             for e in events if e.get("type") == "tool_invocation"]
    text_at = [(i, " ".join(c.get("text", "") for c in e.get("content") or [] if isinstance(c, dict)).strip())
               for i, e in enumerate(events) if e.get("type") == "agent_response"]
    text_at = [(i, t) for i, t in text_at if t]
    last_tool = max((i for i, e in enumerate(events) if e.get("type") == "tool_invocation"), default=-1)
    return {
        "calls": calls,
        "reads": [a.get("file_path", "") for n, a in calls if n == "read_file"],
        "dql_calls": sum(1 for n, _ in calls if n == "execute-dql"),
        "reply": text_at[-1][1] if text_at else "",
        "ends_on_text": bool(text_at) and text_at[-1][0] > last_tool,
    }


def norm(text: str) -> str:
    return " ".join(text.split())


def expand(items: list[str], truth: dict) -> list[str]:
    """Replace {truth.<scenario>.<field>} with ground-truth values (a list expands to its items)."""
    out: list[str] = []
    for item in items:
        match = TRUTH_RE.match(item)
        if not match:
            out.append(item)
            continue
        value = truth.get(match.group(1), {}).get(match.group(2))
        values = [str(v) for v in (value if isinstance(value, list) else [value]) if v not in (None, "")]
        if not values:
            raise KeyError(item)
        out.extend(values)
    return out


def check_turn(summary: dict, expect: dict, truth: dict, forbid: bool = True) -> list[str]:
    """Return the failed assertions for one turn (empty list = pass)."""
    fails: list[str] = []
    reply, low, reads = summary["reply"], summary["reply"].lower(), summary["reads"]

    def values(key: str) -> list[str]:
        try:
            return expand(expect.get(key, []), truth)
        except KeyError as e:  # an empty ground truth must fail the check, never skip it
            fails.append(f"no ground truth for {e.args[0]}")
            return []

    if expect.get("ends_on_text", True) and not summary["ends_on_text"]:
        fails.append("the turn did not end on text")
    if "first_read_contains" in expect and not (reads and expect["first_read_contains"] in reads[0]):
        fails.append(f"first file read was not {expect['first_read_contains']} (reads: {reads[:2]})")
    for needle in expect.get("reads_include", []):
        if not any(needle in r for r in reads):
            fails.append(f"never read a file containing {needle}")
    for needle in expect.get("reads_exclude", []):
        if any(needle in r for r in reads):
            fails.append(f"read a file containing {needle}")
    if expect.get("no_dql") and summary["dql_calls"]:
        fails.append(f"ran DQL ({summary['dql_calls']} calls) but should not have")
    if expect.get("requires_dql") and not summary["dql_calls"]:
        fails.append("ran no DQL")
    if "reply_equals" in expect and norm(reply) != norm(expect["reply_equals"]):
        fails.append(f"reply is not exactly {expect['reply_equals']!r}")
    for needle in values("reply_contains"):
        if needle.lower() not in low:
            fails.append(f"reply lacks {needle!r}")
    any_of = values("reply_contains_any")
    if any_of and not any(n.lower() in low for n in any_of):
        fails.append(f"reply contains none of {any_of}")
    for needle in values("reply_excludes"):
        if needle.lower() in low:
            fails.append(f"reply contains forbidden {needle!r}")
    if forbid:
        for pattern in FORBIDDEN:
            if re.search(pattern, reply, re.I):
                fails.append(f"reply matches forbidden pattern {pattern}")
    return fails


# ---------------------------------------------------------------------------
# Ground truth (Playground, read-only dtctl context)
# ---------------------------------------------------------------------------

def ground_truth(scenario_id: str) -> dict:
    """The resolver row and the deployment commits the agent should report for a scenario."""
    os.environ["DTCTL_CONTEXT"] = "playground"
    validate = load_module("validate_dt_skill")
    pf = validate._load_preflight()
    resolver_file, beats_file = validate.SCENARIO_FILES[scenario_id]

    def run(raw: str) -> tuple[dict, list[dict]]:
        rc, out, _ = pf.run_dtctl("query", validate.strip_dql_comments(raw), "-o", "json",
                                  "--max-field-chars", "0", "-M=all")
        envelope = pf.parse_envelope(out)
        return (envelope or {}), (pf._flatten_records(envelope) if envelope and envelope.get("ok") else [])

    envelope, rows = {}, []
    for block in validate.extract_dql_blocks(resolver_file)[:2]:
        envelope, rows = run(block)
        if rows:
            break
    if not rows:
        return {}
    row = rows[0]
    truth = {k: row.get(k) for k in ("display_id", "affected_users", "root_cause", "status", "duration_min")}
    state = validate.extract_state_from_resolver(pf, envelope)
    commits: list[str] = []
    for block in validate.extract_dql_blocks(beats_file):
        if "CUSTOM_DEPLOYMENT" in block and "{{TRACE_ID}}" not in block:
            _, deploys = run(pf.substitute_placeholders(block, state, pass_through_unknown=True))
            commits = list(dict.fromkeys(str(d["commit"]) for d in deploys if d.get("commit")))
            break
    truth["commits"] = commits
    truth["commit7s"] = [c[:7] for c in commits]
    return truth


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------

def load_cases() -> list[dict]:
    import yaml
    cases = []
    for path in sorted(CASES_DIR.glob("*.yaml")):
        case = yaml.safe_load(path.read_text(encoding="utf-8"))
        case["file"] = path.name
        cases.append(case)
    return cases


def run_case(agent_mod, tenant, case: dict, run_no: int, truth: dict) -> dict:
    conversation, turns = None, []
    for turn in case["turns"]:
        try:
            conversation, events = agent_mod.invoke_agent(tenant, AGENT, turn["ask"], conversation)
        except Exception as e:  # a failed request is a failed run, not a crash
            turns.append({"ask": turn["ask"], "calls": [], "reply": "", "failures": [f"request failed: {e}"[:300]]})
            break
        summary = summarize(events)
        summary["ask"] = turn["ask"]
        summary["failures"] = check_turn(summary, turn.get("expect", {}), truth, case.get("forbid", True))
        turns.append(summary)
    return {"case": case["id"], "run": run_no, "turns": turns,
            "passed": all(not t["failures"] for t in turns)}


def write_sheet(path: Path, results: list[dict], tenant_name: str, stamp: str) -> None:
    lines = [f"# demo-agent eval review sheet — {tenant_name}, {stamp}", "",
             "Scripted checks are marked PASS or FAIL per run. Read the replies for tone and persona.", ""]
    for r in results:
        lines += [f"## {r['case']} — run {r['run']}: {'PASS' if r['passed'] else 'FAIL'}", ""]
        for t in r["turns"]:
            lines += [f"**Ask:** {t['ask']}", ""]
            if t["calls"]:
                shown = [f"`{n}`" + (f" {a.get('file_path', '').rsplit('/', 1)[-1]}" if n == "read_file" else "")
                         for n, a in t["calls"]]
                lines += ["Tools: " + ", ".join(shown), ""]
            lines += ["Reply:", "", "> " + (t["reply"].replace("\n", "\n> ") or "(none)"), ""]
            lines += [f"- FAIL: {f}" for f in t["failures"]] + ([""] if t["failures"] else [])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--tenant", choices=list(TENANTS), help="which tenant's agent to test")
    parser.add_argument("--case", help="comma-separated case ids (default: all for the tenant)")
    parser.add_argument("--runs", type=int, help="override runs per case")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--list", action="store_true", help="list the cases and exit")
    parser.add_argument("--truth", metavar="SCENARIO", help="print the ground truth for a scenario and exit")
    parser.add_argument("--include-draft", action="store_true", help="also run cases marked status: draft")
    parser.add_argument("--out", help="review sheet path (default: tests/evals/dt-agent/reports/…)")
    args = parser.parse_args(argv[1:])

    if args.truth:
        print(json.dumps(ground_truth(args.truth), indent=2, ensure_ascii=False))
        return 0
    cases = load_cases()
    if args.list:
        for c in cases:
            print(f"  {c['id']:24} tenant={c['tenant']:10} runs={c.get('runs', 3)} status={c.get('status', 'ready')}")
        return 0
    if not args.tenant:
        parser.error("--tenant is required to run cases")

    wanted = set(args.case.split(",")) if args.case else None
    selected = [c for c in cases if c["tenant"] == args.tenant and (wanted is None or c["id"] in wanted)
                and (args.include_draft or c.get("status", "ready") != "draft")]
    if not selected:
        print("no cases selected")
        return 0
    agent_mod = load_module("dt_agent")
    url, token_var = TENANTS[args.tenant]
    tenant = agent_mod.Tenant(url, token_var)
    if agent_mod.deployed_template(tenant, AGENT) is None:
        print(f"SKIP all: no {AGENT} template on {args.tenant} ({url})")
        return 0

    truth: dict = {}
    for scenario in sorted({s for c in selected for s in c.get("truth", [])}):
        truth[scenario.replace("-", "_")] = ground_truth(scenario)
    runnable = []
    for case in selected:
        missing = [s for s in case.get("truth", []) if not truth.get(s.replace("-", "_"))]
        if missing:
            print(f"SKIP {case['id']}: no live problem in the last 48h for {missing}")
        else:
            runnable.append(case)

    jobs = [(c, n) for c in runnable for n in range(1, (args.runs or c.get("runs", 3)) + 1)]
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(lambda j: run_case(agent_mod, tenant, j[0], j[1], truth), jobs))

    print(f"\n{'case':26} runs  pass  failures")
    exit_code = 0
    for case in runnable:
        mine = [r for r in results if r["case"] == case["id"]]
        passed = sum(r["passed"] for r in mine)
        first = next((f for r in mine for t in r["turns"] for f in t["failures"]), "")
        print(f"{case['id']:26} {len(mine):<5} {passed}/{len(mine):<3} {first[:90]}")
        exit_code |= int(passed != len(mine))
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sheet = Path(args.out) if args.out else REPORTS_DIR / f"{stamp}-{args.tenant}.md"
    write_sheet(sheet, results, args.tenant, stamp)
    print(f"\nreview sheet: {sheet}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
