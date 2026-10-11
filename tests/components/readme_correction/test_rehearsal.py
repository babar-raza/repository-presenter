"""A correction, proposed end to end against the workflow rehearsal's fake GitHub and a local bare
remote (TC-REF-11 tooling): no network, no real GitHub write.

The upstream is a synthetic repository served from a bare git remote; ``correct-readme``'s own
``produce_correction`` clones its head and writes the bundle; the typed correction gate loads it;
the real ``propose_candidate`` effect, its gates and the real ``core/github`` client run unchanged
against the stateful fake REST. What is shown: the presenter branch carries exactly the commit
whose diff is ``README.patch``; one pull request with the correction's own title and an evidence
line per edit; a second run creates nothing; a new commit upstream refuses the proposal and writes
nothing; a settled pull request is not recreated.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.propose.effect import (
    AUTHORIZATION_VARIABLE,
    presenter_branch_name,
    propose_candidate,
)
from repository_presenter.components.readme.composition.renderer import render_patch
from repository_presenter.components.readme_correction import run as correction_run
from repository_presenter.components.readme_correction.bundle import PATCH_NAME
from repository_presenter.components.readme_correction.gate import load_proposable_correction
from repository_presenter.components.readme_correction.pull_request import (
    compose_correction_pull_request,
)
from repository_presenter.core.authorization.proposal import authorize_proposal
from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError
from repository_presenter.core.facts import Evidence, Fact, FactsDocument, write_facts
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from repository_presenter.core.registry.write_gate import WritePermit
from support import REPO_ROOT

TOOL_DIR = REPO_ROOT / "tools" / "workflow_rehearsal"
sys.path.insert(0, str(TOOL_DIR))

import cycle  # noqa: E402
import scenarios  # noqa: E402

REPOSITORY = "rehearsal-org/correctable"
README = """# Synthetic Pkg

Synthetic Pkg does one thing.

## Installation

```bash
pip install synthetic-pkg==1.0.0
```

## Scope and Limitations

Only the happy path works.

## License

