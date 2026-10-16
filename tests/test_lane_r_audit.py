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
