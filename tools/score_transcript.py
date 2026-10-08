#!/usr/bin/env python3
"""
score_transcript.py — Score a Claude Code subagent transcript against an eval case.

This is the way to run the evals inside a Claude Code session, with no API key and no deployed
agent: spawn a subagent that plays the demo-agent (docs/DYNATRACE-SKILL.md → "In-session evals"),
give it the case's turns one by one, then score the transcript it leaves behind. The transcript
is read by this script, never printed, so it costs no context.

A subagent transcript is ~/.claude/projects/<project>/<session>/subagents/agent-<id>.jsonl.
Mapping to the events run_dt_evals.py asserts on:
    Read of a skill file            -> read_file /resources/documents/skills/<path>
    Bash cat/head/sed of skill .md  -> one read_file per file named (a subagent often reads this way)
    Bash running `dtctl … query`    -> execute-dql (one per query)
    SubagentHandback(message=…)     -> the turn's reply (it ends the turn)

A subagent writes no text between tool calls, so progress-line assertions pass trivially and the
status line cannot be checked here.

Usage:
    python tools/score_transcript.py <case-id> <agent.jsonl> [<agent.jsonl> …] [--out sheet.md]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).parent
SKILLS_MARKER = "dynatrace-intelligence/skills/"
MOUNT = "/resources/documents/skills/"
DTCTL_QUERY = re.compile(r"\bdtctl(?:\.exe)?['\"]?\s+query\b")
READ_COMMAND = re.compile(r"\b(?:cat|head|tail|sed|less|more|type|Get-Content)\b")
SKILL_DIR = re.compile(r"dynatrace-intelligence/skills/([\w-]+)")
MD_FILE = re.compile(r"[\w-]+\.md\b")


def shell_reads(command: str) -> list[str]:
    """Skill documents a shell command reads, as read_file paths (cat a.md b.md after a cd into the skill)."""
    skill = SKILL_DIR.search(command.replace("\\", "/"))
    if not skill or not READ_COMMAND.search(command):
        return []
    base = MOUNT + skill.group(1) + "/"
    names = list(dict.fromkeys(MD_FILE.findall(command)))
    return [base + ("SKILL.md" if n == "SKILL.md" else "references/" + n) for n in names]


def load_runner():
    spec = importlib.util.spec_from_file_location("run_dt_evals", TOOLS_DIR / "run_dt_evals.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_dt_evals"] = module
    spec.loader.exec_module(module)
    return module


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def to_turns(rows: list[dict]) -> list[list[dict]]:
    """Split a transcript into turns of runner events; each SubagentHandback ends one turn."""
    turns: list[list[dict]] = []
    events: list[dict] = []
    for row in rows:
        content = (row.get("message") or {}).get("content")
        if row.get("type") != "assistant" or not isinstance(content, list):
            continue
        for block in content:
            kind = block.get("type")
            if kind == "text" and block.get("text", "").strip():
                events.append({"type": "agent_response", "content": [{"text": block["text"]}]})
            elif kind == "tool_use":
                name, args = block.get("name"), block.get("input") or {}
                if name == "SubagentHandback":
                    reply = args.get("message", "").strip()
                    # a subagent often writes its answer as text just before handing it back: that is the reply, not progress
                    events = [e for e in events if e["type"] != "agent_response"
                              or e["content"][0]["text"].strip() != reply]
                    events.append({"type": "agent_response", "content": [{"text": args.get("message", "")}]})
                    turns.append(events)
                    events = []
                elif name == "Read":
                    path = (args.get("file_path") or "").replace("\\", "/")
                    at = path.find(SKILLS_MARKER)
                    if at >= 0:
                        events.append({"type": "tool_invocation", "tool_call": {
                            "name": "read_file", "args": {"file_path": MOUNT + path[at + len(SKILLS_MARKER):]}}})
                elif name == "Bash":
                    for path in shell_reads(args.get("command", "")):
                        events.append({"type": "tool_invocation", "tool_call": {
                            "name": "read_file", "args": {"file_path": path}}})
                    for _ in DTCTL_QUERY.findall(args.get("command", "")):
                        events.append({"type": "tool_invocation", "tool_call": {
                            "name": "execute-dql", "args": {"command": args.get("command", "")}}})
    return turns


def score(ev, case: dict, turns: list[list[dict]], run_no: int, truth: dict) -> dict:
    results = []
    for i, turn in enumerate(case["turns"]):
        if i >= len(turns):
            results.append({"ask": turn["ask"], "calls": [], "reply": "",
                            "failures": ["no reply for this turn in the transcript"]})
            break
        summary = ev.summarize(turns[i])
        summary["ask"] = turn["ask"]
        summary["failures"] = ev.check_turn(summary, turn.get("expect", {}), truth, case.get("forbid", True))
        results.append(summary)
    return {"case": case["id"], "run": run_no, "turns": results,
            "passed": all(not t["failures"] for t in results)}


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("case", help="eval case id")
    parser.add_argument("transcripts", nargs="+", type=Path, help="subagent transcript(s), one per run")
    parser.add_argument("--out", help="write a review sheet here")
    args = parser.parse_args(argv[1:])

    ev = load_runner()
    case = next((c for c in ev.load_cases() if c["id"] == args.case), None)
    if case is None:
        print(f"no such case: {args.case}")
        return 2
    truth = {s.replace("-", "_"): ev.ground_truth(s) for s in case.get("truth", [])}
    results = [score(ev, case, to_turns(load_rows(p)), n, truth) for n, p in enumerate(args.transcripts, 1)]
    for r in results:
        print(f"{r['case']} run {r['run']}: {'PASS' if r['passed'] else 'FAIL'}")
        for t in r["turns"]:
            for failure in t["failures"]:
                print(f"   - {failure}")
    if args.out:
        ev.write_sheet(Path(args.out), results, "in-session subagent", "")
        print(f"review sheet: {args.out}")
    return int(not all(r["passed"] for r in results))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
