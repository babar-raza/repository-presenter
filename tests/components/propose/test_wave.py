"""The proposal-wave operator tool (``components/propose/wave.py``, ``repository-presenter
wave-readiness``): a read-only readiness table and a dry-run record emitter.

No test makes a live GitHub call: the live head and README presence are injected fakes, and the
provenance check is either a fake or a real disposable git repository. The negative controls are the
point of the tool: an unlisted repository, an expired or over-long window, a candidate hash that no
longer matches what the owner approved, a moved source, and a destination inside
``ops/proposal-authorizations/`` are each refused, and one refusal writes nothing at all.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from repository_presenter import cli
from repository_presenter.cli import EXIT_OK, EXIT_UNSAFE, EXIT_USAGE, main
from repository_presenter.components.propose.effect import presenter_branch_name
from repository_presenter.components.propose.wave import (
    DISPATCH_PAUSE_SECONDS,
    LiveObservation,
    OwnerEntry,
    WaveError,
    assess_wave,
    emit_records,
    parse_owner_entries,
    render_table,
)
from repository_presenter.core.authorization.proposal import (
    AUTHORIZATION_DIRNAME,
    authorize_proposal,
    load_authorization_file,
    record_filename,
    render_record,
    validate_authorization,
)
from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError
from repository_presenter.core.github.read_client import DefaultBranchRead, FileRead
from repository_presenter.core.hashing import sha256_text
from repository_presenter.core.registry.loader import load_registry
from support import (
    merge_to_origin_main,
    monitor_registry_entry,
    write_proposable_bundle,
    write_registry_file,
)

FULL = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
DRY = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
OTHER = "aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp"
UNLISTED = "aspose-words-foss/Aspose.Words-FOSS-for-Python"
REV_FULL = "a" * 40
REV_DRY = "b" * 40
REV_OTHER = "c" * 40
README = {FULL: "# Java\n\ncontent\n", DRY: "# 3D\n\ncontent\n", OTHER: "# PDF\n\ncontent\n"}
REVISIONS = {FULL: REV_FULL, DRY: REV_DRY, OTHER: REV_OTHER}
NOW = datetime(2026, 10, 11, 8, 0, 0, tzinfo=UTC)
ISSUED = NOW
EXPIRES = NOW + timedelta(days=2)


def stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def hash_of(repository: str) -> str:
    return sha256_text(README[repository])


@pytest.fixture
def control(project: Path) -> Path:
    tmp_path = project
    write_registry_file(
        tmp_path,
        [
            monitor_registry_entry(DRY, mode="dry_run", repository_id=1),
            monitor_registry_entry(FULL, mode="full", repository_id=2),
            monitor_registry_entry(OTHER, mode="dry_run", repository_id=3),
        ],
    )
    for repository in (FULL, DRY, OTHER):
        write_proposable_bundle(tmp_path, repository, REVISIONS[repository], README[repository])
    return tmp_path


class LiveWorld:
    """The upstream as the fakes see it: head per repository, and whether it has a README.md."""

    def __init__(self) -> None:
        self.heads = dict(REVISIONS)
        self.readme: dict[str, bool] = {}
        self.errors: dict[str, str] = {}
        self.reads: list[str] = []

    def __call__(self, repository: str) -> LiveObservation:
        self.reads.append(repository)
        if repository in self.errors:
            return LiveObservation(error=self.errors[repository])
        return LiveObservation(
            sha=self.heads.get(repository, "f" * 40),
            branch="main",
            readme_found=self.readme.get(repository, True),
        )


def merged(_record: Path, _root: Path) -> str:
    return "0" * 40


def unmerged(_record: Path, _root: Path) -> str:
    raise WriteRefusedError(Refusal.AUTHORIZATION_NOT_COMMITTED, "not on origin/main")


def assess(
    control: Path,
    world: LiveWorld | None,
    *,
    repositories: list[str] | None = None,
    provenance=merged,  # type: ignore[no-untyped-def]
    now: datetime = NOW,
):
    return assess_wave(
        control,
        load_registry(control / "data" / "registry.json"),
        repositories=repositories,
        live_read=world,
        now=now,
        provenance=provenance,
    )


def write_record(control: Path, repository: str, **overrides: object) -> Path:
    fields: dict[str, object] = {
        "repository": repository,
        "candidate_hash": hash_of(repository),
        "source_revision": REVISIONS[repository],
        "base_branch": "main",
        "branch": presenter_branch_name(),
        "approver": "owner",
        "issued_at": stamp(NOW - timedelta(hours=1)),
        "expires_at": stamp(NOW + timedelta(days=1)),
    }
    fields.update(overrides)
    path = control / AUTHORIZATION_DIRNAME / record_filename(repository, hash_of(repository))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_record(authorize_proposal(**fields)), encoding="utf-8")  # type: ignore[arg-type]
    return path


# ---------------------------------------------------------------------------------------------
# the readiness table
# ---------------------------------------------------------------------------------------------


def test_default_selection_is_every_ready_candidate_and_nothing_else(control: Path) -> None:
    write_proposable_bundle(control, UNLISTED, "d" * 40, "# x\n", state="VALID_UPDATE_AVAILABLE")
    rows = assess(control, LiveWorld())
    assert sorted(row.repository for row in rows) == sorted([FULL, DRY, OTHER])


def test_a_full_mode_current_candidate_with_a_merged_record_is_ready_to_dispatch(
    control: Path,
) -> None:
    write_record(control, FULL)
    (row,) = assess(control, LiveWorld(), repositories=[FULL])
    assert row.verdict == "READY_TO_DISPATCH"
    assert row.registry == "full"
    assert row.source == "current"
    assert row.readme == "present"
    assert row.authorization.startswith("valid+merged")
    assert row.candidate_hash == hash_of(FULL)
    assert row.blockers == () and row.owner_steps == ()


def test_a_dry_run_candidate_without_a_record_needs_the_owner_not_a_fix(control: Path) -> None:
    (row,) = assess(control, LiveWorld(), repositories=[DRY])
    assert row.verdict == "READY_TO_AUTHORIZE"
    assert row.blockers == ()
    assert any("flip registry mode to full" in step for step in row.owner_steps)
    assert any(record_filename(DRY, hash_of(DRY)) in step for step in row.owner_steps)


def test_a_moved_source_blocks_the_candidate(control: Path) -> None:
    world = LiveWorld()
    world.heads[FULL] = "e" * 40
    (row,) = assess(control, world, repositories=[FULL])
    assert row.verdict == "BLOCKED"
    assert row.source.startswith("MOVED")
    assert any(str(Refusal.SOURCE_MOVED) in blocker for blocker in row.blockers)


def test_a_head_without_a_readme_md_blocks_the_candidate(control: Path) -> None:
    world = LiveWorld()
    world.readme[FULL] = False
    (row,) = assess(control, world, repositories=[FULL])
    assert row.verdict == "BLOCKED" and row.readme == "MISSING"


def test_an_unreadable_head_blocks_rather_than_guessing_freshness(control: Path) -> None:
    world = LiveWorld()
    world.errors[FULL] = "HTTP 502"
    (row,) = assess(control, world, repositories=[FULL])
    assert row.verdict == "BLOCKED" and "UNREADABLE" in row.source


def test_an_unlisted_repository_and_a_missing_bundle_and_a_non_final_bundle_are_blocked(
    control: Path,
) -> None:
    write_proposable_bundle(
        control, OTHER, REV_OTHER, README[OTHER], state="VALID_UPDATE_AVAILABLE"
    )
    write_proposable_bundle(control, UNLISTED, "d" * 40, "# x\n")
    rows = {
        row.repository: row
        for row in assess(control, LiveWorld(), repositories=[UNLISTED, OTHER, "aspose-x/none"])
    }
    assert any(str(Refusal.REGISTRY_NOT_LISTED) in b for b in rows[UNLISTED].blockers)
    assert any(str(Refusal.BUNDLE_NOT_READY) in b for b in rows[OTHER].blockers)
    assert rows["aspose-x/none"].state == "NO BUNDLE"
    assert all(row.verdict == "BLOCKED" for row in rows.values())


def test_every_authorization_state_is_named(control: Path) -> None:
    states: dict[str, str] = {}

    def state_of(provenance=merged) -> str:  # type: ignore[no-untyped-def]
        (row,) = assess(control, LiveWorld(), repositories=[FULL], provenance=provenance)
        return row.authorization

    states["none"] = state_of()
    record = write_record(control, FULL)
    states["merged"] = state_of()
    states["unmerged"] = state_of(unmerged)
    record.write_text(
        render_record(
            authorize_proposal(
                repository=FULL,
                candidate_hash=hash_of(FULL),
                source_revision=REV_FULL,
                base_branch="main",
                branch=presenter_branch_name(),
                approver="owner",
                issued_at=stamp(NOW - timedelta(days=3)),
                expires_at=stamp(NOW - timedelta(days=1)),
            )
        ),
        encoding="utf-8",
    )
    states["expired"] = state_of()
    record.write_text("{not json", encoding="utf-8")
    states["unreadable"] = state_of()
    assert states["none"] == "none"
    assert states["merged"].startswith("valid+merged until")
    assert "NOT merged" in states["unmerged"]
    assert states["expired"].startswith("expired")
    assert states["unreadable"] == "unreadable"


def test_a_record_for_a_different_source_revision_is_a_mismatch_not_valid(control: Path) -> None:
    write_record(control, FULL, source_revision="9" * 40)
    (row,) = assess(control, LiveWorld(), repositories=[FULL])
    assert row.authorization.startswith("mismatch")
    assert row.verdict == "READY_TO_AUTHORIZE"


def test_the_table_is_offline_capable_and_reads_nothing_live(control: Path) -> None:
    rows = assess(control, None)
    assert {row.source for row in rows} == {"unread (offline)"}
    assert "unread (offline)" in render_table(rows)


def test_the_table_reports_stale_bundles_but_staleness_never_blocks(control: Path) -> None:
    from repository_presenter.core.candidates import StaleCandidate

    slug = FULL.replace("/", "__")
    rows = assess_wave(
        control,
        load_registry(control / "data" / "registry.json"),
        repositories=[FULL],
        live_read=LiveWorld(),
        stale=[StaleCandidate(slug, REV_FULL, ("components.renderer 24 -> 30",))],
        now=NOW,
        provenance=merged,
    )
    assert rows[0].stale and rows[0].blockers == ()
    assert "behind code" in render_table(rows)


# ---------------------------------------------------------------------------------------------
# the owner's list
# ---------------------------------------------------------------------------------------------


def test_owner_lines_are_parsed_and_comments_skipped() -> None:
    entries = parse_owner_entries(
        [
            "# batch of 2026-10-11",
            f"{FULL}@{hash_of(FULL)[:16]}   # first",
            "",
            f"{DRY}@{hash_of(DRY)}",
        ]
    )
    assert [e.repository for e in entries] == [FULL, DRY]


@pytest.mark.parametrize(
    "line",
    [
        FULL,  # no hash: the owner approves an exact candidate, never "whatever is current"
        f"{FULL}@abc",  # too short to be unambiguous
        f"{FULL}@{'Z' * 20}",  # not hex
        f"not-a-repo@{'a' * 20}",
        f"@{'a' * 20}",
    ],
)
def test_a_malformed_owner_line_is_a_usage_error(line: str) -> None:
    with pytest.raises(WaveError):
        parse_owner_entries([line])


def test_an_empty_or_duplicated_owner_list_is_a_usage_error() -> None:
    with pytest.raises(WaveError):
        parse_owner_entries(["# nothing", ""])
    with pytest.raises(WaveError):
        parse_owner_entries([f"{FULL}@{'a' * 12}", f"{FULL}@{'b' * 12}"])


# ---------------------------------------------------------------------------------------------
# the dry-run emitter
# ---------------------------------------------------------------------------------------------


def emit(
    control: Path,
    destination: Path,
    entries: list[OwnerEntry],
    world: LiveWorld | None = None,
    *,
    issued: datetime = ISSUED,
    expires: datetime = EXPIRES,
    approver: str = "owner",
    now: datetime = NOW,
):
    registry = load_registry(control / "data" / "registry.json")
    rows = assess(control, world or LiveWorld(), repositories=[e.repository for e in entries])
    return emit_records(
        control,
        registry,
        rows,
        entries,
        approver=approver,
        issued_at=issued,
        expires_at=expires,
        destination=destination,
        now=now,
    )


def test_emit_writes_exactly_the_records_the_effect_later_accepts(
    control: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    entries = [OwnerEntry(FULL, hash_of(FULL)[:12]), OwnerEntry(DRY, hash_of(DRY))]
    result = emit(control, scratch, entries)
    assert result.refusals == ()
    names = sorted(path.name for path in result.written)
    assert record_filename(FULL, hash_of(FULL)) in names
    assert record_filename(DRY, hash_of(DRY)) in names
    assert {"registry.json", "dispatch-plan.sh", "wave-manifest.json"} <= set(names)
    for repository in (FULL, DRY):
        record = load_authorization_file(scratch / record_filename(repository, hash_of(repository)))
        decision = validate_authorization(
            record,
            now=stamp(NOW + timedelta(hours=1)),
            expected_repository=repository,
            expected_candidate_hash=hash_of(repository),
            expected_source_revision=REVISIONS[repository],
            expected_base_branch="main",
            expected_branch=presenter_branch_name(),
        )
        assert decision.granted, decision.reason
        assert record.approver == "owner"
        assert record.supersedes_prs == ()


def test_emit_flips_only_the_listed_repositories_in_the_scratch_registry(
    control: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    before = (control / "data" / "registry.json").read_text(encoding="utf-8")
    assert emit(control, scratch, [OwnerEntry(DRY, hash_of(DRY))]).refusals == ()
    flipped = {
        e["repository"]: e["mode"]
        for e in json.loads((scratch / "registry.json").read_text(encoding="utf-8"))["entries"]
    }
    assert flipped == {DRY: "full", FULL: "full", OTHER: "dry_run"}  # FULL was already full
    # the real registry is untouched
    assert (control / "data" / "registry.json").read_text(encoding="utf-8") == before


def test_emit_never_touches_the_authorization_directory_or_the_registry(
    control: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    assert emit(control, scratch, [OwnerEntry(FULL, hash_of(FULL))]).refusals == ()
    assert not (control / AUTHORIZATION_DIRNAME).exists()


def test_emit_writes_a_paced_dispatch_plan_it_never_runs(
    control: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    entries = [OwnerEntry(FULL, hash_of(FULL)), OwnerEntry(DRY, hash_of(DRY))]
    assert emit(control, scratch, entries).refusals == ()
    plan = (scratch / "dispatch-plan.sh").read_text(encoding="utf-8")
    assert plan.count("gh workflow run propose.yml") == 2
    assert plan.count(f"sleep {DISPATCH_PAUSE_SECONDS}") == 1  # between, not after, the last one
    assert f"-f repo={FULL}" in plan and "-f do_propose=true" in plan
    record = record_filename(FULL, hash_of(FULL))
    assert f"-f authorization_record=ops/proposal-authorizations/{record}" in plan
    assert "--ref main" in plan


def test_an_unlisted_repository_is_refused_and_nothing_is_written(
    control: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    write_proposable_bundle(control, UNLISTED, "d" * 40, "# x\n")
    result = emit(
        control,
        scratch,
        [OwnerEntry(FULL, hash_of(FULL)), OwnerEntry(UNLISTED, sha256_text("# x\n"))],
    )
    assert [r.repository for r in result.refusals] == [UNLISTED]
    assert result.refusals[0].code == str(Refusal.REGISTRY_NOT_LISTED)
    assert not scratch.exists()  # all or nothing: the good entry was not written either


def test_a_repository_the_owner_did_not_list_is_never_emitted(
    control: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    registry = load_registry(control / "data" / "registry.json")
    rows = assess(control, LiveWorld())  # all three candidates assessed
    result = emit_records(
        control,
        registry,
        rows,
        [OwnerEntry(FULL, hash_of(FULL))],
        approver="owner",
        issued_at=ISSUED,
        expires_at=EXPIRES,
        destination=scratch,
        now=NOW,
    )
    assert result.refusals == ()
    emitted = {p.name for p in scratch.glob("*.json")}
    assert record_filename(DRY, hash_of(DRY)) not in emitted
    assert record_filename(OTHER, hash_of(OTHER)) not in emitted


def test_an_owner_entry_outside_the_assessed_selection_is_refused(
    control: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    registry = load_registry(control / "data" / "registry.json")
    rows = assess(control, LiveWorld(), repositories=[FULL])
    result = emit_records(
        control,
        registry,
        rows,
        [OwnerEntry(DRY, hash_of(DRY))],
        approver="owner",
        issued_at=ISSUED,
        expires_at=EXPIRES,
        destination=scratch,
        now=NOW,
    )
    assert result.refusals[0].code == "not_in_selection"
    assert not scratch.exists()


def test_an_expired_window_is_refused(
    control: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    result = emit(
        control,
        scratch,
        [OwnerEntry(FULL, hash_of(FULL))],
        issued=NOW - timedelta(days=3),
        expires=NOW - timedelta(days=1),
    )
    assert any(r.code == str(Refusal.AUTHORIZATION_EXPIRED) for r in result.refusals)
    assert not scratch.exists()


def test_a_window_longer_than_seven_days_or_empty_is_refused(
    control: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    entries = [OwnerEntry(FULL, hash_of(FULL))]
    long = emit(control, scratch, entries, expires=ISSUED + timedelta(days=8))
    assert any("exceeds 7 days" in r.reason for r in long.refusals)
    empty = emit(
        control, scratch, entries, issued=NOW + timedelta(hours=2), expires=NOW + timedelta(hours=1)
    )
    assert any(r.code == str(Refusal.AUTHORIZATION_MISMATCH) for r in empty.refusals)
    assert not scratch.exists()


def test_a_hash_that_no_longer_matches_what_the_owner_approved_is_refused(
    control: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    approved = hash_of(FULL)
    # the candidate is re-sealed after the owner signed: same repository, different README
    write_proposable_bundle(control, FULL, REV_FULL, "# Java\n\nre-sealed and different\n")
    result = emit(control, scratch, [OwnerEntry(FULL, approved[:12])])
    assert result.refusals[0].code == str(Refusal.AUTHORIZATION_MISMATCH)
    assert "changed since the list was written" in result.refusals[0].reason
    assert not scratch.exists()


def test_a_moved_source_a_missing_readme_and_a_non_final_bundle_are_refused(
    control: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    world = LiveWorld()
    world.heads[FULL] = "e" * 40
    assert (
        emit(control, scratch, [OwnerEntry(FULL, hash_of(FULL))], world).refusals[0].code
        == "blocked"
    )
    world = LiveWorld()
    world.readme[FULL] = False
    assert (
        emit(control, scratch, [OwnerEntry(FULL, hash_of(FULL))], world).refusals[0].code
        == "blocked"
    )
    write_proposable_bundle(control, FULL, REV_FULL, README[FULL], state="INVALIDATED")
    assert emit(control, scratch, [OwnerEntry(FULL, hash_of(FULL))]).refusals[0].code == "blocked"
    assert not scratch.exists()


def test_an_offline_assessment_cannot_be_emitted(
    control: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    registry = load_registry(control / "data" / "registry.json")
    rows = assess(control, None, repositories=[FULL])
    result = emit_records(
        control,
        registry,
        rows,
        [OwnerEntry(FULL, hash_of(FULL))],
        approver="owner",
        issued_at=ISSUED,
        expires_at=EXPIRES,
        destination=scratch,
        now=NOW,
    )
    assert result.refusals[0].code == "source_unobserved"
    assert not scratch.exists()


def test_a_missing_approver_is_refused(
    control: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    result = emit(control, scratch, [OwnerEntry(FULL, hash_of(FULL))], approver="  ")
    assert any(r.code == "approver_missing" for r in result.refusals)


@pytest.mark.parametrize(
    "relative", ["ops/proposal-authorizations", "ops/proposal-authorizations/wave", "ops"]
)
def test_a_destination_inside_or_around_the_record_directory_is_refused(
    control: Path, relative: str
) -> None:
    result = emit(control, control / relative, [OwnerEntry(FULL, hash_of(FULL))])
    assert result.refusals[0].code == "destination_is_the_record_directory"
    assert not (control / AUTHORIZATION_DIRNAME).exists()


def test_an_existing_scratch_record_is_never_overwritten(
    control: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    entries = [OwnerEntry(FULL, hash_of(FULL))]
    assert emit(control, scratch, entries).refusals == ()
    again = emit(control, scratch, entries)
    assert again.refusals[0].code == "exists"


# ---------------------------------------------------------------------------------------------
# the subcommand
# ---------------------------------------------------------------------------------------------


@pytest.fixture
def fake_github(monkeypatch: pytest.MonkeyPatch) -> LiveWorld:
    world = LiveWorld()
    calls: list[str] = []

    def head(repository: str, *, token: str | None = None) -> DefaultBranchRead:
        calls.append(repository)
        if repository in world.errors:
            return DefaultBranchRead(repository, error=world.errors[repository])
        return DefaultBranchRead(repository, sha=world.heads[repository], branch="main")

    def readme(repository: str, revision: str, path: str, *, token: str | None = None) -> FileRead:
        assert path == "README.md"
        return FileRead(repository, revision, path, found=world.readme.get(repository, True))

    monkeypatch.setattr(cli, "fetch_default_branch_sha", head)
    monkeypatch.setattr(cli, "fetch_file", readme)
    # nothing in the subcommand may write: any write-capable function fails the test if reached
    for name in ("default_put_contents", "default_create_ref", "default_create_pull_request"):
        monkeypatch.setattr(cli, name, lambda *a, **k: pytest.fail("a GitHub write was attempted"))
    return world


def run_cli(control: Path, *extra: str) -> int:
    return main(["wave-readiness", "--root", str(control), *extra])


def test_the_subcommand_prints_the_table_and_writes_nothing(
    control: Path, fake_github: LiveWorld, capsys: pytest.CaptureFixture[str]
) -> None:
    merge_to_origin_main(control, "sealed candidates")
    assert run_cli(control) == EXIT_OK
    out = capsys.readouterr().out
    assert FULL in out and DRY in out and OTHER in out
    assert "3 candidate(s)" in out and "READY_TO_AUTHORIZE" in out
    assert not (control / AUTHORIZATION_DIRNAME).exists()


def test_the_subcommand_reports_a_committed_and_merged_record_as_valid(
    control: Path, fake_github: LiveWorld, capsys: pytest.CaptureFixture[str]
) -> None:
    now = datetime.now(UTC)
    write_record(
        control,
        FULL,
        issued_at=stamp(now - timedelta(hours=1)),
        expires_at=stamp(now + timedelta(days=1)),
    )
    merge_to_origin_main(control, "record merged")
    assert run_cli(control, "--repo", FULL) == EXIT_OK
    out = capsys.readouterr().out
    assert "valid+merged" in out and "READY_TO_DISPATCH" in out


def test_the_subcommand_emits_into_a_scratch_directory_and_reports_the_dry_run(
    control: Path,
    fake_github: LiveWorld,
    tmp_path_factory: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    now = datetime.now(UTC).replace(microsecond=0)
    code = run_cli(
        control,
        "--emit-records",
        str(scratch),
        "--authorize",
        f"{FULL}@{hash_of(FULL)[:12]}",
        "--authorize",
        f"{DRY}@{hash_of(DRY)[:12]}",
        "--approver",
        "owner",
        "--expires-at",
        stamp(now + timedelta(days=2)),
    )
    out = capsys.readouterr().out
    assert code == EXIT_OK, out
    assert "dry run complete" in out
    assert (scratch / record_filename(DRY, hash_of(DRY))).is_file()
    assert not (control / AUTHORIZATION_DIRNAME).exists()


def test_the_subcommand_exits_unsafe_and_writes_nothing_for_an_unlisted_repository(
    control: Path,
    fake_github: LiveWorld,
    tmp_path_factory: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    now = datetime.now(UTC).replace(microsecond=0)
    code = run_cli(
        control,
        "--emit-records",
        str(scratch),
        "--authorize",
        f"{UNLISTED}@{'a' * 12}",
        "--approver",
        "owner",
        "--expires-at",
        stamp(now + timedelta(days=2)),
    )
    captured = capsys.readouterr()
    assert code == EXIT_UNSAFE
    assert "registry_not_listed" in captured.err
    assert not scratch.exists()


def test_the_subcommand_refuses_usage_mistakes(
    control: Path, fake_github: LiveWorld, tmp_path_factory: pytest.TempPathFactory
) -> None:
    scratch = tmp_path_factory.mktemp("scratch") / "wave"
    now = datetime.now(UTC).replace(microsecond=0)
    expires = stamp(now + timedelta(days=2))
    authorize = ["--authorize", f"{FULL}@{hash_of(FULL)[:12]}"]
    assert run_cli(control, *authorize) == EXIT_USAGE  # --authorize without --emit-records
    assert run_cli(control, "--emit-records", str(scratch), "--offline", *authorize) == EXIT_USAGE
    assert run_cli(control, "--emit-records", str(scratch), *authorize) == EXIT_USAGE  # no expiry
    assert (
        run_cli(control, "--emit-records", str(scratch), "--expires-at", "tomorrow", *authorize)
        == EXIT_USAGE
    )
    assert (
        run_cli(control, "--emit-records", str(scratch), "--expires-at", expires) == EXIT_USAGE
    )  # no list
    assert not scratch.exists()


def test_the_subcommand_refuses_the_record_directory_as_a_destination(
    control: Path, fake_github: LiveWorld
) -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    code = run_cli(
        control,
        "--emit-records",
        str(control / AUTHORIZATION_DIRNAME),
        "--authorize",
        f"{FULL}@{hash_of(FULL)[:12]}",
        "--approver",
        "owner",
        "--expires-at",
        stamp(now + timedelta(days=2)),
    )
    assert code == EXIT_UNSAFE
    assert not (control / AUTHORIZATION_DIRNAME).exists()
