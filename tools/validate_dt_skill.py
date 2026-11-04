#!/usr/bin/env python3
"""
validate_dt_skill.py — Validate a Dynatrace skill scenario by running its resolver DQL
and all beat DQL blocks against the scenario's live tenant, including the chained trace query.

Usage:
    python tools/validate_dt_skill.py --scenario payment-failure
    python tools/validate_dt_skill.py <resolver-file>.md <beats-file>.md

Files are read in order; the resolver file must come first so its result feeds the beats.

Reuses run_dtctl(), parse_envelope(), _flatten_records(), and substitute_placeholders()
from tools/preflight.py.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SCENARIO_DIR = (REPO_ROOT / "dynatrace-intelligence" / "skills"
                / "investigating-playground-incidents" / "references")

SCENARIO_FILES = {
    "payment-failure": SCENARIO_DIR / "scenario-payment-failure.md",
    "broken-images": SCENARIO_DIR / "scenario-broken-images.md",
    "disk-cpu-cascade": SCENARIO_DIR / "scenario-disk-cpu-cascade.md",
    "cloud-observability": SCENARIO_DIR / "scenario-cloud-observability.md",
}
# ---------------------------------------------------------------------------
# Bootstrap: import preflight by file path (no package install needed).
# ---------------------------------------------------------------------------

def _load_preflight():
    spec = importlib.util.spec_from_file_location(
        "preflight", REPO_ROOT / "tools" / "preflight.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_PF = _load_preflight()

SESSION_PROTOCOL = SCENARIO_DIR / "session-protocol.md"

# The environment registry is preflight's; this module only reads it.
ENVIRONMENTS = _PF.ENVIRONMENTS
SCENARIO_ENVIRONMENTS = _PF.SCENARIO_ENVIRONMENTS
DEFAULT_ENVIRONMENT = "playground"


def environments_for(scenario):
    """The environments a scenario's data lives on, most-default first."""
    envs = SCENARIO_ENVIRONMENTS.get(scenario, ())
    return sorted(envs, key=lambda e: e != DEFAULT_ENVIRONMENT)

# Showcases have no survey row: their beats supply the tokens (see harvest_showcase_state).
SHOWCASES = {"cloud-observability"}

# Runtime-only tokens: present in DQL until a live query result supplies the value.
RUNTIME_ONLY = {"TRACE_ID"}


# ---------------------------------------------------------------------------
# DQL block extraction
# ---------------------------------------------------------------------------

DQL_FENCE_RE = re.compile(r"```dql\n(.*?)```", re.DOTALL)


def extract_dql_blocks(md_path: Path) -> list[str]:
    """Return all raw DQL strings found in ```dql fences."""
    text = md_path.read_text(encoding="utf-8")
    return [m.group(1).strip() for m in DQL_FENCE_RE.finditer(text)]


def survey_dql(scenario: str | None = None) -> str:
    """The survey query from session-protocol.md, optionally narrowed to one scenario's row.

    Keyed to the "## Session state" heading rather than to fence order, so adding a fence
    elsewhere in that file cannot silently repoint the survey.
    """
    text = SESSION_PROTOCOL.read_text(encoding="utf-8")
    start = text.find("\n## Session state")
    if start < 0:
        raise RuntimeError("session-protocol.md has no '## Session state' heading")
    end = text.find("\n## ", start + 1)
    section = text[start:end if end > 0 else len(text)]
    fences = DQL_FENCE_RE.findall(section)
    if not fences:
        raise RuntimeError("no ```dql fence under '## Session state'")
    dql = fences[0].strip()
    return dql + (f'\n| filter scenario == "{scenario}"' if scenario else "")


DEEP_LINK_RE = re.compile(r'\*\*Deep link\*\* \(label "([^"]+)"\):\s*```text\n(.*?)```', re.DOTALL)


def deep_links(md_path: Path) -> list[tuple[str, str]]:
    """(label, url template) of every beat's deep link, in beat order."""
    text = md_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return [(m.group(1), m.group(2).strip()) for m in DEEP_LINK_RE.finditer(text)]


def strip_dql_comments(dql: str) -> str:
    """Remove // comment lines and collapse to a single line."""
    lines = [ln for ln in dql.splitlines() if not ln.strip().startswith("//")]
    return " ".join(ln.strip() for ln in lines if ln.strip())


def remaining_tokens(dql: str) -> list[str]:
    return re.findall(r"\{\{([A-Z_]+)\}\}", dql)


# ---------------------------------------------------------------------------
# Resolver detection
# ---------------------------------------------------------------------------

def is_resolver_block(raw_dql: str) -> bool:
    """True if this block looks like a resolver (no {{DQL_FROM}} substitution needed)."""
    return "dt.davis.problems" in raw_dql and "{{DQL_FROM}}" not in raw_dql


def is_chained_producer(raw_dql: str) -> bool:
    """True if this block produces trace_id (failing-spans query)."""
    return "trace_id" in raw_dql and "{{TRACE_ID}}" not in raw_dql


def is_chained_consumer(raw_dql: str) -> bool:
    """True if this block needs {{TRACE_ID}} (waterfall query)."""
    return "{{TRACE_ID}}" in raw_dql


# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------

def extract_state_from_resolver(pf, envelope: dict) -> dict:
    """Pull session-state fields from resolver result."""
    records = pf._flatten_records(envelope)
    if not records:
        return {}
    row = records[0]
    return {
        "PROBLEM_ID": row.get("problem_id", ""),
        "STARTED": str(row.get("started", "")),
        "SURVEY_AT": str(row.get("queried_at", "")),
        "TF_REL_H": str(row.get("tf_rel_h", "")),
        "TF_FROM_ISO": str(row.get("tf_from_iso", "")),
        "TF_TO_ISO": str(row.get("tf_to_iso", "")),
        "DQL_FROM": row.get("window_from", "now()-2h"),
        "DQL_TO": row.get("window_to", "now()"),
        "TF_FROM_MS": str(row.get("tf_from_ms", "")),
        "TF_TO_MS": str(row.get("tf_to_ms", "")),
        "ROOT_CAUSE_ID": str(row.get("root_cause_id", "")),
    }


def harvest_showcase_state(pf, envelope: dict, state: dict) -> None:
    """A showcase's tokens come from its beats: the first queried_at is SURVEY_AT, a problem_id row fills the link."""
    records = pf._flatten_records(envelope)
    if not records:
        return
    row = records[0]
    if row.get("queried_at") and "SURVEY_AT" not in state:
        state["SURVEY_AT"] = str(row["queried_at"])
    if row.get("problem_id") and "PROBLEM_ID" not in state:
        state["PROBLEM_ID"] = str(row["problem_id"])
        state["TF_FROM_MS"] = str(row.get("tf_from_ms", ""))
        state["TF_TO_MS"] = str(row.get("tf_to_ms", ""))


def assert_window(pf, envelope: dict) -> None:
    """Warn if window fields are missing from the resolver result."""
    records = pf._flatten_records(envelope)
    if not records:
        return
    row = records[0]
    for field in ("window_from", "window_to", "tf_from_ms", "tf_to_ms"):
        if not row.get(field):
            print(f"  WARN — resolver result missing '{field}': deep links will break")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Dynatrace skill scenario DQL blocks against the scenario's live tenant."
    )
    parser.add_argument(
        "--environment", "--context", dest="environment", default=None,
        help="environment to validate against (default: the scenario's own; required when a "
             "scenario lives on more than one). Set per run, never saved, so a different current "
             "context cannot redirect the validation."
    )
    parser.add_argument(
        "--links", action="store_true",
        help="with --scenario: print every beat's deep link, substituted from the live survey row, "
             "and run no beat query. Open each one and judge it against its label."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--scenario", choices=list(SCENARIO_FILES), metavar="SCENARIO_ID",
        help=f"Scenario ID to validate. Choices: {', '.join(SCENARIO_FILES)}"
    )
    group.add_argument(
        "md_files", nargs="*", default=[], metavar="FILE",
        help="Direct paths to scenario markdown files, resolver file first."
    )
    args = parser.parse_args(argv[1:])
    if args.links and not args.scenario:
        parser.error("--links needs --scenario")
    return args


