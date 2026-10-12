"""The idempotence gate (tools/idempotence, TC-IDM-01): the live-first lane over the corpus.

For each of the committed live READMEs the correction lane is run on the README and on its own
output. The gate fails when the second run is not a no-op, when a non-diagram live line is lost
without a reported edit covering it, or when a changed line has no edit to explain it. The
mutation tests then inject one controlled defect into a conformant README and require exactly the
detector that owns it to find it. Negative controls prove each of these can fail.

Offline and model-free: the lane is deterministic code, the facts are sealed candidates' facts
(``candidates/<slug>/<head>/facts.json``) or none.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from dataclasses import replace

import pytest
from tools.idempotence import corpus, gate, lane, mutations, report
from tools.idempotence.lane import EditRecord, LaneRun, fixed_point
from tools.idempotence.mutations import Mutated, Subject
from tools.idempotence.retention import retention

from repository_presenter.components.readme_correction import engine
from repository_presenter.components.readme_correction.detectors import load_detectors
from repository_presenter.components.readme_correction.model import (
    STRUCTURE_FIX,
    Context,
    DetectorResult,
    Edit,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.registry.loader import load_registry, require_listed
from support import REPO_ROOT

ENTRIES = corpus.load()
#: What the lane may do to a README it has no facts for: the three structural detectors only.
STRUCTURAL = {"at_a_glance_diagram", "second_h1", "unclosed_details"}
JAVA = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"


@functools.cache
def _row(repository: str) -> gate.GateRow:
    return gate.gate_entry(ENTRIES[repository])


# --- the gate over the corpus -----------------------------------------------------------------


@pytest.mark.parametrize("repository", sorted(ENTRIES))
def test_the_lane_is_a_fixed_point_and_loses_nothing_it_does_not_report(repository: str) -> None:
    row = _row(repository)
    assert row.ok, "\n".join(row.report.problems())
    assert row.report.idempotent and row.report.lossless and not row.report.unexplained


def test_a_lane_with_no_facts_may_only_make_structural_edits() -> None:
    for repository in ENTRIES:
        row = _row(repository)
        if not row.with_facts:
            assert set(row.report.first.detectors) <= STRUCTURAL, repository


def test_most_of_the_corpus_is_gated_with_real_facts_and_they_exercise_fact_driven_detectors() -> (
    None
):
    rows = [_row(repository) for repository in ENTRIES]
    with_facts = [row for row in rows if row.with_facts]
    assert len(with_facts) >= 10  # a README with sealed facts at its head is gated with them
    fact_driven = {d for row in with_facts for d in row.report.first.detectors} - STRUCTURAL
    assert "missing_sections" in fact_driven


def test_the_gate_is_reproducible_run_to_run() -> None:
    for repository in (
        "aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python",  # with real facts
        "aspose-cells-foss/Aspose.Cells-FOSS-for-Go",  # facts-free, with structural defects
    ):
        row = gate.gate_entry(ENTRIES[repository], cold=True)
        assert row.report.cold is not None and row.report.reproducible and row.ok


def test_the_gate_table_names_every_repository_and_its_verdict() -> None:
    table = gate.render_gate([_row(repository) for repository in sorted(ENTRIES)])
    assert table.count("\n") == len(ENTRIES) + 2
    assert "FAIL" not in table and "no-op" in table


# --- negative controls: each way the gate can fail --------------------------------------------

README = (
    "# Title\n\nFirst paragraph is kept.\n\n## Usage\n\nSecond paragraph is kept.\n\n"
    "## License\n\nMIT.\n"
)


def _run(text: str, *spans: tuple[int, int, str, str]) -> LaneRun:
    edits = tuple(
        EditRecord("FALSE_CLAIM_FIX", "stub", s, e, o, r, ("package:name",)) for s, e, o, r in spans
    )
    return LaneRun(text, edits)


def test_a_lane_that_drops_a_line_without_reporting_an_edit_fails() -> None:
    def lossy(text: str) -> LaneRun:
        return _run(text.replace("Second paragraph is kept.\n\n", ""))

    report = fixed_point(lossy, README)
    assert not report.ok and not report.lossless
    assert any("Second paragraph is kept." in p for p in report.problems())


def test_a_lane_that_reports_the_edit_that_covers_the_change_passes() -> None:
    start = README.index("MIT.")

    def lane_(text: str) -> LaneRun:
        if "BSD." in text:
            return _run(text)
        out = text.replace("MIT.", "BSD.")
        return LaneRun(
            out,
            (
                EditRecord(
                    "FALSE_CLAIM_FIX", "stub", start, start + 4, "MIT.", "BSD.", ("license:spdx",)
                ),
            ),
            ((start, start + 4),),
        )

    assert fixed_point(lane_, README).ok


def test_a_lane_whose_second_run_changes_the_text_fails_the_fixed_point() -> None:
    def growing(text: str) -> LaneRun:
        return _run(text + "More.\n")

    report = fixed_point(growing, README)
    assert not report.idempotent and not report.ok
    assert any("second run is not a no-op" in p for p in report.problems())


def test_a_lane_whose_second_run_reports_an_edit_fails_even_if_the_text_is_unchanged() -> None:
    def restless(text: str) -> LaneRun:
        return _run(text, (0, 1, "#", "#"))

    assert not fixed_point(restless, README).idempotent


def test_a_lane_that_changes_a_line_it_did_not_report_leaves_an_unexplained_hunk() -> None:
    start = README.index("MIT.")

    def sneaky(text: str) -> LaneRun:
        out = text.replace("MIT.", "BSD.").replace("First paragraph", "First section")
        return LaneRun(
            out,
            (
                EditRecord(
                    "FALSE_CLAIM_FIX", "stub", start, start + 4, "MIT.", "BSD.", ("license:spdx",)
                ),
            ),
            ((README.index("MIT."), README.index("MIT.") + 4),),
        )

    report = fixed_point(sneaky, README)
    assert not report.ok and report.unexplained


def test_a_lane_whose_edit_cites_no_evidence_fails() -> None:
    start = README.index("MIT.")

    def unsourced(text: str) -> LaneRun:
        if "BSD." in text:
            return _run(text)
        edit = EditRecord("FALSE_CLAIM_FIX", "stub", start, start + 4, "MIT.", "BSD.")
        return LaneRun(text.replace("MIT.", "BSD."), (edit,), ((start, start + 4),))

    report = fixed_point(unsourced, README)
    assert report.lossless and report.idempotent and not report.unexplained
    assert not report.ok and len(report.unevidenced) == 1
    assert any("cites no fact" in p for p in report.problems())


def test_a_lane_that_is_not_reproducible_fails() -> None:
    seen: list[int] = []

    def drifting(text: str) -> LaneRun:
        seen.append(1)
        return _run(text if len(seen) == 1 else text + "\n")

    report = fixed_point(drifting, README, cold=True)
    assert report.cold is not None and not report.reproducible
    assert any("two cold runs" in p for p in report.problems())


def test_a_regeneration_style_lane_fails_every_measure() -> None:
    def rewrite(text: str) -> LaneRun:
        return _run("# Title\n\nA different document altogether, written from scratch.\n")

    report = fixed_point(rewrite, README)
    assert not report.lossless and report.unexplained and not report.ok


def test_the_correction_lane_is_judged_by_the_same_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """A detector that rewrites a maintainer line is an enumerated edit, so the gate lets it
    through by design; one that also moves another line cannot be built (the engine proves
    confinement), so the gate's own line check is shown on a lane that bypasses the engine."""
    real = ENTRIES[JAVA]
    registered = lane.registry_entry(JAVA)
    bare = lane.correction_lane(registered, None, settle=False)
    intact = fixed_point(bare, real.text, JAVA)
    assert intact.ok

    def bypass(text: str) -> LaneRun:
        run = bare(text)
        lines = run.text.splitlines(keepends=True)
        drop = next(
            i
            for i, ln in enumerate(lines)
            if ln.startswith("## Navigation") or ln.startswith("## ")
        )
        return replace(run, text="".join(lines[:drop] + lines[drop + 1 :]))

    assert not fixed_point(bypass, real.text, JAVA).lossless


