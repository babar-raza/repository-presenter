"""The idempotence harness's measures, held to known answers (tools/idempotence, TC-IDM-01).

Each measure is run on a README written to have one known property and on a deliberately broken
variant, so a measure that stopped seeing loss (or invented it) fails here before it is trusted to
judge a lane. The corpus file is checked against its checksums and against the survey it must agree
with; the bundle report is run on synthetic bundle directories. Offline: no network, no model.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from tools.idempotence import corpus, report
from tools.idempotence.atoms import atomise, mermaid_line_numbers, norm, toks
from tools.idempotence.editscript import edit_script
from tools.idempotence.introduced import fact_texts, introduced_text
from tools.idempotence.retention import (
    LOST,
    REWORDED,
    VERBATIM,
    covered_lines,
    line_retention,
    retention,
)

from repository_presenter.components.readme.composition.renderer import render_patch
from support import REPO_ROOT

LIVE = """\
# Aspose.Demo FOSS for Python

[![PyPI](https://img.shields.io/pypi/v/aspose-demo.svg)](https://pypi.org/project/aspose-demo/)

Aspose.Demo FOSS for Python reads and writes demo files without any native dependency.
It runs on Python 3.10 and later. See [the guide](docs/guide.md) for details.

## Key Capabilities

- Read demo files from disk or from a stream with one call
- Write demo files with every option the format allows
- Convert between demo and plain text formats

## Installation

```bash
pip install aspose-demo==1.2.3
```

![Architecture](docs/arch.png)

## At a Glance

```mermaid
flowchart TD
  a --> b
```

## License

MIT License. See [LICENSE](LICENSE) for the full text.
"""


def _without(text: str, needle: str) -> str:
    assert needle in text
    return text.replace(needle, "", 1)


# --- the cut ----------------------------------------------------------------------------------


def test_the_cut_finds_every_kind_of_atom_with_its_position_and_section() -> None:
    atoms = atomise(LIVE)
    assert [a.text for a in atoms.headings if a.info == "1"] == ["Aspose.Demo FOSS for Python"]
    assert [a.key for a in atoms.headings if a.info == "2"] == [
        "key capabilities",
        "installation",
        "at a glance",
        "license",
    ]
    first = atoms.sentences[0]
    assert first.line == 5 and first.section == "Aspose.Demo FOSS for Python"
    assert first.text.startswith("Aspose.Demo FOSS")
    items = {a.line: a for a in atoms.items}
    assert sorted(items) == [10, 11, 12] and items[10].section == "Key Capabilities"
    assert [a.info for a in atoms.code] == ["bash", "mermaid"]
    assert {a.info for a in atoms.links} == {
        "https://pypi.org/project/aspose-demo/",
        "docs/guide.md",
        "LICENSE",
    }
    assert [a.info for a in atoms.images] == [
        "https://img.shields.io/pypi/v/aspose-demo.svg",
        "docs/arch.png",
    ]


def test_a_fragment_is_not_a_claim() -> None:
    atoms = atomise(
        "## Title\n\n- Python 3.10+\n- Reads files quickly and safely on every platform\n\nShort.\n"
    )
    assert [a.text for a in atoms.items] == ["Reads files quickly and safely on every platform"]
    assert atoms.sentences == []


def test_comparison_keys_ignore_presentation_but_not_words() -> None:
    assert norm("The **`Scene`** class, see [docs](x).") == norm("the scene class, see docs")
    assert toks("It reads files and the writer") == frozenset({"it", "reads", "files", "writer"})


def test_the_diagram_lines_are_the_body_of_a_mermaid_fence_only() -> None:
    assert mermaid_line_numbers(LIVE) == {25, 26}
    assert mermaid_line_numbers("```python\nx = 1\n```\n") == set()


# --- retention (a) ----------------------------------------------------------------------------


def test_a_candidate_equal_to_the_live_readme_loses_nothing() -> None:
    report_ = retention(LIVE, LIVE)
    assert report_.lost_items() == []
    assert report_.prose.verbatim_share == 1.0 and report_.lines.share == 1.0
    assert report_.lines.lost == []


def test_a_dropped_item_is_lost_and_listed_with_its_line() -> None:
    candidate = _without(LIVE, "- Convert between demo and plain text formats\n")
    report_ = retention(LIVE, candidate)
    (lost,) = report_.categories["item"].lost
    assert lost.line == 12 and lost.section == "Key Capabilities"
    assert report_.categories["item"].counts[VERBATIM] == 2
    assert [(ln.number, ln.text) for ln in report_.lines.lost] == [
        (12, "- Convert between demo and plain text formats")
    ]


def test_a_reworded_sentence_is_kept_but_not_verbatim() -> None:
    candidate = LIVE.replace(
        "It runs on Python 3.10 and later.", "Python 3.10 and later is what it runs on."
    )
    report_ = retention(LIVE, candidate)
    assert report_.categories["sentence"].counts[REWORDED] == 1
    assert report_.categories["sentence"].counts[LOST] == 0
    assert report_.prose.verbatim < report_.prose.kept


def test_a_rewritten_sentence_is_lost() -> None:
    candidate = LIVE.replace(
        "It runs on Python 3.10 and later.", "Enterprise customers value long term support."
    )
    report_ = retention(LIVE, candidate)
    assert [a.text for a in report_.categories["sentence"].lost] == [
        "It runs on Python 3.10 and later."
    ]


def test_links_images_code_and_headings_are_each_counted() -> None:
    candidate = (
        LIVE.replace("[the guide](docs/guide.md)", "the guide")
        .replace("![Architecture](docs/arch.png)\n", "")
        .replace("pip install aspose-demo==1.2.3", "pip install aspose-demo==9.9.9 --pre")
        .replace("## License", "## Licence")
    )
    report_ = retention(LIVE, candidate)
    assert [a.info for a in report_.categories["link"].lost] == ["docs/guide.md"]
    assert [a.info for a in report_.categories["image"].lost] == ["docs/arch.png"]
    assert report_.categories["code"].counts[REWORDED] == 1  # a near-copy is not a lost block
    assert [a.text for a in report_.categories["heading"].lost] == ["License"]
    positions = {(a.kind, a.line) for a in report_.lost_items()}
    assert ("link", 6) in positions and ("image", 20) in positions and ("heading", 29) in positions


def test_a_heading_at_another_level_is_reworded_not_lost() -> None:
    report_ = retention(LIVE, LIVE.replace("## License", "### License"))
    assert report_.categories["heading"].counts[REWORDED] == 1
    assert report_.categories["heading"].counts[LOST] == 0


def test_an_unrelated_candidate_loses_every_prose_atom() -> None:
    other = "# Other\n\nSomething entirely different is written here about pottery.\n"
    report_ = retention(LIVE, other)
    assert report_.prose.kept == 0 and report_.prose.kept_share == 0.0
    assert report_.lines.share < 0.2


# --- line retention and the enumerated edits --------------------------------------------------


def test_a_line_an_enumerated_edit_covers_may_change_but_no_other() -> None:
    start = LIVE.index("1.2.3")
    candidate = LIVE.replace("1.2.3", "2.0.0")
    covered = line_retention(LIVE, candidate, [(start, start + 5)])
    assert covered.lost == [] and covered.allowed == 1 and covered.share == 1.0
    uncovered = line_retention(LIVE, candidate)
    assert [ln.number for ln in uncovered.lost] == [17]


def test_a_lost_line_outside_every_edit_is_reported_even_when_another_line_was_edited() -> None:
    start = LIVE.index("1.2.3")
    candidate = _without(
        LIVE.replace("1.2.3", "2.0.0"), "MIT License. See [LICENSE](LICENSE) for the full text.\n"
    )
    result = line_retention(LIVE, candidate, [(start, start + 5)])
    assert [ln.text for ln in result.lost] == [
        "MIT License. See [LICENSE](LICENSE) for the full text."
    ]
    assert result.share < 1.0


def test_the_diagram_body_is_not_held_to_retention() -> None:
    candidate = LIVE.replace("  a --> b\n", "  a --> b\n  b --> c\n").replace(
        "flowchart TD", "flowchart LR"
    )
    result = line_retention(LIVE, candidate)
    assert result.lost == [] and result.diagram == 2


def test_a_pure_insertion_at_a_line_boundary_covers_no_line() -> None:
    at = LIVE.index("## License")
    assert covered_lines(LIVE, [(at, at)]) == set()
    assert covered_lines(LIVE, [(at + 3, at + 3)]) == {29}  # inside a line: it is no longer whole
    assert covered_lines(LIVE, [(at, at + 10)]) == {29}


# --- the edit script (b) ----------------------------------------------------------------------


def test_identical_readmes_have_an_empty_edit_script() -> None:
    script = edit_script(LIVE, LIVE)
    assert script.identical and script.hunks == 0 and script.changed_lines == 0


def test_one_changed_line_is_one_hunk_one_removed_one_added() -> None:
    script = edit_script(LIVE, LIVE.replace("1.2.3", "2.0.0"))
    assert (script.hunks, script.runs, script.removed, script.added) == (1, 1, 1, 1)


def test_distant_changes_are_separate_hunks_and_near_ones_merge() -> None:
    far = LIVE.replace("1.2.3", "2.0.0").replace("MIT License.", "BSD License.")
    near = LIVE.replace("1.2.3", "2.0.0").replace("pip install", "python -m pip install")
    assert (edit_script(LIVE, far).hunks, edit_script(LIVE, far).runs) == (2, 2)
    assert edit_script(LIVE, near).hunks == 1 and edit_script(LIVE, near).runs == 1
    distant_pair = LIVE.replace("flowchart TD", "flowchart LR").replace(
        "MIT License.", "BSD License."
    )
    assert edit_script(LIVE, distant_pair).hunks == 1  # three lines of context reach: one hunk


def test_a_rewrite_is_many_runs() -> None:
    rewritten = "\n".join(f"line {n} of a different document" if n % 2 else "" for n in range(60))
    assert edit_script(LIVE, rewritten).runs > 5


# --- introduced text (c) ----------------------------------------------------------------------


FACTS = [
    {"kind": "install_command", "value": "pip install aspose-demo==1.2.3"},
    {"kind": "package", "value": "aspose-demo", "attributes": {"ecosystem": "python"}},
    {"kind": "inherited_unit", "value": "Marketing text about nothing the facts hold."},
]


def test_text_in_the_live_readme_or_the_facts_is_not_introduced() -> None:
    candidate = (
        "Aspose.Demo FOSS for Python reads and writes demo files without any native dependency.\n\n"
        "Install with pip install aspose-demo==1.2.3 for python.\n"
    )
    result = introduced_text(LIVE, candidate, fact_texts(FACTS))
    assert result.total == 2 and result.from_live == 1 and result.from_facts == 1
    assert result.introduced == []


def test_a_new_claim_is_introduced_and_flagged_when_an_authored_unit_wrote_it() -> None:
    claim = "This library is ideal for enterprise teams who need unmatched performance."
    candidate = f"{claim}\n"
    plain = introduced_text(LIVE, candidate, fact_texts(FACTS))
    assert [i.atom.text for i in plain.introduced] == [claim] and plain.introduced[0].llm is None
    assert plain.llm_share is None
    flagged = introduced_text(LIVE, candidate, fact_texts(FACTS), authored=[claim])
    assert flagged.introduced[0].llm is True and flagged.llm_share == 1.0
    other = introduced_text(
        LIVE, candidate, fact_texts(FACTS), authored=["Something else entirely."]
    )
    assert other.introduced[0].llm is False and other.llm_share == 0.0


def test_an_inherited_unit_fact_is_the_live_readme_not_a_second_source() -> None:
    claim = "Marketing text about nothing the facts hold."
    result = introduced_text("# T\n", claim, fact_texts(FACTS))
    assert [i.atom.text for i in result.introduced] == [claim]


# --- the corpus -------------------------------------------------------------------------------


def test_the_committed_corpus_checks_out_and_agrees_with_the_survey() -> None:
    entries = corpus.load()
    survey = json.loads((REPO_ROOT / "data" / "readme_standard" / "survey.json").read_text("utf-8"))
    for repository, entry in entries.items():
        row = survey["rows"][repository]
        assert (entry.head, entry.sha256) == (row["head"], row["readme_sha256"]), repository


def test_the_corpus_has_a_row_for_every_registry_repository() -> None:
    registered = {
        e["repository"]
        for e in json.loads((REPO_ROOT / "data" / "registry.json").read_text("utf-8"))["entries"]
    }
    document = json.loads(corpus.DEFAULT_CORPUS.read_text("utf-8"))
    assert set(document["rows"]) == registered
    without = sorted(r for r, row in document["rows"].items() if not row["readme"])
    assert without == [
        "aspose-gis-foss/Aspose.GIS.FOSS-for-.Net"
    ]  # the one repository with no README
    assert len(corpus.load()) == len(registered) - len(without)


def test_a_changed_byte_in_the_corpus_is_caught_by_its_checksum() -> None:
    document = json.loads(corpus.DEFAULT_CORPUS.read_text("utf-8"))
    repository = sorted(r for r, row in document["rows"].items() if row["readme"])[0]
    document["rows"][repository]["text"] += " "
    with pytest.raises(corpus.CorpusError, match="does not match its recorded SHA-256"):
        corpus.parse(document)
    with pytest.raises(corpus.CorpusError, match="schema version 1"):
        corpus.parse({"schema_version": 2, "rows": {}})


def _git(directory: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(directory), "-c", "user.email=t@example.org", "-c", "user.name=t", *args],
        check=True,
        capture_output=True,
    )


def test_the_corpus_builder_freezes_the_committed_blob_exactly(tmp_path: Path) -> None:
    clone = tmp_path / "o_Aspose.Demo-FOSS-for-Python"
    clone.mkdir()
    _git(clone, "init", "-q")
    text = "# Demo\r\n\r\nWindows line endings stay.  \r\nUnicode: café.\r\n"
    (clone / "README.md").write_bytes(text.encode("utf-8"))
    _git(clone, "add", "-A")
    _git(clone, "-c", "core.autocrlf=false", "commit", "-q", "-m", "init")
    bare = tmp_path / "x_Aspose.Bare-FOSS-for-Python"
    bare.mkdir()
    _git(bare, "init", "-q")
    (bare / "other.txt").write_text("x", "utf-8")
    _git(bare, "add", "-A")
    _git(bare, "commit", "-q", "-m", "init")
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
    document = corpus.build(tmp_path, registry, "2026-10-12")
    out = tmp_path / "data" / "corpus.json"
    corpus.write(document, out)
    assert "\r" not in out.read_text("utf-8")  # carriage returns are escaped in the JSON, not raw
    loaded = corpus.load(out)
    assert list(loaded) == ["o/Aspose.Demo-FOSS-for-Python"]
    assert loaded["o/Aspose.Demo-FOSS-for-Python"].text == text
    assert document["rows"]["x/Aspose.Bare-FOSS-for-Python"]["readme"] is False
    with pytest.raises(SystemExit, match="no clone of o/Missing"):
        registry.write_text(json.dumps({"entries": [{"repository": "o/Missing"}]}), "utf-8")
        corpus.build(tmp_path, registry, "2026-10-12")


# --- the bundle report ------------------------------------------------------------------------


INTRODUCED = "Aspose.Demo is a library enabling developers to work with demo files in many ways."
CANDIDATE = LIVE.replace(
    "Aspose.Demo FOSS for Python reads and writes demo files without any native dependency.",
    "Aspose.Demo is a library enabling developers to work with demo files in many ways.",
).replace("- Write demo files with every option the format allows\n", "")


def _bundle(root: Path, slug: str, revision: str, **files: str) -> Path:
    directory = root / slug / revision
    directory.mkdir(parents=True)
    for name, content in files.items():
        target = directory / name.replace("__", "/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    return directory


def test_the_report_recovers_the_live_readme_from_the_sealed_patch_and_measures_the_candidate(
    tmp_path: Path,
) -> None:
    revision = "a" * 40
    _bundle(
        tmp_path / "candidates",
        "o__Aspose.Demo-FOSS-for-Python",
        revision,
        **{
            "README.md": CANDIDATE,
            "README.patch": render_patch(LIVE, CANDIDATE),
            "manifest.json": json.dumps({"sealed_at": "2026-10-12T00:00:00Z"}),
            "content_units.json": json.dumps({"units": [{"text": INTRODUCED}]}),
            "facts.json": json.dumps({"facts": FACTS}),
        },
    )
    bundles = report.discover([tmp_path])
    (row,) = report.measure_all(bundles)
    assert (
        row.bundle.live == LIVE
        and row.bundle.live_source == "patch"
        and row.bundle.kind == "sealed"
    )
    assert row.retention is not None and row.introduced is not None and row.script is not None
    assert row.retention.categories["item"].counts[LOST] == 1
    assert row.retention.categories["sentence"].counts[LOST] == 1
    assert [i.atom.text for i in row.introduced.introduced] == [
        "Aspose.Demo is a library enabling developers to work with demo files in many ways."
    ]
    assert row.introduced.introduced[0].llm is True
    assert (row.script.hunks, row.script.runs) == (1, 2)  # the two changes sit within one hunk
    table = report.render_table([row])
    assert "o/Aspose.Demo-FOSS-for-Python" in table and "aaaaaaaa" in table
    assert "Pooled over 1 bundles" in table
    assert report.rows_json([row])[0]["categories"]["item"]["lost"][0]["line"] == 11


def test_the_report_falls_back_to_a_draft_source_then_the_corpus_then_git(tmp_path: Path) -> None:
    draft = _bundle(
        tmp_path / "runs" / "transactions",
        "o__Aspose.Demo-FOSS-for-Python",
        "b" * 40,
        **{"README.md": CANDIDATE, "source__README.md": LIVE},
    )
    (bundle,) = report.discover([tmp_path])
    assert bundle.kind == "draft" and bundle.live == LIVE and bundle.live_source == "source"

    revision = "c" * 40
    orphan = _bundle(
        tmp_path / "candidates",
        "o__Aspose.Demo-FOSS-for-Python",
        revision,
        **{"README.md": CANDIDATE},
    )
    entry = corpus.Entry("o/Aspose.Demo-FOSS-for-Python", revision, LIVE, corpus.digest(LIVE))
    from_corpus = report.load_bundle(orphan, None, {entry.repository: entry})
    assert (
        from_corpus is not None and from_corpus.live_source == "corpus" and from_corpus.live == LIVE
    )

    clone = tmp_path / "clones" / "Aspose.Demo-FOSS-for-Python"
    clone.mkdir(parents=True)
    _git(clone, "init", "-q")
    (clone / "README.md").write_text(LIVE, "utf-8", newline="\n")
    _git(clone, "add", "-A")
    _git(clone, "commit", "-q", "-m", "init")
    head = subprocess.run(
        ["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    unknown = _bundle(
        tmp_path / "candidates", "o__Aspose.Demo-FOSS-for-Python", head, **{"README.md": CANDIDATE}
    )
    from_git = report.load_bundle(unknown, None, None, [tmp_path / "clones"])
    assert from_git is not None and from_git.live_source == "git" and from_git.live == LIVE
    assert draft.is_dir()


def test_a_bundle_whose_live_readme_cannot_be_found_is_listed_not_skipped(tmp_path: Path) -> None:
    _bundle(
        tmp_path / "candidates",
        "o__Aspose.Demo-FOSS-for-Python",
        "d" * 40,
        **{"README.md": CANDIDATE},
    )
    (row,) = report.measure_all(report.discover([tmp_path]))
    assert row.bundle.live_source == "missing" and not row.measured and "not found" in row.note
    assert "not found" in report.render_table([row])


def test_the_report_lists_a_bundle_once_and_can_leave_out_the_committed_ones(
    tmp_path: Path,
) -> None:
    patch = render_patch(LIVE, CANDIDATE)
    for checkout in ("one", "two"):
        _bundle(
            tmp_path / checkout / "candidates",
            "o__Aspose.Demo-FOSS-for-Python",
            "e" * 40,
            **{"README.md": CANDIDATE, "README.patch": patch},
        )
    both = report.discover([tmp_path / "one", tmp_path / "two"])
    assert len(both) == 1
    assert report.discover([tmp_path / "one"], exclude=[tmp_path / "two" / "candidates"]) == []
    changed = _bundle(
        tmp_path / "three" / "candidates",
        "o__Aspose.Demo-FOSS-for-Python",
        "e" * 40,
        **{
            "README.md": CANDIDATE + "\nExtra.\n",
            "README.patch": render_patch(LIVE, CANDIDATE + "\nExtra.\n"),
        },
    )
    kept = report.discover([tmp_path / "three"], exclude=[tmp_path / "two" / "candidates"])
    assert [b.path for b in kept] == [changed]


def test_since_leaves_out_what_a_checkout_started_with(tmp_path: Path) -> None:
    patch = render_patch(LIVE, CANDIDATE)
    _bundle(
        tmp_path / "candidates",
        "o__Aspose.Demo-FOSS-for-Python",
        "f" * 40,
        **{
            "README.md": CANDIDATE,
            "README.patch": patch,
            "manifest.json": json.dumps({"sealed_at": "2026-09-01T00:00:00Z"}),
        },
    )
    assert len(report.discover([tmp_path])) == 1
    assert report.discover([tmp_path], since="2026-10-01T00:00:00Z") == []
    assert len(report.discover([tmp_path], since="2026-09-01T00:00:00Z")) == 1


def test_a_correction_bundle_is_measured_against_its_original(tmp_path: Path) -> None:
    directory = tmp_path / "corrections" / "run1" / "o__Aspose.Demo-FOSS-for-Python"
    directory.mkdir(parents=True)
    (directory / "README.md").write_text(LIVE.replace("1.2.3", "2.0.0"), "utf-8", newline="\n")
    (directory / "README.original.md").write_text(LIVE, "utf-8", newline="\n")
    (directory / "manifest.json").write_text(
        json.dumps({"repository": "o/Aspose.Demo-FOSS-for-Python", "revision": "9" * 40}), "utf-8"
    )
    (row,) = report.measure_all(report.discover([tmp_path]))
    assert row.bundle.kind == "correction" and row.bundle.live_source == "original"
    assert row.bundle.revision == "9" * 40
    assert row.retention is not None and row.script is not None
    assert row.retention.prose.verbatim_share == 1.0 and row.script.hunks == 1
