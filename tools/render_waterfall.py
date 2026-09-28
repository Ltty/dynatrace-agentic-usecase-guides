#!/usr/bin/env python3
"""
render_waterfall.py -- ASCII trace waterfall from a dtctl query envelope.

Usage:
  python tools/render_waterfall.py < envelope.json
  python tools/render_waterfall.py --file envelope.json
  python tools/preflight.py run-query payment-failure queries/beat-04-trace-waterfall.dql \
    --var TRACE_ID=<id> --render waterfall

Reads a dtctl JSON envelope (result.kind == "records"), reconstructs full rows
from constant+record merging, and renders a proportional ASCII bar chart of the
distributed trace call hierarchy.

Uses a "critical path" strategy: spans on the path from root to any failing span
are always shown individually. Sibling spans that are not on the failing path are
collapsed into a single summary line. This keeps output to ~10 lines even for
34-span traces while making the failure immediately visible.
"""

import json
import sys
from datetime import datetime, timezone


def reconstruct_records(envelope):
    """Merge result.constant with each record to get full rows."""
    result = envelope.get("result", {})
    constant = result.get("constant", {})
    raw_records = result.get("records", [])
    full = []
    for r in raw_records:
        row = dict(constant)
        row.update(r)
        full.append(row)
    return full


def _parse_time(ts):
    """Parse a timestamp value to float seconds. Returns None on failure."""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return float(ts) / 1000.0 if ts > 1e12 else float(ts)
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            pass
    return None


def _to_float(v):
    if v is None:
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


def render_waterfall(records, max_lines=12):
    """
    Render proportional ASCII bars for a distributed trace.
    Uses critical-path collapsing: off-path sibling groups are summarised in one line
    so the failing span always appears even in deep, wide traces.
    Returns a multi-line string.
    """
    if not records:
        return "(no spans returned)"

    # Parse spans into a dict
    spans = {}
    for r in records:
        sid = r.get("span.id") or r.get("span_id", "")
        if not sid:
            continue
        pid = r.get("span.parent_id") or r.get("span_parent_id") or ""
        start = _parse_time(r.get("start_time"))
        dur_ms = _to_float(r.get("duration_ms", r.get("duration", 0)))
        service = r.get("service") or r.get("dt.service.name") or "?"
        name = r.get("span_name") or r.get("span.name") or ""
        failed = bool(
            r.get("failed") or r.get("request.is_failed")
            or r.get("status") == "error"
        )

        spans[sid] = {
            "id": sid,
            "parent_id": pid if pid else None,
            "start": start,
            "end": (start + dur_ms / 1000.0) if start is not None else None,
            "duration_ms": dur_ms,
            "service": service,
            "name": name,
            "failed": failed,
            "children": [],
        }

    if not spans:
        return "(no parseable spans in envelope)"

    known = set(spans)

    # Build parent->child links; use time-containment fallback for orphans
    for sid, span in spans.items():
        pid = span["parent_id"]
        if pid and pid in known:
            spans[pid]["children"].append(sid)

    roots = []
    for sid, span in spans.items():
        pid = span["parent_id"]
        if pid and pid in known:
            continue  # already linked
        # Orphan -- find the smallest containing span by time window
        container = None
        container_dur = float("inf")
        if span["start"] is not None and span["end"] is not None:
            for oid, other in spans.items():
                if oid == sid:
                    continue
                if (other["start"] is not None and other["end"] is not None
                        and other["start"] <= span["start"]
                        and other["end"] >= span["end"]
                        and (other["end"] - other["start"]) < container_dur):
                    container = oid
                    container_dur = other["end"] - other["start"]
        if container:
            spans[container]["children"].append(sid)
            span["parent_id"] = container
        else:
            roots.append(sid)

    # Sort children by start time
    for sid in spans:
        spans[sid]["children"].sort(key=lambda x: spans[x].get("start") or 0)

    if not roots:
        roots = [min(spans, key=lambda x: spans[x].get("start") or 0)]

    # Identify the "critical path": every span that is failing OR has a failing descendant.
    # These are always rendered individually; sibling spans not on this path are collapsed.
    def _on_failing_path(sid):
        span = spans[sid]
        if span["failed"]:
            return True
        return any(_on_failing_path(c) for c in span["children"])

    critical = {sid for sid in spans if _on_failing_path(sid)}

    # If nothing is failing, critical path = everything (no collapsing needed)
    if not critical:
        critical = set(spans)

    # Compute trace window for proportional bars
    all_starts = [s["start"] for s in spans.values() if s["start"] is not None]
    all_ends = [s["end"] for s in spans.values() if s["end"] is not None]
    if not all_starts:
        return "(cannot parse span timestamps)"

    trace_start = min(all_starts)
    trace_end = max(all_ends) if all_ends else trace_start + 1
    trace_dur = max(trace_end - trace_start, 0.001)

    BAR_WIDTH = 36
    lines = []

    def _bar(span):
        if span["start"] is not None:
            offset = int((span["start"] - trace_start) / trace_dur * BAR_WIDTH)
            bar_w = max(1, int((span["duration_ms"] / 1000.0) / trace_dur * BAR_WIDTH))
            if offset + bar_w > BAR_WIDTH:
                bar_w = max(1, BAR_WIDTH - offset)
        else:
            offset, bar_w = 0, 1
        return (" " * offset + "#" * bar_w).ljust(BAR_WIDTH)

    def render_span(sid, depth):
        span = spans[sid]
        indent = "  " * depth
        max_label = max(18, 32 - len(indent))
        label = f"{span['service']} > {span['name']}"
        if len(label) > max_label:
            label = label[:max_label - 1] + "."
        mark = " FAIL <-- exception" if span["failed"] else " ok"
        dur_str = f"{span['duration_ms']:.0f}ms"
        lines.append(f"{indent}{label:<{max_label}}  [{_bar(span)}]  {dur_str}{mark}")

        children = span["children"]
        if not children:
            return

        # Partition children: on the critical path vs. not
        on_path = [cid for cid in children if cid in critical]
        off_path = [cid for cid in children if cid not in critical]

        # Collapse all off-path children into one summary line (if any)
        if off_path:
            off_services = list(dict.fromkeys(spans[c]["service"] for c in off_path))
            svc_str = ", ".join(off_services[:5])
            if len(off_services) > 5:
                svc_str += "..."
            max_dur = max(spans[c]["duration_ms"] for c in off_path)
            child_indent = "  " * (depth + 1)
            lines.append(
                f"{child_indent}+-- {len(off_path)} calls ({svc_str}) -- all ok, <={max_dur:.0f}ms"
            )

        for cid in on_path:
            render_span(cid, depth + 1)

    for root in sorted(roots, key=lambda x: spans[x].get("start") or 0):
        render_span(root, 0)

    if len(lines) > max_lines:
        lines = lines[:max_lines - 1] + [f"  ... ({len(lines) - max_lines + 1} more spans)"]

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Render ASCII trace waterfall from a dtctl query envelope"
    )
    parser.add_argument("--file", "-f", help="JSON envelope file (default: stdin)")
    parser.add_argument("--max-lines", type=int, default=12, help="Max output lines (default: 12)")
    parsed = parser.parse_args()

    if parsed.file:
        with open(parsed.file) as f:
            raw = json.load(f)
    else:
        raw = json.load(sys.stdin)

    if not raw.get("ok"):
        print("Error: envelope ok=false", file=sys.stderr)
        sys.exit(1)

    records = reconstruct_records(raw)
    print(render_waterfall(records, max_lines=parsed.max_lines))


if __name__ == "__main__":
    main()
