"""The re-detection pass (docs/investigations/03-issue-tracking.md section 6), exercised against
the two real backfilled artifacts named in the task: HTML-Python's BC-02 and TeX-Python's
NOT_PROCESSABLE. Every read is injected (`RedetectionReads`) - no test reaches live network,
matching this suite's own `no_package_registry_network` convention for the package-registry half
and simply never calling the live GitHub defaults for the other."""

from __future__ import annotations

from dataclasses import replace

import pytest

from repository_presenter.components.issues.model import Handoff, IssueRef, load_handoff
from repository_presenter.components.issues.redetect import (
    RedetectionReads,
    RedetectorNotRegisteredError,
    apply_redetection,
    redetect,
    registered_check_ids,
)
from repository_presenter.components.readme.extractors.platforms.python_registry import (
    RegistryObservation,
)
from repository_presenter.core.github.read_client import DefaultBranchRead, FileRead
from support import REPO_ROOT

HTML_PYTHON_HANDOFF = (
    REPO_ROOT
    / "evidence"
    / "upstream-defects"
    / "aspose-html-foss__Aspose.HTML-FOSS-for-Python"
    / "ae9f06b95a4cc18609d64276e4a831bf9260ed6ea9c613f36cf2876478ea849a.json"
)
TEX_PYTHON_HANDOFF = (
    REPO_ROOT
    / "evidence"
    / "upstream-defects"
    / "aspose-tex-foss__Aspose.TeX-FOSS-for-Python"
    / "c00f9615a81bb9f3c77f45df5ded5036d8da0cce6d6dee01634a27b3f3659188.json"
)


def test_registered_check_ids_cover_both_backfilled_shapes() -> None:
    assert registered_check_ids() == ("BC-02", "NOT_PROCESSABLE")


def test_unregistered_check_id_fails_closed() -> None:
    original = load_handoff(HTML_PYTHON_HANDOFF)
    handoff = replace(original, triggering_check=replace(original.triggering_check, id="BC-99"))
    with pytest.raises(RedetectorNotRegisteredError, match="BC-99"):
        redetect(handoff)


# --- BC-02 (HTML-Python: install_command CONTRADICTED against the package registry) ---------


def test_bc02_still_fires_when_the_registry_still_has_no_distribution() -> None:
    handoff = load_handoff(HTML_PYTHON_HANDOFF)
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=handoff.source_revision, branch="main"
        ),
        fetch_file=lambda repository, revision, path, **_: FileRead(
            repository,
            revision,
            path,
            found=True,
            content='build-backend = "setuptools.backends.legacy:build"\n',
        ),
        observe_pypi=lambda name, version, **_: RegistryObservation(
            name, f"https://pypi.org/pypi/{name}/json", found=False, status=404
        ),
    )
    result = redetect(handoff, reads=reads)
    assert result.still_fires is True
    assert result.proposed_status is None
    assert "aspose-html-foss" in result.note
    assert result.revision_drifted is False
    assert any("build-backend" in e.detail for e in result.fresh_evidence if e.detail)


def test_bc02_no_longer_fires_once_the_registry_lists_the_distribution() -> None:
    handoff = load_handoff(HTML_PYTHON_HANDOFF)
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=handoff.source_revision, branch="main"
        ),
        fetch_file=lambda repository, revision, path, **_: FileRead(
            repository,
            revision,
            path,
            found=True,
            content='build-backend = "setuptools.build_meta"\n',
        ),
        observe_pypi=lambda name, version, **_: RegistryObservation(
            name,
            f"https://pypi.org/pypi/{name}/json",
            found=True,
            latest_version="26.1.0",
            manifest_version_published=None,
            status=200,
        ),
    )
    # An unfiled (HANDOFF_PENDING) handoff never gets an automatic status transition, even once
    # the defect is gone - RESOLVED_UPSTREAM requires an issue_ref this handoff does not carry.
    result = redetect(handoff, reads=reads)
    assert result.still_fires is False
    assert result.proposed_status is None

    filed = replace(
        handoff,
        status="FILED",
        issue_ref=IssueRef(number=1, url="https://github.com/aspose-html-foss/x/issues/1"),
    )
    filed_result = redetect(filed, reads=reads)
    assert filed_result.still_fires is False
    assert filed_result.proposed_status == "RESOLVED_UPSTREAM"
    updated = apply_redetection(filed, filed_result)
    assert updated.status == "RESOLVED_UPSTREAM"
    assert updated.issue_ref == filed.issue_ref  # never touched


