#!/usr/bin/env python3
"""
PreToolUse hook: guard-dtctl.py

Validates every Bash and PowerShell tool call that touches dtctl.
Enforces read-only access at the verb and DQL level, independently of
dtctl's own client-side safety level (defence in depth).

Contract (shared hook protocol — Claude Code PreToolUse and OpenCode tool.execute.before):
- Reads JSON from stdin: {"tool_name": "Bash"|"PowerShell", "tool_input": {"command": "..."}}
  (OpenCode normalises its tool name to "Bash" before calling this script)
- Exit 0  -> allow
- Exit 2  -> block; message on stderr is shown to the model as the refusal reason

Every command segment is checked, not just the first token: `cd x && dtctl delete`,
a quoted executable, PowerShell's `& "...\\dtctl.exe"`, a variable holding the dtctl
path, and wrappers such as `bash -c` or `env` are all recognised.
"""

from __future__ import annotations

import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SHELL_TOOLS = {"Bash", "PowerShell"}

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

# Heads whose arguments are themselves a command to check.
WRAPPERS = {
    "bash", "sh", "zsh", "cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh",
    "env", "sudo", "nohup", "time", "xargs", "eval", "exec",
    "start-process", "invoke-expression", "iex", "call",
}

WEB_FETCH = re.compile(r"\b(curl|wget|Invoke-WebRequest|Invoke-RestMethod|iwr|irm)\b", re.IGNORECASE)
DTCTL_EXE = re.compile(r"(?:.*[\\/])?dtctl(?:\.exe)?", re.IGNORECASE)
VAR_REF = re.compile(r"\$\{?([A-Za-z_]\w*)\}?")
# A bare assignment only; `VAR=x cmd` is an env prefix and is handled as a command.
BASH_ASSIGN = re.compile(r"""^(?:export\s+)?([A-Za-z_]\w*)=("[^"]*"|'[^']*'|\$\(.*\)|`[^`]*`|\S*)$""", re.DOTALL)
PS_ASSIGN = re.compile(r"^\$([A-Za-z_]\w*)\s*=\s*(.*)$", re.DOTALL)
SUBST_HEAD = re.compile(r"^(?:\$\((?P<a>[^)]*)\)|`(?P<b>[^`]*)`|\((?P<c>[^)]*)\))\s*(?P<rest>.*)$", re.DOTALL)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def block(reason):
    print(reason, file=sys.stderr)
    sys.exit(2)


def split_segments(cmd: str) -> list[str]:
    """Split on unquoted ; & | and newlines (covers &&, ||, pipes and PowerShell's & operator)."""
    segments, buf, quote, escape = [], [], None, False
    for ch in cmd:
        if escape:
            buf.append(ch)
            escape = False
        elif quote:
            buf.append(ch)
            if quote == '"' and ch in "\\`":
                escape = True
            elif ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            buf.append(ch)
        elif ch in ";&|\n":
            segments.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    segments.append("".join(buf))
    return [s.strip() for s in segments if s.strip()]


def unquote(token: str) -> str:
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "'\"":
        return token[1:-1]
    return token


def head_and_rest(segment: str) -> tuple[str, str]:
    """First token (quotes removed) and the remainder, after leading VAR=value prefixes."""
    segment = re.sub(r"^(?:[A-Za-z_]\w*=\S*\s+)+", "", segment)
    m = re.match(r'("[^"]*"|\'[^\']*\'|\S+)\s*(.*)', segment, re.DOTALL)
    if not m:
        return "", ""
    return unquote(m.group(1)), m.group(2).strip()


def dtctl_variables(segments: list[str]) -> set[str]:
    """Names of shell variables assigned something that mentions dtctl in this command."""
    names = set()
    for seg in segments:
        m = BASH_ASSIGN.match(seg) or PS_ASSIGN.match(seg)
        if m and "dtctl" in m.group(2).lower():
            names.add(m.group(1).lower())
    return names


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
    """Pull the inline DQL string from a 'query <DQL>' sub-command."""
    m = re.match(r'query\s+(.*)', sub, re.DOTALL | re.IGNORECASE)
    if not m:
        return None
    return m.group(1).strip().strip('"').strip("'") or None


