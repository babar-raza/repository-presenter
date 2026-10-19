"""The Lane R measurement harness (G3-W12 card C1), held to known answers.

Stage 1: the pinned reader, M1 to M3, M9 and the reproduction of the v1 baseline. The tests that
read the pinned bundles need the control revision in the checkout; when it is absent they FAIL
(the reader raises ``PinnedInputError``), they never skip - a skipped ratchet is a false green.
Offline: no network, no model, no write outside tmp_path.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from tools.lane_r_audit import ledger, measure, pinned

from support import REPO_ROOT

V1_PATH = REPO_ROOT / "evidence" / "lane-r-dependability" / "ledger_baseline.json"


@pytest.fixture(scope="module")
def pins() -> pinned.Pins:
    return pinned.load_pins()


@pytest.fixture(scope="module")
def bundles(pins: pinned.Pins) -> list[pinned.PinnedBundle]:
    return pinned.read_bundles(pins)


@pytest.fixture(scope="module")
def measured(pins: pinned.Pins) -> dict[str, Any]:
    return measure.measure(pins)


# --- the pinned reader --------------------------------------------------------------------------


def test_pins_name_thirty_bundles_with_hashes(pins: pinned.Pins) -> None:
    assert len(pins.bundles) == 30
    assert len({pin.directory for pin in pins.bundles}) == 30
    for pin in pins.bundles:
        assert len(pin.revision) == 40
        assert len(pin.manifest_sha256) == 64
        assert pin.live_readme_sha256 is not None and len(pin.live_readme_sha256) == 64
    assert len(pins.survey_sha256) == 64


def test_pinned_reader_reads_the_bundles_through_git(
    bundles: list[pinned.PinnedBundle], pins: pinned.Pins
) -> None:
    assert [b.pin for b in bundles] == list(pins.bundles)
    for bundle in bundles:
        assert bundle.sealed.facts is not None and bundle.sealed.dispositions is not None
        assert bundle.content_units is not None and bundle.plan is not None
        assert bundle.live is not None


def test_pinned_reader_rejects_a_changed_manifest_hash(pins: pinned.Pins) -> None:
    first = replace(pins.bundles[0], manifest_sha256="0" * 64)
    with pytest.raises(pinned.PinnedInputError, match="not the pinned bytes"):
        pinned.read_bundles(replace(pins, bundles=(first, *pins.bundles[1:])))


def test_pinned_reader_rejects_a_changed_live_readme_hash(pins: pinned.Pins) -> None:
    first = replace(pins.bundles[0], live_readme_sha256="1" * 64)
    with pytest.raises(pinned.PinnedInputError, match="live README"):
        pinned.read_bundles(replace(pins, bundles=(first, *pins.bundles[1:])))


def test_pinned_reader_fails_rather_than_skips_when_the_revision_is_absent(
    pins: pinned.Pins,
) -> None:
    with pytest.raises(pinned.PinnedInputError, match="never skips"):
        pinned.read_bundles(replace(pins, control_revision="0" * 40))


def test_pinned_reader_fails_when_the_revision_is_not_a_git_checkout(
    pins: pinned.Pins, tmp_path: Path
) -> None:
    with pytest.raises(pinned.PinnedInputError):
        pinned.read_bundles(pins, tmp_path)


def test_survey_must_be_the_pinned_bytes(pins: pinned.Pins, tmp_path: Path) -> None:
    pinned.check_survey(pins)
    changed = tmp_path / "survey.json"
    changed.write_bytes(pinned.SURVEY_PATH.read_bytes() + b" ")
    with pytest.raises(pinned.PinnedInputError, match="pinned bytes"):
        pinned.check_survey(pins, changed)


def test_pins_are_reproducible_from_the_control_revision(pins: pinned.Pins) -> None:
    assert pinned.build_pins(pins.control_revision) == pins


# --- the v1 reproduction ------------------------------------------------------------------------


def test_the_harness_reproduces_the_v1_baseline_totals(measured: dict[str, Any]) -> None:
    v1 = json.loads(V1_PATH.read_text(encoding="utf-8"))
    totals = v1["totals"]
    assert measured["v1"] == {
        "units": 2761,
        "kept": 746,
        "kept_not_printed": 389,
        "omit_unsupported": 338,
        "omit_unsupported_without_fact": 316,
        "supersede_redundant": 1514,
    }
    assert measured["v1"] == totals
    assert (measured["judge"]["J4_fail"], measured["judge"]["J6_fail"]) == (29, 26)


def test_the_harness_reproduces_the_v1_baseline_per_bundle(measured: dict[str, Any]) -> None:
    v1 = json.loads(V1_PATH.read_text(encoding="utf-8"))["bundles"]
    assert set(measured["bundles"]) == set(v1)
    for name, row in v1.items():
        mine = measured["bundles"][name]
        assert mine["revision"] == row["revision"]
        assert mine["v1"]["units"] == row["units"]
        assert mine["v1"]["kept_not_printed"] == row["kept_not_printed"]
        assert mine["v1"]["omit_unsupported"] == row["omit_unsupported"]
        assert mine["v1"]["omit_unsupported_without_fact"] == row["omit_unsupported_without_fact"]
        assert mine["judge_failing"] == row["judge_failing"], name


def test_two_measurements_are_identical(pins: pinned.Pins, measured: dict[str, Any]) -> None:
    assert measure.dumps(measure.measure(pins)) == measure.dumps(measured)


def test_the_committed_v2_baseline_is_what_the_harness_writes(
    measured: dict[str, Any], pins: pinned.Pins
) -> None:
    committed = measure.BASELINE_V2_PATH.read_text(encoding="utf-8")
    assert committed == measure.dumps(measure.baseline_v2(measured, pins))


def test_the_v2_baseline_carries_the_new_numbers_and_the_frozen_threshold() -> None:
    baseline = json.loads(measure.BASELINE_V2_PATH.read_text(encoding="utf-8"))
    assert baseline["m3_definition"]["threshold"] == 0.8
    assert baseline["m3"]["threshold"] == 0.8
    assert baseline["m2"]["value"] == 318  # 338 OMIT_UNSUPPORTED, 20 cite a CONTRADICTED fact
    assert baseline["m2"]["of_omit_unsupported"] == 338
    assert baseline["m2"]["of_which_cite_no_fact"] == 316
    assert baseline["m1"]["over"] > 0 and baseline["m1"]["value"] < 1.0
    assert baseline["m9"] == {"authorizable": 0, "inputs": 30}
    assert baseline["v1_reproduced"]["kept_not_printed"] == 389


# --- M1, M2, M3 on synthetic ledgers ------------------------------------------------------------


def _account(**kw: Any) -> ledger.UnitAccount:
    base: dict[str, Any] = {
        "unit_id": "inherited_unit:001.paragraph",
        "kind": "paragraph",
        "disposition": "VERIFIED_PRESERVE",
        "destination": None,
        "present": False,
        "contradicted": (),
        "cited": 0,
        "coverage": None,
        "located": True,
    }
    base.update(kw)
    return ledger.UnitAccount(**base)


def test_accounting_rules_by_disposition() -> None:
    assert _account(present=True).accounted
    assert not _account().accounted  # kept but not printed
    assert not _account(disposition="DEFER_UNRESOLVED", present=True).accounted
    assert not _account(disposition=None, present=True).accounted
    assert not _account(disposition="OMIT_UNSUPPORTED", cited=3).accounted
    assert _account(disposition="OMIT_UNSUPPORTED", contradicted=("example:003",)).accounted
    assert not _account(disposition="SUPERSEDE_REDUNDANT", coverage=0.79).accounted
    assert _account(disposition="SUPERSEDE_REDUNDANT", coverage=0.8).accounted
    assert not _account(disposition="SUPERSEDE_REDUNDANT", coverage=None).accounted


def test_m1_counts_defer_as_not_accounted_so_moving_a_unit_to_defer_cannot_raise_it() -> None:
    kept = [_account(present=True), _account(present=True)]
    assert ledger.ledger_metrics(kept).m1 == 1.0
    moved = [_account(present=True), _account(disposition="DEFER_UNRESOLVED")]
    assert ledger.ledger_metrics(moved).m1 == 0.5


def test_m2_and_m3_count_only_unproven_removals() -> None:
    rows = [
        _account(disposition="OMIT_UNSUPPORTED"),
        _account(disposition="OMIT_UNSUPPORTED", cited=1),
        _account(disposition="OMIT_UNSUPPORTED", contradicted=("link_target:009",), cited=1),
        _account(disposition="SUPERSEDE_REDUNDANT", coverage=0.5),
        _account(disposition="SUPERSEDE_REDUNDANT", coverage=1.0),
    ]
    metrics = ledger.ledger_metrics(rows)
    assert (metrics.m2, metrics.omit_unsupported, metrics.omit_without_fact) == (2, 3, 1)
    assert (metrics.m3, metrics.supersede) == (1, 2)


def test_coverage_is_the_share_of_unit_tokens_in_the_destination() -> None:
    unit = "Install with `pip install aspose-cells-foss` for Python"
    assert ledger.coverage(unit, unit) == 1.0
    assert ledger.coverage(unit, "nothing in common here") == 0.0
    half = ledger.coverage("alpha beta gamma delta", "alpha beta")
    assert half == 0.5
    assert ledger.coverage(unit, None) == 0.0


def test_destination_sections_are_located_by_heading_and_lead() -> None:
    readme = (
        "# T\n\nlead text\n\n## Installation\n\nrun pip\n\n### Sub\n\nmore\n\n## License\n\nMIT\n"
    )
    sections = ledger.section_texts(readme)
    assert "lead text" in (ledger.destination_text("opening", sections, readme) or "")
    install = ledger.destination_text("installation", sections, readme) or ""
    assert "run pip" in install and "more" in install and "MIT" not in install
    assert ledger.destination_text("quick_start", sections, readme) is None
    assert ledger.destination_text(None, sections, readme) is None
    assert ledger.destination_text("enterprise_relationship", sections, readme) == readme


def test_a_dropped_unit_lowers_m1_on_a_real_bundle(bundles: list[pinned.PinnedBundle]) -> None:
    """Negative control: delete a kept unit's text from the printed README and M1 falls."""
    bundle = bundles[0]
    before = ledger.ledger_metrics(ledger.unit_accounts(bundle))
    units = bundle.sealed.inherited_units() or {}
    kept = next(
        row
        for row in bundle.sealed.disposition_rows() or []
        if row.get("disposition") in ledger.judge.KEPT
        and len(units[str(row["unit_id"])]) > 40
        and units[str(row["unit_id"])] in bundle.readme
    )
    edited = bundle.readme.replace(units[str(kept["unit_id"])], "")
    mutated = replace(bundle, readme=edited, sealed=replace(bundle.sealed, readme=edited))
    after = ledger.ledger_metrics(ledger.unit_accounts(mutated))
    assert after.accounted < before.accounted
    assert after.m1 < before.m1