def test_bc02_registry_error_is_inconclusive_never_a_resolution() -> None:
    handoff = load_handoff(HTML_PYTHON_HANDOFF)
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=handoff.source_revision, branch="main"
        ),
        observe_pypi=lambda name, version, **_: RegistryObservation(
            name, f"https://pypi.org/pypi/{name}/json", found=False, error="ConnectError: timeout"
        ),
    )
    result = redetect(handoff, reads=reads)
    assert result.still_fires is None
    assert result.proposed_status is None
    assert "inconclusive" in result.note


def test_bc02_detects_revision_drift() -> None:
    handoff = load_handoff(HTML_PYTHON_HANDOFF)
    new_revision = "f" * 40
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=new_revision, branch="main"
        ),
        fetch_file=lambda repository, revision, path, **_: FileRead(
            repository, revision, path, found=False
        ),
        observe_pypi=lambda name, version, **_: RegistryObservation(
            name, f"https://pypi.org/pypi/{name}/json", found=False, status=404
        ),
    )
    result = redetect(handoff, reads=reads)
    assert result.revision_drifted is True
    assert result.checked_at_revision == new_revision


def test_bc02_cannot_redetect_without_a_pypi_evidence_url() -> None:
    handoff = load_handoff(HTML_PYTHON_HANDOFF)
    stripped = replace(handoff, evidence=(handoff.evidence[-1],))  # drop the PyPI evidence entry
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=handoff.source_revision, branch="main"
        )
    )
    result = redetect(stripped, reads=reads)
    assert result.still_fires is None
    assert "cannot redetect" in result.note


# --- NOT_PROCESSABLE (TeX-Python: named source paths fail ast.parse) -------------------------


def test_not_processable_still_fires_when_the_entry_point_still_fails_to_parse() -> None:
    handoff = load_handoff(TEX_PYTHON_HANDOFF)
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=handoff.source_revision, branch="main"
        ),
        fetch_file=lambda repository, revision, path, **_: FileRead(
            repository,
            revision,
            path,
            found=True,
            content="def f():\n return 1\n\ndef g():\n if True:\nreturn 2\n",  # bad indent
        ),
    )
    result = redetect(handoff, reads=reads)
    assert result.still_fires is True
    assert result.proposed_status is None
    assert "IndentationError" in "".join(e.detail or "" for e in result.fresh_evidence)


def test_not_processable_no_longer_fires_once_the_named_paths_parse_cleanly() -> None:
    handoff = load_handoff(TEX_PYTHON_HANDOFF)
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=handoff.source_revision, branch="main"
        ),
        fetch_file=lambda repository, revision, path, **_: FileRead(
            repository, revision, path, found=True, content="def f():\n    return 1\n"
        ),
    )
    result = redetect(handoff, reads=reads)
    assert result.still_fires is False
    assert result.proposed_status is None  # HANDOFF_PENDING: never auto-transitioned


def test_not_processable_missing_file_is_inconclusive() -> None:
    handoff = load_handoff(TEX_PYTHON_HANDOFF)
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=handoff.source_revision, branch="main"
        ),
        fetch_file=lambda repository, revision, path, **_: FileRead(
            repository, revision, path, found=False, error=None
        ),
    )
    result = redetect(handoff, reads=reads)
    assert result.still_fires is None
    assert "inconclusive" in result.note


def test_not_processable_cannot_resolve_current_revision_is_inconclusive() -> None:
    handoff = load_handoff(TEX_PYTHON_HANDOFF)
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, error="HTTP 502"
        )
    )
    result = redetect(handoff, reads=reads)
    assert result.still_fires is None
    assert result.checked_at_revision is None
    assert "inconclusive" in result.note


# --- close_reason (G6-W04, docs/investigations/03-issue-tracking.md section 6): "completed" vs
# "not planned" must be a real, evidence-grounded distinction, never a default - exercised against
# both real backfilled artifacts, each driven to FILED first (the only status a RESOLVED_UPSTREAM
# transition may ever be proposed from), matching this task's own acceptance text: a synthetic
# re-run where the check now passes transitions FILED -> RESOLVED_UPSTREAM with the correct reason;
# one where it still fails stays FILED. ------------------------------------------------------


def _as_filed(handoff: Handoff, *, number: int = 1) -> Handoff:
    return replace(
        handoff,
        status="FILED",
        issue_ref=IssueRef(
            number=number, url=f"https://github.com/{handoff.repository}/issues/{number}"
        ),
    )


