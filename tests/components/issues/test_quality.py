"""The deterministic quality gate for upstream issue text (TC-ISS-04, G6-W07).

Every check has a failing fixture and a passing one: the passing fixture is a good issue, and each
failing fixture changes exactly one thing about it, so a finding can only come from that change.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from repository_presenter.components.issues.draft import (
    draft_handoff,
    record_handoff_if_new,
)
from repository_presenter.components.issues.ledger import load_ledger
from repository_presenter.components.issues.model import (
    EvidenceEntry,
    Handoff,
    TriggeringCheck,
    load_handoff,
)
from repository_presenter.components.issues.quality import (
    CODES,
    MAX_TITLE_LENGTH,
    HandoffQualityError,
    issue_quality_findings,
    require_issue_quality,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from support import REPO_ROOT

REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-.NET"
REVISION = "52b0f00ebf28a0b4173921725ff170685ec2c502"
FINGERPRINT = "sha256:" + "ab" * 32
MARKER = f"<!-- repository-presenter-defect: {FINGERPRINT} -->"

GOOD_TITLE = "Aspose.3D FOSS for .NET: Scene.FromFile(string, FileFormat) has no matching overload"
GOOD_BODY = f"""## Summary

The README example for enumerating a scene's node hierarchy does not compile against the library.

## Environment

- Repository: {REPOSITORY}
- Revision: `{REVISION}` (default branch `main`, verified against this revision)
- .NET SDK 10.0.401

## Steps to reproduce

README.md lines 166-172 as `Program.cs`, then:

```
dotnet build
```

## Expected

The example builds, as the README presents it.

## Actual

```
Program.cs(3,41): error CS1503: Argument 2: cannot convert from 'FileFormat' to 'CancellationToken'
```

`src/main/Aspose.ThreeD/Aspose/ThreeD/Scene.cs:314` declares the overloads;
none takes `(string, FileFormat)`.

{MARKER}
"""


def make(
    *, title: str = GOOD_TITLE, body: str = GOOD_BODY, repository: str = REPOSITORY
) -> Handoff:
    return Handoff(
        schema_version=1,
        repository=repository,
        source_revision=REVISION,
        defect_fingerprint=FINGERPRINT,
        triggering_check=TriggeringCheck(id="BC-03", version="1", causal_stage="EXTRACTING"),
        evidence=(EvidenceEntry(path="README.md", detail="lines 166-172"),),
        claim="The README example does not compile.",
        suggested_issue_title=title,
        suggested_issue_body=body,
        status="HANDOFF_PENDING",
        issue_ref=None,
        close_reason=None,
    )


def codes(handoff: Handoff) -> set[str]:
    return {finding.code for finding in issue_quality_findings(handoff)}


# --- the passing fixture -----------------------------------------------------------------------


def test_a_good_issue_has_no_findings() -> None:
    assert issue_quality_findings(make()) == []
    require_issue_quality(make())  # does not raise


def test_findings_are_deterministic() -> None:
    bad = make(title="oops", body="nothing")
    assert issue_quality_findings(bad) == issue_quality_findings(bad)


def test_every_documented_code_has_a_failing_fixture() -> None:
    """The set of codes is closed: this module's fixtures below cover each one."""
    seen: set[str] = set()
    for handoff in FAILING.values():
        seen |= codes(handoff)
    assert seen == set(CODES)


# --- one failing fixture per check -------------------------------------------------------------

