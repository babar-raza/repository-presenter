"""Portfolio discovery scan: enumerate every `aspose-<family>-foss` GitHub organization and its
public repositories, diff against `data/registry.json`, and write a structured report.

READ-ONLY, REPORT-ONLY. This module and its CLI never write to `data/registry.json` or any other
production/governance file except the one investigation report it is told to produce. It answers
"what exists that the registry does not yet know about," never "what the registry should now
contain" - admitting a discovered repository into the registry is a separate, deliberate,
human-reviewed act (owner standing rule, 2026-09-17: no new candidate ever enters
`data/registry.json` without asking first, however real and well-formed it looks).

Owner/reviewer tooling (`tools/README.md`): never imported by `src/repository_presenter`, never
read by the loop's own acceptance predicates, never wired into the production CLI
(`repository-presenter ...`). Mirrors `tools/census/portfolio_census.py`'s shape - a one-shot,
read-only, planning-time data-gathering script, not ongoing supervision or a production pipeline
stage.

Every repository this module observes - already registered or newly discovered - is also
classified into a `family`/`platform` pair (`classify_repo_name`, `RepoObservation.classification`)
via the three-regex convention classifier (see that function's own docstring). A name that matches
none of the three patterns is reported with an explicit `matched=False` outcome, never silently
dropped or left blank - the same "always evidence-backed, never silent" discipline this module
already applies to org-level exclusions (see `docs/PRODUCTION_ROADMAP.md` WS4, "Confirmed gap,
2026-09-17", and `docs/investigations/10-portfolio-discovery.md`).

Eligibility scope (owner's explicit, standing rule, enforced here): a candidate is only real when
it lives in a GitHub organization literally named `aspose-<family>-foss`. No other org naming
pattern, and no independently-hosted or external repository, counts - this module never looks
anywhere else.

## How the candidate organization list is assembled

GitHub has no direct "list every org matching a name pattern" API, so this module unions two
legs:

1. **Search leg** (`search_candidate_orgs`) - `GET /search/repositories?q=FOSS-for-+in:name`,
   every hit's owner login filtered to the `aspose-<slug>-foss` pattern. Finds any org that has
   at least one matching-shaped repository, including one neither this file's maintained list nor
   the owner's own manual check anticipated.
2. **Probe leg** (`probe_org` over `KNOWN_FAMILY_SLUGS`) - a direct `GET /orgs/aspose-<slug>-foss`
   existence check for a maintained, documented, extensible list of plausible Aspose product-
   family slugs. This is the load-bearing leg for any family this project already has reason to
   expect, including a reserved-but-currently-empty org the search leg can never find (an empty
   org has no repository for the search index to match).

**Known limitation, stated plainly, not papered over**: the search leg ranks results by
relevance and does not guarantee full recall. GitHub's search index can miss, or rank far enough
down to fall outside the pages this module fetches, an org with exactly one matching repository -
especially one created very recently. A purely search-based approach can therefore under-report.
This is exactly why the probe leg exists and carries the real weight; the search leg's only job
is to surface a family neither `KNOWN_FAMILY_SLUGS` nor a human anticipated. Whoever reviews a
report this module produces should fold any such newly-confirmed slug back into
`KNOWN_FAMILY_SLUGS` below so future runs probe it directly rather than depending on search luck.

## Provenance of `KNOWN_FAMILY_SLUGS`

- The 13 families already in `data/registry.json`'s 34 entries (as of 2026-09-17).
- 13 further families this project has *evidence* exist as `aspose-<slug>-foss` orgs:
  `docs/investigations/04-portfolio-discovery.md` §3.5 records that `Aspose/aspose.org`'s own
  `update_product_registry.py` scans exactly these plus the 13 above (26 organizations total),
  read there via that private repository's read-only Contents API - never pulled, cloned, or
  imported into this project. The owner independently spot-checked most of these by hand this
  session (`gh api orgs/aspose-<slug>-foss`) before commissioning this module.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = REPO_ROOT / "data" / "registry.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "investigations" / "10-portfolio-discovery.md"

API_ROOT = "https://api.github.com"
USER_AGENT = "repository-presenter-portfolio-discovery/1 (owner review, read-only)"
SEARCH_RESULT_CAP = 1000  # GitHub search API's own hard cap regardless of total_count

# The naming convention registered entries follow: "Aspose.<Family>-FOSS-for-<Ecosystem>" (dot)
# or "Aspose-<Family>-FOSS-for-<Ecosystem>" (hyphen) - both forms are live in data/registry.json
# today (aspose-pdf-foss/Aspose-PDF-FOSS-for-Go and .../Aspose-PDF-FOSS-for-Python use the hyphen
# form; this was discovered by this module's own first run misclassifying both as noise, fixed
# 2026-09-17 before landing). Matched case-insensitively (docs/investigations/
# 04-portfolio-discovery.md records a real upstream miss from a case-sensitive version of this
# same check: "Aspose.Imaging-Foss-for-.NET", mixed-case "Foss", silently unclassified until the
# check was made case-insensitive). This intentionally also matches a same-shaped repository that
# turns out, on human review, to be a non-SDK companion rather than a real product port (e.g.
# "Aspose-PDF-FOSS-for-Go-MCP", an MCP server - see docs/investigations/04-portfolio-discovery.md
# §2.5, which records Aspose/aspose.org's own registry_exclusions.json entry for exactly this
# repository) - this module reports it as an unregistered, convention-shaped repository for a
# human to adjudicate, same as every other new candidate; it never guesses "SDK vs. companion"
# from the name alone.
NAME_PATTERN = re.compile(r"^Aspose[.-][A-Za-z0-9]+-FOSS-for-", re.IGNORECASE)
ORG_PATTERN = re.compile(r"^aspose-([a-z0-9]+)-foss$", re.IGNORECASE)

KNOWN_FAMILY_SLUGS: frozenset[str] = frozenset(
    {
        # Already in data/registry.json (13 families, 34 entries, 2026-09-17):
        "3d",
        "barcode",
        "cells",
        "email",
        "font",
        "html",
        "note",
        "page",
        "pdf",
        "psd",
        "slides",
        "tex",
        "words",
        # Confirmed to exist as GitHub orgs but not yet in the registry (investigation 04 +
        # this session's own probes, 2026-09-17):
        "cad",
        "diagram",
        "drawing",
        "finance",
        "gis",
        "imaging",
        "medical",
        "ocr",
        "omr",
        "pub",
        "svg",
        "tasks",
        "zip",
    }
)


class OrgScanError(Exception):
    """A paginated repository listing for one org failed partway through.

    Raised instead of silently returning whatever pages already succeeded - Gate C0
    (`plans/idea.md`) requires a failed scan to never be reported as an empty success, so a
    caller must be able to tell "this org has zero repos" apart from "this org's scan broke."
    """

    def __init__(self, org: str, page: int, status_code: int, body: Any) -> None:
        self.org = org
        self.page = page
        self.status_code = status_code
        self.body = body
        super().__init__(f"{org}: page {page} returned HTTP {status_code}: {body!r}")


FetchFn = Callable[[str, "str | None"], "tuple[int, Any]"]


def default_fetch(url: str, token: str | None) -> tuple[int, Any]:
    """GET ``url`` from the GitHub REST API. Returns ``(status_code, parsed_json_or_none)``.

    Never raises for an HTTP-level failure (404, 403, 5xx): every caller decides what a given
    status means (200 populated/empty, 404 does-not-exist, 403 rate-limited-or-denied, -1
    unreachable) rather than this function collapsing the distinction Gate C0 cares about. Tests
    never call this - they inject a fake ``FetchFn`` fixture instead (see
    ``test_portfolio_discovery.py``), so no test in this suite makes a live network call.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            body = response.read()
            return response.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = None
        return exc.code, parsed
    except OSError as exc:
        return -1, str(exc)


