#!/usr/bin/env python3
"""
preflight.py — Phase 0/2 gate tool and runtime resolver.

Two modes:
  python tools/preflight.py                        # connectivity + auth check
  python tools/preflight.py resolve payment-failure # resolve live problem + derive timeframe

Exit codes:
  0 = all checks passed (or live problem found)
  1 = check failed or problem not found (fixture fallback recommended)
  2 = usage error

Output (resolve mode): JSON to stdout — matches .demo-state.json shape.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DTCTL = "dtctl"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_dtctl(*args, capture=True) -> tuple[int, str]:
    cmd = [DTCTL, "--agent", "--plain"] + list(args)
    try:
        result = subprocess.run(
            cmd, capture_output=capture, text=True, timeout=30
        )
        return result.returncode, result.stdout
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, ""


def parse_envelope(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except Exception:
        # dtctl may emit YAML when -o auto picks it
        return None


def check(label: str, ok: bool, detail: str = ""):
    status = "OK  " if ok else "FAIL"
    line = f"[{status}] {label}"
    if detail:
        line += f" — {detail}"
    print(line)
    return ok


# ---------------------------------------------------------------------------
# Connectivity check
# ---------------------------------------------------------------------------

def check_connectivity() -> bool:
    all_ok = True
    print("=== dtctl preflight ===\n")

    # 1. dtctl installed
    rc, out = run_dtctl("version")
    version = out.strip().split("\n")[0] if rc == 0 else ""
    all_ok &= check("dtctl installed", rc == 0, version or "not found — run the devcontainer setup")

    if rc != 0:
        print("\nInstall dtctl: https://github.com/dynatrace-oss/dtctl")
        return False

    # 2. doctor
    rc, out = run_dtctl("doctor")
    doctor_ok = rc == 0 and "[FAIL]" not in out and "[WARN]" not in out
    # Extract the most relevant line
    lines = [l for l in out.splitlines() if "[OK]" in l or "[FAIL]" in l or "[WARN]" in l]
    summary = f"{len([l for l in lines if '[OK]' in l])} OK" + (
        f", {len([l for l in lines if '[FAIL]' in l])} FAIL" if "[FAIL]" in out else ""
    )
    all_ok &= check("dtctl doctor", doctor_ok, summary)

    if not doctor_ok:
        print("\n  Run: dtctl auth login --context playground "
              "--environment https://playground.apps.dynatrace.com")
        return False

    # 3. Safety level
    rc, out = run_dtctl("config", "describe-context", "playground")
    readonly = "readonly" in out.lower() if rc == 0 else False
    all_ok &= check("safety level = readonly", readonly,
                    "" if readonly else "run: dtctl config set-context playground --safety-level readonly")

    # 4. Quick DQL probe
    rc, out = run_dtctl("query", "fetch dt.davis.problems | limit 1 | fields event.id")
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

def resolve_scenario(scenario_id: str) -> int:
    scenario_dir = REPO_ROOT / "scenarios" / scenario_id
    manifest_path = scenario_dir / "scenario.yaml"

    if not manifest_path.exists():
        print(json.dumps({"error": f"scenario '{scenario_id}' not found"}))
        return 2

    # Load resolver query
    try:
        import yaml
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
    except Exception as e:
        print(json.dumps({"error": f"cannot load manifest: {e}"}))
        return 2

    query_rel = manifest["resolve"]["problem"]["query"]
    fallback_rel = manifest["resolve"]["problem"]["fallback"]
    query_path = scenario_dir / query_rel
    fallback_path = scenario_dir / fallback_rel

    if not query_path.exists():
        print(json.dumps({"error": f"resolver query not found: {query_path}"}))
        return 2

    # Run the live query
    rc, out = run_dtctl("query", "--file", str(query_path), "-o", "json", "--max-field-chars", "0")
    envelope = parse_envelope(out)

    if rc == 0 and envelope and envelope.get("ok"):
        records = envelope.get("result", {}).get("records", [])
        if records:
            rec = records[0]
            return _emit_state(scenario_id, rec, live=True)

    # Fallback to fixture
    if fallback_path.exists():
        try:
            with open(fallback_path) as f:
                fixture = json.load(f)
            fixture_records = fixture.get("result", {}).get("records", [])
            if fixture_records:
                # fixture records may be YAML-encoded string
                raw_records = fixture_records
                if isinstance(raw_records, str):
                    import yaml as _yaml
                    raw_records = _yaml.safe_load(raw_records) or []
                if raw_records:
                    rec = raw_records[0] if isinstance(raw_records, list) else raw_records
                    return _emit_state(scenario_id, rec, live=False)
        except Exception as e:
            print(json.dumps({"error": f"fixture load failed: {e}"}))
            return 1

    print(json.dumps({
        "error": "no live problem found and fixture load failed",
        "hint": "Capture a fresh fixture with: python tools/preflight.py capture payment-failure"
    }))
    return 1


def _emit_state(scenario_id: str, rec: dict, live: bool) -> int:
    problem_id = rec.get("problem_id", rec.get("event.id", ""))
    display_id = rec.get("display_id", "")
    started = rec.get("started", rec.get("event.start", ""))
    ended = rec.get("ended", rec.get("event.end", ""))
    status = rec.get("status", rec.get("event.status", "UNKNOWN"))

    # Derive timeframe: 30 min before start to 30 min after end (or now if still active)
    try:
        start_dt = datetime.fromisoformat(started.replace("Z", "+00:00")) if started else None
        end_dt = datetime.fromisoformat(ended.replace("Z", "+00:00")) if ended else datetime.now(timezone.utc)
        from datetime import timedelta
        tf_from = int((start_dt - timedelta(minutes=30)).timestamp() * 1000) if start_dt else None
        tf_to = int((end_dt + timedelta(minutes=30)).timestamp() * 1000)
        tf_from_str = str(tf_from) if tf_from else "now()-2h"
        tf_to_str = str(tf_to)
    except Exception:
        tf_from_str = "now()-2h"
        tf_to_str = "now()"

    state = {
        "scenario_id": scenario_id,
        "mode": "live" if live else "fixture",
        "resolved_at": datetime.now(timezone.utc).isoformat(),
        "problem": {
            "id": problem_id,
            "display_id": display_id,
            "status": status,
            "started": started,
            "ended": ended if ended else None,
        },
        "placeholders": {
            "PAYMENT_FAILURE_PROBLEM": problem_id,
            "TIMEFRAME_FROM": tf_from_str,
            "TIMEFRAME_TO": tf_to_str,
        },
        "beats_completed": [],
        "current_beat": 0,
        "session_started": datetime.now(timezone.utc).isoformat(),
    }

    print(json.dumps(state, indent=2))

    if not live:
        print("# NOTE: running in fixture mode — live problem not found in last 24h", file=sys.stderr)

    return 0 if live else 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    if not args or args[0] == "check":
        ok = check_connectivity()
        sys.exit(0 if ok else 1)

    if args[0] == "resolve" and len(args) >= 2:
        sys.exit(resolve_scenario(args[1]))

    print(f"Usage: {sys.argv[0]} [check|resolve <scenario-id>]", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
