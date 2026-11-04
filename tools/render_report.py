#!/usr/bin/env python3
"""
render_report.py - turn a demo session's established facts into an HTML report.

Local only. The Dynatrace-hosted agent has execute-dql and nothing else, so it never calls
this; only skills/local-runtime/SKILL.md does, and that file is never uploaded.

Usage:
    python tools/render_report.py < payload.json
    ... | python tools/render_report.py --out reports/

The payload is read from stdin (OpenCode denies file edits, so the agent cannot write one
first) and validated against tools/report-schema.json. Every field except kind, environment,
scenario and title is optional, and an absent field renders nothing at all -- the same rule the
handoff block follows: a value with no result behind it is left out, never guessed.

Prints the path it wrote. Exit codes: 0 written, 2 bad payload.
"""

import argparse
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
TEMPLATE = Path(__file__).parent / "report-template.html"
SCHEMA = Path(__file__).parent / "report-schema.json"
DEFAULT_OUT = REPO_ROOT / "reports"

TAG = re.compile(r"\{\{([#/]?)([\w.]+)\}\}")


def lookup(ctx: dict, path: str):
    """Resolve a dotted path against the context; a missing key is None, never an error."""
    cur = ctx
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def render(template: str, ctx: dict) -> str:
    """A section renders once for a truthy value, once per item for a list, never for a falsy one."""
    out = []
    i = 0
    while True:
        m = TAG.search(template, i)
        if not m:
            out.append(template[i:])
            return "".join(out)
        out.append(template[i:m.start()])
        sigil, name = m.group(1), m.group(2)

        if sigil == "/":
            raise ValueError(f"unopened section {{{{/{name}}}}}")

        if sigil != "#":
            value = lookup(ctx, name)
            out.append("" if value is None else html.escape(str(value), quote=True))
            i = m.end()
            continue

        inner, i = section_body(template, m.end(), name)
        value = lookup(ctx, name)
        if isinstance(value, list):
            for item in value:
                out.append(render(inner, {**ctx, **item} if isinstance(item, dict) else ctx))
        elif value:
            out.append(render(inner, {**ctx, **value} if isinstance(value, dict) else ctx))


def section_body(template: str, start: int, name: str):
    """The text up to this section's own closing tag, and the index just past it."""
    depth, pos = 1, start
    while True:
        m = TAG.search(template, pos)
        if not m:
            raise ValueError(f"unclosed section {{{{#{name}}}}}")
        if m.group(2) == name:
            if m.group(1) == "#":
                depth += 1
            elif m.group(1) == "/":
                depth -= 1
                if depth == 0:
                    return template[start:m.start()], m.end()
        pos = m.end()


def derive(payload: dict) -> dict:
    """Flags the template branches on, so the payload carries facts and nothing else."""
    ctx = dict(payload)
    ctx.setdefault("generated_at", dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    ctx["is_incident"] = payload["kind"] == "incident"
    ctx["is_showcase"] = payload["kind"] == "showcase"
    ctx["has_stats"] = bool(payload.get("stats"))
    ctx["has_timeline"] = bool(payload.get("timeline"))
    ctx["has_evidence"] = bool(payload.get("evidence"))
    ctx["has_incident"] = any((payload.get("incident") or {}).values())
    cost = payload.get("cost") or {}
    ctx["has_cost"] = bool(cost.get("total") or cost.get("target"))
    ctx["has_actions"] = bool(cost.get("actions"))
    return ctx


def validate(payload: dict) -> None:
    try:
        import jsonschema
    except ImportError:
        print("warning: jsonschema not installed, payload not validated", file=sys.stderr)
        return
    jsonschema.validate(payload, json.loads(SCHEMA.read_text(encoding="utf-8")))


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help="directory to write into (default: reports/)")
    args = ap.parse_args(argv[1:])

    raw = sys.stdin.read()
    if not raw.strip():
        print("error: no payload on stdin", file=sys.stderr)
        return 2
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"error: payload is not JSON - {e}", file=sys.stderr)
        return 2
    try:
        validate(payload)
    except Exception as e:
        print(f"error: payload does not match the schema - {e}", file=sys.stderr)
        return 2

    body = render(TEMPLATE.read_text(encoding="utf-8"), derive(payload))

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"{stamp}-{payload['environment']}-{payload['scenario']}.html"
    path.write_text(body, encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
