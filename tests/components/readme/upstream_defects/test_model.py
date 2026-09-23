"""Loading a handoff artifact fails closed on a missing field, an unknown status, a
causal_stage other than EXTRACTING, or a status/issue_ref mismatch - the same drift
tests/test_schemas.py's own jsonschema-based test already exercises against the schema, here
exercised against the typed reader `redetect.py`/`ledger.py` actually consume."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repository_presenter.components.readme.upstream_defects.model import (
    EvidenceEntry,
    Handoff,
    HandoffError,
    IssueRef,
    TriggeringCheck,
    handoff_to_dict,
    load_handoff,
    write_handoff,
)
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


def _minimal_payload(**overrides: object) -> dict:
    payload = {
        "schema_version": 1,
        "repository": "o/r",
        "source_revision": "a" * 40,
        "defect_fingerprint": "sha256:" + "b" * 64,
        "triggering_check": {"id": "BC-02", "version": "2", "causal_stage": "EXTRACTING"},
        "evidence": [{"path": "https://pypi.org/pypi/x/json", "detail": "not found"}],
        "claim": "a plain factual sentence",
        "suggested_issue_title": "title",
        "suggested_issue_body": "body",
        "status": "HANDOFF_PENDING",
        "issue_ref": None,
    }
    payload.update(overrides)
    return payload


def test_loads_the_two_real_backfilled_artifacts() -> None:
    html = load_handoff(HTML_PYTHON_HANDOFF)
    assert html.repository == "aspose-html-foss/Aspose.HTML-FOSS-for-Python"
    assert html.triggering_check == TriggeringCheck("BC-02", "2", "EXTRACTING")
    assert html.status == "HANDOFF_PENDING" and html.issue_ref is None
    assert html.key == (html.repository, html.defect_fingerprint)

    tex = load_handoff(TEX_PYTHON_HANDOFF)
    assert tex.triggering_check.id == "NOT_PROCESSABLE"
    assert any(e.path.endswith(".py") for e in tex.evidence)


def test_missing_required_field_fails_closed(tmp_path: Path) -> None:
    payload = _minimal_payload()
    del payload["claim"]
    path = tmp_path / "h.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(HandoffError, match="claim"):
        load_handoff(path)


def test_unknown_status_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "h.json"
    path.write_text(json.dumps(_minimal_payload(status="DONE")), encoding="utf-8")
    with pytest.raises(HandoffError, match="status"):
        load_handoff(path)


def test_causal_stage_other_than_extracting_fails_closed(tmp_path: Path) -> None:
    payload = _minimal_payload()
    payload["triggering_check"]["causal_stage"] = "COMPOSING"
    path = tmp_path / "h.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(HandoffError, match="EXTRACTING"):
        load_handoff(path)


def test_filed_without_issue_ref_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "h.json"
    path.write_text(json.dumps(_minimal_payload(status="FILED")), encoding="utf-8")
    with pytest.raises(HandoffError, match="issue_ref"):
        load_handoff(path)


def test_pending_with_issue_ref_fails_closed(tmp_path: Path) -> None:
    payload = _minimal_payload(issue_ref={"number": 1, "url": "https://github.com/o/r/issues/1"})
    path = tmp_path / "h.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(HandoffError, match="issue_ref"):
        load_handoff(path)


def test_malformed_json_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "h.json"
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(HandoffError):
        load_handoff(path)


def test_write_handoff_round_trips(tmp_path: Path) -> None:
    original = load_handoff(HTML_PYTHON_HANDOFF)
    out = tmp_path / "sub" / "out.json"
    write_handoff(original, out)
    reloaded = load_handoff(out)
    assert reloaded == original
    assert out.read_text(encoding="utf-8").endswith("\n")


def test_handoff_to_dict_round_trips_through_from_dict(tmp_path: Path) -> None:
    original = load_handoff(HTML_PYTHON_HANDOFF)
    payload = handoff_to_dict(original)
    assert payload["repository"] == original.repository
    assert payload["evidence"][0] == {
        "path": original.evidence[0].path,
        "detail": original.evidence[0].detail,
    }
    assert payload["issue_ref"] is None


def test_evidence_entry_and_issue_ref_are_plain_frozen_records() -> None:
    entry = EvidenceEntry(path="p", detail="d")
    ref = IssueRef(number=1, url="https://github.com/o/r/issues/1")
    assert entry.path == "p" and ref.number == 1
    handoff = Handoff(
        schema_version=1,
        repository="o/r",
        source_revision="a" * 40,
        defect_fingerprint="sha256:" + "b" * 64,
        triggering_check=TriggeringCheck("BC-02", "1", "EXTRACTING"),
        evidence=(entry,),
        claim="claim",
        suggested_issue_title="t",
        suggested_issue_body="b",
        status="FILED",
        issue_ref=ref,
    )
    assert handoff.key == ("o/r", "sha256:" + "b" * 64)
