#!/usr/bin/env python3
"""
preflight.py — connectivity gate, scenario liveness, and dtctl helpers.

Modes:
  python tools/preflight.py                  # connectivity + auth check (same as `check`)
  python tools/preflight.py preflight        # is each scenario's problem live? (uses the skill's resolver DQL)
  python tools/preflight.py dtctl-path       # how to invoke dtctl: bare `dtctl` if on PATH, else the full path
  python tools/preflight.py login            # browser OAuth flow

Also the shared helpers other tools import: run_dtctl, parse_envelope, _flatten_records,
substitute_placeholders, check.

Exit codes:
  0 = all checks passed / all scenarios live
  1 = check failed / at least one scenario not live
  2 = usage error / cannot determine state
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


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


def _flatten_records(envelope: dict) -> list:
    """Merge envelope constant + per-row deltas into full record dicts."""
    result = envelope.get("result", {})
    constant = result.get("constant", {})
    rows = result.get("records", [])
    return [{**constant, **row} for row in rows]


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
# Login helper
# ---------------------------------------------------------------------------

def _normalize_callback(pasted: str, derived_base: str | None = None) -> str:
    """Accept any URL the browser shows after a failed callback and return a
    loopback URL ready to replay into dtctl's callback server.

    Uses the port dtctl actually opened (carried in derived_base, extracted from
    the authorization URL's redirect_uri param) rather than a hardcoded constant.
    Raises ValueError if no 'code' parameter is present in the pasted URL.
    """
    pasted = pasted.strip()

    fallback_base = derived_base or "http://127.0.0.1/auth/login"

    if pasted.startswith("?"):
        pasted = fallback_base + pasted

    parsed = urllib.parse.urlparse(pasted)
    qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)

    if "code" not in qs:
        raise ValueError("no 'code' parameter found in pasted URL — copy the full browser URL")

    if derived_base:
        # Use the host:port dtctl is actually listening on, keeping the path/query from the paste.
        base_parsed = urllib.parse.urlparse(derived_base)
        netloc = base_parsed.netloc
        path = base_parsed.path or "/auth/login"
    else:
        # No derived base: keep whatever netloc/path was in the paste, but warn.
        netloc = parsed.netloc or "127.0.0.1"
        path = parsed.path or "/auth/login"

    return urllib.parse.urlunparse(("http", netloc, path, "", parsed.query, ""))


def _replay_callback(url: str):
    """Deliver the callback URL to dtctl's local callback server.
    An HTTPError still means the request was received — treat it as success."""
    try:
        urllib.request.urlopen(url, timeout=10)
    except urllib.error.HTTPError:
        pass  # dtctl consumed the request; a non-2xx reply is expected
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Could not reach dtctl's callback server at {url} — {e.reason}.\n"
            "This usually means dtctl exited before the replay arrived."
        ) from e


def _extract_redirect_base(auth_url: str) -> str | None:
    """Pull the loopback callback base (scheme://host:port/path) from the
    redirect_uri query param inside dtctl's authorization URL."""
    try:
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(auth_url).query)
        raw = qs.get("redirect_uri", [None])[0]
        if not raw:
            return None
        parsed = urllib.parse.urlparse(urllib.parse.unquote(raw))
        if parsed.scheme != "http" or not parsed.netloc:
            return None
        return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    except Exception:
        return None


def _run_client_credentials_login():
    """Non-interactive login using the OAuth client-credentials grant.
    Activated when DTCTL_CLIENT_ID and DTCTL_CLIENT_SECRET are both set.
    Note: this grant issues no refresh token (RFC 6749 §4.4.3); re-run on expiry.
    """
    print()
    print("  Dynatrace Playground Sign-In (client credentials — no browser)")
    print("  " + "-" * 40)
    print()
    print("  DTCTL_CLIENT_ID and DTCTL_CLIENT_SECRET are set; using client credentials grant.")
    print("  Note: no refresh token is issued — re-run this command when the token expires.")
    print()

    cmd = [
        DTCTL,
        "--no-agent",
        "auth", "login",
        "--context", "playground",
        "--environment", "https://playground.apps.dynatrace.com",
        "--safety-level", "readonly",
        "--client-id", os.environ["DTCTL_CLIENT_ID"],
        "--client-secret", os.environ["DTCTL_CLIENT_SECRET"],
    ]
    if os.environ.get("DTCTL_ACCOUNT_URN"):
        cmd += ["--account-urn", os.environ["DTCTL_ACCOUNT_URN"]]

    subprocess.run(cmd, text=True, encoding="utf-8")
    print()
    print("  " + "-" * 40)
    print()
    ok = check_connectivity()
    sys.exit(0 if ok else 1)


def codespace_login():
    """dtctl auth login with auto-completion detection and paste-back relay."""
    import threading
    import time

    if os.environ.get("DTCTL_CLIENT_ID") and os.environ.get("DTCTL_CLIENT_SECRET"):
        _run_client_credentials_login()
        return

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
    auth_complete = threading.Event()
    shared = {"sso_url": None, "redirect_base": None, "dtctl_lines": []}

    url_re = re.compile(r"https://\S+")

    def _note_url(candidate: str):
        if shared["sso_url"]:
            return
        # An OAuth authorization URL carries these params; ordinary links don't.
        if "redirect_uri=" not in candidate and "client_id=" not in candidate:
            return
        shared["sso_url"] = candidate
        shared["redirect_base"] = _extract_redirect_base(candidate)
        sso_url_ready.set()

    def _read_output():
        """Echo dtctl's output live, char by char, so partial lines (prompts,
        progress dots) appear immediately instead of being swallowed."""
        buf = ""
        while True:
            ch = proc.stdout.read(1)
            if ch == "":
                break
            sys.stdout.write(ch)
            sys.stdout.flush()
            if ch == "\n":
                line = buf.strip()
                if line:
                    shared["dtctl_lines"].append(line)
                    for m in url_re.finditer(line):
                        _note_url(m.group(0))
                    if line == "Authentication successful!":
                        auth_complete.set()
                buf = ""
            else:
                buf += ch
        if buf.strip():
            shared["dtctl_lines"].append(buf.strip())
            for m in url_re.finditer(buf):
                _note_url(m.group(0))

    threading.Thread(target=_read_output, daemon=True).start()

    # Give dtctl a moment to emit the authorization URL, but don't block long —
    # the prompt below works whether or not we managed to capture it.
    sso_url_ready.wait(timeout=10)

    if auth_complete.is_set() or proc.poll() == 0:
        print()
        print("  Sign-in completed.")
    else:
        print()
        print("  " + "-" * 40)
        if shared["sso_url"]:
            print()
            print("  Sign-in URL — open this in your browser:")
            print()
            print(f"    {shared['sso_url']}")
        else:
            print()
            print("  If a sign-in URL appeared above, open it in your browser.")
        print()
        print("  After signing in, the browser lands on a page that can't load")
        print("  (\"this site can't be reached\"). That is expected — the redirect points")
        print("  at a port inside this container. Copy that page's full address and")
        print("  paste it below to finish.")
        if shared["redirect_base"]:
            port = urllib.parse.urlparse(shared["redirect_base"]).port
            print(f"  It looks like:  http://localhost:{port}/auth/login?state=...&code=...")
        print()
        print("  No account? https://www.dynatrace.com/signup/playground/")
        print()
        sys.stdout.write("  Paste callback URL (or press Enter if already signed in) → ")
        sys.stdout.flush()

        try:
            pasted = sys.stdin.readline().strip()
        except (EOFError, KeyboardInterrupt):
            proc.terminate()
            print("\nCancelled.")
            sys.exit(1)

        if pasted:
            if proc.poll() == 0 or auth_complete.is_set():
                print()
                print("  Auth completed while you were copying — skipping replay.")
            else:
                try:
                    callback_url = _normalize_callback(pasted, shared["redirect_base"])
                except ValueError as e:
                    proc.terminate()
                    print(f"\n  Error: {e}")
                    sys.exit(1)

                port_info = ""
                if shared["redirect_base"]:
                    port = urllib.parse.urlparse(shared["redirect_base"]).port
                    port_info = f" (port {port})"

                sys.stdout.write(f"\n  Sending callback to dtctl{port_info}... ")
                sys.stdout.flush()
                try:
                    _replay_callback(callback_url)
                    print("done.")
                except RuntimeError as e:
                    print(f"failed.\n\n  {e}")
                    proc.terminate()
                    sys.exit(1)

                # Wait for dtctl to confirm the token exchange completed.
                # Poll so we don't wait 60s if dtctl exits without printing confirmation.
                deadline = time.monotonic() + 60
                while not auth_complete.is_set() and proc.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.3)

                if auth_complete.is_set():
                    pass  # "Authentication successful!" already printed by the read thread
                elif proc.poll() is not None and proc.returncode != 0:
                    print(f"\n  Warning: dtctl exited with code {proc.returncode} — token may not have been saved.")

    # Wait for dtctl to finish writing the token before running the connectivity check.
    try:
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print()
    print("  " + "-" * 40)
    print()
    ok = check_connectivity()
    sys.exit(0 if ok else 1)