def matches_product_convention(name: str) -> bool:
    """Whether ``name`` follows the ``Aspose.<Family>-FOSS-for-<Ecosystem>`` convention."""
    return bool(NAME_PATTERN.match(name))


# Family/platform classifier (docs/PRODUCTION_ROADMAP.md WS4, "Confirmed gap, 2026-09-17": this
# module enumerated repositories but never classified family/platform). A clean-room
# reimplementation of `Aspose/aspose.org`'s own `scripts/pipeline/commands/ops/
# update_product_registry.py`'s `_classify_repo` - studied read-only via that private sibling
# repository's Contents API (`gh api repos/Aspose/aspose.org/contents/...`), never cloned or
# pulled from directly, per this project's existing pull-discipline precedent (study, then write
# an independent implementation here). Same three-regex shape, in the same precedence order:
#
# 1. Canonical: ``Aspose.<Family>-FOSS-for-<Platform>`` (dot form).
# 2. Lowercase variant: ``aspose-<family>-foss-for-<platform>``.
# 3. Legacy: ``aspose-<family>-<platform>`` - the loosest shape, tried last so it never shadows a
#    canonical or lowercase match.
#
# All three are matched case-insensitively from the start. That upstream module's own code
# comment records a real historical bug worth not repeating: a case-sensitive version of pattern 1
# silently failed to classify the real repository "Aspose.Imaging-Foss-for-.NET" (mixed-case
# "Foss") with no error - fixed there, and never introduced here, by using ``re.IGNORECASE`` from
# the first commit rather than as a later patch.
_CLASSIFY_PATTERN_CANONICAL = re.compile(
    r"^Aspose\.([A-Za-z0-9]+)-FOSS-for-([A-Za-z0-9.]+)$", re.IGNORECASE
)
_CLASSIFY_PATTERN_LOWERCASE = re.compile(r"^aspose-([a-z0-9]+)-foss-for-([a-z0-9]+)$")
_CLASSIFY_PATTERN_LEGACY = re.compile(r"^aspose-([a-z0-9]+)-([a-z0-9]+)$")

