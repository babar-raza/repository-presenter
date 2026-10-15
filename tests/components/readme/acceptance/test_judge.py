"""The judge: a computed, deterministic verdict on one sealed bundle, a clause at a time.

Each clause has a passing bundle and a negative control that tampers exactly one input. The
reviewer's verdict is advisory in both directions. A synthetic bundle carries only the files the
judge reads; a real sealed bundle is copied in the last tests.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme.acceptance import judge as judge_module
from repository_presenter.components.readme.acceptance.judge import (
    FAIL,
    J1,
    J2,
    J3,
    J4,
    J5,
    J6,
    NOT_APPLICABLE,
    PASS,
    UNEVALUATED,
    JudgeVerdict,
    heading_key,
    judge_bundle,
    judge_repository_bundle,
    live_is_standard_for,
    load_standard,
)
from repository_presenter.components.readme.composition.renderer import render_patch
from support import REPO_ROOT

REVISION = "a" * 40
UNASSIGNED = "acme/Widget-FOSS-for-Python"  # no assignment: the common core applies
ASSIGNED = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"  # std-registry: the whole core applies
CHECKS = tuple(f"BC-{number:02d}" for number in range(1, 13))

LIVE = """# Widget FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/widget.svg)](https://pypi.org/project/widget/)

Widget reads and writes widgets.

## Install

```bash
pip install widget
```

## Usage