def _current_live_bc02_version() -> str:
    from repository_presenter.components.readme.validation.registry import BLOCKING_CHECKS

    return next(c.version for c in BLOCKING_CHECKS if c.id == "BC-02")


def test_html_python_filed_handoff_stays_filed_when_the_distribution_is_still_missing() -> None:
    """Proof case 1 (still fails): the real HTML-Python artifact, driven to FILED, re-checked
    against reads that reproduce today's actual state (PyPI still 404) - stays FILED, no status or
    reason proposed."""
    filed = _as_filed(load_handoff(HTML_PYTHON_HANDOFF))
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=filed.source_revision, branch="main"
        ),
        fetch_file=lambda repository, revision, path, **_: FileRead(
            repository,
            revision,
            path,
            found=True,
            content='build-backend = "setuptools.backends.legacy:build"\n',
        ),
        observe_pypi=lambda name, version, **_: RegistryObservation(
            name, f"https://pypi.org/pypi/{name}/json", found=False, status=404
        ),
    )
    result = redetect(filed, reads=reads)
    assert result.still_fires is True
    assert result.proposed_status is None
    assert result.proposed_close_reason is None
    updated = apply_redetection(filed, result)
    assert updated is filed
    assert updated.status == "FILED"


def test_html_python_resolves_not_planned_when_the_checks_own_version_has_moved_on() -> None:
    """Proof case 2 (now passes): the real HTML-Python artifact's own `triggering_check.version`
    is "2" (read directly off the committed artifact below), but `validation/registry.py`'s live
    `BLOCKING_CHECKS` now has BC-02 at version "3" - a real, present check-version drift, not a
    constructed one. Even though the synthetic read shows the registry now listing the
    distribution (the defect's own evidence gone), the correct reason is "not planned": what BC-02
    itself judges moved since this handoff was filed, so "the maintainers fixed it" cannot be
    asserted - this is exactly the "check-version change" half of section 6's two reasons, not
    defaulted to "completed" just because the fact flipped."""
    original = load_handoff(HTML_PYTHON_HANDOFF)
    assert original.triggering_check.version == "2"
    assert original.triggering_check.id == "BC-02"
    assert _current_live_bc02_version() != "2", (
        "this proof needs a real version drift between the handoff's filed-at version and "
        'BLOCKING_CHECKS\' current one; if BC-02 is ever bumped back to "2" this assertion (and '
        "the real artifact's own triggering_check.version) must be revisited, never silently kept"
    )
    filed = _as_filed(original)
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=filed.source_revision, branch="main"
        ),
        fetch_file=lambda repository, revision, path, **_: FileRead(
            repository,
            revision,
            path,
            found=True,
            content='build-backend = "setuptools.build_meta"\n',
        ),
        observe_pypi=lambda name, version, **_: RegistryObservation(
            name,
            f"https://pypi.org/pypi/{name}/json",
            found=True,
            latest_version="26.1.0",
            manifest_version_published=None,
            status=200,
        ),
    )
    result = redetect(filed, reads=reads)
    assert result.still_fires is False
    assert result.proposed_status == "RESOLVED_UPSTREAM"
    assert result.proposed_close_reason == "not planned"
    updated = apply_redetection(filed, result)
    assert updated.status == "RESOLVED_UPSTREAM"
    assert updated.close_reason == "not planned"


def test_html_python_resolves_completed_when_filed_at_current_version_and_revision_moved() -> None:
    """The "completed" counterpart to the test above, isolating the one variable that actually
    distinguishes the two reasons: a handoff filed at the *current* BC-02 version (so no
    check-version drift muddies the read), re-checked at a revision that has genuinely moved since
    filing, where the defect's own evidence is gone - the literal "the maintainers fixed it"
    shape. Built from the same real HTML-Python evidence/claim/fingerprint, only
    `triggering_check.version` bumped to match today's live registry (never a fabricated finding -
    same repository, same fingerprint, same evidence, only the one input this decision is
    sensitive to isolated)."""
    current_version = _current_live_bc02_version()
    loaded = load_handoff(HTML_PYTHON_HANDOFF)
    original = replace(
        loaded, triggering_check=replace(loaded.triggering_check, version=current_version)
    )
    filed = _as_filed(original)
    new_revision = "f" * 40
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=new_revision, branch="main"
        ),
        fetch_file=lambda repository, revision, path, **_: FileRead(
            repository,
            revision,
            path,
            found=True,
            content='build-backend = "setuptools.build_meta"\n',
        ),
        observe_pypi=lambda name, version, **_: RegistryObservation(
            name,
            f"https://pypi.org/pypi/{name}/json",
            found=True,
            latest_version="26.1.0",
            manifest_version_published=None,
            status=200,
        ),
    )
    result = redetect(filed, reads=reads)
    assert result.still_fires is False
    assert result.revision_drifted is True
    assert result.proposed_status == "RESOLVED_UPSTREAM"
    assert result.proposed_close_reason == "completed"
    updated = apply_redetection(filed, result)
    assert updated.status == "RESOLVED_UPSTREAM"
    assert updated.close_reason == "completed"


