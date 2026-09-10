"""Promotes tools/reviewer/'s bundle-consistency audits into real, CI-run test coverage.

`tools/reviewer/audit_link_completeness.py` and `audit_preserved_api_lists.py` already expose
`audit_one(manifest_dir: Path) -> list[str]`; importing them here is `tests/` reaching into
`tools/reviewer/*`, an unrestricted direction (only `src/` importing `tools/` is forbidden). Three
more rules of the same shape were added alongside this file: `audit_install_claims.py`,
`audit_format_claims.py`, `audit_second_reader_ledger.py` (PHASE0/TB-10+RC-07) - their own
docstrings record the real portfolio data each was checked against before being trusted.

`tools/reviewer/*`'s scripts all glob every historical revision under `candidates/*/*`, broader
than `test_sealed_bytes.py`'s own `CURRENT`-only walk (`sealed_bundles()` there resolves only the
one revision each `candidates/*/CURRENT` file names). This file keeps that broader scope
deliberately: a gap in a superseded revision still proves the historical record was inconsistent
at the time it was sealed, which `CURRENT`-only walking would hide entirely.

Two of the five rules have real, currently-live findings in the sealed portfolio today - not
schema noise, genuine pre-existing gaps in bundles sealed before their respective fix landed,
confirmed by running each script directly against `candidates/` before writing anything here (see
each `KNOWN_*` dict below for the exact finding counts observed). The fix in each case prevents a
*new* gap of that shape from being sealed; it does not retroactively repair an already-frozen
bundle. `xfail(strict=True)` pins today's exact known set, so a newly-sealed candidate reproducing
the same defect shape fails loudly instead of blending into an already-red baseline, and so a
future re-seal that finally clears a known gap shows up as XPASS (forcing this file to be updated)
instead of silently staying invisible.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import tools.reviewer.audit_format_claims as audit_format_claims
import tools.reviewer.audit_install_claims as audit_install_claims
import tools.reviewer.audit_link_completeness as audit_link_completeness
import tools.reviewer.audit_preserved_api_lists as audit_preserved_api_lists
import tools.reviewer.audit_second_reader_ledger as audit_second_reader_ledger

from support import REPO_ROOT

CANDIDATES = REPO_ROOT / "candidates"


def manifest_dirs() -> list[Path]:
    return sorted(p for p in CANDIDATES.glob("*/*") if p.is_dir())


def _label(manifest_dir: Path) -> str:
    return f"{manifest_dir.parent.name}/{manifest_dir.name[:12]}"


def _param(manifest_dir: Path, known: dict[str, str]) -> Any:
    label = _label(manifest_dir)
    reason = known.get(label)
    marks = [pytest.mark.xfail(reason=reason, strict=True)] if reason else []
    return pytest.param(manifest_dir, marks=marks, id=label)


def test_there_is_at_least_one_manifest_directory_to_hold_the_audits_to() -> None:
    assert manifest_dirs(), "no sealed candidate on disk; the audits would pass vacuously"


# --- promoted: audit_link_completeness (TB-10) -----------------------------------------------

# Both are CURRENT candidates, sealed before planning.py's VERIFIED_REWRITE/plan.json "links"
# fix landed (2026-09-08) - confirmed 2026-09-10 by running audit_link_completeness.py directly:
# 8 gaps total, all in these two directories, none elsewhere across all 9 manifest dirs.
LINK_COMPLETENESS_KNOWN = {
    "aspose-3d-foss__Aspose.3D-FOSS-for-Java/e308de588886": (
        "pre-existing gap (2 link_target citations absent from plan.json's links), sealed "
        "before the VERIFIED_REWRITE/links fix landed - see audit_link_completeness.py's "
        "own docstring"
    ),
    "aspose-email-foss__Aspose.Email-FOSS-for-Python/10a906b48c0c": (
        "pre-existing gap (6 link_target citations absent from plan.json's links), sealed "
        "before the VERIFIED_REWRITE/links fix landed - see audit_link_completeness.py's "
        "own docstring"
    ),
}


@pytest.mark.parametrize(
    "manifest_dir", [_param(d, LINK_COMPLETENESS_KNOWN) for d in manifest_dirs()]
)
def test_no_link_completeness_gap(manifest_dir: Path) -> None:
    assert audit_link_completeness.audit_one(manifest_dir) == []


# --- promoted: audit_preserved_api_lists (RC-07) ----------------------------------------------

# All three are CURRENT candidates. audit_preserved_api_lists.py's own docstring documents this
# as a diagnostic sweep, not a fix - RC-06 addresses the root cause upstream (extraction-time
# unit-granularity) for newly-sealed candidates only. Confirmed 2026-09-10: 12 suspects total,
# all in these three directories, none elsewhere.
PRESERVED_API_LISTS_KNOWN = {
    "aspose-cells-foss__Aspose.Cells-FOSS-for-.NET/941814fd138d": (
        "pre-existing module-level-only preserved list (5 units), predates RC-06's "
        "extraction-time fix - see audit_preserved_api_lists.py's own docstring"
    ),
    "aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp/9f852d0ff1cf": (
        "pre-existing module-level-only preserved list (1 unit), predates RC-06's "
        "extraction-time fix - see audit_preserved_api_lists.py's own docstring"
    ),
    "aspose-pdf-foss__Aspose.PDF-FOSS-for-Java/099e70a8b309": (
        "pre-existing module-level-only preserved list (6 units), predates RC-06's "
        "extraction-time fix - see audit_preserved_api_lists.py's own docstring"
    ),
}


@pytest.mark.parametrize(
    "manifest_dir", [_param(d, PRESERVED_API_LISTS_KNOWN) for d in manifest_dirs()]
)
def test_no_preserved_api_list_duplication_suspect(manifest_dir: Path) -> None:
    assert audit_preserved_api_lists.audit_one(manifest_dir) == []


# --- new: audit_install_claims (TB-10+RC-07) ---------------------------------------------------

# The only non-CURRENT manifest directory in the portfolio (Aspose.3D-Python's superseded prior
# revision) predates examples.json's introduction entirely (EVAL-01 companion work, this pass) -
# a schema-age gap, not a claim/ledger contradiction.
INSTALL_CLAIMS_KNOWN = {
    "aspose-3d-foss__Aspose.3D-FOSS-for-Python/d9f3bfe50d47": (
        "superseded revision predates examples.json's introduction - no receipts to check "
        "build_verified against at all"
    ),
}


@pytest.mark.parametrize("manifest_dir", [_param(d, INSTALL_CLAIMS_KNOWN) for d in manifest_dirs()])
def test_no_install_claim_ledger_contradiction(manifest_dir: Path) -> None:
    assert audit_install_claims.audit_one(manifest_dir) == []


def test_install_claim_rule_flags_a_verified_source_build_with_no_corroborating_receipt(
    tmp_path: Path,
) -> None:
    facts = {
        "facts": [
            {
                "id": "install_command:0",
                "kind": "install_command",
                "polarity": "SUPPORTED",
                "value": "cmake -S . -B build",
                "evidence": [
                    {
                        "path": "CMakeLists.txt",
                        "detail": (
                            "install command for the CMake project the manifest declares "
                            "package registry: none could not be read verified source "
                            "build: an example executed against this revision"
                        ),
                    }
                ],
            }
        ]
    }
    examples = [{"ordinal": 1, "outcome": "EXECUTED", "build_verified": False}]
    (tmp_path / "facts.json").write_text(json.dumps(facts), encoding="utf-8")
    (tmp_path / "examples.json").write_text(json.dumps(examples), encoding="utf-8")
    findings = audit_install_claims.audit_one(tmp_path)
    assert len(findings) == 1
    assert "install_command:0" in findings[0]
    assert "no EXECUTED example receipt records build_verified=true" in findings[0]


def test_install_claim_rule_does_not_flag_a_receipt_missing_build_verified_entirely(
    tmp_path: Path,
) -> None:
    """The exact real-portfolio shape (both actual 'verified source build' candidates): every
    receipt predates the build_verified field, so the key is absent, not false. Confirmed 2026-09-10
    against aspose-cells-foss's real Cpp and Rust sealed bundles before writing this test."""
    facts = {
        "facts": [
            {
                "id": "install_command:0",
                "kind": "install_command",
                "polarity": "SUPPORTED",
                "value": "cargo build",
                "evidence": [{"path": "Cargo.toml", "detail": "verified source build: ..."}],
            }
        ]
    }
    examples = [{"ordinal": 1, "outcome": "EXECUTED"}]
    (tmp_path / "facts.json").write_text(json.dumps(facts), encoding="utf-8")
    (tmp_path / "examples.json").write_text(json.dumps(examples), encoding="utf-8")
    assert audit_install_claims.audit_one(tmp_path) == []


