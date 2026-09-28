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


def substitute_placeholders(text: str, placeholders: dict,
                            pass_through_unknown: bool = False) -> str:
    """Replace every {{KEY}} token in text with placeholders[KEY].
    With pass_through_unknown=True, unknown keys are left as {{KEY}} instead of raising.
    """
    def _sub(m):
        key = m.group(1)
        if key not in placeholders:
            if pass_through_unknown:
                return m.group(0)
            raise KeyError(f"unknown placeholder '{{{{{key}}}}}'  — not in state placeholders")
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
# Query pre-loader — substitutes placeholders at session start
# ---------------------------------------------------------------------------

def _dql_to_single_line(dql: str) -> str:
    """Strip // comments and collapse a multi-line DQL query to one line.
    DQL is whitespace-insensitive so this is always safe.
    """
    parts = []
    for line in dql.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("//"):
            parts.append(stripped)
    return " ".join(parts)


def load_queries(scenario_id: str) -> int:
    """Pre-substitute all beat queries for a scenario and emit as a JSON dict.

    Each entry: {relative_path: single_line_dql}.  State placeholders
    (TIMEFRAME_FROM, PAYMENT_FAILURE_PROBLEM, etc.) are substituted; runtime-only
    placeholders like {{TRACE_ID}} are left as-is for the engine to fill later.
    The engine calls this once at session start and holds the dict in context,
    then runs dtctl query directly per beat.
    """
    scenario_dir = REPO_ROOT / "scenarios" / scenario_id
    if not scenario_dir.exists():
        print(json.dumps({"error": f"scenario '{scenario_id}' not found"}))
        return 2
    if not STATE_PATH.exists():
        print(json.dumps({"error": "no .demo-state.json — run resolve first"}))
        return 2

    with open(STATE_PATH) as f:
        state = json.load(f)

    placeholders = state.get("placeholders", {})
    queries_dir = scenario_dir / "queries"
    result = {}

    for dql_path in sorted(queries_dir.glob("*.dql")):
        rel = "queries/" + dql_path.name
        try:
            raw = dql_path.read_text(encoding="utf-8")
            substituted = substitute_placeholders(raw, placeholders, pass_through_unknown=True)
            result[rel] = _dql_to_single_line(substituted)
        except Exception as e:
            result[rel] = f"ERROR: {e}"

    print(json.dumps(result, indent=2))
    return 0


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
    """Wizard-style dtctl auth login with paste-back relay for Codespace environments."""
    import threading

    cmd = [
        DTCTL,
        "--no-agent",  # suppress JSON envelope when CLAUDECODE env var is set
        "auth", "login",
        "--context", "playground",
        "--environment", "https://playground.apps.dynatrace.com",
        "--safety-level", "readonly",
        "--timeout", "10m",
    ]

    print()
    print("  Dynatrace Playground Sign-In")
    print("  " + "-" * 40)
    print()

    # Pipe stdout+stderr so we can extract the SSO URL in real time.
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    sso_url_ready = threading.Event()
    shared = {"sso_url": None}

    def _read_output():
        want_url = False
        for raw in proc.stdout:
            line = raw.rstrip()
            if "please visit:" in line.lower():
                want_url = True
            elif want_url and line.startswith("https://"):
                shared["sso_url"] = line
                sso_url_ready.set()
                want_url = False

    threading.Thread(target=_read_output, daemon=True).start()

    # Wait up to 15 s for dtctl to emit the SSO URL, then show it.
    sso_url_ready.wait(timeout=15)

    print("Step 1 — Open this URL in your browser and sign in:")
    print()
    if shared["sso_url"]:
        print(f"  {shared['sso_url']}")
    else:
        print("  (copy the URL dtctl printed above)")
    print()
    print("  No account? https://www.dynatrace.com/signup/playground/")
    print()
    print("Step 2 — After sign-in, the browser redirects to localhost:3232.")
    print("  • Connection error in browser → copy that URL and paste it below.")
    print("  • Auth completed silently (VS Code forwarded the port) → press Enter.")
    print()
    sys.stdout.write("  Paste URL or press Enter → ")
    sys.stdout.flush()

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
        sys.stdout.write("\n  Completing authentication... ")
        sys.stdout.flush()
        try:
            _replay_callback(callback_url)
            print("done.")
        except Exception as e:
            print(f"failed: {e}")
            proc.terminate()
            sys.exit(1)

    # Give dtctl time to wrap up the token exchange; terminate if it hangs.
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print()
    print("  " + "-" * 40)
    print()
    check_connectivity()

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

    if args[0] == "load-queries" and len(args) >= 2:
        sys.exit(load_queries(args[1]))

    if args[0] == "login":
        codespace_login()
        sys.exit(0)

    print(f"Usage: {sys.argv[0]} [check|resolve <scenario-id> [--write]|"
          f"run-query <scenario-id> <dql-path> [--var KEY=VALUE ...] [--render waterfall]|load-queries <scenario-id>|login]",
          file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
