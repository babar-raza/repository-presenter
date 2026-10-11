"""README_CONTRACT.md section 2.1 as the pure function BC-07 and planning will delegate to."""

from __future__ import annotations

from repository_presenter.components.readme_diagram import Glance, balanced_columns, build_body
from repository_presenter.components.readme_diagram.contract import (
    COMPOSING,
    MAX_LABEL_LINES,
    PLANNING,
    ContractFailure,
    label_failures,
    title_failure,
    topology_failures,
)

CAPS = tuple(f"Capability {n} of the product" for n in range(1, 9))


def glance(count: int = 6, *, inputs: bool = True) -> Glance:
    return Glance(
        "Aspose.Cells FOSS for Go",
        ("An existing XLSX workbook",) if inputs else (),
        balanced_columns(CAPS[:count]),
        ("XLSX workbooks",),
    )


def messages(failures: list[ContractFailure]) -> list[str]:
    return [f"{failure.stage}: {failure.message}" for failure in failures]


def test_the_builders_diagram_meets_the_contract_for_three_to_eight_capabilities() -> None:
    for count in range(3, 9):
        assert topology_failures(build_body(glance(count)), has_inputs=True) == [], count


def test_starting_points_without_a_verified_input_format_is_a_planning_failure() -> None:
    failures = topology_failures(build_body(glance()), has_inputs=False)
    assert [f.stage for f in failures] == [PLANNING]
    assert "without a verified input format" in failures[0].message
    assert topology_failures(build_body(glance(inputs=False)), has_inputs=False) == []


def test_fewer_than_three_or_more_than_eight_capabilities_is_a_planning_failure() -> None:
    few = Glance("P", (), (("A", "B"),), ())
    assert any("at least 3" in m for m in messages(topology_failures(build_body(few), False)))
    many = Glance("P", (), balanced_columns(tuple(f"Cap {n}" for n in range(9))), ())
    assert any("at most 8" in m for m in messages(topology_failures(build_body(many), False)))


def test_the_column_rule_is_one_column_to_five_and_two_balanced_from_six() -> None:
    two_for_five = Glance("P", (), (("A", "B", "C"), ("D", "E")), ())
    assert any(
        "one column, not two" in m
        for m in messages(topology_failures(build_body(two_for_five), False))
    )
    one_for_six = Glance("P", (), (tuple(CAPS[:6]),), ())
    assert any(
        "two balanced columns" in m
        for m in messages(topology_failures(build_body(one_for_six), False))
    )
    lopsided = Glance("P", (), (tuple(CAPS[:5]), tuple(CAPS[5:6])), ())
    assert any(
        "found 5 and 1" in m for m in messages(topology_failures(build_body(lopsided), False))
    )


def test_the_old_vertical_drawing_is_not_the_contract(live: dict[str, str]) -> None:
    for name, source in live.items():
        failures = topology_failures(source, has_inputs=True)
        assert any(f.stage == COMPOSING and "horizontal drawing" in f.message for f in failures), (
            name
        )


def test_a_diagram_that_is_not_the_chain_is_refused_with_the_reason() -> None:
    failures = topology_failures("sequenceDiagram\n  A->>B: x\n", has_inputs=False)
    assert len(failures) == 1 and "not the contract's chain" in failures[0].message


def test_a_label_that_is_hand_wrapped_or_restyled_is_not_the_contract() -> None:
    body = build_body(glance())
    tampered = body.replace("Capability 1<br/>of the product", "Capability 1 of<br/>the product")
    assert any("horizontal drawing" in m for m in messages(topology_failures(tampered, True)))
    styled = body + "  style PRODUCT fill:#fff\n"
    assert any("not the contract's chain" in m for m in messages(topology_failures(styled, True)))


def test_a_title_past_the_line_ceiling_or_with_a_too_wide_word_is_shortened_at_planning() -> None:
    long_title = "Create, read, update, delete, import, export, merge, and split documents"
    assert title_failure("Data validation", 8) is None
    assert "wraps to" in (title_failure(long_title, 8) or "")
    assert "word wider" in (title_failure("W" * 40, 3) or "")
    wide = Glance("P", (), balanced_columns((long_title, *"BCDEFGH")), ())
    failures = label_failures(wide)
    assert failures and all(f.stage == PLANNING for f in failures)
    assert MAX_LABEL_LINES == 4
