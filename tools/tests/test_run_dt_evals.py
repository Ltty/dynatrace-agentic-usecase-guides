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
REPO_ROOT = TOOLS.parent
spec = importlib.util.spec_from_file_location("run_dt_evals", TOOLS / "run_dt_evals.py")
ev = importlib.util.module_from_spec(spec)
sys.modules["run_dt_evals"] = ev
spec.loader.exec_module(ev)

CLEAN = "Environment looks clean — nothing I'd page on right now."
SKILL = "/resources/documents/skills/investigating-demo-incidents/SKILL.md"
REFS = "/resources/documents/skills/investigating-demo-incidents/references/"


def call(name, **args):
    return {"type": "tool_invocation", "tool_call": {"name": name, "args": args}}


def say(text):
    return {"type": "agent_response", "content": [{"type": "text", "text": text}]}


def stream(*, reads=(), dql=0, reply=CLEAN, tail_tool=False):
    events = [call("read_file", file_path=p) for p in reads] + [call("execute-dql")] * dql + [say(reply)]
    return events + ([call("execute-dql")] if tail_tool else [])


CLEAN_EXPECT = {"first_read_contains": "/SKILL.md", "reads_include": ["session-protocol.md"],
                "reads_exclude": ["scenario-"], "requires_dql": True, "reply_equals": CLEAN}
GOOD = stream(reads=[SKILL, REFS + "session-protocol.md"], dql=2)


def fails(events, expect, truth=None, forbid=True):
    return ev.check_turn(ev.summarize(events), expect, truth or {}, forbid)


def test_open_app_is_a_context_line_on_the_first_turn_only():
    sent = []

    class Agent:
        def invoke_agent(self, tenant, agent, text, conversation=None):
            sent.append(text)
            return "c", [{"type": "agent_response", "content": [{"text": "ok"}]}]

    case = {"id": "x", "open_app": "dynatrace.kubernetes", "turns": [{"ask": "What can I do here?"}, {"ask": "yes"}]}
    ev.run_case(Agent(), None, case, 1, {})
    assert sent[0] == "(The Dynatrace app open in the browser is `dynatrace.kubernetes`.) What can I do here?"
    assert sent[1] == "yes"
    assert ev.with_open_app("hi", None) == "hi"


STEP = """### What shipped just before it started

To know whether the deploy caused this, we need the failure rate either side of it.

**Two deploys landed within minutes of the first slow request.**

| Commit | First deployed (UTC) | Gap (min) |
|---|---|---|
| 56e23b6 | 04:01 | 2.3 |

- **Lead suspect:** commit `56e23b6` reached the service 2.3 minutes before the problem and was redeployed six times.
- **Timing only:** a short gap suggests a cause; it does not prove one.

[The deploys on the problem record](https://playground.apps.dynatrace.com/ui/apps/x?from=1&to=2)

**Next:**
- **a)** what the service did request by request
- **b)** the shoppers who sat through it
I'd take (a): it ties the deploy to the slowdown. Say a, b or next.
"""


def layout_fails(reply, **expect):
    return ev.check_layout(reply, {"layout": "step", **expect})


def test_a_well_formed_step_passes_the_layout_checks():
    assert layout_fails(STEP) == []


def test_layout_needs_a_headline():
    body = STEP.split("\n", 1)[1]
    assert any("headline" in f for f in layout_fails(body))
    # the approach line may come first on a scenario's first step
    assert layout_fails("Here's how I'd work it: who, then what.\n\n" + STEP) == []


def test_layout_rejects_a_bare_url_and_accepts_a_labelled_one():
    bare = STEP.replace("[The deploys on the problem record](https://playground.apps.dynatrace.com/ui/apps/x?from=1&to=2)",
                        "The deploys: https://playground.apps.dynatrace.com/ui/apps/x?from=1&to=2")
    assert any("bare URL" in f for f in layout_fails(bare))


def test_layout_caps_words_outside_the_table_and_link():
    padded = STEP + "\n" + "word " * 260
    assert any("words outside" in f for f in layout_fails(padded))
    assert layout_fails(padded, max_words=400) == [] or not any("words outside" in f for f in layout_fails(padded, max_words=400))


def test_layout_caps_sentences_in_a_paragraph_and_a_bullet():
    wall = STEP.replace("**Two deploys landed within minutes of the first slow request.**",
                        "One. Two. Three. Four sentences here.")
    assert any("paragraph has more" in f for f in layout_fails(wall))
    fat = STEP.replace("- **Timing only:** a short gap suggests a cause; it does not prove one.",
                       "- **Timing only:** one. Two. Three.")
    assert any("bullet has more" in f for f in layout_fails(fat))


def test_layout_counts_what_it_means_bullets_but_not_the_options():
    one = STEP.replace("- **Timing only:** a short gap suggests a cause; it does not prove one.\n", "")
    assert any("1 bullets" in f for f in layout_fails(one))
    five = STEP.replace("- **Timing only:** a short gap suggests a cause; it does not prove one.\n",
                        "".join(f"- **Point {i}:** text.\n" for i in range(5)))
    assert any("bullets, expected" in f for f in layout_fails(five))


def test_layout_checks_are_opt_in():
    assert ev.check_layout("no headline and a bare http://x.y link, " + "w " * 500, {}) == []
    assert ev.check_layout("no headline", {"headline": True}) != []


def test_a_placeholder_is_forbidden():
    assert any("forbidden" in f for f in fails(stream(reply="Latency is 370 ms ago... (see below)"), {}))


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


def test_scenario_file_read_fails_exclude():
    out = fails(stream(reads=[SKILL, REFS + "session-protocol.md", REFS + "scenario-x.md"], dql=1), CLEAN_EXPECT)
    assert any("scenario-" in f for f in out), out


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


def test_quoted_exclusions_still_exist_in_the_skill():
    """A forbidden phrase the skill can no longer produce has stopped testing anything.

    `reply_excludes` is mostly intent ("global outage", "davis", "I can't") and those must never
    appear in the skill. `reply_excludes_quoted` is the other kind: a phrase copied *from* the skill,
    forbidden where it does not belong — a showcase asking the incident mode question, say. Reword the
    skill and such a case keeps passing while asserting nothing, which is how the mode-question
    rewrite silently emptied six cases. This test fails instead, naming the case.
    """
    roots = [REPO_ROOT / "dynatrace-intelligence", REPO_ROOT / "skills"]
    corpus = chr(10).join(
        f.read_text(encoding="utf-8").lower()
        for root in roots for f in root.rglob("*.md")
    )
    assert corpus, "no skill documents found"
    checked = 0
    for case in ev.load_cases():
        for turn in case["turns"]:
            for needle in turn.get("expect", {}).get("reply_excludes_quoted", []):
                if needle.startswith("{truth."):
                    continue
                checked += 1
                assert needle.lower() in corpus, (
                    case["id"], f"quoted exclusion no longer in any skill document: {needle!r}")
    assert checked, "reply_excludes_quoted is declared but unused"


def test_case_files_are_well_formed():
    cases = ev.load_cases()
    assert len(cases) >= 9
    known = {"first_read_contains", "reads_include", "reads_exclude", "no_dql", "requires_dql", "ends_on_text",
             "reply_equals", "reply_contains", "reply_contains_any", "reply_excludes",
             "reply_excludes_quoted",
             "max_progress_lines", "progress_equals", "max_dql_calls",
             "layout", "headline", "max_words", "max_paragraph_sentences", "max_bullet_sentences", "bullets",
             "labelled_links"}
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
                             ("reply_contains", "reply_contains_any", "reply_excludes",
                              "reply_excludes_quoted")), []):
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
