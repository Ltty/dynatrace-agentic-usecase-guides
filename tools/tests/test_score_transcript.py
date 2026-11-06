#!/usr/bin/env python3
"""
Tests for tools/score_transcript.py (offline: synthetic subagent transcripts, no tenant, no key).

Exit 0 = all pass. Exit 1 = failures present.
"""

import importlib.util
import sys
import traceback
from pathlib import Path

TOOLS = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("score_transcript", TOOLS / "score_transcript.py")
st = importlib.util.module_from_spec(spec)
sys.modules["score_transcript"] = st
spec.loader.exec_module(st)
ev = st.load_runner()

SKILL = "C:\\repo\\dynatrace-intelligence\\skills\\investigating-demo-incidents\\SKILL.md"


def assistant(*blocks):
    return {"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}


def use(name, **args):
    return {"type": "tool_use", "id": "x", "name": name, "input": args}


def handback(text):
    return use("SubagentHandback", message=text)


CASE = {"id": "t", "turns": [
    {"ask": "any issues?", "expect": {"first_read_contains": "/SKILL.md", "requires_dql": True,
                                      "reply_contains": ["P-1"]}},
    {"ask": "revert it", "expect": {"no_dql": True, "reply_contains": ["owning team"]}},
]}


def transcript():
    return [
        assistant(use("Read", file_path=SKILL)),
        assistant(use("Bash", command="dtctl query 'fetch dt.davis.problems' --context playground")),
        assistant(use("Bash", command="python tools/preflight.py dtctl-path")),
        assistant(handback("One open problem: P-1.")),
        assistant(handback("That call goes to the owning team.")),
    ]


def test_turns_split_on_each_handback_and_events_map():
    turns = st.to_turns(transcript())
    assert len(turns) == 2
    s = ev.summarize(turns[0])
    assert s["reads"] == ["/resources/documents/skills/investigating-demo-incidents/SKILL.md"]
    assert s["dql_calls"] == 1, "a dtctl query counts once; other Bash commands do not"
    assert s["reply"] == "One open problem: P-1." and s["ends_on_text"]
    assert ev.summarize(turns[1])["dql_calls"] == 0


def test_a_good_transcript_passes():
    assert st.score(ev, CASE, st.to_turns(transcript()), 1, {})["passed"]


def test_a_missing_turn_and_a_forbidden_phrase_fail():
    short = st.score(ev, CASE, st.to_turns(transcript()[:4]), 1, {})
    assert not short["passed"] and "no reply" in short["turns"][1]["failures"][0]
    bad = transcript()[:3] + [assistant(handback("I can't revert that.")), assistant(handback("x"))]
    assert not st.score(ev, CASE, st.to_turns(bad), 1, {})["passed"]


def test_shell_reads_of_skill_files_count_as_reads():
    cmd = ("cd C:/repo/dynatrace-intelligence/skills/investigating-demo-incidents/references && "
           "cat session-protocol.md scenario-payment-failure.md")
    rows = [assistant(use("Bash", command=cmd)), assistant(handback("ok"))]
    s = ev.summarize(st.to_turns(rows)[0])
    base = "/resources/documents/skills/investigating-demo-incidents/references/"
    assert s["reads"] == [base + "session-protocol.md", base + "scenario-payment-failure.md"]
    assert st.shell_reads("ls dynatrace-intelligence/skills/x/") == []
    assert st.shell_reads("cat README.md") == []


def test_shell_reads_credit_each_file_to_the_skill_it_names():
    """With two skills, an agent cds into the skills folder and names the skill in the path.

    The scorer used to find only `skills/<name>` and credit every file in the command to that one
    skill, so a read of the tour's SKILL.md after such a cd was dropped, and a case asserting it
    failed although the agent had read it.
    """
    base = "/resources/documents/skills/"
    two = ("cd C:/repo/dynatrace-intelligence/skills; cat touring-cloud-observability/SKILL.md "
           "investigating-demo-incidents/references/session-protocol.md")
    assert st.shell_reads(two) == [base + "touring-cloud-observability/SKILL.md",
                                   base + "investigating-demo-incidents/references/session-protocol.md"]
    absolute = "cat C:/repo/dynatrace-intelligence/skills/touring-cloud-observability/references/tour-protocol.md"
    assert st.shell_reads(absolute) == [base + "touring-cloud-observability/references/tour-protocol.md"]
    inside = "cd C:/repo/dynatrace-intelligence/skills/touring-cloud-observability && cat SKILL.md"
    assert st.shell_reads(inside) == [base + "touring-cloud-observability/SKILL.md"]
    assert st.shell_reads("ls touring-cloud-observability") == []


def test_an_answer_written_before_the_handback_is_not_progress():
    rows = [assistant({"type": "text", "text": "Checking."}, use("Read", file_path=SKILL)),
            assistant({"type": "text", "text": "The answer."}),
            assistant(handback("The answer."))]
    s = ev.summarize(st.to_turns(rows)[0])
    assert s["progress"] == ["Checking."] and s["reply"] == "The answer."


def test_other_reads_and_text_are_handled():
    rows = [assistant({"type": "text", "text": "Checking."}, use("Read", file_path="C:\\elsewhere\\notes.md")),
            assistant(handback("done"))]
    turn = st.to_turns(rows)[0]
    s = ev.summarize(turn)
    assert s["reads"] == [] and s["progress"] == ["Checking."] and s["reply"] == "done"


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