def query_file(sub):
    """Contents of a `-f <file>` / `--file <file>` DQL file, if it can be read."""
    m = re.search(r'(?:^|\s)(?:-f|--file)[\s=]+("[^"]*"|\'[^\']*\'|\S+)', sub)
    if not m:
        return None
    try:
        with open(os.path.expanduser(unquote(m.group(1))), encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def check_dtctl(sub: str, whole_cmd: str):
    """Block reason for one dtctl sub-command (everything after the executable), or None."""
    verb = parse_verb(sub)

    for bv in BLOCKED_VERBS:
        if verb == bv or sub.startswith(bv):
            return ("BLOCKED: dtctl '{}' is a mutating operation. "
                    "The Playground is read-only.".format(verb))

    if not any(verb == av or sub.startswith(av) for av in ALLOWED_VERBS):
        return ("BLOCKED: dtctl '{}' is not in the read-only allow list. "
                "Allowed: {}".format(verb, ", ".join(sorted(ALLOWED_VERBS))))

    if verb == "query":
        # Inline DQL; else a -f file; else DQL piped in, so check the whole command.
        dql = extract_dql(sub)
        if dql is None or dql.startswith("-"):
            dql = query_file(sub) or whole_cmd
        for pattern in DQL_WRITE_PATTERNS:
            if re.search(pattern, dql, re.IGNORECASE):
                return ("BLOCKED: DQL contains a write construct '{}'. "
                        "Only read queries are permitted.".format(pattern))
    return None


def check_command(cmd: str, whole_cmd: str, depth: int = 0):
    """Block reason for a command line, or None if every dtctl use in it is read-only."""
    if depth > 3:
        return "BLOCKED: command nesting too deep to verify."
    segments = split_segments(cmd)
    dt_vars = dtctl_variables(segments)

    for seg in segments:
        assign = BASH_ASSIGN.match(seg) or PS_ASSIGN.match(seg)
        if assign:
            # `X=$(dtctl delete …)` or `$x = dtctl delete …` runs the value: check it as a command.
            value = assign.group(2).strip()
            inner = re.fullmatch(r"\$\((.*)\)|`(.*)`|\"\$\((.*)\)\"", value, re.DOTALL)
            if inner:
                value = next(g for g in inner.groups() if g is not None)
            reason = check_command(value, whole_cmd, depth + 1) if value else None
            if reason:
                return reason
            continue

        subst = SUBST_HEAD.match(seg)
        if subst:
            inner = subst.group("a") or subst.group("b") or subst.group("c") or ""
            if "dtctl" in inner.lower():
                reason = check_dtctl(subst.group("rest"), whole_cmd)
                if reason:
                    return reason
                continue

        head, rest = head_and_rest(seg)
        var = VAR_REF.fullmatch(head)
        if DTCTL_EXE.fullmatch(head) or (var and var.group(1).lower() in dt_vars):
            reason = check_dtctl(rest, whole_cmd)
        elif head.lower() in WRAPPERS:
            tokens = rest
            while True:
                m = re.match(r'(?:-{1,2}|/)\S+\s*(.*)', tokens, re.DOTALL)
                if not m:
                    break
                tokens = m.group(1)
            reason = check_command(unquote(tokens.strip()), whole_cmd, depth + 1) if tokens.strip() else None
        else:
            reason = None
        if reason:
            return reason
    return None

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if payload.get("tool_name", "") not in SHELL_TOOLS:
        sys.exit(0)

    cmd = payload.get("tool_input", {}).get("command", "") or ""

    reason = check_command(cmd, cmd)
    if reason:
        block(reason)

    if WEB_FETCH.search(cmd) and not re.search(r"playground\.apps\.dynatrace\.com", cmd):
        block(
            "BLOCKED: web requests must target playground.apps.dynatrace.com only. "
            "Use dtctl query for data access."
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