See the [docs](https://widget.example.com/docs/) for details.

## License

MIT
"""

CANDIDATE = """# Widget FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/widget.svg)](https://pypi.org/project/widget/)

Widget FOSS for Python reads and writes widgets.

## Key Capabilities

- Reads widgets.

## Installation

```bash
pip install widget
```

## Usage

See the [docs](https://widget.example.com/docs/) for details.

## Scope and Limitations

- Handles widgets only.

## License

MIT
"""

# unit id, text, disposition, cites a fact
UNITS: tuple[tuple[str, str, str, bool], ...] = (
    ("inherited_unit:001.heading", "# Widget FOSS for Python", "SUPERSEDE_REDUNDANT", True),
    (
        "inherited_unit:002.badge_row",
        "[![PyPI](https://img.shields.io/pypi/v/widget.svg)](https://pypi.org/project/widget/)",
        "SUPERSEDE_REDUNDANT",
        True,
    ),
    (
        "inherited_unit:003.paragraph",
        "Widget reads and writes widgets.",
        "SUPERSEDE_REDUNDANT",
        True,
    ),
    ("inherited_unit:004.heading", "## Install", "SUPERSEDE_REDUNDANT", True),
    (
        "inherited_unit:005.code_block",
        "```bash\npip install widget\n```",
        "SUPERSEDE_REDUNDANT",
        True,
    ),
    ("inherited_unit:006.heading", "## Usage", "VERIFIED_PRESERVE", False),
    (
        "inherited_unit:007.paragraph",
        "See the [docs](https://widget.example.com/docs/) for details.",
        "VERIFIED_PRESERVE",
        False,
    ),
    ("inherited_unit:008.heading", "## License", "VERIFIED_PRESERVE", False),
    ("inherited_unit:009.paragraph", "MIT", "VERIFIED_PRESERVE", False),
)


def _write(path: Path, document: Any) -> None:
    path.write_text(json.dumps(document), encoding="utf-8")


class Bundle:
    """A synthetic sealed bundle with the files the judge reads, and handles to tamper with them."""

    def __init__(self, directory: Path, repository: str = UNASSIGNED) -> None:
        self.path = directory
        self.repository = repository
        directory.mkdir(parents=True)
        self.live = LIVE
        self.write_readme(CANDIDATE)
        _write(
            directory / "validation.json",
            {
                "source_revision": REVISION,
                "readme_sha256": self.readme_hash,
                "checks": [{"id": check, "verdict": "PASS", "failures": []} for check in CHECKS],
            },
        )
        _write(
            directory / "manifest.json",
            {
                "repository": repository,
                "revision": REVISION,
                "state": "READY_FOR_PROPOSAL",
                "no_op_proof": {"byte_identical": True, "fresh_process": True, "provider_calls": 0},
            },
        )
        _write(directory / "review.json", {"verdict": "ACCEPT"})
        facts: list[dict[str, Any]] = [
            {"id": unit, "kind": "inherited_unit", "polarity": "SUPPORTED", "value": text}
            for unit, text, _, _ in UNITS
        ]
        facts.append(
            {
                "id": "install_command:pip",
                "kind": "install_command",
                "polarity": "SUPPORTED",
                "value": "pip install widget",
            }
        )
        _write(directory / "facts.json", {"repository": repository, "facts": facts})
        _write(
            directory / "dispositions.json",
            {
                "dispositions": [
                    {
                        "unit_id": unit,
                        "disposition": disposition,
                        "destination_section": None,
                        "fact_ids": ["package:name"] if cites else [],
                        "rationale": "rendered from a verified fact"
                        if cites
                        else "kept as written",
                    }
                    for unit, _, disposition, cites in UNITS
                ]
            },
        )

    @property
    def readme_hash(self) -> str:
        return hashlib.sha256((self.path / "README.md").read_bytes()).hexdigest()

    def write_readme(self, text: str) -> None:
        """A new candidate README, its patch from the live one, and validation bound to it."""
        (self.path / "README.md").write_bytes(text.encode("utf-8"))
        patch = render_patch(self.live, text)
        (self.path / "README.patch").write_bytes(patch.encode("utf-8"))
        if (self.path / "validation.json").exists():
            self.edit("validation.json", lambda doc: doc.update(readme_sha256=self.readme_hash))

    def edit(self, name: str, change: Callable[[Any], Any]) -> None:
        document = json.loads((self.path / name).read_text(encoding="utf-8"))
        change(document)
        _write(self.path / name, document)

    def check(self, check: str, verdict: str, failure: str = "") -> None:
        def change(document: dict[str, Any]) -> None:
            for row in document["checks"]:
                if row["id"] == check:
                    row["verdict"] = verdict
                    row["failures"] = [{"detail": failure, "section": "opening"}] if failure else []

        self.edit("validation.json", change)

    def disposition(self, unit: str, **fields: Any) -> None:
        def change(document: dict[str, Any]) -> None:
            for row in document["dispositions"]:
                if row["unit_id"] == unit:
                    row.update(fields)

        self.edit("dispositions.json", change)

    def judge(self, live_is_standard: bool | None = False) -> JudgeVerdict:
        return judge_bundle(self.path, live_is_standard=live_is_standard)


@pytest.fixture
def bundle(tmp_path: Path) -> Bundle:
    return Bundle(tmp_path / "bundle")


def _status(verdict: JudgeVerdict, clause: str) -> str:
    return verdict.clause(clause).status


# --- the passing bundle ------------------------------


def test_a_bundle_every_clause_passes_is_authorizable(bundle: Bundle) -> None:
    verdict = bundle.judge(live_is_standard=True)
    assert [clause.status for clause in verdict.clauses] == [PASS] * 6
    assert verdict.authorizable and verdict.failing == ()
    assert verdict.reviewer_advisory == "ACCEPT"
    document = verdict.to_json()
    assert document["authorizable"] is True and document["failing"] == []
    assert [row["id"] for row in document["clauses"]] == [J1, J2, J3, J4, J5, J6]
    assert verdict.refusal() is None


def test_the_verdict_is_a_pure_function_of_the_files(bundle: Bundle) -> None:
    assert bundle.judge(True) == bundle.judge(True)
    assert bundle.judge(True).to_json() == bundle.judge(True).to_json()


def test_a_live_readme_that_is_not_standard_makes_j6_not_applicable(bundle: Bundle) -> None:
    verdict = bundle.judge(live_is_standard=False)
    assert _status(verdict, J6) == NOT_APPLICABLE and verdict.authorizable


def test_unknown_applicability_of_j6_is_unevaluated_and_not_passing(bundle: Bundle) -> None:
    verdict = bundle.judge(live_is_standard=None)
    assert _status(verdict, J6) == UNEVALUATED
    assert not verdict.authorizable and verdict.failing == (J6,)


# --- J1: facts ------------------------------


@pytest.mark.parametrize("check", ["BC-01", "BC-02", "BC-03", "BC-06", "BC-08", "BC-09"])
def test_j1_fails_on_any_fact_check_and_names_it(bundle: Bundle, check: str) -> None:
    bundle.check(check, "FAIL", "the install command is unverified")
    verdict = bundle.judge()
    clause = verdict.clause(J1)
    assert clause.status == FAIL and check in clause.detail and "unverified" in clause.detail
    assert "(section opening)" in clause.detail
    assert verdict.failing == (J1,) and not verdict.authorizable
    assert J1 in (verdict.refusal() or "") and check in (verdict.refusal() or "")


def test_j1_is_unevaluated_when_a_fact_check_is_not_recorded(bundle: Bundle) -> None:
    bundle.edit(
        "validation.json",
        lambda doc: doc.update(checks=[c for c in doc["checks"] if c["id"] != "BC-09"]),
    )
    verdict = bundle.judge()
    assert (
        _status(verdict, J1) == UNEVALUATED and "BC-09 is not recorded" in verdict.clause(J1).detail
    )
    assert not verdict.authorizable


def test_j1_is_unevaluated_when_validation_cannot_be_read(bundle: Bundle) -> None:
    (bundle.path / "validation.json").unlink()
    verdict = bundle.judge()
    for clause in (J1, J2, J3):
        assert _status(verdict, clause) == UNEVALUATED


def test_validation_that_judged_another_readme_or_revision_fails_every_clause_reading_it(
    bundle: Bundle,
) -> None:
    bundle.edit("validation.json", lambda doc: doc.update(readme_sha256="0" * 64))
    verdict = bundle.judge()
    assert _status(verdict, J1) == FAIL and "different README" in verdict.clause(J1).detail
    assert _status(verdict, J3) == FAIL and _status(verdict, J2) == FAIL
    bundle.edit("validation.json", lambda doc: doc.update(readme_sha256=bundle.readme_hash))
    bundle.edit("validation.json", lambda doc: doc.update(source_revision="b" * 40))
    assert "revision" in bundle.judge().clause(J1).detail


# --- J2: the standard ------------------------------


def test_j2_fails_when_a_required_heading_is_missing_and_names_the_element(bundle: Bundle) -> None:
    bundle.write_readme(CANDIDATE.replace("## License\n\nMIT\n", ""))
    verdict = bundle.judge()
    clause = verdict.clause(J2)
    assert clause.status == FAIL and "license" in clause.detail and "common core" in clause.detail
    assert verdict.clause(J1).status == PASS  # nothing else moved


def test_j2_fails_when_the_structure_check_fails(bundle: Bundle) -> None:
    bundle.check("BC-07", "FAIL", "heading is not title case")
    clause = bundle.judge().clause(J2)
    assert clause.status == FAIL and "BC-07" in clause.detail and "title case" in clause.detail


def test_j2_reads_the_assigned_archetype_not_only_the_common_core(tmp_path: Path) -> None:
    assigned = Bundle(tmp_path / "assigned", ASSIGNED)
    verdict = assigned.judge()
    assert _status(verdict, J2) == FAIL
    detail = verdict.clause(J2).detail
    assert "std-registry" in detail
    for element in ("navigation", "dependencies", "api_reference"):
        assert element in detail
    assert "license" not in detail  # present
    full = CANDIDATE.replace(
        "## Key Capabilities",
        "## Navigation\n\n- [Usage](#usage)\n\n## Key Capabilities",
    ).replace(
        "## Usage",
        "## Dependencies\n\nNone.\n\n## API Reference\n\n- `Widget`\n\n## Usage",
    )
    assigned.write_readme(full)
    assert _status(assigned.judge(), J2) == PASS


def test_j2_matches_headings_ignoring_case_and_ampersands() -> None:
    assert heading_key("Documentation & Resources") == heading_key("documentation and resources")
    assert heading_key("Scope and Limitations") != heading_key("Scope")


@pytest.mark.parametrize(
    ("readme", "missing"),
    [
        (
            CANDIDATE.replace("# Widget FOSS for Python\n", "## Widget FOSS for Python\n"),
            "identity_h1",
        ),
        (
            CANDIDATE.replace(
                "[![PyPI](https://img.shields.io/pypi/v/widget.svg)](https://pypi.org/project/widget/)\n",
                "",
            ),
            "badge_row",
        ),
        (CANDIDATE.replace("Widget FOSS for Python reads and writes widgets.\n", ""), "opening"),
    ],
)
def test_j2_checks_the_unheaded_elements(bundle: Bundle, readme: str, missing: str) -> None:
    bundle.write_readme(readme)
    clause = bundle.judge().clause(J2)
    assert clause.status == FAIL and missing in clause.detail


def test_j2_never_guesses_an_element_it_cannot_match(
    bundle: Bundle, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        judge_module,
        "ELEMENT_MATCHERS",
        {k: v for k, v in judge_module.ELEMENT_MATCHERS.items() if k != "opening"},
    )
    verdict = bundle.judge()
    clause = verdict.clause(J2)
    assert clause.status == UNEVALUATED and "no deterministic match" in clause.detail
    assert "opening" in clause.detail and not verdict.authorizable


def test_the_standard_comes_from_the_data_files() -> None:
    standard = load_standard()
    assert standard.assignments[ASSIGNED] == "std-registry"
    archetype, required = standard.required_for(UNASSIGNED)
    assert archetype == "common core" and "license" in required
    assert "navigation" in standard.required_for(ASSIGNED)[1]
    assert (
        "badge_row"
        not in standard.required_for("aspose-cells-foss/Aspose.Cells-FOSS-for-Python")[1]
    )


# --- J3: claims ------------------------------


def test_j3_fails_when_a_claim_cites_no_accepted_fact(bundle: Bundle) -> None:
    bundle.check("BC-04", "FAIL", "unit opening cites a fact outside its slot")
    verdict = bundle.judge()
    clause = verdict.clause(J3)
    assert (
        clause.status == FAIL and "BC-04" in clause.detail and "outside its slot" in clause.detail
    )
    assert verdict.failing == (J3,)


# --- J4: dispositions ------------------------------


def test_j4_fails_when_the_dispositions_check_fails(bundle: Bundle) -> None:
    bundle.check("BC-05", "FAIL", "unit 007 deferred")
    assert "BC-05" in bundle.judge().clause(J4).detail


def test_j4_fails_when_kept_text_is_not_printed(bundle: Bundle) -> None:
    bundle.write_readme(
        CANDIDATE.replace(
            "See the [docs](https://widget.example.com/docs/) for details.", "See docs."
        )
    )
    clause = bundle.judge().clause(J4)
    assert clause.status == FAIL
    assert "inherited_unit:007.paragraph" in clause.detail and "VERIFIED_PRESERVE" in clause.detail


def test_j4_accepts_a_kept_heading_that_was_re_leveled_and_re_cased(bundle: Bundle) -> None:
    bundle.write_readme(CANDIDATE.replace("## Usage", "### usage"))
    assert _status(bundle.judge(), J4) == PASS


def test_j4_fails_for_a_unit_with_no_disposition_or_two(bundle: Bundle) -> None:
    def drop(document: dict[str, Any]) -> None:
        document["dispositions"] = [
            row
            for row in document["dispositions"]
            if row["unit_id"] != "inherited_unit:009.paragraph"
        ]

    bundle.edit("dispositions.json", drop)
    assert "inherited_unit:009.paragraph has 0 dispositions" in bundle.judge().clause(J4).detail

    def duplicate(document: dict[str, Any]) -> None:
        document["dispositions"].append(dict(document["dispositions"][0]))

    bundle.edit("dispositions.json", duplicate)
    assert "inherited_unit:001.heading has 2 dispositions" in bundle.judge().clause(J4).detail


def test_j4_fails_for_a_disposition_naming_an_unknown_unit(bundle: Bundle) -> None:
    bundle.edit(
        "dispositions.json",
        lambda doc: doc["dispositions"].append(
            {"unit_id": "inherited_unit:099.paragraph", "disposition": "NON_CONTENT"}
        ),
    )
    assert (
        "inherited_unit:099.paragraph is not an inherited unit" in bundle.judge().clause(J4).detail
    )


def test_j4_is_unevaluated_without_the_dispositions_file(bundle: Bundle) -> None:
    (bundle.path / "dispositions.json").unlink()
    assert _status(bundle.judge(), J4) == UNEVALUATED


# --- J5: rerun ------------------------------


@pytest.mark.parametrize(
    "proof",
    [
        None,
        {"byte_identical": False, "fresh_process": True, "provider_calls": 0},
        {"byte_identical": True, "fresh_process": False, "provider_calls": 0},
        {"byte_identical": True, "fresh_process": True, "provider_calls": 2},
    ],
)
def test_j5_fails_without_a_zero_call_byte_identical_fresh_process_rerun(
    bundle: Bundle, proof: dict[str, Any] | None
) -> None:
    bundle.edit("manifest.json", lambda doc: doc.update(no_op_proof=proof))
    verdict = bundle.judge()
    assert _status(verdict, J5) == FAIL and verdict.failing == (J5,)
    assert "no byte-identical" in verdict.clause(J5).detail


def test_j5_fails_when_bc_11_fails(bundle: Bundle) -> None:
    bundle.check("BC-11", "FAIL", "rerun differs")
    clause = bundle.judge().clause(J5)
    assert clause.status == FAIL and "BC-11" in clause.detail


def test_j5_is_unevaluated_without_a_manifest(bundle: Bundle) -> None:
    (bundle.path / "manifest.json").unlink()
    assert _status(bundle.judge(), J5) == UNEVALUATED


# --- J6: not worse than the live README ------------------------------


def _without(text: str, removed: str) -> str:
    assert removed in text
    return text.replace(removed, "")


def test_j6_fails_when_a_live_heading_is_dropped_without_a_disposition(bundle: Bundle) -> None:
    bundle.write_readme(
        _without(
            CANDIDATE,
            "## Usage\n\nSee the [docs](https://widget.example.com/docs/) for details.\n\n",
        )
    )
    clause = bundle.judge(True).clause(J6)
    assert clause.status == FAIL and "heading 'Usage'" in clause.detail
    assert "link https://widget.example.com/docs/" in clause.detail


def test_j6_accepts_a_dropped_section_a_disposition_accounts_for_with_evidence(
    bundle: Bundle,
) -> None:
    bundle.write_readme(
        _without(
            CANDIDATE,
            "## Usage\n\nSee the [docs](https://widget.example.com/docs/) for details.\n\n",
        )
    )
    for unit in ("inherited_unit:006.heading", "inherited_unit:007.paragraph"):
        bundle.disposition(
            unit,
            disposition="OMIT_UNSUPPORTED",
            fact_ids=["link_target:docs"],
            rationale="the docs link now 404s (CONTRADICTED)",
        )
    verdict = bundle.judge(True)
    assert _status(verdict, J6) == PASS and verdict.authorizable


@pytest.mark.parametrize(
    "change",
    [
        {"fact_ids": []},
        {"rationale": "  "},
        {"disposition": "DEFER_UNRESOLVED"},
        {"disposition": "NON_CONTENT"},
    ],
)
def test_j6_does_not_take_a_disposition_without_evidence_as_an_account(
    bundle: Bundle, change: dict[str, Any]
) -> None:
    bundle.write_readme(
        _without(
            CANDIDATE,
            "## Usage\n\nSee the [docs](https://widget.example.com/docs/) for details.\n\n",
        )
    )
    for unit in ("inherited_unit:006.heading", "inherited_unit:007.paragraph"):
        bundle.disposition(
            unit,
            **{"disposition": "OMIT_UNSUPPORTED", "fact_ids": ["f"], "rationale": "r", **change},
        )
    assert "heading 'Usage'" in bundle.judge(True).clause(J6).detail


def test_j6_fails_for_a_lost_code_block_and_names_it(bundle: Bundle) -> None:
    bundle.write_readme(CANDIDATE.replace("pip install widget", "uv add widget"))
    bundle.disposition("inherited_unit:005.code_block", disposition="NON_CONTENT")
    detail = bundle.judge(True).clause(J6).detail
    assert "code block 'pip install widget'" in detail and "command 'pip install widget'" in detail


def test_j6_accepts_a_replaced_code_block_the_disposition_accounts_for(bundle: Bundle) -> None:
    bundle.write_readme(CANDIDATE.replace("pip install widget", "uv add widget"))
    assert _status(bundle.judge(True), J6) == PASS  # unit 005 is SUPERSEDE_REDUNDANT with a fact


def test_j6_fails_for_a_lost_link_target(bundle: Bundle) -> None:
    bundle.write_readme(CANDIDATE.replace("(https://widget.example.com/docs/)", "(#usage)"))
    bundle.disposition("inherited_unit:007.paragraph", disposition="NON_CONTENT")
    assert "link https://widget.example.com/docs/" in bundle.judge(True).clause(J6).detail


def test_j6_is_unevaluated_when_the_live_readme_cannot_be_recovered(bundle: Bundle) -> None:
    (bundle.path / "README.patch").write_text(
        "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-x\n+y\n"
    )
    verdict = bundle.judge(True)
    clause = verdict.clause(J6)
    assert clause.status == UNEVALUATED and "cannot be recovered" in clause.detail
    assert not verdict.authorizable
    (bundle.path / "README.patch").unlink()
    assert _status(bundle.judge(True), J6) == UNEVALUATED


# --- the reviewer is advisory ------------------------------


def test_an_accepting_reviewer_cannot_authorize_a_bundle_with_a_failing_clause(
    bundle: Bundle,
) -> None:
    bundle.check("BC-04", "FAIL", "unsupported claim")
    bundle.edit("review.json", lambda doc: doc.update(verdict="ACCEPT"))
    verdict = bundle.judge()
    assert verdict.reviewer_advisory == "ACCEPT"
    assert not verdict.authorizable and verdict.failing == (J3,)


def test_a_rejecting_reviewer_cannot_block_a_bundle_every_clause_passes(bundle: Bundle) -> None:
    bundle.edit("review.json", lambda doc: doc.update(verdict="REJECT_FACTUAL"))
    verdict = bundle.judge(True)
    assert verdict.reviewer_advisory == "REJECT_FACTUAL"
    assert verdict.authorizable and verdict.failing == ()


def test_no_review_file_changes_nothing(bundle: Bundle) -> None:
    (bundle.path / "review.json").unlink()
    verdict = bundle.judge(True)
    assert verdict.reviewer_advisory is None and verdict.authorizable


# --- is the live README standard? ------------------------------


def test_live_is_standard_follows_the_survey_rows() -> None:
    rows = json.loads((REPO_ROOT / "data" / "readme_standard" / "survey.json").read_text("utf-8"))[
        "rows"
    ]
    for repository, row in rows.items():
        expected = (
            row.get("readme") is True and bool(row.get("glance_form")) and row.get("banner") is True
        )
        assert live_is_standard_for(repository) is expected, repository
    assert live_is_standard_for("aspose-3d-foss/Aspose.3D-FOSS-for-.NET") is True
    assert live_is_standard_for("not-listed/Anything") is False


def test_live_is_standard_reads_each_condition(tmp_path: Path) -> None:
    rows = {
        "o/standard": {"readme": True, "glance_form": "mermaid", "banner": True},
        "o/no-readme": {"readme": False, "glance_form": None, "banner": None},
        "o/no-glance": {"readme": True, "glance_form": None, "banner": True},
        "o/no-banner": {"readme": True, "glance_form": "image", "banner": False},
    }
    (tmp_path / "survey.json").write_text(json.dumps({"rows": rows}), encoding="utf-8")
    assert {name: live_is_standard_for(name, standard_dir=tmp_path) for name in rows} == {
        "o/standard": True,
        "o/no-readme": False,
        "o/no-glance": False,
        "o/no-banner": False,
    }
    assert live_is_standard_for("o/standard", standard_dir=tmp_path / "missing") is False


def test_the_production_call_asks_the_survey(tmp_path: Path) -> None:
    standard = Bundle(tmp_path / "standard", "aspose-3d-foss/Aspose.3D-FOSS-for-.NET")
    other = Bundle(tmp_path / "other", UNASSIGNED)
    assert judge_repository_bundle(standard.path, standard.repository).clause(J6).status != (
        NOT_APPLICABLE
    )
    assert judge_repository_bundle(other.path, other.repository).clause(J6).status == NOT_APPLICABLE


# --- a real sealed bundle ------------------------------


def _real_bundle(destination: Path) -> Path | None:
    for current in sorted((REPO_ROOT / "candidates").glob("*/CURRENT")):
        source = current.parent / current.read_text(encoding="utf-8").strip()
        if (source / "validation.json").is_file():
            shutil.copytree(source, destination)
            return destination
    return None


def test_the_judge_reads_a_real_sealed_bundle_without_a_model(tmp_path: Path) -> None:
    copied = _real_bundle(tmp_path / "real")
    if copied is None:
        pytest.skip("no sealed bundle in this checkout")
    repository = json.loads((copied / "manifest.json").read_text("utf-8"))["repository"]
    first = judge_repository_bundle(copied, repository)
    second = judge_repository_bundle(copied, repository)
    assert first.to_json() == second.to_json()
    assert [clause.id for clause in first.clauses] == [J1, J2, J3, J4, J5, J6]
    assert all(clause.status != UNEVALUATED for clause in first.clauses)
    assert (
        first.reviewer_advisory
        == json.loads((copied / "review.json").read_text("utf-8"))["verdict"]
    )


def test_tampering_with_a_real_bundle_readme_fails_the_clauses_that_read_it(
    tmp_path: Path,
) -> None:
    copied = _real_bundle(tmp_path / "real")
    if copied is None:
        pytest.skip("no sealed bundle in this checkout")
    readme = (copied / "README.md").read_bytes()
    repository = json.loads((copied / "manifest.json").read_text("utf-8"))["repository"]
    (copied / "README.md").write_bytes(readme + b"\nAn unvalidated sentence.\n")
    verdict = judge_repository_bundle(copied, repository)
    assert not verdict.authorizable
    assert "different README" in verdict.clause(J1).detail