# --- stage 2: M4, M5, the detector registry, the sampler ----------------------------------------

import ast  # noqa: E402

from tools.lane_r_audit import claims_ref, corpus, detectors, lint, sampler  # noqa: E402

FACTS: dict[str, dict[str, Any]] = {
    "identity:repository": {"kind": "identity", "value": "'x/y'", "attributes": None},
    "package:name": {"kind": "package", "value": "aspose-note-foss", "attributes": None},
    "package:version": {"kind": "package", "value": "26.9.0", "attributes": None},
    "format:pdf": {"kind": "format", "value": "PDF", "attributes": None},
    "public_symbol:a.scene": {
        "kind": "public_symbol",
        "value": "Aspose.Note.Scene",
        "attributes": {"docstring": "A scene holds nodes.", "symbol_kind": "class"},
    },
}


def _escapes(text: str, cited: list[str], strict: bool = False) -> set[tuple[str, str]]:
    return {(e.cls, e.token) for e in claims_ref.escapes(text, cited, FACTS, strict=strict)}


def test_m4_passes_text_every_token_of_which_a_cited_fact_supports() -> None:
    text = "Version 26.9.0 of `aspose-note-foss` reads PDF and the Aspose.Note.Scene class."
    assert (
        _escapes(text, ["package:name", "package:version", "format:pdf", "public_symbol:a.scene"])
        == set()
    )


