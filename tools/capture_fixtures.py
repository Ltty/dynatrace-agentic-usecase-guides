#!/usr/bin/env python3
"""
capture_fixtures.py — capture beat-level fixtures from a live problem occurrence.

Currently only the resolver has a fixture (fixtures/problem.json); beats have none,
so a fixture-mode run has to improvise evidence for beats 2-5. This tool captures
every beat's evidence query output against a currently-live problem so fixture mode
is fully self-contained offline.

Usage:
  python tools/capture_fixtures.py <scenario-id>

Requires a live (or live_recent) problem to capture from — refuses to run in fixture
mode itself, since there'd be nothing fresh to capture.

Writes:
  scenarios/<id>/fixtures/problem.json       (resolver output — overwrites existing)
  scenarios/<id>/fixtures/<beat-file>.json   (one per evidence query, e.g.
                                               beat-04-failing-spans.json)
"""

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def _load_preflight():
    spec = importlib.util.spec_from_file_location("preflight", Path(__file__).parent / "preflight.py")
    preflight = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preflight)
    return preflight


def capture(scenario_id: str) -> int:
    preflight = _load_preflight()
    scenario_dir = REPO_ROOT / "scenarios" / scenario_id
    manifest_path = scenario_dir / "scenario.yaml"

    if not manifest_path.exists():
        print(f"ERROR: scenario '{scenario_id}' not found", file=sys.stderr)
        return 2

    import yaml
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    print(f"Resolving {scenario_id} against the live Playground...")
    exit_code, state = preflight.resolve_scenario(scenario_id, write_state=False, quiet=True)

    if state is None:
        print("ERROR: resolver failed entirely — nothing to capture from", file=sys.stderr)
        return 1

    mode = state.get("mode")
    if mode == "fixture":
        print(
            "ERROR: no live problem found in the last 24h — refusing to capture a fixture "
            "from a fixture. Try again when the problem pattern is active or recently closed.",
            file=sys.stderr,
        )
        return 1

    print(f"  mode={mode}, problem={state['problem']['display_id']}, "
          f"affected_users={state['problem'].get('affected_users')}")

    fixtures_dir = scenario_dir / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)

    # 1. Resolver fixture (re-capture, always fresh)
    resolver_query_rel = manifest["resolve"]["problem"]["query"]
    resolver_query_path = scenario_dir / resolver_query_rel
    ok, envelope, error_str = preflight.run_query_with_state(resolver_query_path, state)
    if ok:
        fallback_rel = manifest["resolve"]["problem"]["fallback"]
        fallback_path = scenario_dir / fallback_rel
        with open(fallback_path, "w") as f:
            json.dump(envelope, f, indent=2)
        print(f"  captured: {fallback_rel}")
    else:
        print(f"  FAILED: resolver fixture — {error_str}", file=sys.stderr)

    # 2. Every beat's evidence queries
    captured, failed = 0, 0
    for beat in manifest.get("beats", []):
        bid = beat.get("id", "?")
        for ev_rel in beat.get("evidence", []):
            ev_path = scenario_dir / ev_rel
            if not ev_path.exists():
                print(f"  SKIP: {ev_rel} (file not found)", file=sys.stderr)
                failed += 1
                continue

            ok, envelope, error_str = preflight.run_query_with_state(ev_path, state)
            if not ok:
                print(f"  FAILED: beats[{bid}] {ev_rel} — {error_str}", file=sys.stderr)
                failed += 1
                continue

            fixture_name = Path(ev_rel).stem + ".json"  # beat-04-failing-spans.dql -> .json
            fixture_path = fixtures_dir / fixture_name
            with open(fixture_path, "w") as f:
                json.dump(envelope, f, indent=2)
            n_records = len(envelope.get("result", {}).get("records", []))
            print(f"  captured: fixtures/{fixture_name} ({n_records} records)")
            captured += 1

    print(f"\nDone. {captured} beat fixtures captured, {failed} failed.")
    return 0 if failed == 0 else 1


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <scenario-id>", file=sys.stderr)
        sys.exit(2)
    sys.exit(capture(sys.argv[1]))


if __name__ == "__main__":
    main()