def test_tex_python_filed_handoff_stays_filed_when_the_entry_point_still_fails_to_parse() -> None:
    """Proof case 1 (still fails) for the second real artifact: NOT_PROCESSABLE has no independent
    versioning (always "1"), so this exercises the revision-drift/false-positive half of the logic
    in isolation from any check-version concern."""
    filed = _as_filed(load_handoff(TEX_PYTHON_HANDOFF))
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=filed.source_revision, branch="main"
        ),
        fetch_file=lambda repository, revision, path, **_: FileRead(
            repository,
            revision,
            path,
            found=True,
            content="def f():\n return 1\n\ndef g():\n if True:\nreturn 2\n",  # bad indent
        ),
    )
    result = redetect(filed, reads=reads)
    assert result.still_fires is True
    assert result.proposed_status is None
    assert result.proposed_close_reason is None
    assert apply_redetection(filed, result) is filed


def test_tex_python_resolves_not_planned_when_parsing_cleanly_at_the_same_revision() -> None:
    """Proof case 2a (now passes, same revision): nothing about the target repository has
    changed - the revision this re-run observes is identical to the one filed against - so a check
    that no longer fires here cannot be "the maintainers fixed it"; the only honest reading is that
    the original finding was a false positive. `not planned`, never defaulted to `completed`."""
    filed = _as_filed(load_handoff(TEX_PYTHON_HANDOFF))
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=filed.source_revision, branch="main"
        ),
        fetch_file=lambda repository, revision, path, **_: FileRead(
            repository, revision, path, found=True, content="def f():\n    return 1\n"
        ),
    )
    result = redetect(filed, reads=reads)
    assert result.still_fires is False
    assert result.revision_drifted is False
    assert result.proposed_status == "RESOLVED_UPSTREAM"
    assert result.proposed_close_reason == "not planned"
    updated = apply_redetection(filed, result)
    assert updated.status == "RESOLVED_UPSTREAM"
    assert updated.close_reason == "not planned"


def test_tex_python_resolves_completed_when_parsing_cleanly_at_a_drifted_revision() -> None:
    """Proof case 2b (now passes, revision moved): the repository's own default branch has moved
    past the filed-at revision, and the named entry point now parses cleanly there - the genuine
    "fixed upstream" shape. `completed`, the one case this module may ever assert a product fix."""
    filed = _as_filed(load_handoff(TEX_PYTHON_HANDOFF))
    new_revision = "e" * 40
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=new_revision, branch="main"
        ),
        fetch_file=lambda repository, revision, path, **_: FileRead(
            repository, revision, path, found=True, content="def f():\n    return 1\n"
        ),
    )
    result = redetect(filed, reads=reads)
    assert result.still_fires is False
    assert result.revision_drifted is True
    assert result.proposed_status == "RESOLVED_UPSTREAM"
    assert result.proposed_close_reason == "completed"
    updated = apply_redetection(filed, result)
    assert updated.status == "RESOLVED_UPSTREAM"
    assert updated.close_reason == "completed"


def test_apply_redetection_is_a_no_op_when_nothing_is_proposed() -> None:
    handoff = load_handoff(TEX_PYTHON_HANDOFF)
    reads = RedetectionReads(
        fetch_default_branch_sha=lambda repository, **_: DefaultBranchRead(
            repository, sha=handoff.source_revision, branch="main"
        ),
        fetch_file=lambda repository, revision, path, **_: FileRead(
            repository,
            revision,
            path,
            found=True,
            content="def f():\ndo_not_parse(\n",
        ),
    )
    result = redetect(handoff, reads=reads)
    assert apply_redetection(handoff, result) is handoff
