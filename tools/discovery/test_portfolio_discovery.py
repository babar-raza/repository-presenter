"""Regression tests for portfolio_discovery.py.

Every test injects a fake `FetchFn` fixture; none makes a live network call (this project's own
test convention - see tools/reviewer/test_research_edit.py, and the module's own docstring). Run
directly: `pytest tools/discovery/test_portfolio_discovery.py` - this directory is deliberately
outside pyproject.toml's `pythonpath`/collection scope (`tools/README.md`'s boundary from
`src/`), so it never runs as part of `pytest tests/`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

# tools/discovery/ is outside pyproject.toml's pythonpath, same as tools/reviewer/ - inserted
# here rather than adding a conftest.py, matching tools/reviewer/test_research_edit.py's own
# precedent.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from portfolio_discovery import (  # noqa: E402
    KNOWN_FAMILY_SLUGS,
    BuildProbeResult,
    DiscoveryReport,
    OrgResult,
    RepoClassification,
    RepoObservation,
    _noise_hint,
    classify_repo_name,
    default_build_probe,
    evaluate_admission_criteria,
    list_org_repos,
    load_registered_repositories,
    matches_product_convention,
    probe_org,
    render_report,
    run_auto_admission,
    run_discovery,
    search_candidate_orgs,
    write_admitted_entries,
)


def _repo(
    org: str,
    name: str,
    *,
    repo_id: int = 1,
    node_id: str = "R_1",
    private: bool = False,
    archived: bool = False,
    fork: bool = False,
    pushed_at: str = "2026-09-01T00:00:00Z",
) -> dict[str, Any]:
    return {
        "name": name,
        "full_name": f"{org}/{name}",
        "id": repo_id,
        "node_id": node_id,
        "private": private,
        "archived": archived,
        "fork": fork,
        "pushed_at": pushed_at,
    }


class FakeGitHub:
    """A tiny in-memory stand-in for the GitHub REST API, keyed on exact URL prefixes.

    Registered via `orgs[login] = {"public_repos": N, "pages": [[repo, ...], ...]}` and
    `search_pages = [...]`. Anything not registered 404s, matching the real API's behaviour for
    an org that does not exist.
    """

    def __init__(self) -> None:
        self.orgs: dict[str, dict[str, Any]] = {}
        self.search_pages: list[dict[str, Any]] = []
        self.calls: list[str] = []

    def register_org(
        self,
        login: str,
        *,
        public_repos: int,
        repos: list[dict[str, Any]] | None = None,
    ) -> None:
        self.orgs[login] = {"public_repos": public_repos, "repos": repos or []}

    def fetch(self, url: str, token: str | None) -> tuple[int, Any]:
        self.calls.append(url)
        if url.startswith("https://api.github.com/orgs/") and "/repos" not in url:
            login = url.rsplit("/", 1)[-1]
            org = self.orgs.get(login)
            if org is None:
                return 404, {"message": "Not Found"}
            return 200, {"login": login, "public_repos": org["public_repos"]}
        if "/repos?type=public" in url:
            login = url.split("/orgs/", 1)[1].split("/repos", 1)[0]
            org = self.orgs.get(login)
            if org is None:
                return 404, {"message": "Not Found"}
            page = int(url.rsplit("page=", 1)[-1])
            per_page = int(url.split("per_page=", 1)[1].split("&", 1)[0])
            all_repos = org["repos"]
            start = (page - 1) * per_page
            return 200, all_repos[start : start + per_page]
        if url.startswith("https://api.github.com/search/repositories"):
            page = int(url.rsplit("page=", 1)[-1])
            index = page - 1
            if index < len(self.search_pages):
                return 200, self.search_pages[index]
            return 200, {"items": []}
        return 404, {"message": "unregistered URL in test fixture"}


def test_matches_product_convention_accepts_the_canonical_shape_case_insensitively() -> (
    None
):
    assert matches_product_convention("Aspose.3D-FOSS-for-Python")  # dot form
    assert matches_product_convention(
        "Aspose-PDF-FOSS-for-Go"
    )  # hyphen form, also registered
    assert matches_product_convention(
        "Aspose.Imaging-Foss-for-.NET"
    )  # the real 2026-09-11 miss
    assert not matches_product_convention(".github")
    # Same convention shape as a real product repo, but a known non-SDK companion (MCP server,
    # docs/investigations/04-portfolio-discovery.md §2.5) - deliberately still matches, since name
    # shape alone cannot make that adjudication; it is a "new candidate" for a human to exclude,
    # never a silent auto-exclusion.
    assert matches_product_convention("Aspose-PDF-FOSS-for-Go-MCP")


def test_classify_repo_name_matches_the_canonical_dot_form() -> None:
    result = classify_repo_name("Aspose.3D-FOSS-for-Python")
    assert result == RepoClassification(family="3d", platform="python", matched=True)


def test_classify_repo_name_matches_the_lowercase_foss_for_variant() -> None:
    result = classify_repo_name("aspose-pdf-foss-for-go")
    assert result == RepoClassification(family="pdf", platform="go", matched=True)


def test_classify_repo_name_matches_the_legacy_form() -> None:
    result = classify_repo_name("aspose-3d-python")
    assert result == RepoClassification(family="3d", platform="python", matched=True)


def test_classify_repo_name_is_case_insensitive_for_the_real_2026_09_11_miss() -> None:
    # The real historical bug this classifier must not repeat: a case-sensitive canonical
    # pattern silently failed to classify "Aspose.Imaging-Foss-for-.NET" (mixed-case "Foss"),
    # docs/investigations/04-portfolio-discovery.md §2.5.
    result = classify_repo_name("Aspose.Imaging-Foss-for-.NET")
    assert result == RepoClassification(family="imaging", platform="net", matched=True)
    # Also confirm an all-uppercase / all-lowercase spelling of the same shape still matches.
    assert classify_repo_name("ASPOSE.IMAGING-FOSS-FOR-.NET").matched
    assert classify_repo_name("aspose.imaging-foss-for-.net").matched


def test_classify_repo_name_reports_an_unmatched_name_explicitly_not_silently() -> None:
    result = classify_repo_name(".github")
    # Explicit typed outcome, never a bare None - the field is present and False, not absent.
    assert result.matched is False
    assert result.family is None
    assert result.platform is None
    assert isinstance(result, RepoClassification)


def test_repo_observation_from_api_carries_the_classification_through() -> None:
    observation = RepoObservation.from_api(
        "aspose-imaging-foss",
        _repo("aspose-imaging-foss", "Aspose.Imaging-Foss-for-.NET"),
    )
    assert observation.classification == RepoClassification(
        family="imaging", platform="net", matched=True
    )

    unmatched_observation = RepoObservation.from_api(
        "aspose-imaging-foss", _repo("aspose-imaging-foss", ".github")
    )
    assert unmatched_observation.classification.matched is False


def test_load_registered_repositories_lowercases_and_reads_only(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    original = json.dumps(
        {"entries": [{"repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python"}]}
    )
    registry.write_text(original, encoding="utf-8", newline="\n")
    result = load_registered_repositories(registry)
    assert result == {"aspose-3d-foss/aspose.3d-foss-for-python"}
    assert registry.read_text(encoding="utf-8") == original  # never written


def test_probe_org_distinguishes_populated_empty_not_found_and_inaccessible() -> None:
    gh = FakeGitHub()
    gh.register_org(
        "aspose-3d-foss", public_repos=1, repos=[_repo("aspose-3d-foss", "x")]
    )
    gh.register_org("aspose-medical-foss", public_repos=0, repos=[])

    populated = probe_org("aspose-3d-foss", token=None, fetch=gh.fetch)
    assert populated.status == "populated"
    assert len(populated.repos) == 1

    empty = probe_org("aspose-medical-foss", token=None, fetch=gh.fetch)
    assert empty.status == "empty"
    assert empty.repos == ()

    missing = probe_org("aspose-nonexistent-foss", token=None, fetch=gh.fetch)
    assert missing.status == "not_found"

    def broken_fetch(url: str, token: str | None) -> tuple[int, Any]:
        if "/repos" not in url:
            return 200, {"login": "aspose-broken-foss", "public_repos": 5}
        return 403, {"message": "rate limited"}

    inaccessible = probe_org("aspose-broken-foss", token=None, fetch=broken_fetch)
    assert inaccessible.status == "inaccessible"
    assert inaccessible.detail is not None
    # The essential Gate C0 distinction under test: a failed scan is never reported the same way
    # as a genuinely empty org.
    assert inaccessible.status != empty.status


def test_list_org_repos_paginates_until_a_short_page() -> None:
    gh = FakeGitHub()
    many = [
        _repo("aspose-pdf-foss", f"Aspose.PDF-FOSS-for-Lang{i}", repo_id=i)
        for i in range(1, 151)
    ]
    gh.register_org("aspose-pdf-foss", public_repos=len(many), repos=many)
    repos = list_org_repos("aspose-pdf-foss", token=None, fetch=gh.fetch, per_page=100)
    assert len(repos) == 150
    assert repos[0].name == "Aspose.PDF-FOSS-for-Lang1"
    assert repos[-1].name == "Aspose.PDF-FOSS-for-Lang150"


def test_search_candidate_orgs_filters_to_the_aspose_foss_org_pattern() -> None:
    gh = FakeGitHub()
    gh.search_pages = [
        {
            "items": [
                {"owner": {"login": "aspose-imaging-foss"}},
                {
                    "owner": {"login": "aspose-imaging-foss"}
                },  # duplicate, dedupes to one
                {"owner": {"login": "some-other-org"}},  # wrong pattern, excluded
                {"owner": {"login": "ASPOSE-CAD-FOSS"}},  # case-insensitive match
            ]
        }
    ]
    orgs = search_candidate_orgs(token=None, fetch=gh.fetch)
    assert orgs == {"aspose-imaging-foss", "aspose-cad-foss"}


def test_run_discovery_identifies_a_known_missing_entry_against_the_registry(
    tmp_path: Path,
) -> None:
    """The core diff-logic proof the task requires: a real, populated, convention-matching repo
    that is absent from the registry must land in `new_candidates`, and one already present must
    land in `already_registered` - mirroring the live aspose-imaging-foss/Aspose.Imaging-FOSS-
    for-.NET finding this module was built to formalize.
    """
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {"entries": [{"repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python"}]}
        ),
        encoding="utf-8",
        newline="\n",
    )
    gh = FakeGitHub()
    gh.register_org(
        "aspose-3d-foss",
        public_repos=1,
        repos=[_repo("aspose-3d-foss", "Aspose.3D-FOSS-for-Python", repo_id=101)],
    )
    gh.register_org(
        "aspose-imaging-foss",
        public_repos=2,
        repos=[
            _repo("aspose-imaging-foss", "Aspose.Imaging-FOSS-for-.NET", repo_id=202),
            _repo("aspose-imaging-foss", ".github", repo_id=203),  # noise, unmatched
        ],
    )
    for slug in KNOWN_FAMILY_SLUGS - {"3d", "imaging"}:
        gh.register_org(f"aspose-{slug}-foss", public_repos=0, repos=[])

    report = run_discovery(registry_path=registry, token=None, fetch=gh.fetch)

    already = {r.full_name for r in report.already_registered}
    new = {r.full_name for r in report.new_candidates}
    unmatched = {r.full_name for r in report.unmatched_repos}
    assert already == {"aspose-3d-foss/Aspose.3D-FOSS-for-Python"}
    assert new == {"aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET"}
    assert unmatched == {"aspose-imaging-foss/.github"}
    empty_logins = {r.org for r in report.empty_orgs}
    assert (
        "aspose-medical-foss" in empty_logins
    )  # one of KNOWN_FAMILY_SLUGS registered empty


def test_noise_hint_flags_mcp_suffix_without_excluding_anything() -> None:
    assert _noise_hint("Aspose-PDF-FOSS-for-Go-MCP") is not None
    assert "04" in _noise_hint("Aspose-PDF-FOSS-for-Go-MCP")  # points at the precedent
    assert _noise_hint("Aspose.PDF-FOSS-for-Go") is None
    # The hint is annotation-only: it must never change what run_discovery classifies a repo as.
    assert matches_product_convention("Aspose-PDF-FOSS-for-Go-MCP")


def test_run_discovery_never_writes_the_registry_file(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    original = json.dumps({"entries": []})
    registry.write_text(original, encoding="utf-8", newline="\n")
    before = registry.stat().st_mtime_ns
    gh = FakeGitHub()
    for slug in KNOWN_FAMILY_SLUGS:
        gh.register_org(f"aspose-{slug}-foss", public_repos=0, repos=[])
    run_discovery(registry_path=registry, token=None, fetch=gh.fetch)
    assert registry.stat().st_mtime_ns == before
    assert registry.read_text(encoding="utf-8") == original


def test_render_report_includes_every_required_section() -> None:
    report = DiscoveryReport(
        scanned_at="2026-09-17T00:00:00+00:00",
        probed_slugs=("3d", "imaging"),
        search_discovered_orgs=("aspose-imaging-foss",),
        org_results=(
            OrgResult(
                org="aspose-medical-foss",
                status="empty",
                public_repos_reported=0,
                repos=(),
            ),
            OrgResult(
                org="aspose-nope-foss",
                status="not_found",
                public_repos_reported=None,
                repos=(),
            ),
            OrgResult(
                org="aspose-broken-foss",
                status="inaccessible",
                public_repos_reported=None,
                repos=(),
                detail="rate limited",
            ),
        ),
        already_registered=(
            RepoObservation(
                org="aspose-3d-foss",
                name="Aspose.3D-FOSS-for-Python",
                full_name="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
                repository_id=1,
                node_id="R_1",
                private=False,
                archived=False,
                fork=False,
                pushed_at="2026-09-01T00:00:00Z",
                matches_convention=True,
                classification=RepoClassification(
                    family="3d", platform="python", matched=True
                ),
            ),
        ),
        new_candidates=(
            RepoObservation(
                org="aspose-imaging-foss",
                name="Aspose.Imaging-FOSS-for-.NET",
                full_name="aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET",
                repository_id=2,
                node_id="R_2",
                private=False,
                archived=False,
                fork=False,
                pushed_at="2026-09-16T00:00:00Z",
                matches_convention=True,
                classification=RepoClassification(
                    family="imaging", platform="net", matched=True
                ),
            ),
        ),
        unmatched_repos=(),
    )
    text = render_report(report, investigation_number="10")
    assert text.startswith("# Investigation 10 — Portfolio Discovery Scan\n")
    for heading in (
        "## How the candidate organization list was assembled",
        "### Already registered (1 matches)",
        "### Newly discovered, populated (1 candidates - not yet in the registry)",
        "### Unmatched / noise repositories (0)",
        "### Reserved, empty organizations (1)",
        "### Probed slugs with no matching organization (1)",
        "### Inaccessible organizations - scan failed, not treated as empty (1)",
    ):
        assert heading in text, heading
    assert "aspose-3d-foss/Aspose.3D-FOSS-for-Python" in text
    assert "aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET" in text
    assert "aspose-medical-foss" in text
    assert "aspose-broken-foss" in text
    assert "rate limited" in text


# --- Auto-admission (OWNER-08 follow-up) ---------------------------------------------------------
#
# Every test below is either pure (evaluate_admission_criteria, no network/filesystem at all) or
# injects a fake BuildProbeFn - the same "no live network/build call in this suite" convention
# FakeGitHub already established for FetchFn. default_build_probe's own real clone/subprocess path
# is never exercised here; two of its purely-offline early-exit branches are, since they return
# before ever touching the network (see the two tests at the bottom of this section).


def _observation(
    org: str,
    name: str,
    *,
    repo_id: int = 900,
    node_id: str = "R_900",
    fork: bool = False,
    archived: bool = False,
) -> RepoObservation:
    return RepoObservation.from_api(
        org,
        _repo(
            org, name, repo_id=repo_id, node_id=node_id, fork=fork, archived=archived
        ),
    )


def _registry_file(tmp_path: Path, entries: list[dict[str, Any]]) -> Path:
    path = tmp_path / "registry.json"
    path.write_text(
        json.dumps(
            {"schema_version": 1, "entries": entries}, indent=2, ensure_ascii=False
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


_EXISTING_ENTRY = {
    "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
    "family": "3d",
    "platform": "python",
    "ecosystem": "python",
    "mode": "dry_run",
    "policy_profile": "aspose-3d-foss-python",
    "active": True,
    "provider_identity": {
        "provider": "github",
        "repository_id": 101,
        "node_id": "R_101",
    },
}


def test_evaluate_admission_criteria_passes_a_clean_known_family_repository() -> None:
    repo = _observation("aspose-imaging-foss", "Aspose.Imaging-FOSS-for-.NET")
    assert "imaging" in KNOWN_FAMILY_SLUGS
    assert evaluate_admission_criteria(repo) is None


def test_evaluate_admission_criteria_rejects_a_fork() -> None:
    repo = _observation(
        "aspose-imaging-foss", "Aspose.Imaging-FOSS-for-.NET", fork=True
    )
    reason = evaluate_admission_criteria(repo)
    assert reason == "repository is a fork"


def test_evaluate_admission_criteria_rejects_an_archived_repository() -> None:
    repo = _observation(
        "aspose-imaging-foss", "Aspose.Imaging-FOSS-for-.NET", archived=True
    )
    reason = evaluate_admission_criteria(repo)
    assert reason == "repository is archived"


def test_evaluate_admission_criteria_rejects_an_org_outside_known_family_slugs() -> (
    None
):
    # A real, convention-shaped repository under a real aspose-<family>-foss-pattern org that is
    # not (yet) on the maintained KNOWN_FAMILY_SLUGS list - e.g. found only by the search leg.
    # Standing "no external repos" scope is unaffected: the org shape itself is still fine, only
    # KNOWN_FAMILY_SLUGS membership is missing.
    repo = _observation("aspose-madeup-foss", "Aspose.Madeup-FOSS-for-Python")
    assert "madeup" not in KNOWN_FAMILY_SLUGS
    reason = evaluate_admission_criteria(repo)
    assert reason is not None
    assert "KNOWN_FAMILY_SLUGS" in reason


def test_evaluate_admission_criteria_rejects_an_org_outside_the_aspose_foss_pattern() -> (
    None
):
    repo = _observation("some-other-org", "Aspose.Imaging-FOSS-for-.NET")
    reason = evaluate_admission_criteria(repo)
    assert reason is not None
    assert "is not an aspose-<family>-foss org" in reason


def test_evaluate_admission_criteria_rejects_the_strict_naming_mismatch() -> None:
    # Matches the looser discovery-time prefix (matches_convention) but not the registry's own
    # strict full-match naming contract - the real, previously documented non-SDK companion repo
    # (docs/investigations/04-portfolio-discovery.md §2.5). Under a real KNOWN_FAMILY_SLUGS org so
    # only the naming check, not the scope check, is under test.
    repo = _observation("aspose-pdf-foss", "Aspose-PDF-FOSS-for-Go-MCP")
    assert "pdf" in KNOWN_FAMILY_SLUGS
    assert repo.matches_convention  # the loose check this module already uses elsewhere
    reason = evaluate_admission_criteria(repo)
    assert reason is not None
    assert "strict naming contract" in reason


def test_write_admitted_entries_inserts_alphabetically_and_preserves_json_style(
    tmp_path: Path,
) -> None:
    registry = _registry_file(tmp_path, [_EXISTING_ENTRY])
    original_bytes = registry.read_bytes()
    # aspose-3d-foss sorts before aspose-imaging-foss, so the new entry belongs after the
    # existing one - proving insertion is a real sort, not a naive append.
    repo = _observation(
        "aspose-imaging-foss",
        "Aspose.Imaging-FOSS-for-.NET",
        repo_id=202,
        node_id="R_202",
    )
    write_admitted_entries(registry, [repo])

    data = json.loads(registry.read_text(encoding="utf-8"))
    names = [e["repository"] for e in data["entries"]]
    assert names == sorted(names, key=str.casefold)
    assert names == [
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET",
    ]
    new_entry = data["entries"][1]
    assert new_entry == {
        "repository": "aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET",
        "family": "imaging",
        "platform": "net",
        "ecosystem": "net",
        "mode": "disabled",
        "policy_profile": "aspose-imaging-foss-net",
        "active": True,
        "provider_identity": {
            "provider": "github",
            "repository_id": 202,
            "node_id": "R_202",
        },
    }
    # Re-serialization stays in the file's own existing byte style: 2-space indent, no trailing
    # whitespace, exactly one trailing newline - matches data/registry.json's own real formatting
    # (checked 2026-09-24 to round-trip byte-identically before this module ever wrote to it).
    raw = registry.read_bytes()
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert (
        b'      "repository": "aspose-imaging-foss/Aspose.Imaging-FOSS-for-.NET",\n'
        in raw
    )
    assert raw != original_bytes


def test_run_auto_admission_admits_passing_repos_and_leaves_failing_ones_unregistered_with_reason(
    tmp_path: Path,
) -> None:
    registry = _registry_file(tmp_path, [_EXISTING_ENTRY])
    passing = _observation(
        "aspose-imaging-foss",
        "Aspose.Imaging-FOSS-for-.NET",
        repo_id=202,
        node_id="R_202",
    )
    failing_fork = _observation(
        "aspose-cad-foss",
        "Aspose.CAD-FOSS-for-Python",
        repo_id=303,
        node_id="R_303",
        fork=True,
    )
    discovery = DiscoveryReport(
        scanned_at="2026-09-24T00:00:00+00:00",
        probed_slugs=tuple(sorted(KNOWN_FAMILY_SLUGS)),
        search_discovered_orgs=(),
        org_results=(),
        already_registered=(),
        new_candidates=(passing, failing_fork),
        unmatched_repos=(),
    )

    def fake_build_probe(repo: RepoObservation, token: str | None) -> BuildProbeResult:
        return BuildProbeResult(
            ok=True, detail="fake: build succeeded", build_command="fake"
        )

    report, outcomes = run_auto_admission(
        registry_path=registry,
        token=None,
        build_probe=fake_build_probe,
        discovery=discovery,
    )
    assert report is discovery
    by_repo = {o.repo.full_name: o for o in outcomes}
    assert by_repo[passing.full_name].admitted is True
    assert by_repo[passing.full_name].reason == "admitted"
    assert by_repo[failing_fork.full_name].admitted is False
    assert by_repo[failing_fork.full_name].reason == "repository is a fork"

    data = json.loads(registry.read_text(encoding="utf-8"))
    names = {e["repository"] for e in data["entries"]}
    assert passing.full_name in names
    assert failing_fork.full_name not in names
    assert (
        len(data["entries"]) == 2
    )  # the pre-existing entry plus exactly the one admission


def test_run_auto_admission_never_writes_the_registry_when_nothing_passes(
    tmp_path: Path,
) -> None:
    registry = _registry_file(tmp_path, [_EXISTING_ENTRY])
    original = registry.read_bytes()
    failing = _observation(
        "aspose-cad-foss",
        "Aspose.CAD-FOSS-for-Python",
        repo_id=303,
        node_id="R_303",
        archived=True,
    )
    discovery = DiscoveryReport(
        scanned_at="2026-09-24T00:00:00+00:00",
        probed_slugs=tuple(sorted(KNOWN_FAMILY_SLUGS)),
        search_discovered_orgs=(),
        org_results=(),
        already_registered=(),
        new_candidates=(failing,),
        unmatched_repos=(),
    )

    def unreachable_build_probe(
        repo: RepoObservation, token: str | None
    ) -> BuildProbeResult:
        raise AssertionError(
            "the build probe must never run once criteria (a)-(c) already failed"
        )

    _, outcomes = run_auto_admission(
        registry_path=registry,
        token=None,
        build_probe=unreachable_build_probe,
        discovery=discovery,
    )
    assert all(not o.admitted for o in outcomes)
    assert registry.read_bytes() == original


def test_run_auto_admission_never_admits_a_second_entry_for_the_same_repository_id(
    tmp_path: Path,
) -> None:
    # The existing entry's own repository_id (101) reappears on a "new" candidate under a
    # different name - simulating a rename/transfer the discovery diff (name-keyed) would not by
    # itself catch. RegistryEntry.validate_stable_identities treats a duplicate repository_id as
    # a hard invariant; this must never be written, never an automatic decision.
    registry = _registry_file(tmp_path, [_EXISTING_ENTRY])
    renamed = _observation(
        "aspose-3d-foss",
        "Aspose.3D-FOSS-for-Rust",
        repo_id=101,
        node_id="R_101_renamed",
    )
    discovery = DiscoveryReport(
        scanned_at="2026-09-24T00:00:00+00:00",
        probed_slugs=tuple(sorted(KNOWN_FAMILY_SLUGS)),
        search_discovered_orgs=(),
        org_results=(),
        already_registered=(),
        new_candidates=(renamed,),
        unmatched_repos=(),
    )

    def fake_build_probe(repo: RepoObservation, token: str | None) -> BuildProbeResult:
        return BuildProbeResult(ok=True, detail="fake: build succeeded")

    _, outcomes = run_auto_admission(
        registry_path=registry,
        token=None,
        build_probe=fake_build_probe,
        discovery=discovery,
    )
    assert len(outcomes) == 1
    assert outcomes[0].admitted is False
    assert "already claimed" in outcomes[0].reason
    data = json.loads(registry.read_text(encoding="utf-8"))
    assert len(data["entries"]) == 1


def test_default_build_probe_fails_closed_without_network_for_an_unclassified_platform() -> (
    None
):
    repo = _observation("aspose-imaging-foss", ".github")  # matches_convention is False
    assert repo.classification.platform is None
    result = default_build_probe(repo, None)
    assert result.ok is False
    assert "no classified platform" in result.detail


def test_default_build_probe_fails_closed_without_network_for_an_unknown_ecosystem_platform() -> (
    None
):
    # "javascript" classifies fine (per _PLATFORM_NORMALIZATION) but has no
    # extractors/platforms/javascript.py plugin module - plugin_for() must fail before this
    # function ever attempts a network clone.
    repo = _observation("aspose-imaging-foss", "Aspose.Imaging-FOSS-for-JavaScript")
    assert repo.classification.platform == "javascript"
    result = default_build_probe(repo, None)
    assert result.ok is False
    assert "no platform plugin registered" in result.detail


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