# Platform-token normalization: matches this project's own data/registry.json convention (every
# entry there already stores e.g. "net", not ".NET" - see data/registry.json's "platform" values),
# so a freshly classified repository's platform string lines up with an existing registry entry's
# for the same family/platform pair rather than needing a second normalization pass later.
_PLATFORM_NORMALIZATION: dict[str, str] = {
    "python": "python",
    "java": "java",
    ".net": "net",
    "net": "net",
    "cpp": "cpp",
    "c++": "cpp",
    "typescript": "typescript",
    "javascript": "javascript",
    "nodejs": "nodejs",
    "go": "go",
    "rust": "rust",
}


@dataclass(frozen=True)
class RepoClassification:
    """The outcome of matching one repository name against the family/platform classifier.

    ``matched`` is its own explicit field - never inferred from ``family``/``platform`` being
    ``None`` - so a caller can tell "classified" apart from "unmatched" without relying on a
    field-presence convention. This mirrors this module's existing discipline of never silently
    excluding a repository (see ``unmatched_repos`` / the "Unmatched / noise repositories" report
    section): a name that fails all three classifier patterns is reported as explicitly
    unmatched, not dropped.
    """

    family: str | None
    platform: str | None
    matched: bool


def classify_repo_name(name: str) -> RepoClassification:
    """Classify a bare repository ``name`` (not ``org/name``) into ``(family, platform)``.

    Tries the three patterns documented on this module above, in precedence order, all
    case-insensitively. Returns ``RepoClassification(family=None, platform=None, matched=False)``
    - an explicit, typed "unmatched" outcome, never a bare ``None`` - when no pattern matches.
    """
    match = _CLASSIFY_PATTERN_CANONICAL.match(name)
    if match:
        family = match.group(1).lower()
        platform_raw = match.group(2).lower()
        return RepoClassification(
            family=family,
            platform=_PLATFORM_NORMALIZATION.get(platform_raw, platform_raw),
            matched=True,
        )

    match = _CLASSIFY_PATTERN_LOWERCASE.match(name.lower())
    if match:
        family = match.group(1)
        platform_raw = match.group(2)
        return RepoClassification(
            family=family,
            platform=_PLATFORM_NORMALIZATION.get(platform_raw, platform_raw),
            matched=True,
        )

    match = _CLASSIFY_PATTERN_LEGACY.match(name.lower())
    if match:
        family = match.group(1)
        platform_raw = match.group(2)
        return RepoClassification(
            family=family,
            platform=_PLATFORM_NORMALIZATION.get(platform_raw, platform_raw),
            matched=True,
        )

    return RepoClassification(family=None, platform=None, matched=False)


