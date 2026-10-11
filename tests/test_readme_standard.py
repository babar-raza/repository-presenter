"""The README standard's data is consistent, covers the registry, and cannot drift from its survey.

tools/readme_standard/check_profiles.py validates data/readme_standard/ (schema, every registry
repository assigned to exactly one archetype, cross-references, frequencies recomputed from
survey.json, the document's tags and tables). The committed data must pass; each way it can go wrong
is injected into a temporary copy and must be reported. The survey's measures are held to the
defects they name by synthetic READMEs, and the closed predicate language is held operator by
operator.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
import yaml
from tools.readme_standard import build_survey, observations, render_tables, survey_features
from tools.readme_standard import check_profiles as cp

from support import REPO_ROOT

DATA = REPO_ROOT / "data" / "readme_standard"
REGISTRY = REPO_ROOT / "data" / "registry.json"
DOCUMENT = REPO_ROOT / "docs" / "README_STANDARD.md"


# --- the committed standard ----------------------------------------------------------------------


def test_the_committed_standard_passes_every_check() -> None:
    assert cp.check() == []


def test_all_registry_repositories_are_assigned_exactly_once() -> None:
    registered = [e["repository"] for e in json.loads(REGISTRY.read_text("utf-8"))["entries"]]
    assigned = [
        a["repository"]
        for a in yaml.safe_load((DATA / "assignments.yaml").read_text("utf-8"))["assignments"]
    ]
    assert len(registered) == 36
    assert Counter(assigned) == Counter(registered)


def test_the_command_line_reports_ok_on_the_committed_data(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cp.main([]) == 0
    assert "36 repositories assigned once each" in capsys.readouterr().out


def test_every_archetype_has_a_member_and_every_member_an_archetype() -> None:
    assignments = yaml.safe_load((DATA / "assignments.yaml").read_text("utf-8"))["assignments"]
    archetypes = {path.stem for path in (DATA / "archetypes").glob("*.yaml")}
    assert {a["archetype"] for a in assignments} == archetypes


# --- negative controls on a copy -----------------------------------------------------------------


class Copy:
    """A throwaway copy of the data, the registry and the document, with edit helpers."""

    def __init__(self, root: Path) -> None:
        self.data = root / "data" / "readme_standard"
        self.registry = root / "data" / "registry.json"
        self.document = root / "docs" / "README_STANDARD.md"
        shutil.copytree(DATA, self.data)
        shutil.copy(REGISTRY, self.registry)
        self.document.parent.mkdir(parents=True)
        shutil.copy(DOCUMENT, self.document)

    def check(self) -> list[str]:
        return cp.check(self.data, self.registry, self.document)

    def edit_yaml(self, name: str, change: Any) -> None:
        path = self.data / name
        document = yaml.safe_load(path.read_text("utf-8"))
        change(document)
        path.write_text(yaml.safe_dump(document, sort_keys=False, width=100), "utf-8")

    def edit_survey(self, change: Any) -> None:
        path = self.data / "survey.json"
        survey = json.loads(path.read_text("utf-8"))
        change(survey)
        path.write_text(json.dumps(survey), "utf-8")

    def edit_document(self, pattern: str, replacement: str) -> None:
        text = self.document.read_text("utf-8")
        changed, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
        assert count == 1, f"pattern {pattern!r} not found in the document"
        self.document.write_text(changed, "utf-8")


@pytest.fixture
def copy(tmp_path: Path) -> Copy:
    clone = Copy(tmp_path)
    assert clone.check() == [], "the copy must start clean for a negative control to mean anything"
    return clone


def has(problems: list[str], fragment: str) -> bool:
    return any(fragment in problem for problem in problems)


def test_a_repository_assigned_twice_is_reported(copy: Copy) -> None:
    copy.edit_yaml("assignments.yaml", lambda d: d["assignments"].append(dict(d["assignments"][0])))
    assert has(copy.check(), "is assigned more than once")


def test_an_unassigned_registry_repository_is_reported(copy: Copy) -> None:
    copy.edit_yaml("assignments.yaml", lambda d: d["assignments"].pop())
    problems = copy.check()
    assert has(problems, "is not assigned")
    assert has(problems, "Aspose.Words-FOSS-for-Python")


def test_an_assigned_repository_outside_the_registry_is_reported(copy: Copy) -> None:
    def add(document: dict[str, Any]) -> None:
        entry = dict(document["assignments"][0])
        entry["repository"] = "aspose-nope-foss/Aspose.Nope-FOSS-for-Python"
        document["assignments"].append(entry)

    copy.edit_yaml("assignments.yaml", add)
    assert has(copy.check(), "is not a registry repository")


def test_an_unknown_archetype_in_an_assignment_is_reported(copy: Copy) -> None:
    copy.edit_yaml("assignments.yaml", lambda d: d["assignments"][0].update(archetype="nope"))
    assert has(copy.check(), "unknown archetype nope")


def test_an_archetype_without_members_is_reported(copy: Copy) -> None:
    source = copy.data / "archetypes" / "std-registry.yaml"
    profile = yaml.safe_load(source.read_text("utf-8"))
    profile["id"] = "std-orphan"
    (copy.data / "archetypes" / "std-orphan.yaml").write_text(yaml.safe_dump(profile), "utf-8")
    assert has(copy.check(), "no repository is assigned to it")


def test_an_archetype_whose_id_is_not_its_file_name_is_reported(copy: Copy) -> None:
    path = copy.data / "archetypes" / "std-source.yaml"
    profile = yaml.safe_load(path.read_text("utf-8"))
    profile["id"] = "std-other"
    path.write_text(yaml.safe_dump(profile), "utf-8")
    assert has(copy.check(), "not the file name")


def test_a_family_or_ecosystem_that_differs_from_the_registry_is_reported(copy: Copy) -> None:
    copy.edit_yaml("assignments.yaml", lambda d: d["assignments"][0].update(family="words"))
    problems = copy.check()
    assert has(problems, "family is words but the registry says 3d")
    copy.edit_yaml("assignments.yaml", lambda d: d["assignments"][1].update(ecosystem="python"))
    assert has(copy.check(), "ecosystem is python but the registry says java")


def test_an_axis_value_outside_the_schema_is_reported(copy: Copy) -> None:
    copy.edit_yaml("assignments.yaml", lambda d: d["assignments"][0].update(voice="chatty"))
    problems = copy.check()
    assert has(problems, "assignments.yaml")
    assert has(problems, "chatty")


def test_a_wrong_api_size_class_is_reported(copy: Copy) -> None:
    copy.edit_yaml("assignments.yaml", lambda d: d["assignments"][0].update(api_size_class="XL"))
    assert has(copy.check(), "api_size_class XL")


def test_an_archetype_missing_an_element_is_reported(copy: Copy) -> None:
    copy.edit_yaml("archetypes/std-source.yaml", lambda d: d["elements"].pop("license"))
    assert has(copy.check(), "element license has no requirement")


def test_an_archetype_naming_an_unknown_element_is_reported(copy: Copy) -> None:
    copy.edit_yaml("archetypes/std-source.yaml", lambda d: d["elements"].update(made_up="required"))
    assert has(copy.check(), "unknown element made_up")


def test_an_archetype_citing_an_unknown_defect_class_is_reported(copy: Copy) -> None:
    copy.edit_yaml(
        "archetypes/std-source.yaml",
        lambda d: d["better_than_live"][0].update(defect_classes=["DEF-99"]),
    )
    assert has(copy.check(), "unknown defect class DEF-99")


def test_a_tampered_observation_count_is_reported(copy: Copy) -> None:
    def tamper(document: dict[str, Any]) -> None:
        next(o for o in document["observations"] if o["id"] == "banner_present")["count"] = 5

    copy.edit_yaml("observations.yaml", tamper)
    assert has(copy.check(), "banner_present declares 5/35")


def test_a_tampered_statistic_is_reported(copy: Copy) -> None:
    def tamper(document: dict[str, Any]) -> None:
        next(s for s in document["statistics"] if s["id"] == "lines_max")["value"] = 10.0

    copy.edit_yaml("observations.yaml", tamper)
    assert has(copy.check(), "statistic lines_max declares 10.0")


def test_a_survey_that_loses_a_repository_is_reported(copy: Copy) -> None:
    copy.edit_survey(lambda s: s["rows"].pop("aspose-words-foss/Aspose.Words-FOSS-for-Python"))
    assert has(copy.check(), "no row for registry repository")


def test_a_survey_row_outside_the_registry_is_reported(copy: Copy) -> None:
    copy.edit_survey(lambda s: s["rows"].update({"a/b": {"head": "abcdef0", "readme": False}}))
    assert has(copy.check(), "which is not a registry repository")


def test_an_observation_naming_an_unknown_element_reference_is_reported(copy: Copy) -> None:
    copy.edit_yaml(
        "common.yaml", lambda d: d["elements"][0].update(observations=["not_an_observation"])
    )
    assert has(copy.check(), "unknown observation not_an_observation")


def test_an_observed_common_claim_without_a_common_measure_is_reported(copy: Copy) -> None:
    def claim(document: dict[str, Any]) -> None:
        showcase = next(e for e in document["elements"] if e["id"] == "feature_showcase")
        showcase["basis"] = ["OBSERVED_COMMON"]

    copy.edit_yaml("common.yaml", claim)
    assert has(copy.check(), "element feature_showcase claims OBSERVED_COMMON")


def test_a_defect_list_that_disagrees_with_its_detector_is_reported(copy: Copy) -> None:
    def add(document: dict[str, Any]) -> None:
        defect = next(d for d in document["defect_classes"] if d["id"] == "DEF-01")
        defect["repositories"].append("aspose-words-foss/Aspose.Words-FOSS-for-Python")

    copy.edit_yaml("common.yaml", add)
    assert has(copy.check(), "DEF-01 lists aspose-words-foss/Aspose.Words-FOSS-for-Python")


def test_a_defect_that_omits_a_selected_repository_is_reported(copy: Copy) -> None:
    def drop(document: dict[str, Any]) -> None:
        defect = next(d for d in document["defect_classes"] if d["id"] == "DEF-13")
        defect["repositories"].pop()

    copy.edit_yaml("common.yaml", drop)
    assert has(copy.check(), "DEF-13 omits")


def test_a_placeholder_naming_an_unknown_observation_is_reported(copy: Copy) -> None:
    copy.edit_yaml(
        "common.yaml", lambda d: d["open_decisions"][0].update(question="see {obs:nothing_here}")
    )
    assert has(copy.check(), "{obs:nothing_here}")


def test_a_frequency_tag_that_disagrees_with_the_survey_is_reported(copy: Copy) -> None:
    copy.edit_document(r"\d+/\d+ \(obs:h1_exactly_one\)", "1/35 (obs:h1_exactly_one)")
    assert has(copy.check(), "but observation h1_exactly_one is 34/35")


def test_a_statistic_tag_that_disagrees_with_the_survey_is_reported(copy: Copy) -> None:
    copy.edit_document(r"\[stat:lines_max=[0-9.]+\]", "[stat:lines_max=99.0]")
    assert has(copy.check(), "but statistic lines_max is 4612")


def test_a_tag_naming_an_unknown_observation_is_reported(copy: Copy) -> None:
    copy.edit_document(r"## 8\. Maintaining", "A claim 1/2 (obs:made_up_id).\n\n## 8. Maintaining")
    assert has(copy.check(), "names an unknown observation")


def test_a_hand_edited_generated_table_is_reported(copy: Copy) -> None:
    copy.edit_document("Exactly three operations", "Exactly four operations")
    assert has(copy.check(), "generated block 'rules-prc' is stale")


def test_a_missing_generated_block_is_reported(copy: Copy) -> None:
    copy.edit_document(r"<!-- generated:axes -->.*?<!-- /generated:axes -->", "")
    assert has(copy.check(), "generated block 'axes' is missing")


def test_a_rule_identifier_in_the_document_without_a_definition_is_reported(copy: Copy) -> None:
    copy.edit_document(r"## 8\. Maintaining", "See STR-99.\n\n## 8. Maintaining")
    assert has(copy.check(), "STR-99 is named but not defined")


def test_a_rule_that_the_document_never_names_is_reported(copy: Copy) -> None:
    def add(document: dict[str, Any]) -> None:
        rule = dict(document["rules"][0])
        rule["id"] = "STR-98"
        document["rules"].append(rule)

    copy.edit_yaml("common.yaml", add)
    problems = copy.check()
    assert has(problems, "STR-98 is defined in common.yaml but never named") or has(
        problems, "generated block"
    )


def test_write_doc_repairs_a_stale_table_and_write_counts_repairs_a_count(copy: Copy) -> None:
    copy.edit_document("Exactly three operations", "Exactly four operations")

    def tamper(document: dict[str, Any]) -> None:
        document["observations"][0]["count"] = 0

    copy.edit_yaml("observations.yaml", tamper)
    assert copy.check() != []
    code = cp.main(
        [
            "--data-dir",
            str(copy.data),
            "--registry",
            str(copy.registry),
            "--document",
            str(copy.document),
            "--write-counts",
            "--write-doc",
        ]
    )
    assert code == 0
    assert copy.check() == []


# --- the closed predicate language ----------------------------------------------------------------


ROW = {
    "n": 5,
    "name": "alpha",
    "tags": ["x", "y"],
    "flag": True,
    "nested": {"deep": 3},
    "none": None,
}


@pytest.mark.parametrize(
    ("where", "expected"),
    [
        ({"n": 5}, True),
        ({"n": {"gte": 5}}, True),
        ({"n": {"gt": 5}}, False),
        ({"n": {"lte": 5, "gte": 1}}, True),
        ({"n": {"lt": 5}}, False),
        ({"tags": {"contains": "x"}}, True),
        ({"tags": {"contains": "z"}}, False),
        ({"name": {"startswith": "al"}}, True),
        ({"tags": {"nonempty": True}}, True),
        ({"tags": {"nonempty": False}}, False),
        ({"name": {"in": ["alpha", "beta"]}}, True),
        ({"name": {"not": "alpha"}}, False),
        ({"nested.deep": 3}, True),
        ({"nested.missing": {"gte": 1}}, False),
        ({"none": {"gt": 1}}, False),
        ({"flag": True, "n": 5}, True),
        ({"flag": True, "n": 6}, False),
        ({}, True),
    ],
)
def test_the_predicate_language(where: dict[str, Any], expected: bool) -> None:
    assert observations.matches(ROW, where) is expected


def test_an_unknown_operator_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown operator"):
        observations.matches(ROW, {"n": {"approximately": 5}})


def test_counts_use_only_readme_bearing_rows_and_the_among_filter() -> None:
    rows = {
        "a/a": {"readme": True, "x": 1},
        "b/b": {"readme": True, "x": 2},
        "c/c": {"readme": False},
    }
    assert observations.count_observation(rows, {"x": 1}) == (1, 2)
    assert observations.count_observation(rows, {"x": 2}, {"x": {"gte": 2}}) == (1, 1)
    assert observations.compute_statistic(rows, "x", "median") == 1.5
    assert observations.compute_statistic(rows, "x", "max") == 2.0
    assert observations.compute_statistic(rows, "missing", "min") is None


def test_size_classes_have_the_documented_edges() -> None:
    assert [cp.size_class(n) for n in (0, 1, 49, 50, 199, 200, 499, 500)] == [
        "none",
        "S",
        "S",
        "M",
        "M",
        "L",
        "L",
        "XL",
    ]


# --- the survey's measures are the defects' detectors --------------------------------------------

PYPI = (
    "[![PyPI](https://img.shields.io/pypi/v/aspose-demo-foss.svg)]"
    "(https://pypi.org/project/aspose-demo-foss/)"
)
LICENSE_BADGE = "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)"
BANNER = (
    "[![Aspose.Demo FOSS for Python]"
    "(https://products.aspose.org/media/demo/python/banner-readme.png)]"
    "(https://products.aspose.org/demo/python/)"
)
ENTERPRISE = (
    "These limitations don't apply to [Aspose.Demo for Python — Enterprise Edition]"
    "(https://products.aspose.com/demo/python/), which adds rendering."
)

GOOD = f"""# Aspose.Demo FOSS for Python