MIT.
"""
FILES = {
    "README.md": README,
    "pyproject.toml": '[project]\nname = "synthetic-pkg"\nversion = "2.0.0"\n',
    "LICENSE": "MIT License\n",
    "CHANGELOG.md": "# Changes\n",
}


def fact(fact_id: str, value: str, evidence: Any, attributes: dict[str, str] | None = None) -> Fact:
    return Fact(
        id=fact_id,
        kind=fact_id.split(":", 1)[0],  # type: ignore[arg-type]
        value=value,
        evidence=tuple(Evidence(path, detail) for path, detail in evidence),
        attributes=attributes,
    )


def facts_for(revision: str) -> FactsDocument:
    return FactsDocument(
        REPOSITORY,
        revision,
        (
            fact("identity:repository", REPOSITORY, (("data/registry.json", None),)),
            fact("package:name", "synthetic-pkg", (("pyproject.toml", None),)),
            fact("package:version", "2.0.0", (("pyproject.toml", None),)),
            fact("package:published_version", "2.0.0", (("https://pypi.org/pypi/x/json", None),)),
            fact(
                "install_command:pip",
                "pip install synthetic-pkg",
                (("pyproject.toml", None), ("https://pypi.org/x", "package registry: found")),
                {"install_kind": "registry"},
            ),
            fact("license:spdx", "MIT", (("LICENSE", "license text states this license"),)),
            fact("license:file", "LICENSE", (("LICENSE", None),)),
            fact("dependency:none", "none", (("pyproject.toml", "declares none"),)),
        ),
    )


class Rehearsal:
    """One synthetic upstream on a local bare remote, its correction bundle, and a fake GitHub."""

    def __init__(self, tmp: Path, monkeypatch: pytest.MonkeyPatch, readme: str = README) -> None:
        self.readme = readme
        self.world = tmp / "world"
        self.world.mkdir()
        (self.revision,) = scenarios.build_repository(
            self.world, "correctable", [("initial", {**FILES, "README.md": readme})]
        )
        self.bare = self.world / "upstreams" / scenarios.OWNER / "correctable.git"
        self.entry = cycle._entry(REPOSITORY, "full")
        monkeypatch.setattr(
            correction_run,
            "pinned_read_only_clone",
            lambda url, destination, **kwargs: pinned_read_only_clone(str(self.bare), destination),
        )
        facts = tmp / "facts.json"
        write_facts(facts_for(self.revision), facts)
        self.bundle = tmp / "bundle"
        self.outcome = correction_run.produce_correction(
            self.entry,
            clone_directory=tmp / "clone",
            out_directory=self.bundle,
            facts_path=facts,
        )
        self.rest = cycle._rest(REPOSITORY, readme=readme)

    def head(self) -> str:
        return scenarios._git(["rev-parse", "main"], self.bare)

    def advance_upstream(self) -> str:
        work = self.world / "advance"
        scenarios._git(["clone", "-q", str(self.bare), str(work)], self.world)
        revision = scenarios._commit(work, "upstream moves", {"NOTES.md": "later\n"})
        scenarios._git(["push", "-q", "origin", "HEAD:main"], work)
        return revision

    def propose(self, rest: Any = None) -> Any:
        rest = rest or self.rest
        candidate = load_proposable_correction(
            self.bundle, REPOSITORY, root=REPO_ROOT, entry=self.entry
        )
        content = compose_correction_pull_request(
            bundle=candidate.bundle,
            repository=REPOSITORY,
            candidate_hash=candidate.candidate_hash,
            source_revision=candidate.revision,
            policy_version="rehearsal",
        )
        now = datetime.now(UTC)
        stamp = "%Y-%m-%dT%H:%M:%SZ"
        return propose_candidate(
            repository=REPOSITORY,
            readme_text=candidate.readme_text,
            source_revision=candidate.revision,
            base_branch="main",
            token=cycle.FAKE_TOKEN,
            environment={AUTHORIZATION_VARIABLE: "1"},
            permit=WritePermit(effect="readme_proposal", entry=self.entry),
            load_authorization=lambda: authorize_proposal(
                repository=REPOSITORY,
                candidate_hash=candidate.candidate_hash,
                source_revision=candidate.revision,
                base_branch="main",
                branch=presenter_branch_name(),
                approver="rehearsal-owner",
                issued_at=(now - timedelta(minutes=1)).strftime(stamp),
                expires_at=(now + timedelta(hours=1)).strftime(stamp),
            ),
            recheck_source=self.head,
            pr_title=content.title,
            pr_body=content.body,
            **cycle.propose_seams(rest, REPOSITORY),
        )


@pytest.fixture
def rehearsal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reenabled: None) -> Rehearsal:
    return Rehearsal(tmp_path, monkeypatch)


@pytest.fixture
def default_rehearsal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Rehearsal:
    return Rehearsal(tmp_path, monkeypatch)


def test_the_correction_is_produced_from_the_bare_remote_and_loads_through_its_own_gate(
    rehearsal: Rehearsal,
) -> None:
    assert rehearsal.outcome.status == "corrected"
    assert rehearsal.outcome.revision == rehearsal.revision == rehearsal.head()
    assert rehearsal.outcome.summary == {
        "FALSE_CLAIM_FIX": 1,
        "MISSING_INFO": 1,
        "MISSING_SECTION": 2,
    }


def test_one_pull_request_whose_branch_commit_is_exactly_the_readme_patch(
    rehearsal: Rehearsal,
) -> None:
    result = rehearsal.propose()
    assert result.effected and result.pr_created and result.commit_written
    branch_readme = rehearsal.rest.file(REPOSITORY, presenter_branch_name(), "README.md")
    assert branch_readme is not None and "synthetic-pkg==2.0.0" in branch_readme
    assert rehearsal.rest.file(REPOSITORY, "main", "README.md") == README  # the base is untouched
    patch = (rehearsal.bundle / PATCH_NAME).read_text(encoding="utf-8")
    assert render_patch(README, branch_readme) == patch  # the commit's diff is README.patch
    (pull,) = rehearsal.rest.pulls(REPOSITORY)
    assert pull["title"] == "docs(readme): 4 verified corrections"
    body = pull["body"]
    assert "`1.0.0` -> `2.0.0`" in body
    assert "current release `2.0.0` on the package registry" in body
    assert "inserted `## Dependencies`" in body
    assert "[![PyPI](https://img.shields.io/pypi/v/synthetic-pkg.svg)]" in branch_readme
    assert "### How to decline" in body and "kind: correction" in body
    assert "Refreshes the README" not in body  # it does not claim to be a regeneration


def test_a_second_run_creates_and_writes_nothing(rehearsal: Rehearsal) -> None:
    first = rehearsal.propose()
    writes = len(rehearsal.rest.applied_writes())
    second = rehearsal.propose()
    assert second.effected and not second.pr_created and not second.commit_written
    assert len(rehearsal.rest.applied_writes()) == writes
    assert len(rehearsal.rest.pulls(REPOSITORY)) == 1 and second.pr_number == first.pr_number


def test_a_moved_source_is_refused_and_nothing_is_written(rehearsal: Rehearsal) -> None:
    fresh = cycle._rest(REPOSITORY, readme=README)
    moved = rehearsal.advance_upstream()
    assert moved != rehearsal.revision
    result = rehearsal.propose(fresh)
    assert not result.effected and result.reason_code == Refusal.SOURCE_MOVED
    assert fresh.applied_writes() == []
    assert fresh.pulls(REPOSITORY) == []
    assert fresh.branch(REPOSITORY, presenter_branch_name()) is None


def test_a_settled_pull_request_is_not_recreated(rehearsal: Rehearsal) -> None:
    first = rehearsal.propose()
    rehearsal.rest.close_pull(REPOSITORY, first.pr_number, merged=True)
    writes = len(rehearsal.rest.applied_writes())
    again = rehearsal.propose()
    assert not again.effected and "merged" in (str(again.reason_code) + again.reason).lower()
    assert len(rehearsal.rest.applied_writes()) == writes


def test_a_tampered_bundle_never_reaches_the_remote(rehearsal: Rehearsal) -> None:
    readme = rehearsal.bundle / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + "\nunreviewed\n", encoding="utf-8")
    with pytest.raises(WriteRefusedError):
        rehearsal.propose()
    assert rehearsal.rest.applied_writes() == []


DIAGRAM = """\
flowchart TD
  subgraph StartingPoints["Starting Points"]
    direction LR
    i1["An existing OBJ, STL, or 3MF file"]
  end
  PRODUCT["Synthetic Pkg"]
  subgraph Capabilities["Core Capabilities"]
    direction LR
    subgraph capl[" "]
      direction TB
      c1["Scene-graph construction and traversal"]
      c2["Mesh authoring and editing"]
      c3["Parameterized primitive geometry"]
    end
    subgraph capr[" "]
      direction TB
      c4["Lambert, Phong, and PBR material assignment"]
      c5["Polygon triangulation"]
      c6["Keyframe animation and skeletal pose data"]
    end
  end
  subgraph Outputs["Outputs"]
    direction TB
    o1["OBJ, STL, or 3MF file"]
  end
  StartingPoints --> PRODUCT --> Capabilities --> Outputs
