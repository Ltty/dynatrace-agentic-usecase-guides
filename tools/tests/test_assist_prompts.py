#!/usr/bin/env python3
"""
Tests for assist_prompts.py (offline, no tenant, no token): the rules that keep other people's prompts private.

The prompts the tool reads belong to customers, prospects and colleagues, so what must hold is structural: queries end in
counts, every grouped query has the distinct-user floor, an outside tenant can never be fetched or reported below it,
and the scrub removes what identifies a person.

Exit 0 = all pass. Exit 1 = failures present.
"""

import importlib.util
import re
import sys
import traceback
from pathlib import Path

TOOLS = Path(__file__).parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ap = load("assist_prompts")
guard = load("guard_dtctl")


def raises_exit(fn, *args):
    try:
        fn(*args)
    except SystemExit:
        return True
    return False


def test_scrub_removes_what_identifies_a_person():
    out = ap.scrub("Mail jane.doe+x@example.co.uk about https://playground.apps.dynatrace.com/ui?id=7 "
                   "token abcdefghij0123456789 problem P-26117215 on   host 10.1.2.3")
    for leaked in ("jane", "example.co.uk", "https://", "abcdefghij0123456789", "26117215", "10.1"):
        assert leaked not in out, (leaked, out)
    assert "<email>" in out and "<url>" in out and "<id>" in out and "  " not in out


def test_the_dql_scrub_uses_dynatrace_pattern_syntax_not_regex():
    """replacePattern takes pattern syntax: an unquoted @ is a parse error on the tenant (found live)."""
    expr = ap.scrub_dql("question")
    assert "'@'" in expr and "NSPACE" in expr and "SPACE+" in expr
    assert "https?" not in expr and "\\\\s" not in expr


def test_every_query_ends_in_counts_and_returns_no_text_or_person():
    for name, dql in ap.queries().items():
        assert "summarize" in dql, name
        assert not re.search(r"\|\s*fields\s", dql), (name, "a fields command could return raw columns")
        assert "user_email" not in dql and "user.email" not in dql, name
        by = re.findall(r"by:\s*\{([^}]*)\}", dql)
        for group in by:
            for forbidden in ("user_id", "user_input", "question", "response", "conversation_id"):
                assert forbidden not in group, (name, forbidden)


def test_every_grouped_query_has_the_distinct_user_floor():
    for name, dql in ap.queries().items():
        if name == "profile":
            continue
        assert "users >= __K__" in dql, (name, "no user floor")


def test_an_outside_tenant_is_only_reported_at_or_above_the_floor():
    assert raises_exit(ap.check_report_allowed, "playground", 1)
    assert raises_exit(ap.check_report_allowed, "playground", ap.K_FLOOR - 1)
    ap.check_report_allowed("playground", ap.K_FLOOR)
    ap.check_report_allowed("demo-live", 1)


def test_fetch_is_for_internal_tenants_only():
    assert raises_exit(ap.check_fetch_allowed, "playground")
    assert raises_exit(ap.check_fetch_allowed, "dev")
    ap.check_fetch_allowed("demo-live")


def test_the_queries_pass_the_repos_read_only_guard():
    for name in ap.queries():
        dql = ap.render(name, 30, ap.K_FLOOR)
        for pattern in guard.DQL_WRITE_PATTERNS:
            assert not re.search(pattern, dql, re.IGNORECASE), (name, pattern)


def test_each_intent_rule_stays_under_the_dql_expression_limit():
    """One nested if() over every phrase exceeded 250 sub-expressions on the tenant (found live)."""
    for step in ap.intent_steps():
        assert step.count("matchesPhrase(") + step.count("contains(") <= 60, step[:80]


def test_canned_prompts_are_ruled_out_first_then_orientation_and_every_rule_waits_for_other():
    """Button prompts are separated before anything is counted as a question; the first match wins."""
    steps = ap.intent_steps()
    assert '"canned_ui_prompt"' in steps[1] and '"orientation"' in steps[2]
    assert all('intent == "other"' in s for s in steps[1:])


def test_a_pseudonym_is_stable_within_a_run_and_hides_the_id():
    a = ap.pseudonym("user-123", "salt-1")
    assert a == ap.pseudonym("user-123", "salt-1")
    assert a != ap.pseudonym("user-123", "salt-2") and "user-123" not in a and len(a) == 12


def test_the_query_pack_is_in_step_with_the_module():
    for name, text in ap.pack_files().items():
        path = ap.QUERY_DIR / name
        assert path.exists(), f"{name} missing: run python tools/assist_prompts.py pack"
        assert path.read_text(encoding="utf-8") == text, f"{name} out of date: run python tools/assist_prompts.py pack"
    on_disk = {p.name for p in ap.QUERY_DIR.glob("*.dql")}
    assert on_disk == set(ap.pack_files()), on_disk ^ set(ap.pack_files())


def test_sampling_individual_prompts_needs_the_explicit_clearance_flag():
    class Args:
        tenant = "playground"; days = 30; nofit_mod = 55; offer_mod = 2; cleared = False
    assert raises_exit(ap.cmd_sample, Args())


def test_the_sample_query_never_selects_a_person_a_conversation_or_a_time():
    dql = ap.sample_dql(55, 2, 30)
    final = dql.split("| fields ")[-1].splitlines()[0]
    for forbidden in ("user_id", "user.email", "conversation_id", "timestamp", "user_input", "response", "question"):
        assert forbidden not in final, (forbidden, final)
    assert "<email>" in dql and "<url>" in dql and "<id>" in dql, "prompts holding a placeholder must be dropped"
    assert "limit" in dql
    for pattern in guard.DQL_WRITE_PATTERNS:
        assert not re.search(pattern, dql, re.IGNORECASE), pattern


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
