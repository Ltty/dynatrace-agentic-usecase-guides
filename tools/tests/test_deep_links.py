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