def test_m4_flags_each_class_when_the_cited_facts_do_not_say_it() -> None:
    cited = ["package:name", "package:version"]
    assert ("version", "26.8.0") in _escapes("Release 26.8.0 is on the registry.", cited)
    assert ("number", "48") in _escapes("The suite has 48 test files.", cited)
    assert ("format", "DOCX") in _escapes("It writes DOCX and PDF output.", cited)
    assert ("package", "aspose-note") in _escapes("Run pip install aspose-note to begin.", cited)
    assert ("identifier", "RootNode") in _escapes("It exposes a RootNode property.", cited)


def test_m4_identity_facts_support_nothing_and_the_strict_reading_drops_symbols() -> None:
    assert ("version", "26.9.0") in _escapes("Version 26.9.0 ships.", ["identity:repository"])
    prose = "The Aspose.Note.Scene class holds nodes."
    assert _escapes(prose, ["public_symbol:a.scene"]) == set()
    assert ("identifier", "Aspose.Note.Scene") in _escapes(
        prose, ["public_symbol:a.scene"], strict=True
    )


def test_m4_ignores_brands_file_names_and_plain_words() -> None:
    assert _escapes("See README.md on GitHub for e.g. the 3D samples.", ["package:name"]) == set()


def test_m5_each_rule_fires_on_its_defect_and_not_on_the_twin() -> None:
    pairs = {
        lint.DANGLING_COLON: (
            "Run the tests:\n\n## Next\n",
            "Run the tests:\n\n```sh\npytest\n```\n",
        ),
        lint.SPLIT_SPEC: ("- `skia>=87.0`\n- `<145`\n", "- `skia>=87.0,<145`\n"),
        lint.XML_DOC_FRAGMENT: (
            "| `Node` | The  contains items. |\n",
            "| `Node` | A tree node. |\n",
        ),
        lint.BADGE_SYNTAX: (
            "![py](https://img.shields.io/badge/python-3.10%2C%3C3.13-blue)\n",
            "![py](https://img.shields.io/badge/python-3.10-blue)\n",
        ),
    }
    assert set(pairs) == set(lint.RULES)
    for rule, (bad, good) in pairs.items():
        assert rule in {hit.rule for hit in lint.lint(bad)}, rule
        assert lint.lint(good) == [], rule