@dataclass(frozen=True)
class RepoObservation:
    """One repository as GitHub actually reported it, by stable provider identity."""

    org: str
    name: str
    full_name: str
    repository_id: int
    node_id: str
    private: bool
    archived: bool
    fork: bool
    pushed_at: str | None
    matches_convention: bool
    classification: RepoClassification

    @staticmethod
    def from_api(org: str, item: dict[str, Any]) -> RepoObservation:
        name = str(item.get("name", ""))
        return RepoObservation(
            org=org,
            name=name,
            full_name=str(item.get("full_name", f"{org}/{name}")),
            repository_id=int(item.get("id", 0)),
            node_id=str(item.get("node_id", "")),
            private=bool(item.get("private", False)),
            archived=bool(item.get("archived", False)),
            fork=bool(item.get("fork", False)),
            pushed_at=item.get("pushed_at"),
            matches_convention=matches_product_convention(name),
            classification=classify_repo_name(name),
        )


@dataclass(frozen=True)
class OrgResult:
    """One organization's scan outcome - a typed outcome, never a bare repo list.

    ``status`` is one of ``"populated"`` (>=1 public repo observed), ``"empty"`` (org exists,
    zero public repos), ``"not_found"`` (no such org), or ``"inaccessible"`` (the org lookup or
    its repo pagination failed - rate limit, auth denial, network error; never conflated with
    ``"empty"``).
    """

    org: str
    status: str
    public_repos_reported: int | None
    repos: tuple[RepoObservation, ...]
    detail: str | None = None


def list_org_repos(
    org: str, *, token: str | None, fetch: FetchFn = default_fetch, per_page: int = 100
) -> list[RepoObservation]:
    """Paginate ``GET /orgs/{org}/repos?type=public`` until an exhausted page.

    Raises ``OrgScanError`` on any non-200 page rather than returning a truncated list.
    """
    repos: list[RepoObservation] = []
    page = 1
    while True:
        url = f"{API_ROOT}/orgs/{org}/repos?type=public&per_page={per_page}&page={page}"
        status_code, body = fetch(url, token)
        if status_code != 200 or not isinstance(body, list):
            raise OrgScanError(org, page, status_code, body)
        if not body:
            break
        repos.extend(RepoObservation.from_api(org, item) for item in body)
        if len(body) < per_page:
            break
        page += 1
    return repos


def probe_org(org: str, *, token: str | None, fetch: FetchFn = default_fetch) -> OrgResult:
    """Check whether ``org`` exists and, if so, enumerate its public repositories."""
    meta_status, meta_body = fetch(f"{API_ROOT}/orgs/{org}", token)
    if meta_status == 404:
        return OrgResult(org=org, status="not_found", public_repos_reported=None, repos=())
    if meta_status != 200 or not isinstance(meta_body, dict):
        return OrgResult(
            org=org,
            status="inaccessible",
            public_repos_reported=None,
            repos=(),
            detail=f"org lookup returned HTTP {meta_status}",
        )
    reported = meta_body.get("public_repos")
    try:
        repos = list_org_repos(org, token=token, fetch=fetch)
    except OrgScanError as exc:
        return OrgResult(
            org=org,
            status="inaccessible",
            public_repos_reported=reported,
            repos=(),
            detail=str(exc),
        )
    status = "populated" if repos else "empty"
    return OrgResult(org=org, status=status, public_repos_reported=reported, repos=tuple(repos))


def search_candidate_orgs(*, token: str | None, fetch: FetchFn = default_fetch) -> set[str]:
    """Search leg: return every ``aspose-<slug>-foss`` org login with a name-matching repo.

    See this module's docstring for the documented recall limitation of this leg.
    """
    orgs: set[str] = set()
    page = 1
    per_page = 100
    while True:
        url = (
            f"{API_ROOT}/search/repositories?q=FOSS-for-+in:name"
            f"&per_page={per_page}&page={page}"
        )
        status_code, body = fetch(url, token)
        if status_code != 200 or not isinstance(body, dict):
            break  # a failed search is non-fatal: the probe leg still covers KNOWN_FAMILY_SLUGS
        items = body.get("items", [])
        if not isinstance(items, list):
            break
        for item in items:
            login = str(((item.get("owner") or {}).get("login")) or "")
            if ORG_PATTERN.match(login):
                orgs.add(login.lower())
        if len(items) < per_page or page * per_page >= SEARCH_RESULT_CAP:
            break
        page += 1
    return orgs


