#!/usr/bin/env python3
"""
Tests for the per-step layout spec (offline, no tenant): every step of every scenario carries a **Show:** line
that says what its reply looks like, so the layout is not improvised.

    **Show:** Headline "What shipped just before it started". Table: Commit | First deployed (UTC) | Gap (min), 3-5 rows.
    Finding: the earliest deploy's gap. Bullets: lead suspect; what timing can say; later deploys.

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

STEP_RE = re.compile(r"(?m)^## ((?:Beat|Extra) .*)$")
SHOW_RE = re.compile(r"(?m)^\*\*Show:\*\*(.*(?:\n(?![*#`|\n]).*)*)")


def steps(path: Path) -> list[tuple[str, str]]:
    """(heading, body) of every Beat and Extra section."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    parts = re.split(r"(?m)^## ", text)
    return [(p.split("\n", 1)[0], p) for p in parts if re.match(r"(?:Beat|Extra) ", p)]


def shows(body: str) -> list[str]:
    return [" ".join(m.group(1).split()) for m in SHOW_RE.finditer(body)]


def test_every_step_has_a_show_line_before_its_reveal():
    for scenario, path in v.SCENARIO_FILES.items():
        for heading, body in steps(path):
            found = shows(body)
            assert found, (scenario, heading, "no **Show:** line")
            if "**Reveal:**" in body:
                assert body.index("**Show:**") < body.index("**Reveal:**"), (scenario, heading, "Show after Reveal")


def test_a_show_line_names_headline_table_finding_and_bullets():
    for scenario, path in v.SCENARIO_FILES.items():
        for heading, body in steps(path):
            for show in shows(body):
                for part in ('Headline "', "Table:", "Finding:", "Bullets:"):
                    assert part in show, (scenario, heading, f"Show lacks {part!r}")


def test_a_headline_is_a_short_subject_without_machinery():
    for scenario, path in v.SCENARIO_FILES.items():
        for heading, body in steps(path):
            for show in shows(body):
                headline = re.search(r'Headline "([^"]+)"', show).group(1)
                words = headline.split()
                assert 3 <= len(words) <= 7, (scenario, heading, headline, "3-7 words")
                assert not re.search(r"(?i)\bbeats?\b|\bstep\b|\d", headline), (scenario, heading, headline)


def test_a_table_has_two_to_five_columns():
    """A wider table does not fit a chat reply; trim the columns to what the finding needs."""
    for scenario, path in v.SCENARIO_FILES.items():
        for heading, body in steps(path):
            for show in shows(body):
                table = re.search(r"Table:\s*(.*?)\.\s*Finding:", show)
                assert table, (scenario, heading, "Table: ... Finding:")
                if table.group(1).lower().startswith("none"):
                    continue
                columns = table.group(1).count("|") + 1
                assert 2 <= columns <= 5, (scenario, heading, columns, "columns, expected 2-5")


def test_bullets_are_two_to_four_topics():
    for scenario, path in v.SCENARIO_FILES.items():
        for heading, body in steps(path):
            for show in shows(body):
                topics = [t for t in show.split("Bullets:", 1)[1].split(";") if t.strip(" .")]
                assert 2 <= len(topics) <= 4, (scenario, heading, len(topics), "2-4 bullet topics")


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
