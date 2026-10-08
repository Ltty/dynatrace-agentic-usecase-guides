#!/usr/bin/env python3
"""
Tests for tools/local_agent.py (offline: a scripted model, a fake dtctl, no key, no tenant).
Run after every change to the harness.

Exit 0 = all pass. Exit 1 = failures present.
"""

import importlib.util
import os
import sys
import traceback
from pathlib import Path

TOOLS = Path(__file__).parent.parent
sys.path.insert(0, str(TOOLS))


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


la = load("local_agent")
ev = load("run_dt_evals")

SKILL = "/resources/documents/skills/investigating-playground-incidents/SKILL.md"
ENVELOPE = {"ok": True, "result": {"records": [{"a": 1}]},
            "metadata": {"queryId": "q-123", "scannedRecords": 5, "executionTimeMilliseconds": 3}}


def text(t):
    return {"type": "text", "text": t}


def use(id_, name, **args):
    return {"type": "tool_use", "id": id_, "name": name, "input": args}


def scripted(*replies, seen=None):
    """A model that returns the given content-block lists in order, and records what it was sent."""
    queue = list(replies)

    def complete(system, messages, tools):
        if seen is not None:
            seen.append([dict(m) for m in messages])
        return {"content": queue.pop(0)}
    return complete


def agent(*replies, run_query=None, metadata="keep", seen=None):
    return la.LocalAgent("playground", "test-model", complete=scripted(*replies, seen=seen),
                         run_query=run_query or (lambda dql: ENVELOPE), metadata=metadata)


def test_read_document_serves_the_skill_and_nothing_else():
    body, is_error = la.read_document(SKILL)
    assert not is_error and body.startswith("---") and "\r" not in body
    for bad in ("/etc/passwd", "/resources/documents/skills/../../../README.md",
                "/resources/documents/skills/investigating-playground-incidents/references/nope.md"):
        assert la.read_document(bad)[1], bad


def test_write_dql_is_blocked_before_dtctl():
    def boom(dql):
        raise AssertionError("dtctl must not run")
    _, events = agent([use("1", "execute-dql", query="fetch logs | INGEST x")], [text("done")],
                      run_query=boom).invoke_agent(None, "demo-agent", "hi")
    assert events[-1]["content"][0]["text"] == "done"
    assert la.dql_blocked("fetch logs | limit 1") is None
    assert la.dql_blocked("fetch logs | DELETE")


def test_events_feed_the_runner_assertions():
    cid, events = agent(
        [text("Checking for open issues."), use("1", "read_file", file_path=SKILL),
         use("2", "execute-dql", query="fetch dt.davis.problems")],
        [text("Nothing open.")]).invoke_agent(None, "demo-agent", "any issues?")
    s = ev.summarize(events)
    assert s["reads"] == [SKILL] and s["dql_calls"] == 1
    assert s["reply"] == "Nothing open." and s["progress"] == ["Checking for open issues."]
    assert s["ends_on_text"]
    assert ev.check_turn(s, {"first_read_contains": "/SKILL.md", "requires_dql": True,
                             "reply_contains": ["Nothing open"], "max_progress_lines": 1}, {}) == []


def test_metadata_is_kept_or_stripped():
    for mode, expect in (("keep", True), ("strip", False)):
        seen = []
        agent([use("1", "execute-dql", query="fetch x")], [text("ok")], metadata=mode,
              seen=seen).invoke_agent(None, "demo-agent", "q")
        result = seen[1][-1]["content"][0]["content"]
        assert ("q-123" in result) is expect, (mode, result)
        assert '"a": 1' in result


def test_a_failed_query_reaches_the_model_as_an_error():
    seen = []
    agent([use("1", "execute-dql", query="fetch x")], [text("ok")],
          run_query=lambda dql: {"ok": False, "error": "no permission"}, seen=seen).invoke_agent(None, "a", "q")
    block = seen[1][-1]["content"][0]
    assert block["is_error"] and "no permission" in block["content"]


def test_the_conversation_carries_over_between_turns():
    seen = []
    a = agent([text("first")], [text("second")], seen=seen)
    cid, _ = a.invoke_agent(None, "demo-agent", "one")
    a.invoke_agent(None, "demo-agent", "two", cid)
    assert [m["role"] for m in seen[1]] == ["user", "assistant", "user"]
    assert seen[1][-1]["content"] == "two"


def test_parallel_tool_calls_are_all_answered():
    seen = []
    agent([use("1", "execute-dql", query="fetch a"), use("2", "execute-dql", query="fetch b")],
          [text("ok")], seen=seen).invoke_agent(None, "a", "q")
    ids = [b["tool_use_id"] for b in seen[1][-1]["content"]]
    assert ids == ["1", "2"]


def test_a_runaway_tool_loop_stops():
    loop = [[use(str(i), "read_file", file_path=SKILL)] for i in range(5)]
    a = la.LocalAgent("playground", "m", complete=scripted(*loop), max_rounds=3)
    try:
        a.invoke_agent(None, "a", "q")
    except RuntimeError as e:
        assert "did not finish" in str(e)
    else:
        raise AssertionError("expected the loop to stop")


def test_no_api_key_is_a_clear_error():
    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        la.AnthropicClient("m")
    except RuntimeError as e:
        assert "ANTHROPIC_API_KEY" in str(e)
    else:
        raise AssertionError("expected an error")
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved


def test_the_default_model_is_the_deployed_agents():
    assert la.default_model() == __import__("json").loads(
        la.TEMPLATE.read_text(encoding="utf-8"))["data"]["llm"]


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
