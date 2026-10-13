#!/usr/bin/env python3
"""
Tests for the assertion engine in run_dt_evals.py (offline, no tenant, no token).
Run after every change to the runner or the case files.

Exit 0 = all pass. Exit 1 = failures present.
"""

import importlib.util
import sys
import traceback
from pathlib import Path

TOOLS = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("run_dt_evals", TOOLS / "run_dt_evals.py")
ev = importlib.util.module_from_spec(spec)
sys.modules["run_dt_evals"] = ev
spec.loader.exec_module(ev)

CLEAN = "Environment looks clean — nothing I'd page on right now."
SKILL = "/resources/documents/skills/investigating-playground-incidents/SKILL.md"
REFS = "/resources/documents/skills/investigating-playground-incidents/references/"


def call(name, **args):
    return {"type": "tool_invocation", "tool_call": {"name": name, "args": args}}


def say(text):
    return {"type": "agent_response", "content": [{"type": "text", "text": text}]}


def stream(*, reads=(), dql=0, reply=CLEAN, tail_tool=False):
    events = [call("read_file", file_path=p) for p in reads] + [call("execute-dql")] * dql + [say(reply)]
    return events + ([call("execute-dql")] if tail_tool else [])


CLEAN_EXPECT = {"first_read_contains": "/SKILL.md", "reads_include": ["session-protocol.md"],
                "reads_exclude": ["-beats.md"], "requires_dql": True, "reply_equals": CLEAN}
GOOD = stream(reads=[SKILL, REFS + "session-protocol.md"], dql=2)


def fails(events, expect, truth=None, forbid=True):
    return ev.check_turn(ev.summarize(events), expect, truth or {}, forbid)


def test_good_run_passes():
    assert fails(GOOD, CLEAN_EXPECT) == []


def test_extra_text_fails_reply_equals():
    out = fails(stream(reads=[SKILL, REFS + "session-protocol.md"], dql=1, reply=CLEAN + " Want to dig deeper?"), CLEAN_EXPECT)
    assert any("not exactly" in f for f in out), out


def test_whitespace_differences_are_ignored():
    assert fails(stream(reads=[SKILL, REFS + "session-protocol.md"], dql=1, reply="  " + CLEAN.replace(" — ", "\n— ") + "\n"), CLEAN_EXPECT) == []


def test_skill_not_read_first_fails():
    out = fails(stream(reads=[REFS + "session-protocol.md", SKILL], dql=1), CLEAN_EXPECT)
    assert any("first file read" in f for f in out), out


def test_beats_file_read_fails_exclude():
    out = fails(stream(reads=[SKILL, REFS + "session-protocol.md", REFS + "scenario-x-beats.md"], dql=1), CLEAN_EXPECT)
    assert any("-beats.md" in f for f in out), out


def test_missing_dql_fails():
    out = fails(stream(reads=[SKILL, REFS + "session-protocol.md"], dql=0), CLEAN_EXPECT)
    assert any("ran no DQL" in f for f in out), out


def test_max_dql_calls_assertion():
    assert fails(stream(dql=1, reply="x"), {"max_dql_calls": 1}, forbid=False) == []
    assert fails(stream(dql=0, reply="x"), {"max_dql_calls": 1}, forbid=False) == []
    assert any("allowed 1" in f for f in fails(stream(dql=2, reply="x"), {"max_dql_calls": 1}, forbid=False))


def test_no_dql_assertion():
    assert fails(stream(dql=0, reply="x"), {"no_dql": True}, forbid=False) == []
    assert any("ran DQL" in f for f in fails(stream(dql=1, reply="x"), {"no_dql": True}, forbid=False))


def test_turn_must_end_on_text():
    out = fails(stream(reads=[SKILL, REFS + "session-protocol.md"], dql=1, tail_tool=True), CLEAN_EXPECT)
    assert any("did not end on text" in f for f in out), out


def test_forbidden_phrases_fail_by_default():
    for reply in ("I can't revert that.", "I'm read-only here.", "Beat 3 is next.", "As an AI I cannot."):
        assert fails(stream(reply=reply), {}), reply
    assert fails(stream(reply="I can't revert that."), {}, forbid=False) == []


def test_dynatrace_intelligence_is_forbidden_only_as_self_identification():
    assert fails(stream(reply="Dynatrace Intelligence points at payment as the origin."), {}) == []
    assert fails(stream(reply="I'm Dynatrace Intelligence, your assistant."), {})
    assert fails(stream(reply="As Dynatrace Intelligence I can help."), {})