def _dql_reachable() -> bool:
    """Quick check: can we actually execute a DQL query? Extracted so preflight_report
    can gate the per-scenario loop rather than misreporting quiet Playground as EMPTY."""
    rc, out, _ = run_dtctl("query", "fetch dt.davis.problems | limit 1", "-o", "json")
    env = parse_envelope(out) if rc == 0 else None
    return rc == 0 and bool(env) and env.get("ok", False)


def preflight_report() -> int:
    """Print a go/no-go line per scenario, using the Dynatrace skill's own resolver DQL.

    Exit codes:
      0 — all scenarios live
      1 — at least one scenario empty or broken
      2 — cannot determine (DQL unreachable)
    """
    import importlib.util

    print("=== scenario liveness ===")
    print()

    # The demo always queries the read-only Playground, whatever the saved context is.
    os.environ["DTCTL_CONTEXT"] = "playground"
    if not _dql_reachable():
        print("[FAIL] DQL not reachable — run /demo-doctor to fix auth first")
        return 2

    spec = importlib.util.spec_from_file_location(
        "validate_dt_skill", Path(__file__).parent / "validate_dt_skill.py")
    skill = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(skill)

    live_ids = []
    total = 0
    for scenario_id, (resolver_file, _) in skill.SCENARIO_FILES.items():
        context = skill.SCENARIO_CONTEXT.get(scenario_id, skill.DEFAULT_CONTEXT)
        if context != skill.DEFAULT_CONTEXT:
            print(f"[SKIP] {scenario_id} — its data lives on the '{context}' tenant, not the Playground")
            continue
        total += 1
        try:
            row = None
            # Primary resolver, then the fallback, as the skill's session protocol does.
            for block in skill.extract_dql_blocks(resolver_file)[:2]:
                _, out, _ = run_dtctl("query", skill.strip_dql_comments(block), "-o", "json",
                                      "--max-field-chars", "0")
                envelope = parse_envelope(out)
                rows = _flatten_records(envelope) if envelope and envelope.get("ok") else []
                if rows:
                    row = rows[0]
                    break
            if row:
                mode = "live_active" if row.get("status") == "ACTIVE" or not row.get("ended") else "live_recent"
                check(scenario_id, True, f"{row.get('display_id', '?')} {row.get('status', '?')}, "
                                         f"{row.get('affected_users', '?')} users ({mode})")
                live_ids.append(scenario_id)
            else:
                check(scenario_id, False, "EMPTY — no live problem in the last 48h")
        except Exception as e:
            # One broken scenario must never abort the whole report.
            check(scenario_id, False, f"BROKEN — {e}")

    print()
    print(f"Result: {len(live_ids)} of {total} scenarios live — {', '.join(live_ids) or 'none'}")
    return 0 if len(live_ids) == total else 1


def main():
    args = sys.argv[1:]

    if not args or args[0] == "check":
        ok = check_connectivity()
        sys.exit(0 if ok else 1)

    if args[0] == "preflight":
        sys.exit(preflight_report())

    if args[0] == "dtctl-path":
        # Bare `dtctl` when it is on PATH, so the `Bash(dtctl query *)` allow rule matches;
        # otherwise the full path, with forward slashes for Git Bash.
        import shutil
        print("dtctl" if shutil.which("dtctl") else DTCTL.replace("\\", "/"))
        sys.exit(0)

    if args[0] == "login":
        codespace_login()
        # codespace_login() always calls sys.exit() itself; this is unreachable.

    print(f"Usage: {sys.argv[0]} [check|preflight|dtctl-path|login]", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
