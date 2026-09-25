"""The automatic handoff-drafting hook (`components/issues/draft.py`): the moment the main
pipeline's own validation/invalidation machinery proves a genuine upstream-content defect
(`cli.py::run_present`'s call to `bundle/seal.py::invalidate_bundle`), the matching
`UpstreamDefectHandoff` artifact is created without a separate, manually-invoked CLI subcommand
(docs/investigations/12-supervisor-and-production-reassessment.md section 6). Modeled directly on
the real `aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp` finding: `BC-02` failed at `causal_stage
EXTRACTING` because `install_command:cmake` went `UNRESOLVED` (docs/DECISION_LOG.md 2026-09-23
10:31 UTC; candidates/aspose-cells-foss__Aspose.Cells-FOSS-for-Cpp/.../manifest.json's own
`invalidated` block: `{"check": "BC-02", "causal_stage": "EXTRACTING", ...}`)."""

from __future__ import annotations

import json
from pathlib import Path

from repository_presenter.components.issues.draft import (
    draft_handoff,
    eligible_for_handoff,
    handoff_path,
    record_handoff_if_new,
)
from repository_presenter.components.issues.ledger import load_ledger, lookup
from repository_presenter.components.issues.model import IssueRef, load_handoff, write_handoff
from repository_presenter.core.facts import Evidence, Fact, FactsDocument

REPOSITORY = "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp"
REVISION = "9" + "f" * 39  # a well-formed 40-hex placeholder, distinct from the real revision


def _bc02_check(*, causal_stage: str | None = "EXTRACTING", check_id: str = "BC-02") -> dict:
    return {
        "id": check_id,
        "version": "1",
        "verdict": "FAIL",
        "causal_stage": causal_stage,
        "details": [
            "install_command:cmake is UNRESOLVED: package registry: none could not be read"
        ],
    }


def _facts(*facts: Fact) -> FactsDocument:
    return FactsDocument(repository=REPOSITORY, source_revision=REVISION, facts=tuple(facts))


def _unresolved_install_command() -> Fact:
    # The real shape (facts.json for the trigger case): a source-build install command that
    # never proved, because the verified-source-build promotion never fired (the build itself
    # failed, e.g. on the repository's own upstream trigraph defect).
    return Fact(
        "install_command:cmake",
        "install_command",
        "cmake -S . -B build\ncmake --build build",
        (
            Evidence(
                "CMakeLists.txt",
                "source build for the CMake project the manifest declares; C++ has no package "
                "registry to install from",
            ),
            Evidence("no package registry", "package registry: none could not be read"),
        ),
        polarity="UNRESOLVED",
        confidence=0.5,
    )


def _supported_install_command() -> Fact:
    return Fact(
        "install_command:cmake",
        "install_command",
        "cmake -S . -B build\ncmake --build build",
        (Evidence("CMakeLists.txt", "verified source build: every step exited 0"),),
        polarity="SUPPORTED",
    )


# --- eligible_for_handoff: the conservative check-shape gate -----------------------------------


def test_bc02_at_extracting_is_eligible() -> None:
    assert eligible_for_handoff(_bc02_check()) is True


def test_bc02_at_a_revisable_stage_is_not_eligible() -> None:
    # BC-02's own "the Installation section does not render ..." branch raises COMPOSING, not
    # EXTRACTING - that is about the candidate's own prose, never the target repository.
    assert eligible_for_handoff(_bc02_check(causal_stage="COMPOSING")) is False


def test_bc01_at_extracting_is_not_eligible() -> None:
    # BC-01 raises EXTRACTING for reasons that are this codebase's own snapshot/extraction
    # integrity (an unpinned revision, a fact with no evidence) - never about the target
    # repository's content (investigation 03 section 2's boundary case).
    assert eligible_for_handoff(_bc02_check(check_id="BC-01")) is False


def test_bc10_review_failure_is_never_eligible() -> None:
    assert eligible_for_handoff({"id": "BC-10", "causal_stage": "PLANNING"}) is False


def test_a_check_with_no_causal_stage_is_not_eligible() -> None:
    assert eligible_for_handoff(_bc02_check(causal_stage=None)) is False


# --- draft_handoff: genuine defect drafts, everything else fails closed ------------------------


def test_genuine_upstream_defect_drafts_a_valid_handoff() -> None:
    handoff = draft_handoff(
        repository=REPOSITORY,
        source_revision=REVISION,
        check=_bc02_check(),
        facts=_facts(_unresolved_install_command()),
    )
    assert handoff is not None
    assert handoff.repository == REPOSITORY
    assert handoff.source_revision == REVISION
    assert handoff.triggering_check.id == "BC-02"
    assert handoff.triggering_check.causal_stage == "EXTRACTING"
    assert handoff.status == "HANDOFF_PENDING"
    assert handoff.issue_ref is None
    assert handoff.defect_fingerprint.startswith("sha256:")
    assert len(handoff.defect_fingerprint) == len("sha256:") + 64
    assert len(handoff.evidence) == 2
    assert handoff.evidence[0].path == "CMakeLists.txt"
    assert "install_command:cmake" in handoff.claim
    assert "UNRESOLVED" in handoff.claim
    assert handoff.defect_fingerprint in handoff.suggested_issue_body