def load_registered_repositories(registry_path: Path) -> set[str]:
    """Return every ``entries[].repository`` value from ``data/registry.json``, lowercased.

    Read-only: this function only ever reads the registry, never writes it.
    """
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    return {str(entry["repository"]).lower() for entry in data["entries"]}


@dataclass(frozen=True)
class DiscoveryReport:
    """The full, categorized outcome of one discovery pass."""

    scanned_at: str
    probed_slugs: tuple[str, ...]
    search_discovered_orgs: tuple[str, ...]
    org_results: tuple[OrgResult, ...]
    already_registered: tuple[RepoObservation, ...]
    new_candidates: tuple[RepoObservation, ...]
    unmatched_repos: tuple[RepoObservation, ...]

    @property
    def empty_orgs(self) -> tuple[OrgResult, ...]:
        return tuple(r for r in self.org_results if r.status == "empty")

    @property
    def not_found_slugs(self) -> tuple[OrgResult, ...]:
        return tuple(r for r in self.org_results if r.status == "not_found")

    @property
    def inaccessible_orgs(self) -> tuple[OrgResult, ...]:
        return tuple(r for r in self.org_results if r.status == "inaccessible")


def run_discovery(
    *,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    token: str | None,
    fetch: FetchFn = default_fetch,
    extra_slugs: Iterable[str] = (),
) -> DiscoveryReport:
    """Run one full discovery pass: assemble candidate orgs, scan each, diff against the registry.

    Read-only end to end. Nothing this function calls ever writes to ``registry_path`` or any
    other file - it only returns a typed, in-memory result for a caller to render or inspect.
    """
    registered = load_registered_repositories(registry_path)
    search_orgs = search_candidate_orgs(token=token, fetch=fetch)
    probe_slugs = tuple(sorted(KNOWN_FAMILY_SLUGS | set(extra_slugs)))
    probe_orgs = {f"aspose-{slug}-foss" for slug in probe_slugs}
    all_orgs = sorted(probe_orgs | search_orgs)
    org_results = [probe_org(org, token=token, fetch=fetch) for org in all_orgs]

    already_registered: list[RepoObservation] = []
    new_candidates: list[RepoObservation] = []
    unmatched: list[RepoObservation] = []
    for result in org_results:
        for repo in result.repos:
            if not repo.matches_convention:
                unmatched.append(repo)
            elif repo.full_name.lower() in registered:
                already_registered.append(repo)
            else:
                new_candidates.append(repo)

    return DiscoveryReport(
        scanned_at=datetime.now(UTC).isoformat(timespec="seconds"),
        probed_slugs=probe_slugs,
        search_discovered_orgs=tuple(sorted(search_orgs)),
        org_results=tuple(org_results),
        already_registered=tuple(already_registered),
        new_candidates=tuple(new_candidates),
        unmatched_repos=tuple(unmatched),
    )


_NOISE_HINT_PATTERN = re.compile(r"-mcp$", re.IGNORECASE)


def _noise_hint(name: str) -> str | None:
    """A documented, non-authoritative annotation hint - never used to exclude or reclassify.

    Sourced from a real precedent: docs/investigations/04-portfolio-discovery.md §2.5 records
    Aspose/aspose.org's own registry_exclusions.json entry excluding "Aspose-PDF-FOSS-for-Go-MCP"
    specifically because an MCP server has no class/method API surface to extract - a judgment
    about the repository's content, not something the name shape alone can decide. This flags the
    same shape (an "-MCP" suffix) purely so a human reviewer sees the precedent without this
    module silently excluding or reclassifying anything on its own.
    """
    if _NOISE_HINT_PATTERN.search(name):
        return "name ends in -MCP: matches a known non-SDK companion pattern, see 04 §2.5"
    return None


