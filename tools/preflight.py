#!/usr/bin/env python3
"""
preflight.py — connectivity gate, live resolver, and query-substitution helper.

Modes:
  python tools/preflight.py                                   # connectivity + auth check
  python tools/preflight.py resolve <scenario-id> [--write]    # resolve live problem, derive timeframe
  python tools/preflight.py run-query <scenario-id> <dql-path> [--var KEY=VALUE ...] [--render waterfall]

Exit codes:
  0 = all checks passed / live problem found
  1 = check failed / no live problem found (Playground is quiet)
  2 = usage error

resolve output: JSON to stdout — the .demo-state.json shape.
"""

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
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
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
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


def _extract_dql_snippet(dql: str, max_lines: int = 4) -> list:
    """Extract the most meaningful lines from a DQL query for display."""
    lines = [l.rstrip() for l in dql.splitlines() if l.strip()]
    important = []
    rest = []
    for l in lines:
        s = l.strip()
        if s.startswith("fetch ") or s.startswith("| filter ") or s.startswith("| summarize "):
            important.append(l)
        elif not s.startswith("//"):
            rest.append(l)

    snippet = (important + rest)[:max_lines]
    leftover = len(important + rest) - max_lines
    if leftover > 0:
        snippet.append(f"    ... ({leftover} more lines)")
    return snippet


def _print_proof_stamp(dql: str, envelope: dict):
    """Print DQL snippet + liveness proof to stderr after a successful query."""
    snippet = _extract_dql_snippet(dql)
    meta = envelope.get("metadata", {})
    ctx = envelope.get("context", {})

    qid = meta.get("queryId", "")
    qid_short = qid[:8] if qid else "?"

    scanned_bytes = meta.get("scannedBytes", 0)
    elapsed_ms = meta.get("executionTimeMilliseconds", "?")
    total = ctx.get("total", "?")

    if isinstance(scanned_bytes, int) and scanned_bytes > 0:
        scanned_str = f"{scanned_bytes / 1_000_000:.0f}MB"
    else:
        scanned_str = "?"

    proof = f">> live - queryId {qid_short} - {total} records - {scanned_str} scanned - {elapsed_ms}ms"

    max_len = max((len(l) for l in snippet), default=0)
    w = min(72, max(60, max_len + 4, len(proof) + 4))
    bar = "-" * w

    print(bar, file=sys.stderr)
    for l in snippet:
        print(l, file=sys.stderr)
    print(proof, file=sys.stderr)
    print(bar, file=sys.stderr)


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
        print("\n  Run: python tools/preflight.py login")
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

    Returns (exit_code, state_dict_or_None). exit_code 0 = live problem found,
    1 = no live problem (Playground quiet), 2 = usage error.
    When quiet=True, suppresses the stdout JSON dump but still returns the state dict.
    """
    scenario_dir, manifest = _load_manifest(scenario_id)
    if manifest is None:
        msg = {"error": f"scenario '{scenario_id}' not found"}
        if not quiet:
            print(json.dumps(msg))
        return 2, None

    query_rel = manifest["resolve"]["problem"]["query"]
    query_path = scenario_dir / query_rel

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
            return _emit_state(scenario_id, rec, write_state=write_state, quiet=quiet)

    msg = {
        "status": "no_live_problem",
        "message": (
            f"Playground is quiet — no live problem matching scenario '{scenario_id}' "
            f"in the last 48 hours. This pattern typically fires twice daily; "
            f"try again shortly or check /demo-doctor."
        ),
    }
    if not quiet:
        print(json.dumps(msg, indent=2))
    return 1, None


def _emit_state(scenario_id: str, rec: dict, write_state: bool = False, quiet: bool = False):
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

    mode = "live_active" if (status == "ACTIVE" or not ended) else "live_recent"

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

    return 0, state


# ---------------------------------------------------------------------------
# Query runner — substitutes placeholders from .demo-state.json, executes
# ---------------------------------------------------------------------------

def run_query_with_state(dql_path: Path, state: dict, extra_vars: dict = None):
    """Substitute placeholders from state (plus any extra_vars, e.g. a chained-in
    TRACE_ID discovered from a prior query) and execute. Prints a DQL snippet +
    liveness proof stamp to stderr after each successful call.
    Returns (ok, envelope_or_None, error_str).
    """
    dql_text = dql_path.read_text(encoding="utf-8")
    placeholders = dict(state.get("placeholders", {}))
    if extra_vars:
        placeholders.update(extra_vars)
    try:
        substituted = substitute_placeholders(dql_text, placeholders)
    except KeyError as e:
        return False, None, str(e)

    rc, out, err = run_dtctl(
        "query", substituted, "-o", "json", "--max-field-chars", "0", "-M=all"
    )
    if rc != 0:
        return False, None, f"dtctl query failed (exit {rc}): {err}"

    envelope = parse_envelope(out)
    if not envelope or not envelope.get("ok"):
        error_detail = envelope.get("error", {}) if envelope else {"message": "unparseable output"}
        return False, envelope, f"query returned ok=false: {error_detail}"

    _print_proof_stamp(substituted, envelope)

    return True, envelope, ""


def run_query(scenario_id: str, dql_rel_path: str, extra_vars: dict = None,
              render: str = None) -> int:
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

    ok, envelope, error_str = run_query_with_state(dql_path, state, extra_vars)
    if not ok:
        print(json.dumps({"error": error_str}))
        return 1

    if render == "waterfall":
        renderer = REPO_ROOT / "tools" / "render_waterfall.py"
        if renderer.exists():
            proc = subprocess.run(
                [sys.executable, str(renderer)],
                input=json.dumps(envelope),
                capture_output=True, text=True, encoding="utf-8"
            )
            if proc.returncode == 0:
                print(proc.stdout)
                return 0
            # Renderer failed — fall through to raw JSON
            print(f"# waterfall render failed: {proc.stderr.strip()}", file=sys.stderr)

    print(json.dumps(envelope))
    return 0


def _parse_var_flags(args) -> dict:
    """Parse repeatable --var KEY=VALUE flags from a CLI arg list."""
    result = {}
    i = 0
    while i < len(args):
        if args[i] == "--var" and i + 1 < len(args):
            kv = args[i + 1]
            if "=" not in kv:
                raise ValueError(f"--var must be KEY=VALUE, got: {kv}")
            key, _, value = kv.partition("=")
            result[key] = value
            i += 2
        else:
            i += 1
    return result


# ---------------------------------------------------------------------------
# Codespace login helper
# ---------------------------------------------------------------------------

def _in_container() -> bool:
    return bool(
        os.environ.get("CODESPACES")
        or os.environ.get("REMOTE_CONTAINERS")
        or os.path.exists("/.dockerenv")
    )


def _normalize_callback(pasted: str) -> str:
    """Accept any URL the browser shows after a failed callback; rebuild as
    http://127.0.0.1:3232/auth/login?... Raises ValueError if 'code' is absent."""
    pasted = pasted.strip()

    # Bare query string: ?state=...&code=...
    if pasted.startswith("?"):
        pasted = "http://127.0.0.1:3232/auth/login" + pasted

    parsed = urllib.parse.urlparse(pasted)
    qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)

    if "code" not in qs:
        raise ValueError("no 'code' parameter found in pasted URL — copy the full browser URL")

    # Reconstruct against the local dtctl server regardless of what host was in the paste
    path = parsed.path or "/auth/login"
    rebuilt = urllib.parse.urlunparse(("http", "127.0.0.1:3232", path, "", parsed.query, ""))
    return rebuilt