def print_links(pf, scenario: str, md_path: Path, environment: str) -> int:
    """Print each beat's label and substituted deep link for the scenario's live problem."""
    if scenario in SHOWCASES:
        state: dict = {}
        for raw in extract_dql_blocks(md_path):
            if "PROBLEM_ID" in state:
                break
            dql = pf.substitute_placeholders(raw, state, pass_through_unknown=True)
            if remaining_tokens(dql):
                continue
            _, out, _ = pf.run_dtctl("query", strip_dql_comments(dql), "-o", "json", "--max-field-chars", "0")
            envelope = pf.parse_envelope(out)
            if envelope and envelope.get("ok"):
                harvest_showcase_state(pf, envelope, state)
    else:
        rc, out, _ = pf.run_dtctl("query", strip_dql_comments(survey_dql(scenario)), "-o", "json",
                                  "--max-field-chars", "0")
        envelope = pf.parse_envelope(out)
        state = extract_state_from_resolver(pf, envelope) if envelope and envelope.get("ok") else {}
    state["LINK_HOST"] = _PF.host_of(environment)
    if not state.get("PROBLEM_ID"):
        print(f"No live problem for {scenario}: nothing to substitute.")
        return 1
    unresolved = 0
    for n, (label, url) in enumerate(deep_links(md_path), 1):
        full = pf.substitute_placeholders(url, state, pass_through_unknown=True)
        left = remaining_tokens(full)
        unresolved += bool(left)
        print(f"Beat {n}  {label}" + (f"   UNRESOLVED {left}" if left else ""))
        print(f"  {full}")
    return 1 if unresolved else 0


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.environment is None and args.scenario:
        envs = environments_for(args.scenario)
        if len(envs) > 1:
            print(f"error: {args.scenario} lives on {', '.join(envs)} — "
                  f"pass --environment to say which", file=sys.stderr)
            return 2
        args.environment = envs[0] if envs else DEFAULT_ENVIRONMENT
    args.environment = args.environment or DEFAULT_ENVIRONMENT
    if args.environment not in ENVIRONMENTS:
        print(f"error: unknown environment '{args.environment}' — "
              f"known: {', '.join(ENVIRONMENTS)}", file=sys.stderr)
        return 2
    os.environ["DTCTL_CONTEXT"] = args.environment

    if args.scenario:
        md_paths = [SCENARIO_FILES[args.scenario]]
    else:
        md_paths = [Path(p) for p in args.md_files]

    for md_path in md_paths:
        if not md_path.exists():
            print(f"error: {md_path} not found", file=sys.stderr)
            return 2

    pf = _load_preflight()

    if args.links:
        return print_links(pf, args.scenario, md_paths[0], args.environment)

    blocks = [b for md_path in md_paths for b in extract_dql_blocks(md_path)]
    showcase = args.scenario in SHOWCASES
    if args.scenario and not showcase:
        blocks.insert(0, survey_dql(args.scenario))
    names = ", ".join(p.name for p in md_paths)
    if not blocks:
        print(f"No ```dql blocks found in {names}")
        return 0

    print(f"Validating {names} — {len(blocks)} DQL block(s) on environment '{args.environment}'")
    print("=" * 60)

    placeholders: dict[str, str] = {"LINK_HOST": _PF.host_of(args.environment)}
    passed = failed = skipped = 0
    last_producer_records: list[dict] = []

    for i, raw_dql in enumerate(blocks, 1):
        print(f"\n[Block {i}]")
        first_line = raw_dql.splitlines()[0] if raw_dql.splitlines() else "(empty)"
        print(f"  {first_line[:80]}")

        # --- Substitute what we have so far ---
        try:
            substituted = pf.substitute_placeholders(
                raw_dql, placeholders, pass_through_unknown=True
            )
        except KeyError as e:
            print(f"  SKIP — placeholder error: {e}")
            skipped += 1
            continue

        # --- Handle chained consumer (waterfall) ---
        if is_chained_consumer(substituted):
            # Need trace_id from the previous producer block
            trace_id = None
            for rec in last_producer_records:
                candidate = rec.get("trace_id")
                if candidate:
                    trace_id = str(candidate)
                    break

            if not trace_id:
                print("  SKIP — {{TRACE_ID}} needed but no trace_id in prior result")
                skipped += 1
                continue

            substituted = substituted.replace("{{TRACE_ID}}", trace_id)
            print(f"  NOTE — chained: substituted TRACE_ID = {trace_id[:16]}...")

        single_line = strip_dql_comments(substituted)
        if not single_line:
            print("  SKIP — empty after stripping comments")
            skipped += 1
            continue

        # --- Check for still-unresolved tokens ---
        tokens_left = remaining_tokens(single_line)
        if tokens_left:
            unresolvable = [t for t in tokens_left if t not in RUNTIME_ONLY]
            if unresolvable:
                print(f"  SKIP — unresolved tokens (not in state or RUNTIME_ONLY): {unresolvable}")
                skipped += 1
                continue
            # Only runtime-only tokens left — should have been handled above
            print(f"  SKIP — runtime-only tokens remain and no live value available: {tokens_left}")
            skipped += 1
            continue

        # --- Run the query ---
        rc, out, _ = pf.run_dtctl(
            "query", single_line, "-o", "json", "--max-field-chars", "0", "-M=all"
        )
        envelope = pf.parse_envelope(out)

        if rc == 0 and envelope and envelope.get("ok"):
            records = pf._flatten_records(envelope)
            total = envelope.get("context", {}).get("total", len(records))
            ms = envelope.get("metadata", {}).get("executionTimeMilliseconds", "?")
            scanned = envelope.get("metadata", {}).get("scannedRecords", "?")
            print(f"  PASS — {total} record(s) in {ms}ms, {scanned} records scanned")
            passed += 1

            if showcase:
                harvest_showcase_state(pf, envelope, placeholders)

            # --- If this was the resolver, extract session state ---
            elif is_resolver_block(raw_dql) and "PROBLEM_ID" not in placeholders:
                state = extract_state_from_resolver(pf, envelope)
                if state.get("PROBLEM_ID"):
                    placeholders.update(state)
                    print(f"  INFO — resolver: problem={state['PROBLEM_ID']}, "
                          f"mode={'live_active' if 'ACTIVE' in str(pf._flatten_records(envelope)[0].get('status','')) else 'live_recent'}")
                    assert_window(pf, envelope)
                else:
                    print("  WARN — resolver returned rows but no problem_id — "
                          "downstream DQL substitution will fail")

            # --- If this was the chained producer, save records for waterfall ---
            if is_chained_producer(raw_dql) and records:
                last_producer_records = records

        else:
            print(f"  FAIL — rc={rc}")
            if out:
                print(f"  output: {out[:300]}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")

    if showcase and "PROBLEM_ID" not in placeholders:
        print("WARN — no beat returned a problem_id; the problem deep link stays a template")
    elif not showcase and "PROBLEM_ID" not in placeholders:
        print("WARN — no resolver block ran successfully; beat DQL results may not reflect "
              "real substitution")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
