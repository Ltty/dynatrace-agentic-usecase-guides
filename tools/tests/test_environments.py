#!/usr/bin/env python3
"""The environment registry is stated twice: once for the tools, once for the agent.

preflight.py holds it for the tools; session-protocol.md -> "Environments" states the same
thing for the agent, which cannot import Python. Nothing enforces that they agree, so this
does: a link host that drifts here produces deep links into the wrong tenant, silently.

Run: python tools/tests/test_environments.py
"""

import importlib.util
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SESSION_PROTOCOL = (REPO_ROOT / "dynatrace-intelligence" / "skills"
                    / "investigating-playground-incidents" / "references" / "session-protocol.md")


def load(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def environments_section() -> str:
    text = SESSION_PROTOCOL.read_text(encoding="utf-8")
    start = text.index("\n## Environments")
    end = text.index("\n## ", start + 1)
    return text[start:end]


def rows(section: str):
    """Every markdown table row in the section, as a list of stripped cells."""
    out = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        out.append([c.strip().strip("`") for c in line.strip("|").split("|")])
    return out


def parsed_tables():
    """(hosts, availability) as stated in the markdown."""
    body = rows(environments_section())
    hosts, avail, header = {}, {}, None
    for cells in body:
        if cells[0].lower() == "environment":
            header = None
            continue
        if cells[0].lower() == "scenario":
            header = [c for c in cells[1:]]
            continue
        if header is None:
            hosts[cells[0]] = cells[1]
        else:
            envs = {header[i] for i, c in enumerate(cells[1:]) if c}
            avail[cells[0]] = envs
    return hosts, avail


def test_link_hosts_match_the_registry():
    pf = load("preflight")
    hosts, _ = parsed_tables()
    assert hosts, "no environment table found under '## Environments'"
    assert set(hosts) == set(pf.ENVIRONMENTS), (sorted(hosts), sorted(pf.ENVIRONMENTS))
    for env, host in hosts.items():
        assert host == pf.host_of(env), (env, host, pf.host_of(env))


def test_availability_matches_the_registry():
    pf = load("preflight")
    _, avail = parsed_tables()
    assert avail, "no availability table found under '## Environments'"
    assert set(avail) == set(pf.SCENARIO_ENVIRONMENTS), (sorted(avail), sorted(pf.SCENARIO_ENVIRONMENTS))
    for scenario, envs in avail.items():
        assert envs == set(pf.SCENARIO_ENVIRONMENTS[scenario]), (
            scenario, sorted(envs), sorted(pf.SCENARIO_ENVIRONMENTS[scenario]))


def test_every_scenario_file_is_in_the_availability_table():
    validate = load("validate_dt_skill")
    _, avail = parsed_tables()
    assert set(avail) == set(validate.SCENARIO_FILES), (
        sorted(avail), sorted(validate.SCENARIO_FILES))


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_"):
            continue
        try:
            fn()
            print(f"  PASS {name}")
        except AssertionError as e:
            print(f"  FAIL {name}: {e}")
            failed += 1
    print()
    print("all passed" if not failed else f"{failed} failed")
    sys.exit(1 if failed else 0)