FAILING: dict[str, Handoff] = {
    "ONE_DEFECT/title": make(
        title="Aspose.3D FOSS for .NET: FromFile has no overload; Save drops the format"
    ),
    "ONE_DEFECT/body": make(
        body=GOOD_BODY.replace("## Summary", "## Defect 1").replace(
            "## Environment", "## Defect 2\n\nAnother.\n\n## Environment"
        )
    ),
    "NO_REPRODUCTION": make(
        body=GOOD_BODY.replace("## Steps to reproduce", "## Details")
        .replace("README.md lines 166-172 as `Program.cs`, then:", "")
        .replace("```\ndotnet build\n```", "")
        .replace("`src/main/Aspose.ThreeD/Aspose/ThreeD/Scene.cs:314`", "the scene source")
        .replace("README.md", "the readme")
    ),
    "NO_EXPECTED": make(body=GOOD_BODY.replace("## Expected", "## Intended")),
    "NO_ACTUAL": make(body=GOOD_BODY.replace("## Actual", "## Output")),
    "TITLE_FORMAT/no-separator": make(title="Scene.FromFile has no matching overload"),
    "TITLE_FORMAT/wrong-product": make(title="Some Other Library: FromFile has no overload"),
    "TITLE_LENGTH": make(title="Aspose.3D FOSS for .NET: " + "a very long defect statement " * 5),
    "SECRET": make(
        body=GOOD_BODY.replace("dotnet build", "dotnet build  # ghp_" + "A1b2C3d4E5" * 3)
    ),
    "INTERNAL_NAME": make(
        body=GOOD_BODY.replace("## Actual", "See upstream-issues.md.\n\n## Actual")
    ),
    "EDITION_WORDING": make(
        body=GOOD_BODY.replace("## Actual", "Unlike the commercial edition.\n\n## Actual")
    ),
    "TONE": make(body=GOOD_BODY.replace("## Actual", "We think this is sloppy work.\n\n## Actual")),
    "NO_REVISION": make(body=GOOD_BODY.replace(REVISION, "main")),
}


@pytest.mark.parametrize("name", sorted(FAILING))
def test_each_failing_fixture_is_caught_by_its_own_check(name: str) -> None:
    expected = name.split("/", 1)[0]
    assert expected in codes(FAILING[name])


@pytest.mark.parametrize("name", sorted(FAILING))
def test_each_failing_fixture_differs_from_the_good_one_only_in_its_check(name: str) -> None:
    """Negative control for the fixtures: they fail for the named reason, not for everything."""
    expected = name.split("/", 1)[0]
    others = codes(FAILING[name]) - {expected}
    # a one-line change can also trip a closely related check (e.g. losing the reproduction text
    # also loses a path), but never most of the gate
    assert len(others) <= 2, others


def test_the_good_fixture_survives_each_unrelated_check() -> None:
    """Positive controls: wording that looks close to a forbidden shape but is fine."""
    quoted = GOOD_BODY.replace(
        "## Actual",
        "> Our library is a powerful wrapper for everything.\n\n"
        'The README says "we offer a seamless bridge".\n\n'
        "The type `ThreeDWrapper` is not involved.\n\n## Actual",
    )
    assert codes(make(body=quoted)) == set()


# --- check details ------------------------------------------------------------------------------


def test_the_fingerprint_marker_is_the_only_allowed_internal_name() -> None:
    assert "INTERNAL_NAME" not in codes(make())
    other_comment = GOOD_BODY + "<!-- repository-presenter-note: see runs/x -->\n"
    assert "INTERNAL_NAME" in codes(make(body=other_comment))


@pytest.mark.parametrize(
    "text",
    [
        "upstream-issues.md",
        "content-dispositions.json",
        ".clone_cache/abc",
        "reports/seal.md",
        "runs/wt/x",
        "facts.json",
        "dispositions.json",
        "the sealed bundle",
        "BC-03 failed",
        "install_command:pip",
        "repository-presenter's validation pipeline",
    ],
)
def test_internal_artifact_names_are_findings(text: str) -> None:
    body = GOOD_BODY.replace("## Actual", f"{text}\n\n## Actual")
    assert "INTERNAL_NAME" in codes(make(body=body))


def test_the_product_prefix_may_be_the_repository_name() -> None:
    title = "Aspose.3D-FOSS-for-.NET: FromFile has no matching overload"
    assert issue_quality_findings(make(title=title)) == []


def test_title_length_boundary() -> None:
    prefix = "Aspose.3D FOSS for .NET: "
    at_limit = prefix + "x" * (MAX_TITLE_LENGTH - len(prefix))
    assert "TITLE_LENGTH" not in codes(make(title=at_limit))
    assert "TITLE_LENGTH" in codes(make(title=at_limit + "x"))