"""
README_WITH_DIAGRAM = README.replace(
    "## Installation",
    "## At a Glance\n\n```mermaid\n" + DIAGRAM + "```\n\n## Installation",
    1,
)


@pytest.fixture
def diagram_rehearsal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Rehearsal:
    return Rehearsal(tmp_path, monkeypatch, README_WITH_DIAGRAM)


def test_a_diagram_redraw_is_proposed_as_one_pull_request_whose_commit_is_the_patch(
    diagram_rehearsal: Rehearsal,
) -> None:
    rehearsal = diagram_rehearsal
    assert rehearsal.outcome.status == "corrected"
    assert rehearsal.outcome.summary["DIAGRAM_FIX"] == 1
    result = rehearsal.propose()
    assert result.effected and result.pr_created and result.commit_written
    branch_readme = rehearsal.rest.file(REPOSITORY, presenter_branch_name(), "README.md")
    assert branch_readme is not None and "flowchart LR" in branch_readme
    assert "flowchart TD" not in branch_readme
    assert rehearsal.rest.file(REPOSITORY, "main", "README.md") == README_WITH_DIAGRAM
    patch = (rehearsal.bundle / PATCH_NAME).read_text(encoding="utf-8")
    assert render_patch(README_WITH_DIAGRAM, branch_readme) == patch
    (pull,) = rehearsal.rest.pulls(REPOSITORY)
    assert pull["title"] == "docs(readme): 4 verified corrections"
    assert "drawn left to right so the labels fit their boxes" in pull["body"]
    flat = branch_readme.replace("<br/>", " ")  # the drawing wraps long labels; the words stay
    for label in ("Starting Points", "Core Capabilities", "Outputs", "Polygon triangulation"):
        assert label in flat  # every word the maintainers wrote is still there


def test_a_diagram_redraw_is_idempotent_and_refused_when_the_source_moved(
    diagram_rehearsal: Rehearsal,
) -> None:
    rehearsal = diagram_rehearsal
    first = rehearsal.propose()
    writes = len(rehearsal.rest.applied_writes())
    again = rehearsal.propose()
    assert again.effected and not again.pr_created and again.pr_number == first.pr_number
    assert len(rehearsal.rest.applied_writes()) == writes
    fresh = cycle._rest(REPOSITORY, readme=README_WITH_DIAGRAM)
    rehearsal.advance_upstream()
    refused = rehearsal.propose(fresh)
    assert not refused.effected and refused.reason_code == Refusal.SOURCE_MOVED
    assert fresh.applied_writes() == []


def test_report_only_candidates_stay_in_the_bundle_and_out_of_the_pull_request(
    default_rehearsal: Rehearsal,
) -> None:
    rehearsal = default_rehearsal
    assert rehearsal.outcome.summary == {
        "FALSE_CLAIM_FIX": 1,
        "MISSING_INFO": 1,
        "MISSING_SECTION": 1,
    }
    document = json.loads((rehearsal.bundle / "corrections.json").read_text(encoding="utf-8"))
    held = {(e["detector"], e["report_only_reason"]) for e in document["report_only"]}
    assert ("missing_sections", "RE_ENABLE_CONDITION_UNMET") in held
    assert any("CHANGELOG.md" in e["candidate"] for e in document["report_only"])
    result = rehearsal.propose()
    assert result.effected and result.pr_created
    (pull,) = rehearsal.rest.pulls(REPOSITORY)
    assert "CHANGELOG.md" not in pull["body"]
    assert pull["title"] == (
        "docs(readme): show the current release (2.0.0) in the install snippets, "
        "add the Dependencies section and add the published-version badge"
    )
    branch_readme = rehearsal.rest.file(REPOSITORY, presenter_branch_name(), "README.md")
    assert branch_readme is not None and "CHANGELOG.md" not in branch_readme