# --- mutations (e) ----------------------------------------------------------------------------

SYNTHETIC = """\
# Aspose.3D FOSS for Java

## At a Glance

```mermaid
flowchart TD
  subgraph StartingPoints["Starting Points"]
    direction LR
    i1["An existing OBJ, STL, or 3MF file"]
  end
  PRODUCT["Aspose.3D FOSS for Java"]
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
```

## Installation

```bash
mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.5.0
```

<details>
<summary>More ways to install</summary>

Download the jar from the releases page and add it to the class path.

</details>

## Dependencies

The library has no runtime dependencies.

## Documentation

Read [the guide](docs/guide.md) before you start.

## License

Licensed under the MIT License. See [LICENSE](LICENSE).
"""
REVISION = "a" * 40


def _fact(
    fact_id: str, value: str, *evidence: tuple[str, str | None], polarity: str = "SUPPORTED"
) -> Fact:
    return Fact(
        fact_id,
        fact_id.split(":", 1)[0],  # type: ignore[arg-type]
        value,
        tuple(Evidence(path, detail) for path, detail in evidence) or (Evidence("pom.xml", None),),
        polarity=polarity,  # type: ignore[arg-type]
    )


def synthetic_facts() -> FactsDocument:
    facts = (
        _fact("identity:repository", JAVA, ("source/snapshot.json", None)),
        _fact("identity:revision", REVISION, ("source/snapshot.json", None)),
        _fact("package:name", "org.aspose:aspose-3d-foss"),
        _fact("package:version", "26.8.0"),
        _fact("package:published_version", "26.7.0", ("https://repo1.maven.org/x", None)),
        _fact(
            "install_command:maven",
            "mvn dependency:get -Dartifact=org.aspose:aspose-3d-foss:26.7.0",
            ("pom.xml", None),
            ("https://repo1.maven.org/x", "package registry: found"),
        ),
        _fact("license:spdx", "MIT", ("LICENSE", "license text states this license")),
        _fact("license:file", "LICENSE", ("LICENSE", None)),
        _fact("dependency:none", "none", ("pom.xml", "the manifest declares none")),
        _fact(
            "link_target:001",
            "docs/guide.md",
            ("README.md", "line 62; relative; text 'the guide'"),
            ("README.md", "RESOLVED: tree contains docs/guide.md"),
        ),
    )
    return FactsDocument(JAVA, REVISION, facts)