def test_a_semicolon_inside_quoted_title_text_is_one_defect() -> None:
    title = 'Aspose.3D FOSS for .NET: README sample "a; b" does not compile'
    assert "ONE_DEFECT" not in codes(make(title=title))


@pytest.mark.parametrize(
    "secret",
    [
        "ghp_" + "A1b2C3d4E5" * 3,
        "ghs_" + "A1b2C3d4E5" * 3,
        "github_pat_" + "A1b2C3d4E5" * 3,
        "sk-" + "A1b2C3d4E5" * 2,
        "AKIA" + "ABCDEFGHIJKLMNOP",
        "Bearer " + "abcdefghij" * 3,
        "https://example.com/x?token=" + "abcdef123456",
        "-----BEGIN RSA PRIVATE KEY-----",
        "eyJhbGciOiJIUzI1" + ".eyJzdWIiOiIxMjM0" + ".abcdefghijklmnop",
    ],
)
def test_secret_shaped_values_are_findings_and_never_echoed(secret: str) -> None:
    body = GOOD_BODY.replace("## Actual", f"{secret}\n\n## Actual")
    findings = [f for f in issue_quality_findings(make(body=body)) if f.code == "SECRET"]
    assert len(findings) == 1
    assert secret not in str(findings[0])
    assert secret not in findings[0].message


def test_a_secret_in_the_title_is_a_title_finding() -> None:
    title = "Aspose.3D FOSS for .NET: leaks ghp_" + "A1b2C3d4E5" * 3
    where = {f.where for f in issue_quality_findings(make(title=title)) if f.code == "SECRET"}
    assert where == {"title"}


@pytest.mark.parametrize(
    "phrase",
    [
        "the commercial edition",
        "a paid version",
        "via Java",
        "a wrapper around the JVM",
        "a bridge",
    ],
)
def test_edition_and_bridge_phrases_are_findings(phrase: str) -> None:
    body = GOOD_BODY.replace("## Actual", f"It behaves like {phrase}.\n\n## Actual")
    assert "EDITION_WORDING" in codes(make(body=body))


@pytest.mark.parametrize(
    "sentence",
    [
        "I could not build it.",
        "We found a regression.",
        "Our tests fail.",
        "This is a powerful, seamless library.",
        "This is sloppy and unacceptable.",
        "You forgot to export it.",
    ],
)
def test_first_person_promotional_and_blame_language_are_findings(sentence: str) -> None:
    body = GOOD_BODY.replace("## Actual", f"{sentence}\n\n## Actual")
    assert "TONE" in codes(make(body=body))


def test_a_path_with_a_line_satisfies_the_reproduction_check() -> None:
    body = (
        f"## Steps to reproduce\n\nOpen `src/a/b.cs:12`.\n\n## Expected\n\nCompiles.\n\n"
        f"## Actual\n\nFails.\n\nRevision {REVISION}.\n\n{MARKER}\n"
    )
    assert issue_quality_findings(make(body=body)) == []


def test_a_command_without_a_reproduction_section_is_not_enough() -> None:
    body = GOOD_BODY.replace("## Steps to reproduce", "## Commands").replace(
        "README.md lines 166-172 as `Program.cs`, then:", ""
    )
    assert "NO_REPRODUCTION" in codes(make(body=body))


def test_expected_inside_a_code_block_does_not_count() -> None:
    body = GOOD_BODY.replace("## Expected", "## Result").replace(
        "```\ndotnet build\n```", "```\nexpected: nothing\n```"
    )
    assert "NO_EXPECTED" in codes(make(body=body))


def test_the_error_is_typed_and_carries_every_finding() -> None:
    bad = make(title="oops", body="nothing")
    with pytest.raises(HandoffQualityError) as excinfo:
        require_issue_quality(bad)
    assert {f.code for f in excinfo.value.findings} == codes(bad)
    assert isinstance(excinfo.value, ValueError)


# --- the gate at the point a handoff is drafted -----------------------------------------------


