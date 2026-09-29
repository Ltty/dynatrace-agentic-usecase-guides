#!/usr/bin/env python3
"""
PreToolUse hook: guard-dtctl.py

Validates every Bash tool call that touches dtctl.
Enforces read-only access at the verb and DQL level, independently of
dtctl's own client-side safety level (defence in depth).

Contract (Claude Code hook protocol):
- Reads JSON from stdin: {"tool_name": "Bash", "tool_input": {"command": "..."}}
- Exit 0  -> allow
- Exit 2  -> block; message on stdout is shown to the model as the refusal reason
"""

from __future__ import annotations

import json
import re
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ALLOWED_VERBS = {
    "doctor", "version", "commands", "inventory",
    "query",
    "get", "describe",
    "exec copilot",
    "config current-context", "config describe-context",
    "config get-contexts", "config view",
    "auth status", "auth whoami",
}

# Mutating DQL constructs (ingest, write-side keywords)
DQL_WRITE_PATTERNS = [
    r"\bINGEST\b", r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b",
    r"\bPUT\b", r"\bWRITE\b",
]

# Dtctl mutating verbs (belt-and-suspenders; settings.json deny list is first layer)
BLOCKED_VERBS = {
    "apply", "create", "edit", "delete", "restore",
    "exec workflow", "exec analyzer",
    "auth logout",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def block(reason):
    print(reason)
    sys.exit(2)


def extract_dtctl_command(cmd):
    """Return the dtctl sub-command string, or None if not a dtctl call.

    Only matches when dtctl is the executable being invoked — not when it
    appears inside a string argument (e.g. a git commit message or a Python
    string literal that references dtctl by name).
    """
    # Strip leading env-var exports and PATH assignments
    stripped = re.sub(r"^export\s+[A-Z_]+=\S+\s*;?\s*", "", cmd, flags=re.MULTILINE).strip()
    stripped = re.sub(r"^[A-Z_]+=\S+\s+", "", stripped).strip()

    # dtctl must be the first token (the executable), possibly preceded by a path.
    # This prevents matching dtctl inside commit messages, Python string literals, etc.
    m = re.match(r"(?:[^\s]*[\\/])?dtctl(?:\.exe)?\s*(.*)", stripped, re.DOTALL | re.IGNORECASE)
    if not m:
        return None
    return m.group(1).strip()


def parse_verb(sub):
    """Extract canonical verb (possibly two-word)."""
    parts = sub.split()
    if not parts:
        return ""
    if len(parts) >= 2:
        two_word = parts[0] + " " + parts[1]
        if two_word in ALLOWED_VERBS or two_word in BLOCKED_VERBS:
            return two_word
    return parts[0]


def extract_dql(sub):
    """Pull the DQL string from a 'dtctl query <DQL>' invocation."""
    m = re.match(r'query\s+(.*)', sub, re.DOTALL | re.IGNORECASE)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    cmd = payload.get("tool_input", {}).get("command", "")
    sub = extract_dtctl_command(cmd)

    if sub is None:
        # Not a dtctl call; check curl/wget
        if re.search(r"\b(curl|wget)\b", cmd):
            if not re.search(r"playground\.apps\.dynatrace\.com", cmd):
                block(
                    "BLOCKED: curl/wget must target playground.apps.dynatrace.com only. "
                    "Use dtctl query for data access."
                )
        sys.exit(0)

    verb = parse_verb(sub)

    # Block explicitly banned verbs
    for bv in BLOCKED_VERBS:
        if verb == bv or sub.startswith(bv):
            block(
                "BLOCKED: dtctl '{}' is a mutating operation. "
                "The Playground is read-only.".format(verb)
            )

    # Require verb to be in allow list
    allowed = False
    for av in ALLOWED_VERBS:
        if verb == av or sub.startswith(av):
            allowed = True
            break
    if not allowed:
        block(
            "BLOCKED: dtctl '{}' is not in the read-only allow list. "
            "Allowed: {}".format(verb, ", ".join(sorted(ALLOWED_VERBS)))
        )

    # Validate DQL for write constructs
    dql = extract_dql(sub)
    if dql:
        for pattern in DQL_WRITE_PATTERNS:
            if re.search(pattern, dql, re.IGNORECASE):
                block(
                    "BLOCKED: DQL contains a write construct '{}'. "
                    "Only read queries are permitted.".format(pattern)
                )

    sys.exit(0)


if __name__ == "__main__":
    main()