def test_an_internal_toolchain_check_never_drafts_even_at_extracting() -> None:
    # BC-01 (this codebase's own revision-pin/evidence-integrity check) fails at EXTRACTING too,
    # but it is not in the small, closed, checkable set this hook knows how to draft from.
    assert (
        draft_handoff(
            repository=REPOSITORY,
            source_revision=REVISION,
            check=_bc02_check(check_id="BC-01"),
            facts=_facts(_unresolved_install_command()),
        )
        is None
    )


def test_bc02_failing_at_a_revisable_stage_never_drafts() -> None:
    assert (
        draft_handoff(
            repository=REPOSITORY,
            source_revision=REVISION,
            check=_bc02_check(causal_stage="COMPOSING"),
            facts=_facts(_unresolved_install_command()),
        )
        is None
    )


def test_bc02_at_extracting_with_no_offending_fact_never_drafts() -> None:
    # The check id/stage match, but this run's own facts do not back it (a synthetic/unrelated
    # failure, or a check-version change) - fails closed rather than guessing.
    assert (
        draft_handoff(
            repository=REPOSITORY,
            source_revision=REVISION,
            check=_bc02_check(),
            facts=_facts(_supported_install_command()),
        )
        is None
    )


def test_bc02_at_extracting_with_no_install_command_fact_at_all_never_drafts() -> None:
    assert (
        draft_handoff(
            repository=REPOSITORY, source_revision=REVISION, check=_bc02_check(), facts=_facts()
        )
        is None
    )


def test_draft_is_deterministic_across_equivalent_runs() -> None:
    first = draft_handoff(
        repository=REPOSITORY,
        source_revision=REVISION,
        check=_bc02_check(),
        facts=_facts(_unresolved_install_command()),
    )
    second = draft_handoff(
        repository=REPOSITORY,
        source_revision=REVISION,
        check=_bc02_check(),
        facts=_facts(_unresolved_install_command()),
    )
    assert first is not None and second is not None
    assert first.defect_fingerprint == second.defect_fingerprint


# --- record_handoff_if_new: dedup against the ledger, writes on disk ---------------------------


def test_record_handoff_if_new_writes_a_schema_shaped_artifact(tmp_path: Path) -> None:
    root = tmp_path / "upstream-defects"
    written = record_handoff_if_new(
        root,
        repository=REPOSITORY,
        source_revision=REVISION,
        check=_bc02_check(),
        facts=_facts(_unresolved_install_command()),
    )
    assert written is not None
    assert written.is_file()
    handoff = load_handoff(written)  # fails closed on a malformed artifact; this must parse
    assert handoff.repository == REPOSITORY
    assert handoff.status == "HANDOFF_PENDING"
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["issue_ref"] is None


def test_record_handoff_if_new_never_duplicates_the_same_defect(tmp_path: Path) -> None:
    root = tmp_path / "upstream-defects"
    first = record_handoff_if_new(
        root,
        repository=REPOSITORY,
        source_revision=REVISION,
        check=_bc02_check(),
        facts=_facts(_unresolved_install_command()),
    )
    assert first is not None
    second = record_handoff_if_new(
        root,
        repository=REPOSITORY,
        source_revision=REVISION,
        check=_bc02_check(),
        facts=_facts(_unresolved_install_command()),
    )
    assert second is None  # dedup by {repository, defect_fingerprint}: no second artifact
    ledger = load_ledger(root)
    assert len(ledger) == 1


def test_record_handoff_if_new_respects_a_fingerprint_already_on_record(tmp_path: Path) -> None:
    root = tmp_path / "upstream-defects"
    handoff = draft_handoff(
        repository=REPOSITORY,
        source_revision=REVISION,
        check=_bc02_check(),
        facts=_facts(_unresolved_install_command()),
    )
    assert handoff is not None
    # Simulate a handoff already filed for this exact defect (a human moved it past
    # HANDOFF_PENDING) - dedup must key on the fingerprint, not the status.
    path = handoff_path(root, handoff)
    path.parent.mkdir(parents=True, exist_ok=True)
    from dataclasses import replace

    filed = replace(
        handoff, status="FILED", issue_ref=IssueRef(number=1, url="https://github.com/o/r/issues/1")
    )
    write_handoff(filed, path)
    result = record_handoff_if_new(
        root,
        repository=REPOSITORY,
        source_revision=REVISION,
        check=_bc02_check(),
        facts=_facts(_unresolved_install_command()),
    )
    assert result is None
    ledger = load_ledger(root)
    entry = lookup(ledger, REPOSITORY, handoff.defect_fingerprint)
    assert entry is not None and entry.last_observed_state == "FILED"


def test_record_handoff_if_new_is_none_for_an_internal_failure(tmp_path: Path) -> None:
    root = tmp_path / "upstream-defects"
    result = record_handoff_if_new(
        root,
        repository=REPOSITORY,
        source_revision=REVISION,
        check=_bc02_check(check_id="BC-01"),
        facts=_facts(_unresolved_install_command()),
    )
    assert result is None
    assert not root.exists() or load_ledger(root) == {}
