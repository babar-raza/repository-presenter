"""Filing readiness and the owner's batch approval (``components/issues/readiness.py``).

Every refusal here is a negative control for the step this tool exists to make safe: an owner
signing a batch of approvals for handoffs they did not review, that changed after review, that were
never independently confirmed, or that name a handoff nobody listed. No test makes a GitHub call:
the approval store, registry and clock are all injected, and the emitter writes only under pytest's
temporary directory.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from repository_presenter import cli
from repository_presenter.cli import EXIT_INCONSISTENT, EXIT_OK, EXIT_USAGE, main
from repository_presenter.components.issues import readiness
from repository_presenter.components.issues.approval import (
    MAX_APPROVAL_LIFETIME,
    evidence_digest,
    handoff_id,
    parse_approval,
    verify_approval,
)
from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    TriggeringCheck,
    write_handoff,
)
from repository_presenter.core.registry.loader import load_registry
from support import (
    MemoryApprovalStore,
    approval_text,
    monitor_registry_entry,
    write_registry_file,
)

NOW = datetime(2026, 10, 10, 12, 0, 0, tzinfo=UTC)
HTML = "aspose-html-foss/Aspose.HTML-FOSS-for-Python"
TEX = "aspose-tex-foss/Aspose.TeX-FOSS-for-Python"
LIVE_HEAD = "b" * 40


def make_handoff(
    repository: str = HTML,
    *,
    fingerprint: str = "a" * 64,
    check_id: str = "BC-02",
    evidence_path: str = "https://pypi.org/pypi/aspose-html-foss/json",
    status: Any = "HANDOFF_PENDING",
    title: str = "build-backend does not exist",
) -> Handoff:
    return Handoff(
        schema_version=1,
        repository=repository,
        source_revision="c" * 40,
        defect_fingerprint=f"sha256:{fingerprint}",
        triggering_check=TriggeringCheck(id=check_id, version="2", causal_stage="EXTRACTING"),
        evidence=(EvidenceEntry(path=evidence_path, detail="HTTP 404"),),
        claim="A plain factual sentence.",
        suggested_issue_title=title,
        suggested_issue_body="Body.\n\n<!-- repository-presenter-defect: sha256:"
        + fingerprint
        + " -->\n",
        status=status,
        issue_ref=None,
        close_reason=None,
    )


def reverification_entry(handoff: Handoff, **overrides: Any) -> dict[str, Any]:
    entry = {
        "handoff_id": handoff_id(handoff),
        "verdict": "CONFIRMED",
        "live_head_sha": LIVE_HEAD,
        "verified_at": "2026-10-09T20:50:00Z",
        "evidence_digest": evidence_digest(handoff),
        "method": "gh api repos/x/y/commits/main; pip install . in a clean venv",
        "note": "",
    }
    entry.update(overrides)
    return entry


@pytest.fixture
def world(tmp_path: Path) -> dict[str, Any]:
    """A synthetic project: two handoffs, a registry with html ``full`` and tex ``dry_run``."""
    root = tmp_path / "project"
    (root / "ops" / "issue_approvals").mkdir(parents=True)
    defects = root / "evidence" / "upstream-defects"
    html = make_handoff(HTML)
    tex = make_handoff(
        TEX,
        fingerprint="d" * 64,
        check_id="NOT_PROCESSABLE",
        evidence_path="src/aspose_tex/presentation/__init__.py",
        title="35 of 45 files do not parse",
    )
    for handoff in (html, tex):
        owner, name = handoff.repository.split("/")
        write_handoff(
            handoff, defects / f"{owner}__{name}" / f"{'a' if handoff is html else 'd'}.json"
        )
    write_registry_file(
        root,
        [
            monitor_registry_entry(HTML, mode="full", repository_id=1),
            monitor_registry_entry(TEX, mode="dry_run", repository_id=2),
        ],
    )
    return {"root": root, "defects": defects, "html": html, "tex": tex}


def write_reverifications(world: dict[str, Any], *entries: dict[str, Any]) -> None:
    path = world["root"] / readiness.VERIFICATION_RELATIVE_PATH
    path.write_text(json.dumps({"schema_version": 1, "entries": list(entries)}), encoding="utf-8")


def rows_for(
    world: dict[str, Any], store: MemoryApprovalStore | None = None
) -> list[readiness.ReadinessRow]:
    return readiness.build_rows(
        world["defects"],
        registry=load_registry(world["root"] / "data" / "registry.json"),
        approvals=store or MemoryApprovalStore(),
        reverifications=readiness.load_reverifications(
            world["root"] / readiness.VERIFICATION_RELATIVE_PATH
        ),
        now=lambda: NOW,
    )


def row_of(rows: list[readiness.ReadinessRow], handoff: Handoff) -> readiness.ReadinessRow:
    return next(r for r in rows if r.handoff_id == handoff_id(handoff))


def confirm_all(world: dict[str, Any]) -> None:
    write_reverifications(
        world, reverification_entry(world["html"]), reverification_entry(world["tex"])
    )


# --- the re-verification record ---------------------------------------------------------------


def test_missing_reverification_file_is_empty_not_an_error(tmp_path: Path) -> None:
    assert readiness.load_reverifications(tmp_path / "absent.json") == {}


@pytest.mark.parametrize(
    "mutation",
    [
        {"verdict": "PROBABLY"},
        {"live_head_sha": "abc"},
        {"evidence_digest": "md5:1"},
        {"method": " "},
        {"verified_at": "yesterday"},
        {"verified_at": "2026-10-09T20:50:00"},
        {"handoff_id": "not-an-id"},
    ],
)
def test_a_malformed_reverification_entry_fails_closed(
    world: dict[str, Any], mutation: dict[str, Any]
) -> None:
    write_reverifications(world, reverification_entry(world["html"], **mutation))
    with pytest.raises(readiness.ReadinessError):
        readiness.load_reverifications(world["root"] / readiness.VERIFICATION_RELATIVE_PATH)


def test_a_duplicate_reverification_entry_fails_closed(world: dict[str, Any]) -> None:
    entry = reverification_entry(world["html"])
    write_reverifications(world, entry, entry)
    with pytest.raises(readiness.ReadinessError, match="duplicate"):
        readiness.load_reverifications(world["root"] / readiness.VERIFICATION_RELATIVE_PATH)


# --- the listing ------------------------------------------------------------------------------


def test_an_unverified_handoff_is_not_approvable(world: dict[str, Any]) -> None:
    row = row_of(rows_for(world), world["html"])
    assert not row.approvable
    assert row.reverification.startswith("UNVERIFIED")
    assert any("not independently confirmed" in b for b in row.blockers)


def test_a_confirmed_full_mode_handoff_with_a_replayable_recheck_is_approvable(
    world: dict[str, Any],
) -> None:
    confirm_all(world)
    row = row_of(rows_for(world), world["html"])
    assert row.approvable
    assert row.registry_state == "full" and row.registry_ok
    assert row.replay_gap is None
    assert not row.fileable_now  # no owner approval yet
    assert any(b.startswith("owner approval:") for b in row.blockers)


def test_a_dry_run_registry_entry_is_a_blocker_but_does_not_make_it_unapprovable(
    world: dict[str, Any],
) -> None:
    confirm_all(world)
    row = row_of(rows_for(world), world["tex"])
    assert row.approvable
    assert row.registry_state == "dry_run" and not row.registry_ok
    assert any("write gate refuses issue_filing" in b for b in row.blockers)
    assert not row.fileable_now


def test_a_handoff_changed_after_verification_is_stale_and_unapprovable(
    world: dict[str, Any],
) -> None:
    confirm_all(world)
    changed = replace(world["html"], suggested_issue_title="a different title")
    write_handoff(
        changed, world["defects"] / "aspose-html-foss__Aspose.HTML-FOSS-for-Python" / "a.json"
    )
    row = row_of(rows_for(world), changed)
    assert not row.approvable
    assert row.reverification.startswith("STALE")


@pytest.mark.parametrize("verdict", ["NOT_A_DEFECT", "FIXED_OR_CHANGED", "NOT_VERIFIABLE"])
def test_a_non_confirmed_verdict_is_unapprovable(world: dict[str, Any], verdict: str) -> None:
    write_reverifications(world, reverification_entry(world["html"], verdict=verdict))
    row = row_of(rows_for(world), world["html"])
    assert not row.approvable
    assert row.reverification.startswith(verdict)


def test_a_recheck_that_cannot_conclude_is_a_blocker_and_unapprovable(
    world: dict[str, Any],
) -> None:
    gappy = make_handoff(
        HTML, fingerprint="e" * 64, evidence_path="https://registry.npmjs.org/x", title="npm"
    )
    write_handoff(
        gappy, world["defects"] / "aspose-html-foss__Aspose.HTML-FOSS-for-Python" / "e.json"
    )
    write_reverifications(world, reverification_entry(gappy))
    row = row_of(rows_for(world), gappy)
    assert row.replay_gap is not None and "PyPI" in row.replay_gap
    assert not row.approvable


def test_an_unknown_check_id_has_no_redetector_gap(world: dict[str, Any]) -> None:
    other = make_handoff(HTML, fingerprint="f" * 64, check_id="BC-03", title="example")
    write_handoff(
        other, world["defects"] / "aspose-html-foss__Aspose.HTML-FOSS-for-Python" / "f.json"
    )
    write_reverifications(world, reverification_entry(other))
    row = row_of(rows_for(world), other)
    assert row.replay_gap is not None and "no redetector is registered" in row.replay_gap
    assert not row.approvable


def test_an_unlisted_repository_is_reported_not_listed() -> None:
    state, ok = readiness._registry_state(None, HTML)
    assert not ok and "not loaded" in state


def test_a_filed_handoff_is_not_pending(world: dict[str, Any]) -> None:
    filed = replace(
        world["html"],
        status="FILED",
        issue_ref=__import__(
            "repository_presenter.components.issues.model", fromlist=["IssueRef"]
        ).IssueRef(number=1, url="https://github.com/o/r/issues/1"),
    )
    write_handoff(
        filed, world["defects"] / "aspose-html-foss__Aspose.HTML-FOSS-for-Python" / "a.json"
    )
    write_reverifications(world, reverification_entry(filed))
    row = row_of(rows_for(world), filed)
    assert not row.approvable
    assert any("never re-filed" in b for b in row.blockers)


def test_existing_approval_states_are_reported_from_the_same_verdict_filing_uses(
    world: dict[str, Any],
) -> None:
    confirm_all(world)
    html, tex = world["html"], world["tex"]
    store = MemoryApprovalStore(
        {
            handoff_id(html): approval_text(
                html, approved_at=NOW - timedelta(hours=1), expires_at=NOW + timedelta(days=3)
            ),
            handoff_id(tex): approval_text(
                tex, approved_at=NOW - timedelta(days=9), expires_at=NOW - timedelta(days=2)
            ),
        }
    )
    rows = rows_for(world, store)
    good = row_of(rows, html)
    assert good.approval.approved and good.fileable_now
    expired = row_of(rows, tex)
    assert not expired.approval.approved and "expired" in expired.approval.reason
    stale_store = MemoryApprovalStore(
        {handoff_id(html): approval_text(html, digest="sha256:" + "0" * 64)}
    )
    stale = row_of(rows_for(world, stale_store), html)
    assert not stale.approval.approved and "digest mismatch" in stale.approval.reason


def test_render_listing_names_blockers_and_the_approvable_batch(world: dict[str, Any]) -> None:
    confirm_all(world)
    text = readiness.render_listing(rows_for(world), kill_switch_on=False)
    assert "kill switch" in text and "OFF" in text
    assert f"== {TEX}  [registry: dry_run; write gate REFUSES issue_filing]" in text
    assert f"== {HTML}  [registry: full; write gate OPEN]" in text
    html_row = row_of(rows_for(world), world["html"])
    assert f"{html_row.handoff_id}@{html_row.evidence_digest}" in text


# --- request parsing --------------------------------------------------------------------------


def test_parse_request_accepts_a_bare_id_and_an_id_with_a_digest(world: dict[str, Any]) -> None:
    identifier = handoff_id(world["html"])
    digest = evidence_digest(world["html"])
    assert readiness.parse_request(identifier) == readiness.ApprovalRequest(identifier, None)
    assert readiness.parse_request(f"{identifier}@{digest}") == readiness.ApprovalRequest(
        identifier, digest
    )


@pytest.mark.parametrize("token", ["", "nonsense", "o__n__abc", "o__n__" + "a" * 64 + "@md5:1"])
def test_parse_request_rejects_malformed_tokens(token: str) -> None:
    with pytest.raises(readiness.ReadinessError):
        readiness.parse_request(token)


def test_parse_requests_skips_comments_and_blank_lines(world: dict[str, Any]) -> None:
    identifier = handoff_id(world["html"])
    parsed = readiness.parse_requests(["# the batch", "", f"{identifier}  # html", "   "])
    assert parsed == [readiness.ApprovalRequest(identifier, None)]


# --- emitting approvals -----------------------------------------------------------------------


def emit(
    world: dict[str, Any],
    ids: list[str],
    out_dir: Path,
    *,
    store: MemoryApprovalStore | None = None,
    **overrides: Any,
) -> readiness.EmitOutcome:
    arguments: dict[str, Any] = {
        "root": world["root"],
        "out_dir": out_dir,
        "approver": "owner-login",
        "now": NOW,
    }
    arguments.update(overrides)
    return readiness.emit_approvals(
        rows_for(world, store), [readiness.parse_request(i) for i in ids], **arguments
    )


def test_emit_writes_exactly_the_listed_record_and_it_verifies(
    world: dict[str, Any], tmp_path: Path
) -> None:
    confirm_all(world)
    html, tex = world["html"], world["tex"]
    out = tmp_path / "scratch"
    outcome = emit(world, [f"{handoff_id(html)}@{evidence_digest(html)}"], out)
    assert outcome.refusals == ()
    assert [p.name for p in outcome.written] == [f"{handoff_id(html)}.json"]
    assert sorted(p.name for p in out.iterdir()) == [f"{handoff_id(html)}.json"]  # tex not listed
    text = (out / f"{handoff_id(html)}.json").read_text(encoding="utf-8")
    record = parse_approval(text)
    assert record.approver == "owner-login"
    assert record.approved_at == NOW and record.expires_at == NOW + timedelta(days=7)
    assert record.evidence_digest == evidence_digest(html)
    assert verify_approval(
        html, MemoryApprovalStore({handoff_id(html): text}), now=lambda: NOW
    ).approved
    assert handoff_id(tex) not in {p.stem for p in out.iterdir()}


def test_an_unlisted_handoff_id_is_refused_and_nothing_is_written(
    world: dict[str, Any], tmp_path: Path
) -> None:
    confirm_all(world)
    out = tmp_path / "scratch"
    unknown = "aspose-nothing__Nope__" + "9" * 64
    outcome = emit(world, [handoff_id(world["html"]), unknown], out)
    assert outcome.written == ()
    assert (unknown, "not a handoff on record - unlisted ids are refused") in outcome.refusals
    assert not out.exists()  # all or nothing: the valid one was not written either


def test_a_stale_evidence_digest_is_refused(world: dict[str, Any], tmp_path: Path) -> None:
    confirm_all(world)
    html = world["html"]
    reviewed = evidence_digest(html)
    changed = replace(html, suggested_issue_title="edited after the owner reviewed it")
    write_handoff(
        changed, world["defects"] / "aspose-html-foss__Aspose.HTML-FOSS-for-Python" / "a.json"
    )
    write_reverifications(world, reverification_entry(changed), reverification_entry(world["tex"]))
    out = tmp_path / "scratch"
    outcome = emit(world, [f"{handoff_id(html)}@{reviewed}"], out)
    assert outcome.written == ()
    assert "stale evidence digest" in outcome.refusals[0][1]
    assert not out.exists()


def test_an_expired_or_non_future_window_is_refused(world: dict[str, Any], tmp_path: Path) -> None:
    confirm_all(world)
    outcome = emit(
        world,
        [handoff_id(world["html"])],
        tmp_path / "scratch",
        expires_at=NOW - timedelta(minutes=1),
    )
    assert outcome.written == () and "not after now" in outcome.refusals[0][1]


def test_a_window_beyond_the_maximum_lifetime_is_refused(
    world: dict[str, Any], tmp_path: Path
) -> None:
    confirm_all(world)
    outcome = emit(
        world,
        [handoff_id(world["html"])],
        tmp_path / "scratch",
        expires_at=NOW + MAX_APPROVAL_LIFETIME + timedelta(seconds=1),
    )
    assert outcome.written == () and "standing authorization" in outcome.refusals[0][1]


@pytest.mark.parametrize("approver", ["", "github-actions[bot]", "dependabot[bot]", "has space"])
def test_a_non_person_approver_is_refused(
    world: dict[str, Any], tmp_path: Path, approver: str
) -> None:
    confirm_all(world)
    outcome = emit(world, [handoff_id(world["html"])], tmp_path / "scratch", approver=approver)
    assert outcome.written == () and "not a person's GitHub login" in outcome.refusals[0][1]


def test_an_unconfirmed_handoff_cannot_be_approved(world: dict[str, Any], tmp_path: Path) -> None:
    write_reverifications(world, reverification_entry(world["html"], verdict="FIXED_OR_CHANGED"))
    outcome = emit(world, [handoff_id(world["html"])], tmp_path / "scratch")
    assert outcome.written == () and "not approvable" in outcome.refusals[0][1]


def test_a_handoff_whose_recheck_cannot_conclude_cannot_be_approved(
    world: dict[str, Any], tmp_path: Path
) -> None:
    gappy = make_handoff(HTML, fingerprint="e" * 64, evidence_path="https://registry.npmjs.org/x")
    write_handoff(
        gappy, world["defects"] / "aspose-html-foss__Aspose.HTML-FOSS-for-Python" / "e.json"
    )
    write_reverifications(world, reverification_entry(gappy))
    outcome = emit(world, [handoff_id(gappy)], tmp_path / "scratch")
    assert outcome.written == () and "not approvable" in outcome.refusals[0][1]


@pytest.mark.parametrize("relative", ["ops", "ops/issue_approvals", "ops/nested/deep", ".git"])
def test_a_scratch_directory_inside_ops_or_git_is_refused(
    world: dict[str, Any], relative: str
) -> None:
    confirm_all(world)
    target = world["root"] / relative
    outcome = emit(world, [handoff_id(world["html"])], target)
    assert outcome.written == ()
    assert "scratch directory" in outcome.refusals[0][1]
    assert not any(target.glob("*.json")) if target.exists() else True


def test_an_existing_record_file_is_never_overwritten(
    world: dict[str, Any], tmp_path: Path
) -> None:
    confirm_all(world)
    out = tmp_path / "scratch"
    out.mkdir()
    existing = out / f"{handoff_id(world['html'])}.json"
    existing.write_text("owner's hand edit", encoding="utf-8")
    outcome = emit(world, [handoff_id(world["html"])], out)
    assert outcome.written == () and "already exists" in outcome.refusals[0][1]
    assert existing.read_text(encoding="utf-8") == "owner's hand edit"


def test_an_already_approved_handoff_is_refused(world: dict[str, Any], tmp_path: Path) -> None:
    confirm_all(world)
    html = world["html"]
    store = MemoryApprovalStore(
        {
            handoff_id(html): approval_text(
                html, approved_at=NOW - timedelta(hours=1), expires_at=NOW + timedelta(days=3)
            )
        }
    )
    outcome = emit(world, [handoff_id(html)], tmp_path / "scratch", store=store)
    assert outcome.written == () and "already approved" in outcome.refusals[0][1]


def test_a_duplicate_listing_is_refused(world: dict[str, Any], tmp_path: Path) -> None:
    confirm_all(world)
    identifier = handoff_id(world["html"])
    outcome = emit(world, [identifier, identifier], tmp_path / "scratch")
    assert outcome.written == () and (identifier, "listed twice") in outcome.refusals


def test_an_empty_batch_is_refused(world: dict[str, Any], tmp_path: Path) -> None:
    outcome = emit(world, [], tmp_path / "scratch")
    assert outcome.written == () and "no handoff ids" in outcome.refusals[0][1]


def test_notices_say_when_a_digest_was_not_pinned_and_when_the_registry_still_refuses(
    world: dict[str, Any], tmp_path: Path
) -> None:
    confirm_all(world)
    outcome = emit(world, [handoff_id(world["tex"])], tmp_path / "scratch")
    joined = "\n".join(outcome.notices)
    assert "no digest was supplied" in joined
    assert "registry state is dry_run" in joined
    assert len(outcome.written) == 1


# --- the command ------------------------------------------------------------------------------


class _FakeStore:
    def __init__(self, root: Path, ref: str = "HEAD", *, directory: str = "") -> None:
        self.records: dict[str, str] = {}

    def read(self, identifier: str) -> str | None:
        return self.records.get(identifier)


@pytest.fixture(autouse=True)
def _no_git_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "GitApprovalStore", _FakeStore)
    monkeypatch.delenv("REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED", raising=False)


def cli_root(world: dict[str, Any]) -> str:
    # `_resolve_root` needs the cursor; the synthetic project fixture writes it.
    from support import write_cursor

    write_cursor(world["root"])
    return str(world["root"])


def test_the_listing_command_is_read_only_and_exits_ok(
    world: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    confirm_all(world)
    root = cli_root(world)
    before = sorted(p.as_posix() for p in world["root"].rglob("*") if p.is_file())
    assert main(["issue-readiness", "--root", root]) == EXIT_OK
    out = capsys.readouterr().out
    assert "issue-readiness: 2 handoff(s) on record" in out
    assert sorted(p.as_posix() for p in world["root"].rglob("*") if p.is_file()) == before


def test_the_json_listing_parses(world: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    confirm_all(world)
    assert main(["issue-readiness", "--root", cli_root(world), "--json", "--repo", HTML]) == EXIT_OK
    rows = json.loads(capsys.readouterr().out)
    assert [r["repository"] for r in rows] == [HTML]
    assert rows[0]["approvable"] is True and rows[0]["fileable_now"] is False


def test_the_emit_command_writes_only_the_listed_record_outside_ops(
    world: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    confirm_all(world)
    root = cli_root(world)
    out = tmp_path / "scratch"
    html = world["html"]
    code = main(
        [
            "issue-readiness",
            "--root",
            root,
            "--emit-approvals",
            str(out),
            "--approver",
            "owner-login",
            "--handoff-id",
            f"{handoff_id(html)}@{evidence_digest(html)}",
        ]
    )
    assert code == EXIT_OK
    assert [p.name for p in out.iterdir()] == [f"{handoff_id(html)}.json"]
    assert list((world["root"] / "ops" / "issue_approvals").iterdir()) == []
    assert "committed and sent nothing" in capsys.readouterr().out


def test_the_emit_command_reads_a_ids_file_and_refuses_an_unlisted_one(
    world: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    confirm_all(world)
    ids_file = tmp_path / "ids.txt"
    ids_file.write_text(f"# batch\n{handoff_id(world['html'])}\nunlisted__Nope__{'1' * 64}\n")
    out = tmp_path / "scratch"
    code = main(
        [
            "issue-readiness",
            "--root",
            cli_root(world),
            "--emit-approvals",
            str(out),
            "--approver",
            "owner-login",
            "--handoff-ids-file",
            str(ids_file),
        ]
    )
    assert code == EXIT_USAGE
    assert not out.exists()
    assert "REFUSED unlisted__Nope__" in capsys.readouterr().out


def test_the_emit_command_requires_an_approver(
    world: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        [
            "issue-readiness",
            "--root",
            cli_root(world),
            "--emit-approvals",
            str(tmp_path / "scratch"),
            "--handoff-id",
            handoff_id(world["html"]),
        ]
    )
    assert code == EXIT_USAGE
    assert "--approver" in capsys.readouterr().err


def test_selecting_ids_without_the_emit_flag_is_a_usage_error(
    world: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        ["issue-readiness", "--root", cli_root(world), "--handoff-id", handoff_id(world["html"])]
    )
    assert code == EXIT_USAGE
    assert "--emit-approvals" in capsys.readouterr().err


def test_a_malformed_reverification_record_stops_the_command(
    world: dict[str, Any], capsys: pytest.CaptureFixture[str]
) -> None:
    (world["root"] / readiness.VERIFICATION_RELATIVE_PATH).write_text("{not json", encoding="utf-8")
    assert main(["issue-readiness", "--root", cli_root(world)]) == EXIT_INCONSISTENT
    assert "cannot read/parse" in capsys.readouterr().err