def test_curly_apostrophe_cant_is_forbidden():
    assert fails(stream(reply="I can’t revert that."), {})


def test_heartbeat_is_not_the_word_beat():
    assert fails(stream(reply="The heartbeat check is fine."), {}) == []


def test_reply_contains_any_and_excludes():
    expect = {"reply_contains_any": ["Guardrail intervened", "here for incidents"], "reply_excludes": ["points"]}
    assert fails(stream(reply="Guardrail intervened."), expect) == []
    assert fails(stream(reply="Something else."), expect)
    assert fails(stream(reply="Guardrail intervened. 5 points."), expect)


def test_truth_placeholders_expand():
    truth = {"payment_failure": {"affected_users": 275, "commit7s": ["c93ac9e", "6c3b37f"]}}
    expect = {"reply_contains": ["{truth.payment_failure.affected_users}"],
              "reply_contains_any": ["{truth.payment_failure.commit7s}"]}
    assert fails(stream(reply="275 users, commit 6c3b37f"), expect, truth) == []
    assert fails(stream(reply="275 users, no commit"), expect, truth)
    assert fails(stream(reply="no numbers, commit c93ac9e"), expect, truth)


def test_empty_ground_truth_fails_loudly():
    for truth in ({}, {"payment_failure": {"commit7s": []}}, {"payment_failure": {"affected_users": None}}):
        out = fails(stream(reply="anything"), {"reply_contains": ["{truth.payment_failure.affected_users}"],
                                                "reply_contains_any": ["{truth.payment_failure.commit7s}"]}, truth)
        assert any("no ground truth" in f for f in out), (truth, out)


def progress_stream(*lines, reply=CLEAN):
    events = [say(lines[0]), call("read_file", file_path=SKILL)] if lines else []
    for line in lines[1:]:
        events += [call("execute-dql"), say(line)]
    return events + [call("execute-dql"), say(reply)]


def test_progress_lines_are_counted():
    one = progress_stream("Checking for open issues.")
    assert fails(one, {"max_progress_lines": 1}) == []
    two = progress_stream("Checking for open issues.", "Looking a little closer.")
    assert any("progress lines" in f for f in fails(two, {"max_progress_lines": 1})), "two lines must fail"
    assert any("progress lines" in f for f in fails(one, {"max_progress_lines": 0}))


def test_progress_equals():
    line = "Checking for open issues."
    assert fails(progress_stream(line), {"progress_equals": line}) == []
    assert any("not" in f for f in fails(progress_stream("Hang on."), {"progress_equals": line}))
    assert any("no progress line" in f for f in fails(stream(reply=CLEAN), {"progress_equals": line}))


def test_narrating_the_working_fails():
    for text in ("Now I'll run both resolvers simultaneously.", "Both primaries returned empty — running fallbacks now.",
                 "Reading the skill files first.", "Let me check SKILL.md."):
        out = fails(progress_stream(text), {})
        assert any("narrates its working" in f for f in out), (text, out)
    assert fails(progress_stream("Checking for open issues."), {}) == []
    assert fails(progress_stream(text, reply="All fine."), {}, forbid=False) == []


def test_case_files_are_well_formed():
    cases = ev.load_cases()
    assert len(cases) >= 9
    known = {"first_read_contains", "reads_include", "reads_exclude", "no_dql", "requires_dql", "ends_on_text",
             "reply_equals", "reply_contains", "reply_contains_any", "reply_excludes",
             "max_progress_lines", "progress_equals", "max_dql_calls"}
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), "duplicate case ids"
    for case in cases:
        assert case["id"] == Path(case["file"]).stem, case["file"]
        assert case["tenant"] in ev.TENANTS, case["id"]
        assert case["turns"], case["id"]
        for turn in case["turns"]:
            assert turn["ask"], case["id"]
            assert set(turn.get("expect", {})) <= known, (case["id"], set(turn["expect"]) - known)
            for item in sum((turn.get("expect", {}).get(k, []) for k in
                             ("reply_contains", "reply_contains_any", "reply_excludes")), []):
                if item.startswith("{truth."):
                    assert ev.TRUTH_RE.match(item), item
                    assert item.split(".")[1] in [t.replace("-", "_") for t in case.get("truth", [])], (case["id"], item)


def main() -> int:
    failed = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)):
        try:
            fn()
            print(f"  PASS {name}")
        except Exception:
            failed += 1
            print(f"  FAIL {name}")
            traceback.print_exc()
    print(f"\n{'all passed' if not failed else str(failed) + ' failed'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