# --- new: audit_format_claims (TB-10+RC-07) -----------------------------------------------------

FORMAT_CLAIMS_KNOWN = {
    "aspose-3d-foss__Aspose.3D-FOSS-for-Python/d9f3bfe50d47": (
        "superseded revision predates examples.json's introduction - no receipts to check "
        "format-claim evidence against at all"
    ),
}


@pytest.mark.parametrize("manifest_dir", [_param(d, FORMAT_CLAIMS_KNOWN) for d in manifest_dirs()])
def test_no_format_claim_drift_from_its_own_cited_receipt(manifest_dir: Path) -> None:
    assert audit_format_claims.audit_one(manifest_dir) == []


def test_format_claim_rule_flags_evidence_that_no_longer_matches_its_own_cited_receipt(
    tmp_path: Path,
) -> None:
    facts = {
        "facts": [
            {
                "id": "format:input.png",
                "kind": "format",
                "value": ".png",
                "evidence": [{"path": "examples.json", "detail": "example 1: EXECUTED; exit 0"}],
            }
        ]
    }
    examples = [{"ordinal": 1, "outcome": "FAILED"}]
    (tmp_path / "facts.json").write_text(json.dumps(facts), encoding="utf-8")
    (tmp_path / "examples.json").write_text(json.dumps(examples), encoding="utf-8")
    findings = audit_format_claims.audit_one(tmp_path)
    assert len(findings) == 1
    assert "format:input.png" in findings[0]
    assert "'EXECUTED'" in findings[0]
    assert "'FAILED'" in findings[0]


