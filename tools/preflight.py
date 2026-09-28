#!/usr/bin/env python3
"""
preflight.py — connectivity gate, live resolver, and query-substitution helper.

Modes:
  python tools/preflight.py                                   # connectivity + auth check
  python tools/preflight.py resolve <scenario-id> [--write]    # resolve live problem, derive timeframe
  python tools/preflight.py run-query <scenario-id> <dql-path> # substitute placeholders + execute

Exit codes:
  0 = all checks passed / live problem found
  1 = check failed / no live problem (fixture fallback used)
  2 = usage error

resolve output: JSON to stdout — the .demo-state.json shape.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
STATE_PATH = REPO_ROOT / ".demo-state.json"

# ---------------------------------------------------------------------------
# Auto-locate dtctl (handles new sessions where PATH wasn't updated yet)
# ---------------------------------------------------------------------------

def _find_dtctl() -> str:
    """Return the dtctl executable path, searching common install locations."""
    import shutil

    found = shutil.which("dtctl")
    if found:
        return found

    candidates = []
    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "")
        if local_app:
            candidates.append(os.path.join(local_app, "dtctl", "dtctl.exe"))
        candidates.append(os.path.expanduser(r"~\AppData\Local\dtctl\dtctl.exe"))
    else:
        candidates += [
            os.path.expanduser("~/.local/bin/dtctl"),
            "/usr/local/bin/dtctl",
            "/opt/homebrew/bin/dtctl",
        ]

    for c in candidates:
        if os.path.isfile(c):
            bin_dir = os.path.dirname(c)
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
            return c

    return "dtctl"


DTCTL = _find_dtctl()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_dtctl(*args, timeout=30):
    cmd = [DTCTL, "--agent", "--plain"] + list(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 127, "", "dtctl executable not found"
    except subprocess.TimeoutExpired:
        return 124, "", "dtctl call timed out"


def parse_envelope(raw: str):
    try:
        return json.loads(raw)
    except Exception:
        return None


def check(label: str, ok: bool, detail: str = ""):
    status = "OK  " if ok else "FAIL"
    line = f"[{status}] {label}"
    if detail:
        line += f" — {detail}"
    print(line)
    return ok


PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")


def substitute_placeholders(text: str, placeholders: dict) -> str:
    """Replace every {{KEY}} token in text with placeholders[KEY]. Raises on unknown key."""
    def _sub(m):
        key = m.group(1)
        if key not in placeholders:
            raise KeyError(f"unknown placeholder '{{{{{key}}}}}' — not in state placeholders")
        return str(placeholders[key])
    return PLACEHOLDER_RE.sub(_sub, text)


# ---------------------------------------------------------------------------
# Connectivity check
# ---------------------------------------------------------------------------

def check_connectivity() -> bool:
    all_ok = True
    print("=== dtctl preflight ===\n")

    rc, out, _ = run_dtctl("version")
    version = out.strip().split("\n")[0] if rc == 0 else ""
    location = f"at {DTCTL}" if rc == 0 and DTCTL != "dtctl" else ""
    detail = (f"{version} {location}".strip()) if rc == 0 else (
        "not found — Windows: $env:PATH += ';$env:LOCALAPPDATA\\dtctl'  "
        "| Linux/Mac: export PATH=$HOME/.local/bin:$PATH"
    )
    all_ok &= check("dtctl installed", rc == 0, detail)

    if rc != 0:
        print("\nInstall dtctl: https://github.com/dynatrace-oss/dtctl")
        return False

    rc, out, _ = run_dtctl("doctor")
    doctor_ok = rc == 0 and "[FAIL]" not in out and "[WARN]" not in out
    lines = [l for l in out.splitlines() if "[OK]" in l or "[FAIL]" in l or "[WARN]" in l]
    summary = f"{len([l for l in lines if '[OK]' in l])} OK" + (
        f", {len([l for l in lines if '[FAIL]' in l])} FAIL" if "[FAIL]" in out else ""
    )
    all_ok &= check("dtctl doctor", doctor_ok, summary)

    if not doctor_ok:
        print("\n  Run: dtctl auth login --context playground "
              "--environment https://playground.apps.dynatrace.com")
        return False

    rc, out, _ = run_dtctl("config", "describe-context", "playground")
    readonly = "readonly" in out.lower() if rc == 0 else False
    all_ok &= check("safety level = readonly", readonly,
                    "" if readonly else "run: dtctl config set-context playground --safety-level readonly")

    rc, out, _ = run_dtctl("query", "fetch dt.davis.problems | limit 1 | fields event.id")
    envelope = parse_envelope(out)
    dql_ok = rc == 0 and envelope and envelope.get("ok")
    all_ok &= check("DQL reachable (dt.davis.problems)", bool(dql_ok))

    print()
    if all_ok:
        print("Result: all checks passed — ready to /demo")
    else:
        print("Result: preflight failed — fix the issues above then re-run /demo-doctor")

    return all_ok


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

def _load_manifest(scenario_id: str):
    scenario_dir = REPO_ROOT / "scenarios" / scenario_id
    manifest_path = scenario_dir / "scenario.yaml"
    if not manifest_path.exists():
        return None, None
    import yaml
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    return scenario_dir, manifest


def resolve_scenario(scenario_id: str, write_state: bool = False, quiet: bool = False):
    """Resolve a scenario's live problem state.

    Returns (exit_code, state_dict_or_None). exit_code 0 = live, 1 = fixture/failure,
    2 = usage error. When quiet=True, suppresses the stdout JSON dump (for programmatic
    callers like validate_scenarios.py --live) but still returns the state dict.
    """
    scenario_dir, manifest = _load_manifest(scenario_id)
    if manifest is None:
        msg = {"error": f"scenario '{scenario_id}' not found"}
        if not quiet:
            print(json.dumps(msg))
        return 2, None

    query_rel = manifest["resolve"]["problem"]["query"]
    fallback_rel = manifest["resolve"]["problem"]["fallback"]
    query_path = scenario_dir / query_rel
    fallback_path = scenario_dir / fallback_rel

    if not query_path.exists():
        msg = {"error": f"resolver query not found: {query_path}"}
        if not quiet:
            print(json.dumps(msg))
        return 2, None

    rc, out, _ = run_dtctl("query", "--file", str(query_path), "-o", "json", "--max-field-chars", "0")
    envelope = parse_envelope(out)

    if rc == 0 and envelope and envelope.get("ok"):
        records = envelope.get("result", {}).get("records", [])
        if records:
            rec = records[0]
            return _emit_state(scenario_id, rec, live=True, write_state=write_state, quiet=quiet)

    if fallback_path.exists():
        try:
            with open(fallback_path) as f:
                fixture = json.load(f)
            fixture_records = fixture.get("result", {}).get("records", [])
            raw_records = fixture_records
            if isinstance(raw_records, str):
                import yaml as _yaml
                raw_records = _yaml.safe_load(raw_records) or []
            if raw_records:
                rec = raw_records[0] if isinstance(raw_records, list) else raw_records
                return _emit_state(scenario_id, rec, live=False, write_state=write_state, quiet=quiet)
        except Exception as e:
            msg = {"error": f"fixture load failed: {e}"}
            if not quiet:
                print(json.dumps(msg))
            return 1, None

    msg = {
        "error": "no live problem found and fixture load failed",
        "hint": f"Capture a fixture with: python tools/capture_fixtures.py {scenario_id}"
    }
    if not quiet:
        print(json.dumps(msg))
    return 1, None


def _emit_state(scenario_id: str, rec: dict, live: bool, write_state: bool = False, quiet: bool = False):
    problem_id = rec.get("problem_id", rec.get("event.id", ""))
    display_id = rec.get("display_id", "")
    started = rec.get("started", rec.get("event.start", ""))
    ended = rec.get("ended", rec.get("event.end", ""))
    status = rec.get("status", rec.get("event.status", "UNKNOWN"))
    affected_users = rec.get("affected_users", rec.get("dt.davis.affected_users_count", ""))

    # Derive the incident window: 15 min padding either side of the problem's
    # own start/end. If still active (no ended), pad to now().
    start_dt = end_dt = None
    try:
        if started:
            start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(ended.replace("Z", "+00:00")) if ended else datetime.now(timezone.utc)
    except Exception:
        pass

    if start_dt:
        window_from_dt = start_dt - timedelta(minutes=15)
        window_to_dt = end_dt + timedelta(minutes=15)
        # Epoch-ms — used in Dynatrace app deep-link URLs (tf=FROM;TO)
        tf_from_ms = str(int(window_from_dt.timestamp() * 1000))
        tf_to_ms = str(int(window_to_dt.timestamp() * 1000))
        # ISO8601 — used inside DQL query text (from: "...", to: "...")
        dql_from = window_from_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        dql_to = window_to_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        # No resolvable start time — widest safe fallback
        tf_from_ms, tf_to_ms = "now()-2h", "now()"
        dql_from, dql_to = "now()-2h", "now()"

    # Three-state mode: live_active (still firing), live_recent (closed but
    # queryable — the common case), fixture (nothing live in the last 24h).
    if not live:
        mode = "fixture"
    elif status == "ACTIVE" or not ended:
        mode = "live_active"
    else:
        mode = "live_recent"

    state = {
        "scenario_id": scenario_id,
        "mode": mode,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "problem": {
            "id": problem_id,
            "display_id": display_id,
            "status": status,
            "started": started,
            "ended": ended if ended else None,
            "affected_users": affected_users,
        },
        "placeholders": {
            "PAYMENT_FAILURE_PROBLEM": problem_id,
            "TIMEFRAME_FROM": tf_from_ms,
            "TIMEFRAME_TO": tf_to_ms,
            "DQL_TIMEFRAME_FROM": dql_from,
            "DQL_TIMEFRAME_TO": dql_to,
        },
        "beats_completed": [],
        "current_beat": 0,
        "session_started": datetime.now(timezone.utc).isoformat(),
    }

    if not quiet:
        print(json.dumps(state, indent=2))

    if write_state:
        with open(STATE_PATH, "w") as f:
            json.dump(state, f, indent=2)
        if not quiet:
            print(f"# state written to {STATE_PATH}", file=sys.stderr)

    if mode == "fixture" and not quiet:
        print("# NOTE: running in fixture mode — no live problem in last 24h", file=sys.stderr)

    return (0 if live else 1), state


# ---------------------------------------------------------------------------
# Query runner — substitutes placeholders from .demo-state.json, executes
# ---------------------------------------------------------------------------

def run_query_with_state(dql_path: Path, state: dict):
    """Substitute placeholders from state and execute. Returns (ok, envelope_or_None, error_str)."""
    dql_text = dql_path.read_text(encoding="utf-8")
    try:
        substituted = substitute_placeholders(dql_text, state.get("placeholders", {}))
    except KeyError as e:
        return False, None, str(e)

    rc, out, err = run_dtctl("query", substituted, "-o", "json", "--max-field-chars", "0")
    if rc != 0:
        return False, None, f"dtctl query failed (exit {rc}): {err}"

    envelope = parse_envelope(out)
    if not envelope or not envelope.get("ok"):
        error_detail = envelope.get("error", {}) if envelope else {"message": "unparseable output"}
        return False, envelope, f"query returned ok=false: {error_detail}"

    return True, envelope, ""


def run_query_with_fixture_fallback(dql_path: Path, state: dict):
    """Like run_query_with_state, but if state['mode'] == 'fixture' and a matching
    fixture file exists (fixtures/<dql-stem>.json — see tools/capture_fixtures.py),
    returns the captured fixture instead of calling dtctl live. Falls through to a
    live attempt if no matching fixture exists yet.
    """
    if state.get("mode") == "fixture":
        scenario_id = state.get("scenario_id", "")
        fixture_path = REPO_ROOT / "scenarios" / scenario_id / "fixtures" / (dql_path.stem + ".json")
        if fixture_path.exists():
            try:
                with open(fixture_path) as f:
                    envelope = json.load(f)
                return True, envelope, ""
            except Exception as e:
                return False, None, f"fixture load failed ({fixture_path.name}): {e}"
    return run_query_with_state(dql_path, state)


def run_query(scenario_id: str, dql_rel_path: str) -> int:
    scenario_dir = REPO_ROOT / "scenarios" / scenario_id
    dql_path = scenario_dir / dql_rel_path
    if not dql_path.exists():
        print(json.dumps({"error": f"query file not found: {dql_path}"}))
        return 2

    if not STATE_PATH.exists():
        print(json.dumps({"error": "no .demo-state.json — run resolve first"}))
        return 2

    with open(STATE_PATH) as f:
        state = json.load(f)

    ok, envelope, error_str = run_query_with_fixture_fallback(dql_path, state)
    if not ok:
        print(json.dumps({"error": error_str}))
        return 1

    print(json.dumps(envelope))
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    if not args or args[0] == "check":
        ok = check_connectivity()
        sys.exit(0 if ok else 1)

    if args[0] == "resolve" and len(args) >= 2:
        write_state = "--write" in args
        exit_code, _ = resolve_scenario(args[1], write_state=write_state)
        sys.exit(exit_code)

    if args[0] == "run-query" and len(args) >= 3:
        sys.exit(run_query(args[1], args[2]))

    print(f"Usage: {sys.argv[0]} [check|resolve <scenario-id> [--write]|run-query <scenario-id> <dql-path>]",
          file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