def _install_fact(
    detail: str, *, polarity: str = "CONTRADICTED", path: str = "https://pypi.org/pypi/x/json"
) -> Fact:
    return Fact(
        "install_command:pip",
        "install_command",
        "pip install x",
        (Evidence(path, detail),),
        polarity=polarity,  # type: ignore[arg-type]
        confidence=0.5,
    )


def _check() -> dict[str, object]:
    return {"id": "BC-02", "version": "1", "causal_stage": "EXTRACTING", "verdict": "FAIL"}


def _facts(fact: Fact) -> FactsDocument:
    return FactsDocument(repository=REPOSITORY, source_revision=REVISION, facts=(fact,))


def test_a_drafted_handoff_passes_the_gate_it_is_held_to() -> None:
    handoff = draft_handoff(
        repository=REPOSITORY,
        source_revision=REVISION,
        check=_check(),
        facts=_facts(_install_fact("HTTP 404 on 2026-10-09")),
    )
    assert handoff is not None
    assert issue_quality_findings(handoff) == []
    assert handoff.suggested_issue_title.startswith("Aspose.3D FOSS for .NET: ")
    assert "pip install x" in handoff.suggested_issue_body
    assert "curl -s -o /dev/null" in handoff.suggested_issue_body


def test_an_unresolved_fact_is_reported_as_unverified_not_failed() -> None:
    handoff = draft_handoff(
        repository=REPOSITORY,
        source_revision=REVISION,
        check=_check(),
        facts=_facts(_install_fact("registry unreachable", polarity="UNRESOLVED")),
    )
    assert handoff is not None
    assert "could not be verified" in handoff.suggested_issue_title
    assert "fails verification" not in handoff.suggested_issue_title


def test_draft_refuses_with_a_typed_reason_when_the_text_fails_the_gate() -> None:
    leaked = "token ghp_" + "A1b2C3d4E5" * 3
    with pytest.raises(HandoffQualityError) as excinfo:
        draft_handoff(
            repository=REPOSITORY,
            source_revision=REVISION,
            check=_check(),
            facts=_facts(_install_fact(leaked)),
        )
    assert {f.code for f in excinfo.value.findings} == {"SECRET"}
    assert "ghp_" not in str(excinfo.value)


def test_draft_refuses_internal_vocabulary_in_the_evidence() -> None:
    with pytest.raises(HandoffQualityError) as excinfo:
        draft_handoff(
            repository=REPOSITORY,
            source_revision=REVISION,
            check=_check(),
            facts=_facts(_install_fact("see reports/seal.md and facts.json")),
        )
    assert "INTERNAL_NAME" in {f.code for f in excinfo.value.findings}


def test_record_writes_nothing_when_the_text_fails_the_gate(tmp_path: Path) -> None:
    root = tmp_path / "upstream-defects"
    written = record_handoff_if_new(
        root,
        repository=REPOSITORY,
        source_revision=REVISION,
        check=_check(),
        facts=_facts(_install_fact("see reports/seal.md")),
    )
    assert written is None
    assert not root.exists() or load_ledger(root) == {}


def test_record_still_writes_a_clean_draft(tmp_path: Path) -> None:
    root = tmp_path / "upstream-defects"
    written = record_handoff_if_new(
        root,
        repository=REPOSITORY,
        source_revision=REVISION,
        check=_check(),
        facts=_facts(_install_fact("HTTP 404")),
    )
    assert written is not None
    assert issue_quality_findings(load_handoff(written)) == []


# --- the committed handoffs ---------------------------------------------------------------------


def test_the_gate_runs_over_every_committed_handoff() -> None:
    """A smoke test, not a pass requirement: the committed bodies are rewritten by their own work
    item. It proves the gate can read every artifact on record and returns typed findings."""
    root = REPO_ROOT / "evidence" / "upstream-defects"
    paths = [p for p in sorted(root.glob("*/*.json")) if p.name != "reverification.json"]
    assert paths
    for path in paths:
        handoff = load_handoff(path)
        for finding in issue_quality_findings(handoff):
            assert finding.code in CODES
            assert finding.where in ("title", "body")
        assert replace(handoff, status="HANDOFF_PENDING").repository == handoff.repository