def _replay_callback(url: str):
    """Deliver the callback URL to the dtctl server running on 127.0.0.1:3232.
    An HTTPError still means the request was received — treat it as success."""
    try:
        urllib.request.urlopen(url, timeout=10)
    except urllib.error.HTTPError:
        pass  # dtctl consumed the request; a non-2xx reply is expected


def codespace_login():
    """Run dtctl auth login with an optional paste-back relay.

    Works in all environments. In a Codespace the browser callback to
    127.0.0.1:3232 cannot reach the container; the user pastes the failed
    redirect URL here and we replay it via urllib into the still-running
    dtctl process. On a local machine the browser callback succeeds on its
    own and the user just presses Enter.
    """
    cmd = [
        DTCTL,
        "--no-agent",  # suppress JSON envelope when CLAUDECODE env var is set
        "auth", "login",
        "--context", "playground",
        "--environment", "https://playground.apps.dynatrace.com",
        "--safety-level", "readonly",
        "--timeout", "10m",
    ]

    print("Starting Dynatrace Playground authentication...\n")

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,  # prevent dtctl from stealing terminal stdin
        # stdout and stderr inherited so the user sees the SSO URL
    )

    print("\n--- After SSO in the browser ---")
    print("  Codespace: the browser shows a connection error. Copy the URL from the")
    print("  address bar and paste it here, then press Enter.")
    print("  Local machine: auth completed in the browser. Just press Enter.")
    print()

    try:
        pasted = sys.stdin.readline().strip()
    except (EOFError, KeyboardInterrupt):
        proc.terminate()
        print("\nCancelled.")
        return

    if pasted:
        try:
            callback_url = _normalize_callback(pasted)
        except ValueError as e:
            proc.terminate()
            print(f"\nError: {e}")
            sys.exit(1)

        print("Replaying callback to dtctl... ", end="", flush=True)
        try:
            _replay_callback(callback_url)
            print("done.")
        except Exception as e:
            print(f"failed: {e}")
            proc.terminate()
            sys.exit(1)

    # Give dtctl time to finish the token exchange and exit; terminate if it hangs.
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print("\nAuthentication complete. Run 'python tools/preflight.py check' to verify.")

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
        render = None
        remaining = args[3:]
        if "--render" in remaining:
            idx = remaining.index("--render")
            if idx + 1 < len(remaining):
                render = remaining[idx + 1]
                remaining = remaining[:idx] + remaining[idx + 2:]
        try:
            extra_vars = _parse_var_flags(remaining)
        except ValueError as e:
            print(json.dumps({"error": str(e)}))
            sys.exit(2)
        sys.exit(run_query(args[1], args[2], extra_vars=extra_vars or None, render=render))

    if args[0] == "login":
        codespace_login()
        sys.exit(0)

    print(f"Usage: {sys.argv[0]} [check|resolve <scenario-id> [--write]|"
          f"run-query <scenario-id> <dql-path> [--var KEY=VALUE ...] [--render waterfall]|login]",
          file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