def test_m5_leaves_alone_a_lead_in_before_a_fence_and_html_details() -> None:
    text = (
        "Verify the install:\n```sh\npip list\n```\n<details><summary>More</summary>\n</details>\n"
    )
    assert lint.lint(text) == []


def test_the_reference_modules_import_no_gate_logic() -> None:
    """A gate must not grade itself: M1 to M5 never import validation, reconciliation or
    composition (directly; the judge's readers are the only src modules they cite)."""
    banned = ("validation", "reconciliation", "composition")
    for name in ("ledger", "claims_ref", "lint"):
        tree = ast.parse((REPO_ROOT / "tools" / "lane_r_audit" / f"{name}.py").read_text("utf-8"))
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            elif isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            for module in modules:
                assert not any(part in banned for part in module.split(".")), (name, module)


def test_the_registry_lists_reference_detectors_gates_and_the_live_reviewer() -> None:
    from tools.lane_r_audit import baseline_gates  # noqa: F401  (registers the gates)

    registry = detectors.REGISTRY
    assert {"BC-04", "BC-14", "reviewer"} <= set(registry)
    assert not registry["reviewer"].deterministic
    assert registry["BC-04"].gate and not registry["ref_version"].gate
    assert all(d.classes for d in registry.values())
    assert {d.id for d in detectors.reference_detectors()}.isdisjoint(
        {"BC-04", "BC-14", "reviewer"}
    )
    with pytest.raises(ValueError, match="already registered"):
        detectors.register(registry["ref_version"])


def test_every_class_with_a_floor_has_a_reference_detector() -> None:
    covered = {cls for d in detectors.reference_detectors() for cls in d.classes}
    assert set(detectors.FLOORS) <= covered


def test_lower_bound_is_the_exact_one_sided_bound() -> None:
    assert corpus.lower_bound(0, 0) == 0.0
    assert corpus.lower_bound(10, 10) == pytest.approx(0.05 ** (1 / 10))
    low = corpus.lower_bound(9, 10)
    # Exact one-sided 95 percent lower bound for 9 of 10 (the binomial tail at p is 0.05): 0.605837.
    # (The two-sided 95 percent interval's lower end, 0.555, is the 97.5 percent one-sided bound.)
    assert low == pytest.approx(0.605837, abs=1e-6)
    assert corpus.lower_bound(95, 100) < 0.95 < corpus.lower_bound(100, 100) + 1e-9


def test_the_split_is_a_fixed_hash_of_the_repository_name() -> None:
    assert corpus.split_of("aspose-words-foss/Aspose.Words-FOSS-for-.NET") == corpus.split_of(
        "aspose-words-foss/Aspose.Words-FOSS-for-.NET"
    )
    halves = {corpus.split_of(pin.repository) for pin in pinned.load_pins().bundles}
    assert halves == {"dev", "test"}


def test_the_sampler_is_reproducible_and_blind(bundles: list[pinned.PinnedBundle]) -> None:
    universe = sampler.claim_universe(bundles)
    assert len(universe) > 1000
    first = sampler.draw(universe, sampler.SEED, 200)
    assert first == sampler.draw(universe, sampler.SEED, 200)
    assert first != sampler.draw(universe, sampler.SEED + 1, 200)
    assert len({claim.key for claim in first}) == 200
    form = sampler.blind_form(first)
    assert len(form) == 200 and all(
        set(row) == {"n", "claim", "cited_values", "verdict"} for row in form
    )
    assert not any("|" in row["claim"] and "Aspose." in str(row.get("bundle")) for row in form)
    with pytest.raises(ValueError):
        sampler.draw(universe[:10], 1, 200)


def test_m4_and_m5_baselines_are_in_the_v2_file_and_m7_regression_is_recorded() -> None:
    baseline = json.loads(measure.BASELINE_V2_PATH.read_text(encoding="utf-8"))
    assert baseline["m4"]["value"] > 0 and baseline["m4"]["units"] == 3066
    assert baseline["m5"]["value"] == sum(baseline["m5"]["by_rule"].values())
    assert baseline["m7_regression"] == {"J5_pass": 30, "inputs": 30}
