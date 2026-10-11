"""PACKAGE_METADATA_SOURCE_URL (TC-ISS-A): a published package whose registry metadata does not
name its own source repository.

The check is registry-sourced: the observation is what the package registry says (PyPI's
``home_page`` and ``project_urls``), never the repository tree, so it is not a pure-observation
class in ``classes.py`` (whose schema enum is closed); it is a redetector registered under its own
check id in ``redetect.py``, the way ``BC-02`` replays a registry read. Every read is injected: no
test reaches the network."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from repository_presenter.components.issues.approval import evidence_digest, handoff_id
from repository_presenter.components.issues.ledger import load_ledger
from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    IssueRef,
    TriggeringCheck,
    load_handoff,
)
from repository_presenter.components.issues.quality import issue_quality_findings
from repository_presenter.components.issues.readiness import load_reverifications
from repository_presenter.components.issues.redetect import (
    RedetectionReads,
    redetect,
    registered_check_ids,
    replay_gap,
)
from repository_presenter.core.github.read_client import DefaultBranchRead
from repository_presenter.core.package_registry import RegistryObservation
from support import REPO_ROOT

CHECK_ID = "PACKAGE_METADATA_SOURCE_URL"
UPSTREAM_ROOT = REPO_ROOT / "evidence" / "upstream-defects"
REPO_3D = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
REPO_PAGE = "aspose-page-foss/Aspose.Page-FOSS-for-Python"
REVISION = "a" * 40


def _handoff(
    repository: str = REPO_3D, package: str = "aspose-3d-foss", *, status: str = "HANDOFF_PENDING"
) -> Handoff:
    filed = status == "FILED"
    return Handoff(
        schema_version=1,
        repository=repository,
        source_revision=REVISION,
        defect_fingerprint="sha256:" + "b" * 64,
        triggering_check=TriggeringCheck(id=CHECK_ID, version="1", causal_stage="EXTRACTING"),
        evidence=(
            EvidenceEntry(path=f"https://pypi.org/pypi/{package}/json", detail="project_urls = {}"),
            EvidenceEntry(path="setup.py", detail="line 15: url"),
        ),
        claim="registry metadata names no source repository",
        suggested_issue_title="Product: x",
        suggested_issue_body="body",
        status="FILED" if filed else "HANDOFF_PENDING",
        issue_ref=IssueRef(number=7, url="https://github.com/o/r/issues/7") if filed else None,
        close_reason=None,
        defect_class=None,
    )


def _reads(observation: RegistryObservation, *, head: str | None = REVISION) -> RedetectionReads:
    return RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=head, branch="main", error=None if head else "boom"
        ),
        observe_pypi=lambda name, version, **_: observation,
    )


def _observation(
    urls: tuple[str, ...], *, found: bool = True, error: str | None = None
) -> RegistryObservation:
    return RegistryObservation(
        "aspose-3d-foss",
        "https://pypi.org/pypi/aspose-3d-foss/json",
        found=found,
        latest_version="26.1.0",
        status=200,
        project_urls=urls,
        error=error,
    )


def test_the_check_id_has_a_registered_redetector() -> None:
    assert CHECK_ID in registered_check_ids()


# The negative control: a registry that lists a URL for another repository, and one that lists no
# URL at all, both still fire; one naming this repository is resolved.


def test_fires_when_the_registry_lists_only_a_url_for_another_repository() -> None:
    reads = _reads(_observation(("https://github.com/aspose-3d/Aspose.3D-for-Python",)))
    result = redetect(_handoff(), reads=reads)
    assert result.still_fires is True
    assert "aspose-3d-foss" in result.note


def test_fires_when_the_registry_lists_no_url_at_all() -> None:
    reads = _reads(_observation(()))
    assert redetect(_handoff(), reads=reads).still_fires is True


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "git+https://github.com/Aspose-3D-FOSS/Aspose.3D-FOSS-for-Python.git",
        "https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/issues",
    ],
)
def test_resolved_once_a_registry_url_names_this_repository(url: str) -> None:
    result = redetect(_handoff(), reads=_reads(_observation(("https://example.com/x", url))))
    assert result.still_fires is False
    assert result.proposed_status is None  # not filed: nothing to close


def test_a_filed_handoff_proposes_resolution_once_the_url_is_fixed() -> None:
    reads = _reads(_observation(("https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python",)))
    result = redetect(_handoff(status="FILED"), reads=reads)
    assert result.still_fires is False
    assert result.proposed_status == "RESOLVED_UPSTREAM"


def test_a_registry_error_is_inconclusive_never_a_resolution() -> None:
    reads = _reads(_observation((), found=False, error="ConnectError: timeout"))
    result = redetect(_handoff(status="FILED"), reads=reads)
    assert result.still_fires is None
    assert result.proposed_status is None


def test_a_vanished_package_is_inconclusive() -> None:
    result = redetect(_handoff(), reads=_reads(_observation((), found=False)))
    assert result.still_fires is None
    assert "no longer" in result.note or "not found" in result.note


def test_an_unreadable_head_is_inconclusive() -> None:
    reads = _reads(_observation(()), head=None)
    assert redetect(_handoff(), reads=reads).still_fires is None


def test_a_handoff_without_exactly_one_registry_identity_has_a_replay_gap() -> None:
    none = replace(_handoff(), evidence=(EvidenceEntry(path="setup.py", detail="x"),))
    assert replay_gap(none) is not None
    two = replace(
        _handoff(),
        evidence=(
            EvidenceEntry(path="https://pypi.org/pypi/a/json", detail="x"),
            EvidenceEntry(path="https://pypi.org/pypi/b/json", detail="x"),
        ),
    )
    assert replay_gap(two) is not None
    assert replay_gap(_handoff()) is None


# The two committed handoffs (aspose-3d-foss and aspose-page-foss, found by the cut-2 ownership
# work) hold the same bars as every other CONFIRMED handoff.


def _committed() -> list[Handoff]:
    handoffs = (load_handoff(entry.path) for entry in load_ledger(UPSTREAM_ROOT).values())
    ours = sorted((h for h in handoffs if _is_ours(h)), key=lambda h: h.repository)
    assert len(ours) == 2, "the two committed handoffs are missing"
    return ours


def _is_ours(handoff: Handoff) -> bool:
    return handoff.triggering_check.id == CHECK_ID


def test_both_repositories_have_a_pending_handoff() -> None:
    assert sorted(h.repository for h in _committed()) == [REPO_3D, REPO_PAGE]
    assert all(h.status == "HANDOFF_PENDING" for h in _committed())


def test_committed_handoffs_pass_the_issue_quality_gate_and_replay_cleanly() -> None:
    for handoff in _committed():
        assert issue_quality_findings(handoff) == []
        assert replay_gap(handoff) is None
        assert handoff.suggested_issue_body.count("repository-presenter-defect:") == 1


def test_committed_handoffs_are_confirmed_with_a_matching_digest() -> None:
    records = load_reverifications(UPSTREAM_ROOT / "reverification.json")
    for handoff in _committed():
        record = records[handoff_id(handoff)]
        assert record.verdict == "CONFIRMED"
        assert record.evidence_digest == evidence_digest(handoff)
        assert record.live_head_sha == handoff.source_revision
        assert record.method.strip()


def test_committed_handoff_files_are_named_by_their_fingerprint() -> None:
    for path in UPSTREAM_ROOT.rglob("*.json"):
        if path.name == "reverification.json":
            continue
        handoff = load_handoff(path)
        if _is_ours(handoff):
            assert path.stem == handoff.defect_fingerprint.removeprefix("sha256:")
            json.loads(path.read_text(encoding="utf-8"))
