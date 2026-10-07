#!/usr/bin/env python3
"""
Tests for render_waterfall.py (offline, synthetic traces).
Run after every change to the renderer.

Exit 0 = all pass. Exit 1 = failures present.
"""

import importlib.util
import sys
import traceback
from pathlib import Path

spec = importlib.util.spec_from_file_location("render_waterfall", Path(__file__).parent.parent / "render_waterfall.py")
rw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rw)


def span(sid, parent, start_ms, dur_ms, name, service="svc", failed=False):
    return {"span.id": sid, "span.parent_id": parent, "start_time": f"2026-10-07T03:00:00.{start_ms:03d}000000Z",
            "duration_ms": dur_ms, "service": service, "span_name": name, "failed": failed}


def wide_trace(failed_leaf=False):
    """root > api > [20 fast siblings, 1 slow leaf 'Image resizing']."""
    spans = [span("r", None, 0, 900, "GET /", "frontend"), span("a", "r", 1, 899, "handler", "provider")]
    spans += [span(f"f{i}", "a", 2 + i, 2, f"fast-{i}", "provider") for i in range(20)]
    spans.append(span("slow", "a", 30, 800, "Image resizing", "provider", failed=failed_leaf))
    return spans


def test_slowdown_anchors_on_the_longest_leaf():
    out = rw.render_waterfall(wide_trace())
    assert "Image resizing" in out, out
    assert "most of the time" in out, out
    assert "FAIL" not in out, out
    assert "20 calls" in out, out  # the fast siblings collapse into one line


def test_failing_span_path_is_unchanged():
    out = rw.render_waterfall(wide_trace(failed_leaf=True))
    assert "FAIL <-- exception" in out, out
    assert "most of the time" not in out, out


def test_small_clean_trace_shows_everything():
    spans = [span("r", None, 0, 50, "GET /", "frontend"), span("c", "r", 1, 40, "call", "cart")]
    out = rw.render_waterfall(spans)
    assert "GET /" in out and "call" in out, out
    assert "most of the time" not in out and "calls (" not in out, out


def test_empty_input():
    assert rw.render_waterfall([]) == "(no spans returned)"


def test_long_service_names_are_shortened():
    spans = [span("r", None, 0, 50, "Invoke", "image-provider-playground in us-east-1")]
    out = rw.render_waterfall(spans)
    assert "image-provider > Invoke" in out, out


def main() -> int:
    failed = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)):
        try:
            fn()
            print(f"  PASS {name}")
        except Exception:
            failed += 1
            print(f"  FAIL {name}")
            traceback.print_exc()
    print(f"\n{'all passed' if not failed else str(failed) + ' failed'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
