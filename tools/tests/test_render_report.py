#!/usr/bin/env python3
"""Offline checks for tools/render_report.py.

The report is the one artefact a user keeps and forwards, so the things that matter are that
nothing is left half-rendered, that a fact with no source leaves no empty scaffolding behind,
and that a value out of live data cannot inject markup.

Run: python tools/tests/test_render_report.py
"""

import importlib.util
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

spec = importlib.util.spec_from_file_location("render_report", REPO_ROOT / "tools" / "render_report.py")
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)

TEMPLATE = rr.TEMPLATE.read_text(encoding="utf-8")

INCIDENT = {
    "kind": "incident", "environment": "playground", "scenario": "payment-failure",
    "title": "Payment service failing", "display_id": "P-1",
    "headline": "It failed.",
    "stats": [{"label": "Affected users", "value": "420", "note": "problem record"}],
    "timeline": [{"time": "09:07", "what": "change shipped"}],
    "incident": {"when": "now", "cause": "commit c590ec"},
    "goes_to": "Team-Payments",
    "evidence": [{"label": "Problem", "url": "https://playground.apps.dynatrace.com/x"}],
    "still_open": "Not confirmed.",
}

SHOWCASE = {
    "kind": "showcase", "environment": "demo-live", "scenario": "cloud-observability",
    "title": "Where 10% is",
    "cost": {"total": "$14,122", "target": "$1,412",
             "actions": [{"label": "Largest line", "detail": "CloudWatch, $2,415"}]},
}

MINIMAL = {
    "kind": "incident", "environment": "dev", "scenario": "disk-cpu-cascade", "title": "Disk",
}


def render(payload):
    return rr.render(TEMPLATE, rr.derive(payload))


def test_both_kinds_render_with_nothing_left_unresolved():
    for payload in (INCIDENT, SHOWCASE, MINIMAL):
        out = render(payload)
        assert "{{" not in out, (payload["scenario"], out[out.find("{{"):][:60])
        assert "}}" not in out, payload["scenario"]


def test_each_kind_shows_only_its_own_section():
    inc = render(INCIDENT)
    assert "Incident report" in inc
    assert "Cost action list" not in inc and "Cloud cost summary" not in inc

    show = render(SHOWCASE)
    assert "Cloud cost summary" in show and "Cost action list" in show
    assert "What the evidence shows" not in show and "Incident report" not in show


def test_a_fact_with_no_source_leaves_no_empty_scaffolding():
    out = render(MINIMAL)
    for heading in ("At a glance", "Timeline", "Evidence", "Still open",
                    "What the evidence shows", "Cost action list"):
        assert heading not in out, heading
    assert "<li>" not in out and "<dd>" not in out


def test_values_cannot_inject_markup():
    hostile = dict(INCIDENT, title='<script>alert(1)</script>',
                   goes_to='" onmouseover="alert(1)')
    out = render(hostile)
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    assert 'onmouseover="alert' not in out


def test_a_link_must_be_https():
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        print("  SKIP test_a_link_must_be_https (jsonschema not installed)")
        return
    bad = dict(INCIDENT, evidence=[{"label": "x", "url": "javascript:alert(1)"}])
    try:
        rr.validate(bad)
    except Exception:
        return
    raise AssertionError("a javascript: url was accepted")


def test_a_payload_missing_a_required_field_is_rejected():
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        print("  SKIP test_a_payload_missing_a_required_field_is_rejected")
        return
    try:
        rr.validate({"kind": "incident", "environment": "dev"})
    except Exception:
        return
    raise AssertionError("a payload with no scenario or title was accepted")


def test_it_writes_a_named_file_and_prints_the_path(capsys=None):
    import io
    import json
    with tempfile.TemporaryDirectory() as tmp:
        stdin, stdout = sys.stdin, sys.stdout
        sys.stdin = io.StringIO(json.dumps(SHOWCASE))
        sys.stdout = io.StringIO()
        try:
            rc = rr.main(["render_report.py", "--out", tmp])
            printed = sys.stdout.getvalue().strip()
        finally:
            sys.stdin, sys.stdout = stdin, stdout
        assert rc == 0, rc
        written = Path(printed)
        assert written.exists(), printed
        assert written.name.endswith("-demo-live-cloud-observability.html"), written.name
        assert "Where 10% is" in written.read_text(encoding="utf-8")


def test_an_unclosed_section_is_an_error_not_silent_output():
    try:
        rr.render("{{#stats}}oops", {"stats": [{}]})
    except ValueError:
        return
    raise AssertionError("an unclosed section rendered silently")


if __name__ == "__main__":
    failed = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_"):
            continue
        try:
            fn()
            print(f"  PASS {name}")
        except AssertionError as e:
            print(f"  FAIL {name}: {e}")
            failed += 1
    print()
    print("all passed" if not failed else f"{failed} failed")
    sys.exit(1 if failed else 0)