def synthetic_subject() -> Subject:
    entry = require_listed(load_registry(REPO_ROOT / "data" / "registry.json"), JAVA)
    subject = mutations.make_subject(entry, SYNTHETIC, synthetic_facts())
    assert subject is not None, "the lane must reach a fixed point on the synthetic README"
    return subject


def test_the_synthetic_readme_is_corrected_to_a_fixed_point_with_known_edits() -> None:
    subject = synthetic_subject()
    assert subject.text != SYNTHETIC
    assert "26.7.0" in subject.text and "26.5.0" not in subject.text  # the stale version was fixed
    assert "flowchart LR" in subject.text or "flowchart TD" not in subject.text.split("```")[1]
    quick = lane.correction_lane(subject.entry, subject.facts, tree=subject.tree, settle=False)
    assert quick(subject.text).edits == ()


ALL_KINDS = [
    "dead_link",
    "dropped_section",
    "false_version",
    "second_h1",
    "unclosed_details",
    "vertical_diagram",
]


def test_every_registered_mutation_is_exercised_here() -> None:
    assert sorted(mutations.MUTATORS) == ALL_KINDS


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_one_injected_defect_is_found_by_exactly_its_detector_and_nothing_else_changes(
    kind: str,
) -> None:
    outcome = mutations.run_mutation(synthetic_subject(), kind)
    assert outcome.applicable, f"the synthetic README has a site for {kind}"
    assert outcome.problems == [], outcome.problems
    assert outcome.confined and outcome.extra_detectors == []
    if kind != "dropped_section":
        assert outcome.restored is True  # the lane gives the conformant README back, byte for byte