def _repo_row(repo: RepoObservation) -> str:
    flags = [f for f, on in (("archived", repo.archived), ("fork", repo.fork)) if on]
    hint = _noise_hint(repo.name)
    if hint:
        flags.append(hint)
    flags_text = "; ".join(flags) or "-"
    if repo.classification.matched:
        family_text = f"`{repo.classification.family}`"
        platform_text = f"`{repo.classification.platform}`"
    else:
        # Explicit, never a blank cell - an unmatched classification is reported the same way
        # this module already reports every other exclusion: named, not silently omitted.
        family_text = "unmatched"
        platform_text = "unmatched"
    return (
        f"| `{repo.full_name}` | {family_text} | {platform_text} | {repo.repository_id} | "
        f"`{repo.node_id}` | {repo.pushed_at or '-'} | {flags_text} |"
    )


def render_report(report: DiscoveryReport, *, investigation_number: str = "10") -> str:
    """Render ``report`` as the docs/investigations/ markdown document this module produces.

    Deterministic given the same ``DiscoveryReport`` - rerunning the scan and rendering again is
    how a future reviewer refreshes this document, not hand-editing it.
    """
    lines: list[str] = []
    add = lines.append
    add(f"# Investigation {investigation_number} — Portfolio Discovery Scan")
    add("")
    add(
        f"Scanned {report.scanned_at}, generated by `tools/discovery/portfolio_discovery.py` "
        "(owner/reviewer tooling, read-only - see that module's own docstring for the "
        "never-touches-`data/registry.json` guarantee). Commissioned by "
        "`docs/PRODUCTION_ROADMAP.md` workstream 4 / `plans/idea.md`'s Common Gate C0, "
        "following up `docs/investigations/04-portfolio-discovery.md`'s design analysis with "
        "the first actual enumeration pass. **Eligibility scope (owner's standing rule, "
        "enforced by this scan): a candidate is only real when it lives in a GitHub "
        "organization literally named `aspose-{family}-foss`.** No other org naming pattern, "
        "and no independently-hosted or externally-hosted repository, counts, however "
        "legitimate-looking."
    )
    add("")
    add("## How the candidate organization list was assembled")
    add("")
    add(
        "GitHub has no direct \"list orgs by name pattern\" API, so this scan unions two legs "
        "(full method and its documented limitation in `portfolio_discovery.py`'s own module "
        "docstring):"
    )
    add("")
    add(
        f"1. **Search leg** - `GET /search/repositories?q=FOSS-for-+in:name`. Found "
        f"{len(report.search_discovered_orgs)} matching org login(s): "
        + (", ".join(f"`{o}`" for o in report.search_discovered_orgs) or "none") + "."
    )
    add(
        f"2. **Probe leg** - `GET /orgs/aspose-<slug>-foss` for each of "
        f"{len(report.probed_slugs)} maintained candidate family slugs "
        f"(`KNOWN_FAMILY_SLUGS`): " + ", ".join(f"`{s}`" for s in report.probed_slugs) + "."
    )
    add("")
    add(
        "**Known limitation, stated plainly**: the search leg ranks by relevance and does not "
        "guarantee full recall - an org with exactly one matching, low-relevance, or very "
        "recently created repository can be missing from its results even though it exists. "
        "The probe leg is the load-bearing half for any family this project already has "
        "evidence for; the search leg's only job is to surface a family neither list "
        "anticipated. Neither leg substitutes for the other, and this scan does not claim "
        "either one alone would be complete."
    )
    add("")
    add("## Results")
    add("")
    add(f"### Already registered ({len(report.already_registered)} matches)")
    add("")
    add(
        "Repositories this scan observed that already have a `data/registry.json` entry "
        "(matched by `owner/name`, case-insensitive)."
    )
    add("")
    if report.already_registered:
        add("| Repository | Family | Platform | `repository_id` | `node_id` | Last push | Flags |")
        add("|---|---|---|---|---|---|---|")
        for repo in sorted(report.already_registered, key=lambda r: r.full_name.lower()):
            add(_repo_row(repo))
    else:
        add("None.")
    add("")
    add(
        f"### Newly discovered, populated ({len(report.new_candidates)} candidates - "
        "not yet in the registry)"
    )
    add("")
    add(
        "Real, populated repositories matching the `Aspose.<Family>-FOSS-for-<Ecosystem>` "
        "naming convention, in a confirmed `aspose-<family>-foss` org, with no matching "
        "`data/registry.json` entry. **Not added to the registry by this report** - the owner "
        "reviews and decides admission (`mode: disabled` per `plans/idea.md`'s Gate C0 shape) "
        "separately."
    )
    add("")
    if report.new_candidates:
        add("| Repository | Family | Platform | `repository_id` | `node_id` | Last push | Flags |")
        add("|---|---|---|---|---|---|---|")
        for repo in sorted(report.new_candidates, key=lambda r: r.full_name.lower()):
            add(_repo_row(repo))
    else:
        add("None.")
    add("")
    add(f"### Unmatched / noise repositories ({len(report.unmatched_repos)})")
    add("")
    add(
        "Repositories that exist in a confirmed `aspose-<family>-foss` org but do not match the "
        "`Aspose.<Family>-FOSS-for-<Ecosystem>` naming convention (e.g. an org's generic "
        "`.github` profile repo, a non-SDK companion repo). Recorded for human adjudication, "
        "never auto-excluded - `plans/idea.md`'s Gate C0 requires every exclusion to be "
        "explicit and evidence-backed, not silent."
    )
    add("")
    if report.unmatched_repos:
        add("| Repository | Family | Platform | `repository_id` | `node_id` | Last push | Flags |")
        add("|---|---|---|---|---|---|---|")
        for repo in sorted(report.unmatched_repos, key=lambda r: r.full_name.lower()):
            add(_repo_row(repo))
    else:
        add("None.")
    add("")
    add(f"### Reserved, empty organizations ({len(report.empty_orgs)})")
    add("")
    add("Organization exists, zero public repositories observed - not yet actionable.")
    add("")
    if report.empty_orgs:
        for result in sorted(report.empty_orgs, key=lambda r: r.org):
            add(f"- `{result.org}`")
    else:
        add("None.")
    add("")
    not_found = report.not_found_slugs
    add(f"### Probed slugs with no matching organization ({len(not_found)})")
    add("")
    if not_found:
        for result in sorted(not_found, key=lambda r: r.org):
            add(f"- `{result.org}`")
    else:
        add("None - every probed slug resolved to a real organization.")
    add("")
    inaccessible = report.inaccessible_orgs
    add(f"### Inaccessible organizations - scan failed, not treated as empty ({len(inaccessible)})")
    add("")
    if inaccessible:
        for result in sorted(inaccessible, key=lambda r: r.org):
            add(f"- `{result.org}` - {result.detail}")
    else:
        add("None.")
    add("")
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="portfolio_discovery.py",
        description=(
            "DISCOVER AND REPORT ONLY. Enumerates aspose-<family>-foss GitHub organizations and "
            "their public repositories, diffs against data/registry.json, and writes a markdown "
            "report. This tool NEVER writes to data/registry.json or any file other than the "
            "report it is told to produce - admitting a discovered repository into the registry "
            "is a separate, human-reviewed decision, always."
        ),
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help="path to data/registry.json (read-only)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="path to write the markdown report to",
    )
    parser.add_argument(
        "--investigation-number",
        default="10",
        help="the docs/investigations/ number used in the report's own title",
    )
    parser.add_argument(
        "--extra-slug",
        action="append",
        default=[],
        metavar="SLUG",
        help="an additional family slug to probe beyond KNOWN_FAMILY_SLUGS (repeatable)",
    )
    parser.add_argument(
        "--token-env",
        default="GH_TOKEN",
        help="environment variable holding the GitHub token to authenticate with",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    token = os.environ.get(args.token_env) or None
    report = run_discovery(
        registry_path=args.registry,
        token=token,
        extra_slugs=args.extra_slug,
    )
    text = render_report(report, investigation_number=args.investigation_number)
    args.output.write_text(text, encoding="utf-8", newline="\n")
    print(
        f"wrote {args.output} - {len(report.already_registered)} already registered, "
        f"{len(report.new_candidates)} new candidate(s), {len(report.unmatched_repos)} "
        f"unmatched, {len(report.empty_orgs)} empty org(s), "
        f"{len(report.inaccessible_orgs)} inaccessible"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
