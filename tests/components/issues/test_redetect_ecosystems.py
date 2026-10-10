"""Re-detection for every evidence shape the 2026-10-09 harvest produced (G6-W07, TC-ISS-02).

Each registry gets a resolved-versus-persists pair; the toolchain and link shapes get the same plus
the negative controls that keep an unreadable or changed repository from reading as a resolution.
Every read is injected, so no test reaches a network.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    IssueRef,
    TriggeringCheck,
    load_handoff,
)
from repository_presenter.components.issues.redetect import (
    RedetectionReads,
    apply_redetection,
    redetect,
    replay_gap,
)
from repository_presenter.components.readme.validation.registry import BLOCKING_CHECKS
from repository_presenter.core.github.read_client import DefaultBranchRead, FileRead, TreeRead
from repository_presenter.core.package_registry import RegistryObservation
from support import REPO_ROOT

REPO = "example-org/Example-FOSS"
SOURCE = "a" * 40
MOVED = "b" * 40
CORPUS = sorted((REPO_ROOT / "evidence" / "upstream-defects").glob("*/*.json"))


def handoff(
    check_id: str,
    evidence: tuple[EvidenceEntry, ...],
    *,
    status: Any = "HANDOFF_PENDING",
    version: str = "2",
) -> Handoff:
    filed = status == "FILED"
    return Handoff(
        schema_version=1,
        repository=REPO,
        source_revision=SOURCE,
        defect_fingerprint="sha256:" + "d" * 64,
        triggering_check=TriggeringCheck(id=check_id, version=version, causal_stage="EXTRACTING"),
        evidence=evidence,
        claim="A plain factual sentence.",
        suggested_issue_title="title",
        suggested_issue_body="body",
        status=status,
        issue_ref=IssueRef(1, "https://github.com/o/r/issues/1") if filed else None,
        close_reason=None,
    )


def _refuse(*_a: object, **_k: object) -> Any:
    raise AssertionError("a read this test did not expect")


def reads(head: str | None = SOURCE, **overrides: Any) -> RedetectionReads:
    base: dict[str, Any] = {
        "fetch_default_branch_sha": lambda repository, **_: (
            DefaultBranchRead(repository, sha=head, branch="main")
            if head
            else DefaultBranchRead(repository, error="HTTP 502")
        ),
        "fetch_file": _refuse,
        "fetch_tree": _refuse,
        "observe_pypi": _refuse,
        "observe_registry": _refuse,
    }
    return RedetectionReads(**{**base, **overrides})


# --- registries: resolved versus persists, one pair each -----------------------------------------

REGISTRY_CASES = [
    ("typescript", "@aspose/3d", "https://registry.npmjs.org/@aspose%2f3d"),
    (
        "net",
        "aspose.imaging.foss",
        "https://api.nuget.org/v3-flatcontainer/aspose.imaging.foss/index.json",
    ),
    (
        "java",
        "com.aspose:aspose-slides-foss",
        "https://repo1.maven.org/maven2/com/aspose/aspose-slides-foss/maven-metadata.xml",
    ),
    ("rust", "aspose-cells-foss", "https://crates.io/api/v1/crates/aspose-cells-foss"),
    ("go", "example.com/mod", "https://proxy.golang.org/example.com/mod/@v/list"),
]


def _registry_reads(ecosystem: str, name: str, url: str, observation: RegistryObservation) -> Any:
    asked: list[tuple[str, str, str | None]] = []

    def observe(eco: str, package: str, version: str | None) -> RegistryObservation:
        asked.append((eco, package, version))
        return observation

    return reads(observe_registry=observe), asked


@pytest.mark.parametrize(
    ("ecosystem", "name", "url"), REGISTRY_CASES, ids=[c[0] for c in REGISTRY_CASES]
)
def test_a_registry_that_still_lacks_the_package_persists(
    ecosystem: str, name: str, url: str
) -> None:
    h = handoff("BC-02", (EvidenceEntry(url, "HTTP 404"), EvidenceEntry("README.md", "line 4")))
    r, asked = _registry_reads(ecosystem, name, url, RegistryObservation(name, url, found=False))
    result = redetect(h, reads=r)
    assert result.still_fires is True and result.proposed_status is None
    assert asked == [(ecosystem, name, None)]
    assert name in result.note


@pytest.mark.parametrize(
    ("ecosystem", "name", "url"), REGISTRY_CASES, ids=[c[0] for c in REGISTRY_CASES]
)
def test_a_registry_that_now_has_the_package_resolves_a_filed_handoff(
    ecosystem: str, name: str, url: str
) -> None:
    h = handoff("BC-02", (EvidenceEntry(url, "HTTP 404"),), status="FILED")
    r, _ = _registry_reads(ecosystem, name, url, RegistryObservation(name, url, found=True))
    result = redetect(h, reads=r)
    assert result.still_fires is False
    assert result.proposed_status == "RESOLVED_UPSTREAM"
    assert apply_redetection(h, result).status == "RESOLVED_UPSTREAM"


@pytest.mark.parametrize(
    ("ecosystem", "name", "url"), REGISTRY_CASES, ids=[c[0] for c in REGISTRY_CASES]
)
def test_an_unreachable_registry_is_inconclusive_never_a_resolution(
    ecosystem: str, name: str, url: str
) -> None:
    """Negative control: 'we could not check' is neither 'it now exists' nor 'still missing'."""
    h = handoff("BC-02", (EvidenceEntry(url, "HTTP 404"),), status="FILED")
    r, _ = _registry_reads(
        ecosystem, name, url, RegistryObservation(name, url, found=False, error="registry down")
    )
    result = redetect(h, reads=r)
    assert result.still_fires is None and result.proposed_status is None
    assert "registry down" in result.note


def test_the_control_entry_is_never_probed() -> None:
    nuget = "https://api.nuget.org/v3-flatcontainer/{}/index.json"
    h = handoff(
        "BC-02",
        (
            EvidenceEntry(nuget.format("aspose.imaging.foss"), "HTTP 404"),
            EvidenceEntry("https://www.nuget.org/packages/Aspose.Imaging.Foss", "HTTP 404"),
            EvidenceEntry(nuget.format("aspose.imaging"), "Control: HTTP 200"),
        ),
    )
    r, asked = _registry_reads("net", "x", "u", RegistryObservation("x", "u", found=False))
    redetect(h, reads=r)
    assert asked == [("net", "aspose.imaging.foss", None)]


def test_two_packages_in_one_handoff_is_a_gap_and_not_guessed() -> None:
    h = handoff(
        "BC-02",
        (
            EvidenceEntry("https://pypi.org/pypi/a/json", "HTTP 404"),
            EvidenceEntry("https://registry.npmjs.org/b", "HTTP 404"),
        ),
    )
    assert replay_gap(h) is not None and "2 packages" in replay_gap(h)  # type: ignore[operator]
    result = redetect(h, reads=reads())
    assert result.still_fires is None and "found 2" in result.note


# --- toolchain findings (BC-03, and BC-02 with no registry URL) ----------------------------------

TOOLCHAIN = (
    EvidenceEntry("README.md", "lines 166-172"),
    EvidenceEntry("dotnet build of a console project", "error CS1503"),
    EvidenceEntry("src/Scene.cs", "lines 314, 324"),
)


def _tree(blobs: dict[str, str], *, truncated: bool = False, error: str | None = None) -> TreeRead:
    return TreeRead(
        REPO, "x", paths=tuple(sorted(blobs)), truncated=truncated, error=error, blob_shas=blobs
    )


@pytest.mark.parametrize("check_id", ["BC-03", "BC-02"])
def test_a_toolchain_finding_persists_while_the_revision_has_not_moved(check_id: str) -> None:
    result = redetect(handoff(check_id, TOOLCHAIN), reads=reads())
    assert result.still_fires is True and result.revision_drifted is False
    assert result.proposed_status is None
    assert "not re-executed" in result.note


def test_a_toolchain_finding_persists_when_the_moved_tree_is_identical() -> None:
    same = {"README.md": "1", "src/Scene.cs": "2"}
    r = reads(MOVED, fetch_tree=lambda repository, revision, **_: _tree(dict(same)))
    result = redetect(handoff("BC-03", TOOLCHAIN), reads=r)
    assert result.still_fires is True and result.revision_drifted is True


def test_a_toolchain_finding_is_inconclusive_when_the_tree_changed() -> None:
    """Negative control: a changed tree may or may not have fixed it; only a re-run can say."""
    trees = {
        SOURCE: {"README.md": "1", "src/Scene.cs": "2"},
        MOVED: {"README.md": "1", "src/Scene.cs": "9"},
    }
    r = reads(MOVED, fetch_tree=lambda repository, revision, **_: _tree(trees[revision]))
    result = redetect(handoff("BC-03", TOOLCHAIN, status="FILED"), reads=r)
    assert result.still_fires is None
    assert result.proposed_status is None and result.proposed_close_reason is None
    assert "1 file(s) differ (1 of the 2" in result.note
    assert {e.path: e.detail for e in result.fresh_evidence}["src/Scene.cs"].startswith("changed")


@pytest.mark.parametrize("bad", [_tree({}, truncated=True), _tree({}, error="HTTP 500")])
def test_an_uncomparable_tree_is_inconclusive(bad: TreeRead) -> None:
    r = reads(MOVED, fetch_tree=lambda repository, revision, **_: bad)
    assert redetect(handoff("BC-03", TOOLCHAIN), reads=r).still_fires is None


def test_an_unreadable_head_is_inconclusive() -> None:
    result = redetect(handoff("BC-03", TOOLCHAIN), reads=reads(None))
    assert result.still_fires is None and "HTTP 502" in result.note


def test_a_toolchain_finding_never_proposes_resolution_even_when_filed() -> None:
    """The only way this redetector could say 'fixed' is a re-run it cannot do."""
    r = reads(MOVED, fetch_tree=lambda repository, revision, **_: _tree({"a.cs": "1"}))
    filed = handoff("BC-03", TOOLCHAIN, status="FILED")
    assert redetect(filed, reads=r).proposed_status is None
    assert redetect(filed, reads=reads()).proposed_status is None


def test_a_toolchain_handoff_citing_no_repository_file_is_a_gap() -> None:
    h = handoff("BC-03", (EvidenceEntry("dotnet build of a console project", "error"),))
    assert replay_gap(h) is not None and "BC-03" in replay_gap(h)  # type: ignore[operator]
    result = redetect(h, reads=reads())
    assert result.still_fires is None and "cannot redetect" in result.note


def test_a_bc02_handoff_with_a_registry_url_is_replayed_not_carried_as_toolchain() -> None:
    url = "https://crates.io/api/v1/crates/x"
    h = handoff("BC-02", (EvidenceEntry(url, "HTTP 404"), EvidenceEntry("Cargo.toml", "name")))
    r, asked = _registry_reads("rust", "x", url, RegistryObservation("x", url, found=True))
    redetect(h, reads=r)
    assert asked == [("rust", "x", None)]


# --- BC-06: a README link to a path the tree lacks ------------------------------------------------

LINK = (
    EvidenceEntry("README.md", "line 518: [Guide](docs/guide.md) (revision aaaa)"),
    EvidenceEntry("gh api repos/o/r/contents/docs", "HTTP 404 Not Found"),
)


def _link_reads(readme: str | None, tree: TreeRead, head: str = SOURCE) -> RedetectionReads:
    def fetch_file(repository: str, revision: str, path: str, **_: Any) -> FileRead:
        if readme is None:
            return FileRead(repository, revision, path, found=False, error="HTTP 500")
        return FileRead(repository, revision, path, found=True, content=readme)

    return reads(head, fetch_file=fetch_file, fetch_tree=lambda repository, revision, **_: tree)


def test_a_dead_link_persists_while_linked_and_absent() -> None:
    r = _link_reads("See [Guide](docs/guide.md).", _tree({"README.md": "1"}))
    result = redetect(handoff("BC-06", LINK), reads=r)
    assert result.still_fires is True
    assert "docs/guide.md" in result.note


def test_a_dead_link_resolves_when_the_target_now_exists() -> None:
    r = _link_reads("See [Guide](docs/guide.md).", _tree({"README.md": "1", "docs/guide.md": "2"}))
    filed = handoff("BC-06", LINK, status="FILED")
    result = redetect(filed, reads=r)
    assert result.still_fires is False and result.proposed_status == "RESOLVED_UPSTREAM"


def test_a_dead_link_resolves_when_the_link_was_removed() -> None:
    r = _link_reads("No links any more.", _tree({"README.md": "1"}), head=MOVED)
    current = next(c.version for c in BLOCKING_CHECKS if c.id == "BC-06")
    filed = handoff("BC-06", LINK, status="FILED", version=current)
    result = redetect(filed, reads=r)
    assert result.still_fires is False
    assert result.proposed_close_reason == "completed"  # the revision moved and the check did not
    stale = handoff("BC-06", LINK, status="FILED", version="0")
    assert redetect(stale, reads=r).proposed_close_reason == "not planned"  # the check moved


def test_a_directory_target_exists_when_any_file_is_under_it() -> None:
    link = (EvidenceEntry("README.md", "[Docs](docs/)"),)
    r = _link_reads("[Docs](docs/)", _tree({"docs/a.md": "1"}))
    assert redetect(handoff("BC-06", link), reads=r).still_fires is False


def test_a_link_in_a_subdirectory_document_resolves_relative_to_it() -> None:
    link = (EvidenceEntry("docs/README.md", "[Guide](guide.md)"),)
    absent = _link_reads("[Guide](guide.md)", _tree({"docs/README.md": "1"}))
    assert redetect(handoff("BC-06", link), reads=absent).still_fires is True
    present = _link_reads("[Guide](guide.md)", _tree({"docs/README.md": "1", "docs/guide.md": "2"}))
    assert redetect(handoff("BC-06", link), reads=present).still_fires is False


@pytest.mark.parametrize(
    "tree", [_tree({}, truncated=True), _tree({}, error="HTTP 500")], ids=["truncated", "error"]
)
def test_an_unlistable_tree_is_inconclusive_for_a_link(tree: TreeRead) -> None:
    """Negative control: an unlistable tree must not read as 'the target is missing'."""
    result = redetect(handoff("BC-06", LINK), reads=_link_reads("[Guide](docs/guide.md)", tree))
    assert result.still_fires is None


def test_an_unreadable_document_is_inconclusive_for_a_link() -> None:
    result = redetect(handoff("BC-06", LINK), reads=_link_reads(None, _tree({})))
    assert result.still_fires is None and "could not re-read README.md" in result.note


@pytest.mark.parametrize(
    "detail", ["see https://example.com/x", "[x](https://example.com/x)", "[x](#anchor)", "no link"]
)
def test_a_link_that_is_not_a_repository_path_is_a_gap(detail: str) -> None:
    h = handoff("BC-06", (EvidenceEntry("README.md", detail),))
    assert replay_gap(h) is not None and "BC-06" in replay_gap(h)  # type: ignore[operator]


# --- NOT_PROCESSABLE beyond .py -------------------------------------------------------------------


def _source_reads(contents: dict[str, str | None], head: str = SOURCE) -> RedetectionReads:
    def fetch_file(repository: str, revision: str, path: str, **_: Any) -> FileRead:
        content = contents.get(path)
        if content is None:
            return FileRead(repository, revision, path, found=False)
        return FileRead(repository, revision, path, found=True, content=content)

    return reads(head, fetch_file=fetch_file)


NOT_PROCESSABLE = (
    EvidenceEntry("src/main/A.java", "tree-sitter reports an error"),
    EvidenceEntry("python ast.parse over every .py file", "35 of 45"),
)


def test_a_non_python_source_that_still_fails_to_parse_persists() -> None:
    r = _source_reads({"src/main/A.java": "class A { void f( }\n"})
    result = redetect(handoff("NOT_PROCESSABLE", NOT_PROCESSABLE, version="1"), reads=r)
    assert result.still_fires is True
    assert result.fresh_evidence[0].detail.startswith("tree-sitter (java)")


def test_a_non_python_source_that_now_parses_resolves_a_filed_handoff() -> None:
    r = _source_reads({"src/main/A.java": "class A { void f() {} }\n"})
    filed = handoff("NOT_PROCESSABLE", NOT_PROCESSABLE, status="FILED", version="1")
    result = redetect(filed, reads=r)
    assert result.still_fires is False
    assert result.fresh_evidence[0].detail == "tree-sitter (java): OK"
    assert result.proposed_status == "RESOLVED_UPSTREAM"


def test_a_missing_non_python_source_is_inconclusive() -> None:
    result = redetect(
        handoff("NOT_PROCESSABLE", NOT_PROCESSABLE, version="1"), reads=_source_reads({})
    )
    assert result.still_fires is None


def test_a_suffix_with_no_parser_is_a_gap_not_a_clean_parse() -> None:
    """Negative control: evidence naming only files nothing can parse is unreplayable."""
    h = handoff("NOT_PROCESSABLE", (EvidenceEntry("notes.txt", "garbled"),), version="1")
    assert replay_gap(h) is not None and "names none" in replay_gap(h)  # type: ignore[operator]
    result = redetect(h, reads=reads())
    assert result.still_fires is None


def test_a_command_ending_in_a_source_suffix_is_not_a_named_path() -> None:
    h = handoff("NOT_PROCESSABLE", (EvidenceEntry("python probe.py", "x"),), version="1")
    assert replay_gap(h) is not None


# --- the committed corpus -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path", CORPUS, ids=lambda p: p.parent.name.split("__")[1][:30] + p.stem[:6]
)
def test_every_committed_handoff_has_a_replayable_recheck(path: Path) -> None:
    """The 2026-10-09 harvest's 12 unreplayable handoffs (and the 6 others) are all covered."""
    assert replay_gap(load_handoff(path)) is None


def test_the_corpus_is_the_one_the_gap_was_measured_on() -> None:
    assert len(CORPUS) >= 18
    assert json.loads(CORPUS[0].read_text("utf-8"))["schema_version"] == 1


def test_every_registered_redetector_replays_a_handoff_it_calls_replayable() -> None:
    """A redetector never raises on a handoff its own gap check accepts."""
    for path in CORPUS:
        h = load_handoff(path)
        answered: Callable[..., Any] = lambda *a, **k: RegistryObservation(  # noqa: E731
            "n", "u", found=False
        )
        r = reads(
            h.source_revision,
            observe_pypi=answered,
            observe_registry=answered,
            fetch_file=lambda repository, revision, p, **_: FileRead(
                repository, revision, p, found=False
            ),
            fetch_tree=lambda repository, revision, **_: _tree({}),
        )
        assert redetect(h, reads=r).triggering_check_id == h.triggering_check.id
