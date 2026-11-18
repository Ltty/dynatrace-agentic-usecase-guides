#!/usr/bin/env python3
"""
Tests for the in-app demo offers (offline, no tenant): the offering-live-demos skill must name every app
that a scenario's beats link into, only name scenarios that exist, and carry each app ID in its
description, since the description is what triggers it.

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

SKILL_DIR = v.SKILLS_DIR / "offering-live-demos"
APP_ID_RE = re.compile(r"[a-z][a-z0-9]*(?:\.[a-z0-9]+)+")


def offers() -> dict[str, set[str]]:
    """{app id: scenarios offered} from the table in references/app-offers.md."""
    text = (SKILL_DIR / "references" / "app-offers.md").read_text(encoding="utf-8")
    table: dict[str, set[str]] = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 2 or not line.lstrip().startswith("|"):
            continue
        apps = [t for t in re.findall(r"`([^`]+)`", cells[0]) if APP_ID_RE.fullmatch(t)]
        scenarios = set(re.findall(r"`([a-z][a-z0-9-]*)`", cells[1]))
        for app in apps:
            table.setdefault(app, set()).update(scenarios)
    return table


def description() -> str:
    front = v_front(SKILL_DIR / "SKILL.md")
    return front.get("description", "")


def v_front(path: Path) -> dict[str, str]:
    spec_ = importlib.util.spec_from_file_location("dt_agent", TOOLS / "dt_agent.py")
    mod = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(mod)
    return mod.parse_frontmatter(path.read_bytes().decode("utf-8").replace("\r\n", "\n")) or {}


def test_every_scenario_is_offered_from_each_app_its_beats_link_into():
    table = offers()
    for scenario, path in v.SCENARIO_FILES.items():
        linked = {a for _, url in v.deep_links(path) for a in re.findall(r"/ui/apps/([a-z0-9.]+)/", url)}
        missing = {a for a in linked if scenario not in table.get(a, set())}
        assert not missing, (scenario, "linked app has no offer row for it", sorted(missing))


def test_every_offered_scenario_exists():
    for app, scenarios in offers().items():
        unknown = scenarios - set(v.SCENARIO_FILES)
        assert not unknown, (app, sorted(unknown))


def test_every_offered_app_is_in_the_description():
    desc = description()
    for app in offers():
        assert app in desc, (app, "missing from the SKILL.md description, so it never triggers")


def test_the_description_names_no_app_without_an_offer():
    table = offers()
    for app in set(APP_ID_RE.findall(description())):
        if app.startswith(("dynatrace.", "community.")):
            assert app in table, (app, "in the description but has no offer row")


TRIGGERS = (SKILL_DIR / "references" / "triggers.md").read_text(encoding="utf-8")
SKILL_TEXT = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def trigger_ids():
    return re.findall(r"^\| `(T-[a-z0-9-]+)` \|", TRIGGERS, re.M)


def examples(trigger):
    """(offer, do_not_offer) bullet lists under '### <trigger>' in triggers.md."""
    section = re.search(rf"^### {re.escape(trigger)}\n(.*?)(?=^### |\Z)", TRIGGERS, re.M | re.S).group(1)
    offer, _, rest = section.partition("Do not offer:")
    bullets = lambda text: [b for b in re.findall(r"^- (.+)$", text, re.M)]
    return bullets(offer.split("Offer:", 1)[-1]), bullets(rest)


def test_there_are_triggers_and_each_has_synthetic_examples_both_ways():
    ids = trigger_ids()
    assert ids, "no trigger rows found in references/triggers.md"
    for trigger in ids:
        offer, never = examples(trigger)
        assert len(offer) >= 5, (trigger, "needs at least 5 prompts it should fire on", len(offer))
        assert len(never) >= 5, (trigger, "needs at least 5 prompts it must not fire on", len(never))


def test_the_skill_names_every_trigger_and_the_description_fits():
    for trigger in trigger_ids():
        assert trigger in SKILL_TEXT, f"SKILL.md never mentions {trigger}"
    description = " ".join(re.search(r"description: >\n(.*?)\n---", SKILL_TEXT, re.S).group(1).split())
    assert len(description) <= 1024, f"description is {len(description)} characters; a skill description is capped at 1024"


def test_the_blocks_every_trigger_shares_are_all_there():
    blocks = TRIGGERS.split("## Never offer when", 1)[1].split("## Examples", 1)[0].lower()
    for needle in ("preset button", "mid-task", "reply", "documentation", "cloud costs", "already made"):
        assert needle in blocks, f"the 'never offer when' list lost: {needle}"


def test_no_example_in_triggers_looks_like_a_real_prompt():
    """The examples are written by us. A placeholder, an email or an id would mean one was pasted from data."""
    assert not re.search(r"<(?:email|url|id)>", TRIGGERS)
    assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}", TRIGGERS)


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