def test_format_claim_rule_does_not_flag_evidence_that_still_agrees_with_its_receipt(
    tmp_path: Path,
) -> None:
    facts = {
        "facts": [
            {
                "id": "format:input.png",
                "kind": "format",
                "value": ".png",
                "evidence": [{"path": "examples.json", "detail": "example 1: EXECUTED; exit 0"}],
            }
        ]
    }
    examples = [{"ordinal": 1, "outcome": "EXECUTED"}]
    (tmp_path / "facts.json").write_text(json.dumps(facts), encoding="utf-8")
    (tmp_path / "examples.json").write_text(json.dumps(examples), encoding="utf-8")
    assert audit_format_claims.audit_one(tmp_path) == []


# --- new: audit_second_reader_ledger (TB-10+RC-07) ----------------------------------------------


@pytest.mark.parametrize("manifest_dir", [_param(d, {}) for d in manifest_dirs()])
def test_second_reader_claim_is_backed_by_the_calls_ledger(manifest_dir: Path) -> None:
    assert audit_second_reader_ledger.audit_one(manifest_dir) == []


def test_second_reader_ledger_rule_flags_a_claimed_second_read_with_only_one_logical_call(
    tmp_path: Path,
) -> None:
    review = {"second_reader": {"read": True, "corroborated": ["abc"]}}
    calls = [
        {"job": "independent_review", "outcome": "success", "logical_call_id": "L1"},
        {"job": "independent_review", "outcome": "cache_reuse", "logical_call_id": "L1"},
    ]
    (tmp_path / "review.json").write_text(json.dumps(review), encoding="utf-8")
    (tmp_path / "calls.jsonl").write_text("\n".join(json.dumps(c) for c in calls), encoding="utf-8")
    findings = audit_second_reader_ledger.audit_one(tmp_path)
    assert len(findings) == 1
    assert "only 1 distinct logical_call_id" in findings[0]


def test_second_reader_ledger_rule_does_not_flag_two_distinct_logical_calls(
    tmp_path: Path,
) -> None:
    review = {"second_reader": {"read": True, "corroborated": ["abc"]}}
    calls = [
        {"job": "independent_review", "outcome": "success", "logical_call_id": "L1"},
        {"job": "independent_review", "outcome": "success", "logical_call_id": "L2"},
        {"job": "independent_review", "outcome": "cache_reuse", "logical_call_id": "L2"},
    ]
    (tmp_path / "review.json").write_text(json.dumps(review), encoding="utf-8")
    (tmp_path / "calls.jsonl").write_text("\n".join(json.dumps(c) for c in calls), encoding="utf-8")
    assert audit_second_reader_ledger.audit_one(tmp_path) == []


def test_second_reader_ledger_rule_ignores_non_terminal_retries(tmp_path: Path) -> None:
    """A retried-then-succeeded single reader (response_invalid then success on the same logical
    call) must not be counted as a second reader just because two calls happened."""
    review = {"second_reader": {"read": True, "corroborated": ["abc"]}}
    calls = [
        {"job": "independent_review", "outcome": "response_invalid", "logical_call_id": "L1"},
        {"job": "independent_review", "outcome": "success", "logical_call_id": "L1"},
    ]
    (tmp_path / "review.json").write_text(json.dumps(review), encoding="utf-8")
    (tmp_path / "calls.jsonl").write_text("\n".join(json.dumps(c) for c in calls), encoding="utf-8")
    findings = audit_second_reader_ledger.audit_one(tmp_path)
    assert len(findings) == 1


def test_second_reader_ledger_rule_says_nothing_when_no_second_read_is_claimed(
    tmp_path: Path,
) -> None:
    review = {"second_reader": {"read": False, "corroborated": []}}
    calls = [{"job": "independent_review", "outcome": "success", "logical_call_id": "L1"}]
    (tmp_path / "review.json").write_text(json.dumps(review), encoding="utf-8")
    (tmp_path / "calls.jsonl").write_text("\n".join(json.dumps(c) for c in calls), encoding="utf-8")
    assert audit_second_reader_ledger.audit_one(tmp_path) == []
