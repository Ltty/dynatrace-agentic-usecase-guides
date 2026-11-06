#!/usr/bin/env python3
"""
Tests for the agent template check in dt_agent.py (offline, no tenant, no token).

The check must refuse a template that leaves a skill directory unmounted: the agent could not
read that skill, and nothing else would notice.

Exit 0 = all pass. Exit 1 = failures present.
"""

import importlib.util
import json
import sys
import tempfile
import traceback
from pathlib import Path

TOOLS = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("dt_agent", TOOLS / "dt_agent.py")
dt = importlib.util.module_from_spec(spec)
sys.modules["dt_agent"] = dt
spec.loader.exec_module(dt)

TEMPLATE = json.loads((dt.AGENT_DIR / "template.json").read_text(encoding="utf-8"))
SKILLS = [d.name for d in dt.skill_dirs()]


def errors_for(mutate):
    template = json.loads(json.dumps(TEMPLATE))
    mutate(template["data"])
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "template.json"
        path.write_text(json.dumps(template), encoding="utf-8")
        return dt.check_template(path)


def test_the_shipped_template_passes():
    assert dt.check_template() == []


def test_there_is_more_than_one_skill_to_mount():
    assert len(SKILLS) >= 2, SKILLS


def test_an_unmounted_skill_is_refused():
    only_first = f"documents://name starts-with '/skills/{SKILLS[0]}/'"
    out = errors_for(lambda d: d["resources"].update({"/resources/documents/": only_first}))
    assert any(SKILLS[1] in e and "mount" in e for e in out), out


def test_an_unlisted_skill_is_refused():
    out = errors_for(lambda d: d.update({"skills": d["skills"][:1]}))
    assert any("data.skills must list" in e for e in out), out


def test_a_mount_for_a_skill_that_does_not_exist_is_refused():
    ghost = TEMPLATE["data"]["resources"]["/resources/documents/"] + " or name starts-with '/skills/no-such-skill/'"
    out = errors_for(lambda d: d["resources"].update({"/resources/documents/": ghost}))
    assert any("no-such-skill" in e for e in out), out


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
