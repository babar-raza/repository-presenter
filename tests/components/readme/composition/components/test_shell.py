"""The semantic shell is the contract's section table, in order, with its owners."""

from __future__ import annotations

from repository_presenter.components.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    placeable_section_ids,
    section_ids,
    shell_packet,
)


def test_the_shell_lists_the_seventeen_sections_in_contract_order() -> None:
    assert section_ids() == (
        "identity",
        "badges",
        "opening",
        "navigation",
        "at_a_glance",
        "key_capabilities",
        "installation",
        "dependencies",
        "quick_start",
        "additional_examples",
        "api_reference",
        "documentation_resources",
        "scope_limitations",
        "development_testing",
        "enterprise_relationship",
        "third_party_notices",
        "license",
    )
    assert len(set(section_ids())) == 17
    required = [section.id for section in SEMANTIC_SHELL if section.required]
    assert required == [
        "identity",
        "badges",
        "opening",
        "navigation",
        "key_capabilities",
        "installation",
        "dependencies",
        "quick_start",
        "scope_limitations",
        "license",
    ]
    assert all(section.condition for section in SEMANTIC_SHELL if not section.required)
    assert all(section.condition is None for section in SEMANTIC_SHELL if section.required)


def test_only_llm_and_mixed_sections_can_hold_inherited_units() -> None:
    assert placeable_section_ids() == {
        "opening",
        "at_a_glance",
        "key_capabilities",
        "quick_start",
        "additional_examples",
        "api_reference",
        "documentation_resources",
        "scope_limitations",
        "development_testing",
        "enterprise_relationship",
    }


def test_the_packet_form_carries_every_field_the_jobs_read() -> None:
    packet = shell_packet()
    assert [entry["id"] for entry in packet] == list(section_ids())
    assert packet[6] == {
        "id": "installation",
        "heading": "Installation",
        "required": True,
        "visibility": "visible",
        "owner": "D",
        "placeable": False,
        "condition": None,
        "content": "The verified install command for the ecosystem.",
    }
    assert [entry["id"] for entry in packet if entry["placeable"]] == sorted(
        placeable_section_ids(), key=list(section_ids()).index
    )
