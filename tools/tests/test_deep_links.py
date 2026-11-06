#!/usr/bin/env python3
"""
Tests for the deep links in the scenario files (offline, no tenant): every beat has a label,
and every link uses only tokens the session state can fill.

Exit 0 = all pass. Exit 1 = failures present.
"""

import importlib.util
import re
import sys
import traceback
from pathlib import Path

TOOLS = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("validate_dt_skill", TOOLS / "validate_dt_skill.py")
v = importlib.util.module_from_spec(spec)
sys.modules["validate_dt_skill"] = v
spec.loader.exec_module(v)

KNOWN_TOKENS = {"LINK_HOST", "ROOT_CAUSE_ID", "PROBLEM_SEGMENTS", "PROBLEM_ID", "TF_FROM_MS", "TF_TO_MS", "DQL_FROM", "DQL_TO", "TF_REL_H", "TF_FROM_ISO", "TF_TO_ISO"}


def test_every_beat_has_a_labelled_link():
    for scenario, path in v.SCENARIO_FILES.items():
        # a showcase's "## Extra" sections (offered after the close) carry a link too
        beats = len(re.findall(r"^## (?:Beat|Extra) ", path.read_text(encoding="utf-8"), re.M))
        links = v.deep_links(path)
        assert len(links) == beats, (scenario, beats, len(links))


def test_every_beat_says_why_it_exists():
    """A beat with no purpose line leaves the user asking "so what?" (testrun 16).

    The agent can only say why a step exists if the beat hands it the sentence. Objective
    describes the outcome for the author; it is not the reason, and it is not addressed to
    the user.
    """
    for scenario, path in v.SCENARIO_FILES.items():
        text = path.read_text(encoding="utf-8")
        sections = re.findall(r"^## (?:Beat \d+|Extra)[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        assert sections, scenario
        for body in sections:
            cut = body.find("**Objective:**")
            head = body[:cut] if cut >= 0 else body
            assert "**Why this step:**" in head, (
                scenario, "a beat is missing its 'Why this step' line before the Objective")

def test_every_beat_declares_what_it_requires():
    """Real options need a real graph: a beat is offered once its Requires are complete.

    Without this the agent either offers everything (a choice the argument cannot survive) or
    nothing (the ok-only path the modes collapsed into). The showcase is exempt: it is a
    presentation and orders itself with Tracks.
    """
    for scenario, path in v.SCENARIO_FILES.items():
        if scenario in v.SHOWCASES:
            continue
        text = path.read_text(encoding="utf-8")
        beats = re.findall(r"^## Beat (\d+) ", text, re.M)
        declared = re.findall(r"^\*\*Requires:\*\* (.+)$", text, re.M)
        assert len(declared) == len(beats), (scenario, len(beats), len(declared))
        for n, req in zip(beats, declared):
            if req.strip() == "none":
                continue
            for dep in re.findall(r"\d+", req):
                assert int(dep) < int(n), (scenario, f"beat {n} requires {dep}: not an earlier beat")
                assert dep in beats, (scenario, f"beat {n} requires {dep}: no such beat")
        assert declared[0].strip() == "none", (scenario, "beat 1 must require nothing")


def test_every_incident_proposes_an_approach():
    """Feedforward: the user should know the shape before the first query (conversation-craft).

    The showcase states its approach in its own register, so it is exempt; every incident
    carries an `approach` row in Business context, said once at beat 1.
    """
    for scenario, path in v.SCENARIO_FILES.items():
        if scenario in v.SHOWCASES:
            continue
        text = path.read_text(encoding="utf-8")
        assert "| `approach` |" in text, (scenario, "no `approach` row in Business context")


def test_every_discovery_hook_has_a_route():
    """A bullet is the hook plus its route; without one the openings read interchangeably.

    Parsed from the markdown table rather than a registry, because the survey may not open a
    scenario file (tests/evals/dt-agent/survey-live.yaml -> reads_exclude) and so the route has
    to live here.
    """
    text = v.SESSION_PROTOCOL.read_text(encoding="utf-8")
    table = text.split("**Discovery hooks.**", 1)[1]
    rows = [r for r in table.splitlines() if r.startswith("| `")]
    assert len(rows) >= 5, rows
    for row in rows:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        assert len(cells) == 4, (cells[0], "expected scenario | hook | route | notes")
        assert cells[2], (cells[0], "empty Route cell")


def test_links_use_known_tokens_only():
    for scenario, path in v.SCENARIO_FILES.items():
        for label, url in v.deep_links(path):
            unknown = set(re.findall(r"\{\{([A-Z_]+)\}\}", url)) - KNOWN_TOKENS
            assert not unknown, (scenario, label, unknown)


def test_labels_do_not_promise_the_same_view():
    for scenario, path in v.SCENARIO_FILES.items():
        for label, _ in v.deep_links(path):
            assert "same view" not in label.lower(), (scenario, label)


def test_no_label_called_replays():
    for scenario, path in v.SCENARIO_FILES.items():
        for label, _ in v.deep_links(path):
            assert "replay" not in label.lower(), (scenario, label)


def test_every_showcase_opens_on_what_it_is():
    """A picked tour must say what it is before its first table (user report, 2026-11-06).

    The opening told a user "First challenge: there is no single view" and a table, with no
    word on what the tour was or why it ran in that order. An incident has an `approach` row;
    a showcase has an "Opening" section that says the same thing at the length a tour needs.
    """
    for scenario in v.SHOWCASES:
        text = v.SCENARIO_FILES[scenario].read_text(encoding="utf-8")
        assert "## Opening" in text, (scenario, "no Opening section")
        body = text.split("## Opening", 1)[1].split("## Scope", 1)[0]
        for needed in ("What this is", "The through-line", "The route", "How it goes"):
            assert needed in body, (scenario, f"Opening is missing: {needed}")


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
