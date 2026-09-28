#!/usr/bin/env python3
"""
validate_scenarios.py — scenario pack validator and (--live) execution gate.

Validates scenario packs against the JSON schema, checks referential integrity
(every path referenced in scenario.yaml must exist), and lints DQL files for
write/ingest constructs.

--live additionally EXECUTES every query in the scenario against the live
Playground (resolver + every beat's evidence queries, with placeholder
substitution) and asserts each returns ok:true. This is the standing gate
that makes it structurally impossible to ship a scenario with a query that
has never actually been run — the failure mode that cost the first test run
its naturalness (three query errors debugged live, in front of the user).

Usage:
  python tools/validate_scenarios.py                  # static checks, all scenarios
  python tools/validate_scenarios.py scenarios/foo     # static checks, one scenario
  python tools/validate_scenarios.py --strict          # exit 1 on any warning
  python tools/validate_scenarios.py --live            # static + execute every query
  python tools/validate_scenarios.py --live scenarios/foo
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed. Run: pip install pyyaml jsonschema", file=sys.stderr)
    sys.exit(1)

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema not installed. Run: pip install pyyaml jsonschema", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "scenarios" / "_schema" / "scenario.schema.json"
SCENARIOS_DIR = REPO_ROOT / "scenarios"
TEMPLATE_DIR = SCENARIOS_DIR / "_template"

# DQL constructs that must not appear in any query file
DQL_WRITE_PATTERNS = [
    r"\bINGEST\b", r"\bINSERT\b", r"\bUPDATE\b",
    r"\bDELETE\b", r"\bPUT\b", r"\bWRITE\b",
]

# Placeholder pattern in deep_link templates
PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")

# Known resolvable placeholders (set by tools/preflight.py at resolve time)
KNOWN_PLACEHOLDERS = {
    "PROBLEM_ID", "TIMEFRAME_FROM", "TIMEFRAME_TO",
    "DQL_TIMEFRAME_FROM", "DQL_TIMEFRAME_TO",
    "PAYMENT_FAILURE_PROBLEM",  # alias used in the source guide JSON
}

# Loaded lazily only when --live is used (avoids requiring dtctl for static checks)
_preflight = None


def _load_preflight():
    global _preflight
    if _preflight is None:
        spec = importlib.util.spec_from_file_location("preflight", Path(__file__).parent / "preflight.py")
        _preflight = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_preflight)
    return _preflight

errors: list[str] = []
warnings: list[str] = []


def err(msg: str):
    errors.append(f"  ERROR: {msg}")


def warn(msg: str):
    warnings.append(f"  WARN:  {msg}")


# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------

def load_schema() -> dict:
    with open(SCHEMA_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def validate_scenario_dir(scenario_dir: Path, schema: dict, live: bool = False) -> bool:
    """Validate one scenario directory. Returns True if no errors."""
    global errors, warnings
    errors = []
    warnings = []

    manifest_path = scenario_dir / "scenario.yaml"
    if not manifest_path.exists():
        print(f"\n[SKIP] {scenario_dir.name}: no scenario.yaml")
        return True  # Template or incomplete; not an error

    print(f"\n[CHECK] {scenario_dir.name}")

    # --- Load YAML ---
    try:
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
    except Exception as e:
        err(f"Cannot parse scenario.yaml: {e}")
        _report()
        return False

    # --- JSON Schema ---
    try:
        jsonschema.validate(manifest, schema)
    except jsonschema.ValidationError as e:
        err(f"Schema violation: {e.message} (path: {'.'.join(str(p) for p in e.path)})")
    except jsonschema.SchemaError as e:
        err(f"Schema itself is invalid: {e.message}")

    # --- ID matches directory ---
    if manifest.get("id") != scenario_dir.name:
        err(f"id '{manifest.get('id')}' does not match directory name '{scenario_dir.name}'")

    # --- Resolve paths ---
    resolve = manifest.get("resolve", {})
    problem = resolve.get("problem", {})
    _check_path(scenario_dir, problem.get("query", ""), "resolve.problem.query")
    _check_path(scenario_dir, problem.get("fallback", ""), "resolve.problem.fallback")

    # --- Beats ---
    for beat in manifest.get("beats", []):
        bid = beat.get("id", "?")
        for ev_path in beat.get("evidence", []):
            _check_path(scenario_dir, ev_path, f"beats[{bid}].evidence")
        deep_link = beat.get("deep_link", "")
        if deep_link:
            _validate_deep_link(deep_link, bid)

    # --- DQL lint ---
    queries_dir = scenario_dir / "queries"
    if queries_dir.exists():
        for dql_file in queries_dir.glob("*.dql"):
            _lint_dql(dql_file)

    # --- Fixtures exist ---
    fixtures_dir = scenario_dir / "fixtures"
    if not fixtures_dir.exists() or not any(fixtures_dir.glob("*.json")):
        warn("No fixtures found. Scenario will not work offline (fixture-mode fallback).")

    _report()
    static_ok = len(errors) == 0

    if not live:
        return static_ok

    # --- Live execution gate ---
    live_ok = _validate_live(scenario_dir, manifest)
    return static_ok and live_ok


def _validate_live(scenario_dir: Path, manifest: dict) -> bool:
    """Resolve the scenario live, then execute every query (resolver + all
    beat evidence) with placeholder substitution. Asserts each returns ok:true.
    """
    preflight = _load_preflight()
    scenario_id = scenario_dir.name

    print(f"  [LIVE] resolving {scenario_id}...")
    exit_code, state = preflight.resolve_scenario(scenario_id, write_state=False, quiet=True)
    if state is None:
        print(f"    ERROR: resolver failed entirely (exit {exit_code}) — cannot run live checks")
        return False

    mode = state.get("mode", "?")
    print(f"    resolved: mode={mode}, problem={state.get('problem', {}).get('display_id', '?')}")

    all_ok = True

    # Resolver query itself
    query_rel = manifest["resolve"]["problem"]["query"]
    query_path = scenario_dir / query_rel
    ok, envelope, error_str = preflight.run_query_with_state(query_path, state)
    if ok:
        print(f"    OK    {query_rel}")
    else:
        print(f"    ERROR {query_rel}: {error_str}")
        all_ok = False

    # Every beat's evidence queries
    for beat in manifest.get("beats", []):
        bid = beat.get("id", "?")
        for ev_rel in beat.get("evidence", []):
            ev_path = scenario_dir / ev_rel
            if not ev_path.exists():
                continue  # already reported as a static error
            ok, envelope, error_str = preflight.run_query_with_state(ev_path, state)
            if ok:
                n = len(envelope.get("result", {}).get("records", [])) if envelope else 0
                print(f"    OK    beats[{bid}] {ev_rel} ({n} records)")
            else:
                print(f"    ERROR beats[{bid}] {ev_rel}: {error_str}")
                all_ok = False

    return all_ok


def _check_path(base: Path, rel: str, field: str):
    if not rel:
        err(f"{field} is empty")
        return
    full = (base / rel).resolve()
    if not full.exists():
        try:
            display = full.relative_to(REPO_ROOT.resolve())
        except ValueError:
            display = full
        err(f"{field}: file not found: {display}")


def _validate_deep_link(url: str, beat_id: str):
    placeholders = set(PLACEHOLDER_RE.findall(url))
    unknown = placeholders - KNOWN_PLACEHOLDERS
    if unknown:
        warn(f"beats[{beat_id}].deep_link: unknown placeholders {unknown} — "
             f"add to KNOWN_PLACEHOLDERS in validate_scenarios.py if intentional")


def _lint_dql(dql_file: Path):
    content = dql_file.read_text(encoding="utf-8")
    for pattern in DQL_WRITE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            err(f"DQL write construct '{pattern}' found in {dql_file.name}")

    placeholders = set(PLACEHOLDER_RE.findall(content))
    unknown = placeholders - KNOWN_PLACEHOLDERS
    if unknown:
        warn(f"{dql_file.name}: unknown placeholders {unknown} — "
             f"add to KNOWN_PLACEHOLDERS in validate_scenarios.py if intentional")


def _report():
    for msg in errors:
        print(msg)
    for msg in warnings:
        print(msg)
    if not errors and not warnings:
        print("  OK")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    strict = "--strict" in sys.argv
    live = "--live" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    schema = load_schema()

    if args:
        targets = [Path(a) for a in args]
    else:
        targets = [
            d for d in SCENARIOS_DIR.iterdir()
            if d.is_dir() and d.name not in ("_schema", "_template") and not d.name.startswith(".")
        ]

    all_ok = True
    for target in targets:
        ok = validate_scenario_dir(target, schema, live=live)
        if not ok:
            all_ok = False

    print()
    if all_ok:
        if warnings and strict:
            print("RESULT: warnings present (strict mode) — fix before committing")
            sys.exit(1)
        print("RESULT: all checks passed")
        sys.exit(0)
    else:
        print("RESULT: validation failed — fix errors above before running /demo")
        sys.exit(1)


if __name__ == "__main__":
    main()
