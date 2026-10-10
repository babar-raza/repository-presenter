"""Tests for the coverage-inventory matching helpers and unit extractors (TC-COV-01).

Run directly, like tools/reviewer/test_reconcile.py (outside pyproject's `testpaths`, so never part
of `pytest tests/`):  python -m pytest tools/reviewer/coverage_inventory/test_matching.py

The fixture clone under fixtures/clone is a tiny invented repository, not a real one; the sealed
README and facts texts are inline strings.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import inventory  # noqa: E402
from matching import (MISSING, PRESENT_IN_FACTS, PRESENT_IN_README, Corpus, Unit, body_is_material,  # noqa: E402
                      find_hit, norm_heading, overlap, split_sections, status_of, tokens, version_pattern)

CLONE = HERE / "fixtures" / "clone"


def units_by_type():
    units, meta = inventory.inventory(CLONE, {"tag_name": "v1.2.0", "published_at": "2026-10-01T00:00:00Z",
                                              "body": "Added the layout engine and widget renderer improvements."})
    out = {}
    for u in units:
        out.setdefault(u.unit_type, []).append(u)
    return out, meta


# --- normalisation -------------------------------------------------------------------------

def test_norm_heading_strips_markup_emoji_and_case():
    assert norm_heading("## **Quick Start** :rocket: ##") == "quick start rocket"
    assert norm_heading("### [Install](#install) 🚀") == "install"
    assert norm_heading("What it can do!") == norm_heading("what it can do")


def test_tokens_drop_stopwords_and_short_words_and_keep_versions():
    t = tokens("The layout engine is used with Python 3.10 and ab")
    assert {"layout", "engine", "python", "3.10"} <= t
    assert "the" not in t and "ab" not in t


def test_overlap_is_containment_and_ignores_tiny_units():
    unit = tokens("layout engine arranges widgets")
    assert overlap(unit, tokens("the layout engine arranges many widgets and more")) == 1.0
    assert overlap(unit, tokens("unrelated text about databases")) == 0.0
    assert overlap(tokens("ab cd"), tokens("ab cd")) == 0.0  # below MIN_BODY_TOKENS


def test_split_sections_respects_fences():
    md = "# A\ntext\n```\n# not a heading\n```\n## B\nmore\n"
    assert [h for h, _ in split_sections(md)] == ["A", "B"]


def test_body_is_material_rejects_badge_only_and_bare_url_bodies():
    assert not body_is_material("![b](https://img.shields.io/x)\n")
    assert not body_is_material("https://example.com/a https://example.com/b")
    assert body_is_material("Create a widget and render it with the layout engine.")


# --- corpus search --------------------------------------------------------------------------

def test_has_path_needs_the_whole_path_not_a_word():
    c = Corpus("c", "See [guide](docs/guide.md) and the tests/ folder. docs only")
    assert c.has_path("docs/guide.md")
    assert c.has_path("tests/")
    assert not c.has_path("docs/")  # trailing-slash form is not in the text
    assert not c.has_path("guide.mdx")


def test_has_cli_requires_command_use_in_code_not_the_package_name():
    c = Corpus("c", "Install with `pip install widget-kit`.\n\n```bash\nwidget-cli convert a b\n```\n")
    assert c.has_cli("widget-cli")
    assert not c.has_cli("widget-kit")  # only appears after `pip install`
    assert not Corpus("c", "Use the widget-cli tool in prose only.").has_cli("widget-cli")


def test_has_command_allows_flags_between_tool_and_verb():
    c = Corpus("c", "```\nmvn -B -q verify\n```")
    assert c.has_command(["mvn", "verify"])
    assert not c.has_command(["mvn", "test"])
    assert Corpus("c", "run ./gradlew build").has_command(["gradle", "build"])  # wrapper prefix


# --- find_hit methods -------------------------------------------------------------------------

def test_find_hit_path_then_basename_for_file_units():
    u = Unit("contributing", "docs/CONTRIBUTING.md", path="docs/CONTRIBUTING.md")
    assert find_hit(u, Corpus("c", "[how](docs/CONTRIBUTING.md)"))[0] == "path"
    assert find_hit(u, Corpus("c", "[how](CONTRIBUTING.md)"))[0] == "basename"
    assert find_hit(u, Corpus("c", "nothing here")) is None


def test_find_hit_never_matches_a_manifest_path_for_a_cli_or_framework_unit():
    u = Unit("cli_entry", "tool", path="pyproject.toml", names=["tool"], use_basename=False)
    assert find_hit(u, Corpus("c", "pyproject.toml lists things")) is None


def test_find_hit_matrix_values_with_os_alternates_and_ranges():
    os_unit = Unit("ci_matrix", "os", values=["ubuntu|linux", "windows|win32"], use_basename=False)
    assert find_hit(os_unit, Corpus("c", "Runs on Linux and Windows."))[0] == "values"
    assert find_hit(os_unit, Corpus("c", "Runs on Linux only.")) is None
    py = Unit("ci_matrix", "python-version", values=["3.10", "3.11", "3.12", "3.13"], use_basename=False)
    assert find_hit(py, Corpus("c", "Tested on Python 3.10 through 3.13"))[0] == "values_range"
    assert find_hit(py, Corpus("c", "Tested on Python 3.10"))is None


def test_find_hit_pointer_dir_needs_the_slash_form():
    u = Unit("doc_page", "docs/a.md", path="docs/a.md", pointer_dirs=["docs"])
    assert find_hit(u, Corpus("c", "see docs/ for more"))[0] == "dir_pointer"
    assert find_hit(u, Corpus("c", "read the docs online")) is None


def test_find_hit_readme_unit_heading_plus_overlap_vs_overlap_only():
    live = "## Quick start\n\nCreate a widget and render it with the render pipeline and layout engine.\n"
    (h, body), = split_sections(live)
    u = Unit("readme_unit", h, heading=norm_heading(h), body_tokens=tokens(h + " " + body))
    sealed = Corpus("s", "## Quick Start\n\nCreate a widget, render it with the render pipeline.\n\n## Other\n\nx y z\n", chunked=True)
    assert find_hit(u, sealed)[0] == "heading+overlap"
    moved = Corpus("s", "## Usage\n\nCreate a widget and render it with the render pipeline and layout engine today.\n", chunked=True)
    assert find_hit(u, moved)[0] == "content_overlap"
    other = Corpus("s", "## Usage\n\nA database migration guide for operators.\n", chunked=True)
    assert find_hit(u, other) is None


def test_chunked_overlap_does_not_credit_words_scattered_across_a_big_document():
    unit = Unit("readme_unit", "x", body_tokens=tokens("alpha bravo charlie delta echo foxtrot"))
    scattered = ("## One\n\nalpha bravo\n\n## Two\n\nunrelated filler words\n\n## Three\n\ncharlie delta\n\n"
                 "## Four\n\nmore filler words\n\n## Five\n\necho foxtrot\n")
    assert find_hit(unit, Corpus("s", scattered, chunked=True)) is None  # no section or adjacent pair holds 60%
    assert find_hit(unit, Corpus("s", scattered)) is not None  # the whole-text measure would have credited it


def test_status_precedence():
    assert status_of(("name", 1.0), ("name", 1.0)) == PRESENT_IN_README
    assert status_of(None, ("path", 1.0)) == PRESENT_IN_FACTS
    assert status_of(None, None) == MISSING


def test_version_pattern_recognises_prose_forms():
    assert any(Corpus("c", ".NET 8 is required").has_regex(p) for p in version_pattern("dotnet", "net8.0"))
    assert not any(Corpus("c", "uses net6.0 only").has_regex(p) for p in version_pattern("dotnet", "net8.0"))
    assert any(Corpus("c", "requires Java 21 or newer").has_regex(p) for p in version_pattern("java", "21"))
    assert any(Corpus("c", "Python >=3.10").has_regex(p) for p in version_pattern("python", "3.10"))
    assert not any(Corpus("c", "Python 3.100").has_regex(p) for p in version_pattern("python", "3.10"))


# --- command reduction ------------------------------------------------------------------------

def test_command_key_reduces_to_tool_and_verb():
    assert inventory.command_key("dotnet test src/Lib -c Release") == ("test", ["dotnet", "test"])
    assert inventory.command_key("mvn -B -q verify -Dgpg.skip=true") == ("test", ["mvn", "verify"])
    assert inventory.command_key("npm run build --if-present") == ("build", ["npm", "build"])
    assert inventory.command_key("sudo env FOO=1 go test ./...") == ("test", ["go", "test"])
    assert inventory.command_key("python -m pytest -q") == ("test", ["pytest"])
    assert inventory.command_key("pip install -e .") is None
    assert inventory.command_key("echo build") is None


# --- unit extraction on the fixture clone -------------------------------------------------------

def test_readme_units_skip_badge_only_sections_and_title():
    by, _ = units_by_type()
    assert [u.name for u in by["readme_unit"]] == ["Installation", "Quick start", "Command line"]


def test_community_changelog_license_and_doc_units():
    by, _ = units_by_type()
    assert [u.name for u in by["contributing"]] == ["CONTRIBUTING.md"]  # CONTRIBUTORS.md is not a contributing guide
    assert [u.name for u in by["security_policy"]] == ["SECURITY.md"]
    assert [u.name for u in by["changelog"]] == ["CHANGELOG.md"]
    assert [u.name for u in by["doc_page"]] == ["docs/guide.md"]
    assert [u.name for u in by["root_doc"]] == ["CONTRIBUTORS.md"]
    assert [u.name for u in by["license_notice"]] == ["LICENSE"]
    assert by["doc_page"][0].pointer_dirs == ["docs"]


def test_github_release_unit_carries_the_body_and_a_releases_link_pattern():
    by, _ = units_by_type()
    (rel,) = by["github_release"]
    assert find_hit(rel, Corpus("c", "See https://github.com/o/r/releases for notes"))[0] == "pattern"
    assert find_hit(rel, Corpus("c", "unrelated")) is None


def test_cli_units_exclude_samples_and_example_dirs():
    by, _ = units_by_type()
    assert sorted(u.name for u in by["cli_entry"]) == ["Cli", "widget-cli", "widget-tool"]  # not sample_basic, not _examples/demo


def test_framework_units_union_projects_but_skip_the_cli_free_tests():
    by, _ = units_by_type()
    names = sorted(u.name for u in by["target_framework"])
    assert names == ["requires-python >=3.10", "rust edition 2021", "target framework net10.0",
                     "target framework net8.0", "target framework netstandard2.0"]


def test_matrix_units_keep_platform_axes_and_drop_incidental_ones():
    by, _ = units_by_type()
    names = sorted(u.name for u in by["ci_matrix"])
    assert names == ["os: ubuntu, windows", "python-version: 3.10, 3.11, 3.12"]  # `archive` is not a platform axis
    os_unit = next(u for u in by["ci_matrix"] if u.name.startswith("os"))
    assert os_unit.values == ["ubuntu|linux", "windows|win32"]


def test_example_and_test_units():
    by, _ = units_by_type()
    assert [u.name for u in by["example_file"]] == ["_examples/demo/main.go", "examples/basic.py"]
    assert [(u.name, u.size) for u in by["test_suite"]] == [("tests", 2)]


def test_command_units_merge_ci_and_convention_sources():
    by, _ = units_by_type()
    assert sorted(u.name for u in by["test_command"]) == ["cargo test", "dotnet test", "pytest"]
    assert sorted(u.name for u in by["build_command"]) == ["cargo build", "dotnet build"]
    pytest_unit = next(u for u in by["test_command"] if u.name == "pytest")
    assert "ci:.github/workflows/ci.yml" in pytest_unit.detail