{PYPI}
{LICENSE_BADGE}

{BANNER}

Aspose.Demo FOSS for Python is a free, open-source library for demos. It reads and writes files.

## Navigation

- [At a Glance](#at-a-glance)
- [Installation](#installation)
- [Scope and Limitations](#scope-and-limitations)
- [License](#license)

## At a Glance

```mermaid
flowchart TD
  subgraph StartingPoints["Starting Points"]
    i1["A file"]
  end
  PRODUCT["Aspose.Demo FOSS for Python"]
  subgraph Capabilities["Core Capabilities"]
    c1["Read"]
  end
  subgraph Outputs["Outputs"]
    o1["A file"]
  end
```

## Installation

```bash
pip install "aspose-demo-foss>=1.0"
```

## Scope and Limitations

- Rendering is not implemented.

{ENTERPRISE}

## License

This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying,
modification, distribution, sublicensing, and commercial use, provided its copyright and
permission notice are retained. The software is provided without warranty.
"""


def measure(text: str, tree: Path | None = None) -> dict[str, Any]:
    return survey_features.features(text, tree)


def test_a_clean_readme_measures_clean() -> None:
    f = measure(GOOD)
    assert f["h1_count"] == 1
    assert f["h1_canonical"] is True
    assert f["second_h1"] is False
    assert f["unclosed_details"] is False
    assert f["fences_without_language"] == 0
    assert f["unquoted_pip_specifier"] is False
    assert f["badge_paragraphs"] == 1
    assert f["badge_kinds"] == ["package", "license"]
    assert f["badge_order_ok"] is True
    assert f["banner"] is True
    assert f["banner_links_to_aspose"] is True
    assert f["navigation"] is True
    assert f["navigation_missing_h2"] == []
    assert f["glance_form"] == "mermaid"
    assert f["glance_groups"] == ["Starting Points", "Core Capabilities", "Outputs"]
    assert f["enterprise_shape"] == "dont_apply"
    assert f["enterprise_closes_scope"] is True
    assert f["enterprise_mentions"] == 1
    assert f["license_prose"] is True
    assert f["license_permissions_sentence"] is True
    assert f["license_copyright_line"] is False
    assert f["aspose_links_total"] == 2
    assert f["install_registry_commands"] == ["pip"]


def test_a_second_h1_is_counted() -> None:
    f = measure(GOOD.replace("## Installation", "# Requires Python 3.11\n\n## Installation"))
    assert f["h1_count"] == 2
    assert f["second_h1"] is True


def test_unbalanced_details_are_counted_and_a_code_span_mention_is_not() -> None:
    f = measure(GOOD + "\n<details><summary>View more</summary>\n\ntext\n")
    assert f["unclosed_details"] is True
    mentioned = measure(GOOD + "\nThe `<details>` element is HTML.\n")
    assert mentioned["unclosed_details"] is False


def test_a_fence_without_a_language_is_counted() -> None:
    f = measure(GOOD + "\n```\nplain\n```\n")
    assert f["fences_without_language"] == 1


def test_an_unquoted_pip_specifier_is_found() -> None:
    unquoted = GOOD.replace(
        'pip install "aspose-demo-foss>=1.0"', "pip install aspose-demo-foss>=1.0"
    )
    assert measure(unquoted)["unquoted_pip_specifier"] is True


def test_badge_order_is_judged_against_the_owners_order() -> None:
    swapped = GOOD.replace(f"{PYPI}\n{LICENSE_BADGE}", f"{LICENSE_BADGE}\n{PYPI}")
    assert swapped != GOOD
    assert measure(swapped)["badge_order_ok"] is False


def test_enterprise_shapes_and_naming_are_classified() -> None:
    apply_only = GOOD.replace(
        "These limitations don't apply to [",
        "These limitations apply only to Aspose.Demo FOSS - they don't carry over to [",
    )
    assert measure(apply_only)["enterprise_shape"] == "apply_only"
    see_for = GOOD.replace("These limitations don't apply to [", "For rendering, see [")
    assert measure(see_for)["enterprise_shape"] == "see_for"
    commercial = GOOD + "\nThe commercial product adds more.\n"
    assert measure(commercial)["commercial_substitute_mentions"] == 1
    banned = GOOD + "\nSwitch to the paid version.\n"
    assert measure(banned)["banned_edition_names"] == 1


def test_a_missing_enterprise_paragraph_and_a_forum_link_are_counted() -> None:
    f = measure(
        GOOD.replace("Enterprise Edition", "Edition").replace(
            "https://products.aspose.com/demo/python/)", "https://forum.aspose.com/c/demo/1)"
        )
    )
    assert f["enterprise_mentions"] == 0
    assert f["forum_links"] == 1


def test_stock_api_descriptions_and_a_count_mismatch_are_found() -> None:
    api = (
        "\n## API Reference\n\nThe library has 5 public types.\n\n"
        "<details><summary>View</summary>\n\n"
        "| Class | Description |\n|---|---|\n"
        + "".join(f"| `T{i}` | Class with {i} methods. |\n" for i in range(3))
        + "| `Real` | Reads a file. |\n\n</details>\n"
    )
    f = measure(GOOD.replace("## License", api + "\n## License"))
    assert f["api_rows"] == 4
    assert f["api_boilerplate_rows"] == 3
    assert f["api_claimed_type_counts"] == [5]
    assert f["api_count_mismatch"] is True
    assert f["api_in_details"] is True


def test_an_image_only_at_a_glance_is_recognised() -> None:
    image = GOOD.replace(
        GOOD[GOOD.index("```mermaid") : GOOD.index("## Installation")],
        "![At a glance](docs/glance.png)\n\n",
    )
    assert measure(image)["glance_form"] == "image"


def test_dead_relative_links_need_a_tree_and_an_ellipsis_is_not_a_link(tmp_path: Path) -> None:
    text = GOOD + "\nSee [notes](docs/NOTES.md) and [x](…) and [ok](LICENSE).\n"
    assert measure(text)["dead_relative_links"] is None
    (tmp_path / "LICENSE").write_text("MIT", "utf-8")
    assert measure(text, tmp_path)["dead_relative_links"] == ["docs/NOTES.md"]


def test_absolute_links_to_the_repository_itself_are_counted() -> None:
    text = GOOD + "\n[LICENSE](https://github.com/o/r/blob/main/LICENSE)\n"
    assert measure(text)["absolute_self_blob_links"] == 1


def test_sentence_length_and_voice_are_measured_on_visible_prose() -> None:
    f = measure(
        GOOD + "\nWe think you will like it, and our team agrees with that statement fully.\n"
    )
    assert f["first_person_words"] >= 2
    assert f["second_person_words"] == 1
    assert f["sentence_mean"] is not None
    assert f["emoji"] == 0
    assert measure(GOOD + "\nIt works ✅ well in practice for everyone here.\n")["emoji"] == 1


def test_visible_lines_follow_the_renderers_definition() -> None:
    text = (
        "# T\n\nintro\n\n<details>\n<summary>x</summary>\n\nhidden\nhidden\n\n</details>\n\nafter\n"
    )
    # '# T', blank, 'intro', blank, then the blank and 'after' once the block has closed; the tag
    # lines and everything between them do not count
    assert survey_features.features(text)["visible_lines"] == 6


def test_slug_matches_the_hosts_anchors() -> None:
    assert survey_features.slug("Documentation & Resources") == "documentation--resources"
    assert survey_features.slug("At a Glance") == "at-a-glance"


# --- rendering and the survey builder -------------------------------------------------------------


def test_short_names_read_family_and_platform() -> None:
    assert render_tables.short_name("aspose-cells-foss/Aspose.Cells-FOSS-for-.NET") == "Cells .NET"
    assert render_tables.short_name("aspose-pdf-foss/Aspose-PDF-FOSS-for-Go") == "PDF Go"
    assert render_tables.short_name("aspose-gis-foss/Aspose.GIS.FOSS-for-.Net") == "GIS .Net"


def test_table_cells_escape_pipes_and_stray_angle_brackets_but_not_code_spans() -> None:
    cell = render_tables._cell
    assert cell("a | b") == "a \\| b"
    assert cell("Aspose.<Family> for <Platform>") == "Aspose.&lt;Family&gt; for &lt;Platform&gt;"
    assert cell("`<details>` and <b>") == "`<details>` and &lt;b&gt;"
    assert cell("x" + render_tables.LINE_BREAK + "y") == "x<br>y"


def test_blocks_round_trip_through_the_document() -> None:
    text = "intro\n<!-- generated:a -->\nold\n<!-- /generated:a -->\nouter\n"
    assert render_tables.extract_blocks(text) == {"a": "old"}
    updated = render_tables.apply_blocks(text, {"a": "new\nlines"})
    assert render_tables.extract_blocks(updated) == {"a": "new\nlines"}
    assert updated.startswith("intro\n") and updated.endswith("outer\n")
    assert render_tables.apply_blocks(text, {"other": "x"}) == text


def _git(directory: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(directory), "-c", "user.email=t@example.org", "-c", "user.name=t", *args],
        check=True,
        capture_output=True,
    )


def test_the_survey_builder_reads_the_committed_blob_and_marks_a_missing_readme(
    tmp_path: Path,
) -> None:
    with_readme = tmp_path / "Aspose.Demo-FOSS-for-Python"
    with_readme.mkdir()
    _git(with_readme, "init", "-q")
    (with_readme / "README.md").write_bytes(GOOD.encode("utf-8"))
    (with_readme / "LICENSE").write_text("MIT", "utf-8")
    _git(with_readme, "add", "-A")
    _git(with_readme, "commit", "-q", "-m", "init")
    without = tmp_path / "x_Aspose.Bare-FOSS-for-Python"
    without.mkdir()
    _git(without, "init", "-q")
    (without / "other.txt").write_text("x", "utf-8")
    _git(without, "add", "-A")
    _git(without, "commit", "-q", "-m", "init")
    registry = tmp_path / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "entries": [
                    {"repository": "o/Aspose.Demo-FOSS-for-Python"},
                    {"repository": "x/Aspose.Bare-FOSS-for-Python"},
                ]
            }
        ),
        "utf-8",
    )
    survey = build_survey.build(tmp_path, registry, "2026-10-11")
    rows = survey["rows"]
    assert survey["captured"] == "2026-10-11"
    assert rows["o/Aspose.Demo-FOSS-for-Python"]["readme"] is True
    assert len(rows["o/Aspose.Demo-FOSS-for-Python"]["readme_sha256"]) == 64
    assert rows["o/Aspose.Demo-FOSS-for-Python"]["dead_relative_links"] == []
    assert rows["x/Aspose.Bare-FOSS-for-Python"]["readme"] is False
    assert len(rows["x/Aspose.Bare-FOSS-for-Python"]["head"]) >= 7


def test_the_survey_builder_names_a_registry_repository_it_cannot_find(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"entries": [{"repository": "o/Missing"}]}), "utf-8")
    with pytest.raises(SystemExit, match="no clone of o/Missing"):
        build_survey.build(tmp_path, registry, "2026-10-11")