def test_the_dropped_section_is_refilled_from_facts_and_the_rest_is_untouched() -> None:
    subject = synthetic_subject()
    outcome = mutations.run_mutation(subject, "dropped_section")
    assert outcome.found and set(outcome.found) == {"missing_sections"} and outcome.lost == 0


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_without_its_detector_the_defect_is_missed(
    kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    subject = synthetic_subject()
    owner = {
        "dead_link": "broken_link",
        "dropped_section": "missing_sections",
        "false_version": "claim_version",
        "second_h1": "second_h1",
        "unclosed_details": "unclosed_details",
        "vertical_diagram": "at_a_glance_diagram",
    }[kind]
    detectors = {name: fn for name, fn in load_detectors().items() if name != owner}
    monkeypatch.setattr(engine, "load_detectors", lambda: detectors)
    outcome = mutations.run_mutation(subject, kind)
    assert outcome.applicable and not outcome.detected
    assert any("did not find the defect" in p for p in outcome.problems)


def test_a_detector_that_fires_beyond_its_defect_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = synthetic_subject()

    def rogue(ctx: Context) -> DetectorResult:
        line = ctx.lines[0]
        return DetectorResult(
            edits=(
                Edit(
                    STRUCTURE_FIX,
                    "rogue",
                    line.start,
                    line.start + 1,
                    "#",
                    "##",
                    (),
                    "a rogue heading change",
                    locators=("README.md:1",),
                ),
            )
        )

    detectors = {**load_detectors(), "rogue": rogue}
    monkeypatch.setattr(engine, "load_detectors", lambda: detectors)
    outcome = mutations.run_mutation(subject, "second_h1")
    assert not outcome.detected and outcome.extra_detectors == ["rogue"]


def test_a_lane_that_changes_something_else_while_fixing_is_reported() -> None:
    subject = synthetic_subject()

    def meddling(mutated: Mutated) -> Callable[[str], LaneRun]:
        inner = lane.correction_lane(subject.entry, mutated.facts, tree=mutated.tree, settle=False)

        def run(text: str) -> LaneRun:
            result = inner(text)
            return replace(result, text=result.text.replace("before you start", "after you start"))

        return run

    outcome = mutations.run_mutation(subject, "second_h1", meddling)
    assert not outcome.detected
    assert not outcome.confined or outcome.restored is False


def test_a_mutation_with_no_site_is_not_applicable_not_a_failure() -> None:
    entry = lane.registry_entry(JAVA)
    bare = FactsDocument(JAVA, REVISION, ())
    subject = mutations.make_subject(entry, "# T\n\nOne paragraph.\n\n## A\n\nText.\n", bare)
    assert subject is not None
    outcomes = {o.kind: o for o in mutations.run_all(subject)}
    assert not outcomes["unclosed_details"].applicable
    assert not outcomes["dead_link"].applicable and not outcomes["false_version"].applicable
    assert not outcomes["dropped_section"].applicable  # a section is rendered from facts: none here
    assert not outcomes["vertical_diagram"].applicable
    assert outcomes["second_h1"].detected  # the one site a bare README has


def test_the_mutation_registry_refuses_a_duplicate_name() -> None:
    with pytest.raises(ValueError, match="registered twice"):
        mutations.mutator("second_h1")(lambda subject: None)


def test_five_defects_injected_at_once_are_found_exactly_and_the_conformant_text_returns() -> None:
    subject = synthetic_subject()
    restoring = [k for k in ALL_KINDS if k != "dropped_section"]
    together = mutations.run_combined(subject, restoring)
    assert together.ok, together.problems
    assert sorted(together.applied) == sorted(restoring) and together.skipped == {}
    assert together.expected == together.found
    assert together.expected == {
        "broken_link": 1,
        "claim_version": 1,
        "second_h1": 1,
        "unclosed_details": 1,
        "at_a_glance_diagram": 1,
    }
    assert together.restored is True and together.confined


def test_all_six_defects_at_once_leave_every_other_line_alone() -> None:
    together = mutations.run_combined(synthetic_subject())
    assert together.ok, together.problems
    assert "dropped_section" in together.applied and together.restored is None
    assert together.found.get("missing_sections", 0) >= 1 and together.confined
    # a defect whose site another one removed is named, never silently loosened
    assert all(reason for reason in together.skipped.values())


def test_the_combined_run_names_the_defect_a_missing_detector_lets_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detectors = {name: fn for name, fn in load_detectors().items() if name != "claim_version"}
    monkeypatch.setattr(engine, "load_detectors", lambda: detectors)
    together = mutations.run_combined(synthetic_subject(), ["second_h1", "false_version"])
    assert together.applied == [
        "second_h1"
    ]  # the version defect is not found, so it is not accepted
    assert "false_version" in together.skipped


# --- mutations on the real corpus -------------------------------------------------------------

#: Fast, varied subjects: five with real facts, three with none (one carrying real structural
#: defects: Cells for Go has a second H1 and an unclosed <details>).
SUBJECTS = [
    "aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python",
    "aspose-cells-foss/Aspose.Cells-FOSS-for-.NET",
    "aspose-email-foss/Aspose.Email-FOSS-for-.Net",
    "aspose-html-foss/Aspose.HTML-FOSS-for-Python",
    "aspose-page-foss/Aspose.Page-FOSS-for-Python",
    "aspose-cells-foss/Aspose.Cells-FOSS-for-Go",
    "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript",
    "aspose-pdf-foss/Aspose.PDF-FOSS-for-Cpp",
]


@pytest.fixture(scope="module")
def swept() -> list[gate.MutationRow]:
    return gate.mutation_sweep([ENTRIES[r] for r in SUBJECTS])


def test_every_applicable_mutation_on_the_real_readmes_is_found_exactly(
    swept: list[gate.MutationRow],
) -> None:
    for row in swept:
        assert row.fixed_point, row.repository
        for outcome in row.outcomes:
            if outcome.applicable:
                assert outcome.detected, (row.repository, outcome.kind, outcome.problems)


def test_all_the_defects_a_real_readme_can_hold_are_found_together(
    swept: list[gate.MutationRow],
) -> None:
    for row in swept:
        assert row.combined is not None
        assert row.combined.ok, (row.repository, row.combined.problems, row.combined.skipped)
        assert row.combined.confined


def test_the_real_readmes_give_every_mutation_a_site_somewhere(
    swept: list[gate.MutationRow],
) -> None:
    applicable = {o.kind for row in swept for o in row.outcomes if o.applicable}
    assert applicable == set(ALL_KINDS)


def test_the_fact_driven_mutations_need_facts(swept: list[gate.MutationRow]) -> None:
    for row in swept:
        by_kind = {o.kind: o for o in row.outcomes}
        if not row.with_facts:
            assert not by_kind["dropped_section"].applicable
            assert not by_kind["dead_link"].applicable


def test_the_mutation_table_lists_each_subject() -> None:
    rows = gate.mutation_sweep([ENTRIES[SUBJECTS[0]]])
    table = gate.render_mutations(rows)
    assert SUBJECTS[0] in table and "found" in table and "MISSED" not in table


# --- the regeneration lane: a floor under what the committed candidates keep ----------------

#: What the 38 sealed candidates committed under candidates/ keep of the live README they replaced,
#: pooled (measured 2026-10-12 by tools.idempotence.report: 13.1% of live prose verbatim, 37.2% in
#: any form, 32.3% of non-diagram live lines). The floors sit just under those figures, so a reseal
#: that keeps less of the live README than today's candidates fails here; raising a floor after a
#: reseal that keeps more is the intent, and lowering one is an owner decision, not a test edit.
PROSE_VERBATIM_FLOOR = 0.12
PROSE_KEPT_FLOOR = 0.35
LINES_KEPT_FLOOR = 0.30


def pooled_retention(pairs: list[tuple[str, str]]) -> dict[str, float]:
    """Pooled shares over ``(live, candidate)`` pairs: prose verbatim, prose kept, lines kept."""
    totals = dict.fromkeys(("prose", "verbatim", "kept", "eligible", "lines"), 0)
    for live, candidate in pairs:
        result = retention(live, candidate)
        totals["prose"] += result.prose.total
        totals["verbatim"] += result.prose.verbatim
        totals["kept"] += result.prose.kept
        totals["eligible"] += result.lines.eligible
        totals["lines"] += result.lines.kept
    return {
        "verbatim": totals["verbatim"] / max(1, totals["prose"]),
        "kept": totals["kept"] / max(1, totals["prose"]),
        "lines": totals["lines"] / max(1, totals["eligible"]),
    }


def meets_floors(shares: dict[str, float]) -> bool:
    return (
        shares["verbatim"] >= PROSE_VERBATIM_FLOOR
        and shares["kept"] >= PROSE_KEPT_FLOOR
        and shares["lines"] >= LINES_KEPT_FLOOR
    )


def test_the_committed_regenerations_keep_no_less_of_the_live_readme_than_the_floor() -> None:
    bundles = report.discover([REPO_ROOT / "candidates"])
    assert len(bundles) >= 30 and all(b.live_source == "patch" for b in bundles)
    pairs = [(b.live, b.readme) for b in bundles if b.live is not None]
    assert len(pairs) == len(bundles)
    assert meets_floors(pooled_retention(pairs)), pooled_retention(pairs)


def test_the_floor_fails_a_regeneration_that_keeps_less_and_passes_one_that_keeps_all() -> None:
    live = ENTRIES[JAVA].text
    rewritten = "# Aspose.3D FOSS for Java\n\nA library for working with 3D scenes in Java.\n"
    assert meets_floors(pooled_retention([(live, live)]))
    shares = pooled_retention([(live, rewritten)])
    assert not meets_floors(shares) and shares["kept"] < PROSE_KEPT_FLOOR
