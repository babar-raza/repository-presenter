"""Every schema the composition stage builds, over the shapes it is actually called with, carries no
empty enum. A strict json_schema request with an empty enum cannot be decoded (the S5 HTTP 500/502
on Aspose.GIS, 2026-10-04), so an empty set must be pinned as ``maxItems`` 0 or ``maxLength`` 0,
never as an enum. This scan is the guard for every builder, present and future, in this package."""

from __future__ import annotations

from repository_presenter.components.readme.composition.authoring import (
    SectionTask,
    authoring_schema,
)
from repository_presenter.components.readme.composition.coherence import coherence_schema
from repository_presenter.components.readme.composition.planning import planning_schema
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.registry.models import RegistryEntry
from support import REPO_ROOT, assert_no_empty_enums

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "org/Aspose.Widget-FOSS-for-Python",
        "family": "widget",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "widget",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)
MANIFESTS = load_manifests(REPO_ROOT / "prompts")


def _fact(
    fact_id: str, kind: str, value: str, polarity: str = "SUPPORTED", **attributes: str
) -> Fact:
    return Fact(
        fact_id,
        kind,
        value,
        (Evidence(value, "HTTP 200"),),
        polarity=polarity,  # type: ignore[arg-type]
        attributes=attributes or None,
    )


def _facts(*records: Fact) -> FactsDocument:
    return FactsDocument(ENTRY.repository, "a" * 40, records)


NO_FACTS = _facts()
# Every link target is shell-owned (the Aspose.GIS shape): nothing a plan may assign.
SHELL_ONLY_LINKS = _facts(
    _fact("identity:repository", "identity", ENTRY.repository),
    _fact("format:output.stl", "format", ".stl"),
    _fact("example:001", "example", "print(1)"),
    _fact("public_symbol:widget.scene", "public_symbol", "widget.Scene"),
    _fact(
        "link_target:product.banner",
        "link_target",
        "https://products.aspose.org/media/widget/python/banner-readme.png",
    ),
    _fact("link_target:product.homepage", "link_target", "https://products.aspose.org/widget/"),
    _fact(
        "link_target:product.enterprise",
        "link_target",
        "https://products.aspose.com/widget/python/",
        role="enterprise",
        level="platform",
    ),
)
# Shell-owned links and no public symbol at all: no hub can be chosen.
SHELL_ONLY_NO_SYMBOLS = _facts(*(f for f in SHELL_ONLY_LINKS.facts if f.kind != "public_symbol"))
# Nothing SUPPORTED at all: every planning enum is empty.
UNSUPPORTED = _facts(_fact("example:001", "example", "boom", "CONTRADICTED"))


def test_planning_schema_carries_no_empty_enum_for_any_fact_shape() -> None:
    loaded = MANIFESTS["presentation_planning"]
    for facts in (NO_FACTS, SHELL_ONLY_LINKS, SHELL_ONLY_NO_SYMBOLS, UNSUPPORTED):
        assert_no_empty_enums(planning_schema(loaded, facts, {}, {}))


def _task(accepted: frozenset[str], slot_facts: dict[str, frozenset[str]]) -> SectionTask:
    slots = tuple(sorted(slot_facts)) or ("scope",)
    return SectionTask(
        "scope_limitations",
        {"section_id": "scope_limitations", "slots": []},
        accepted,
        slots,
        slot_facts=slot_facts,
    )


def test_authoring_schema_carries_no_empty_enum_for_a_slot_with_nothing_to_cite() -> None:
    loaded = MANIFESTS["section_authoring"]
    # A slot whose section has no SUPPORTED facts at all: nothing may be cited, so the schema must
    # say so without an empty enum (the unit still needs a citation, so no value is ever valid).
    assert_no_empty_enums(authoring_schema(loaded, _task(frozenset(), {})))
    assert_no_empty_enums(
        authoring_schema(loaded, _task(frozenset(), {"limitation:1": frozenset()}))
    )
    assert_no_empty_enums(
        authoring_schema(
            loaded,
            _task(frozenset({"example:001"}), {"limitation:1": frozenset({"example:001"})}),
        )
    )


def test_coherence_schema_carries_no_empty_enum_with_or_without_citable_facts() -> None:
    loaded = MANIFESTS["section_authoring"]
    unit = {"section": "scope_limitations", "slot": "scope", "text": "x", "fact_ids": []}
    assert_no_empty_enums(coherence_schema(loaded, [], []))
    assert_no_empty_enums(coherence_schema(loaded, [unit], [_task(frozenset(), {})]))
    assert_no_empty_enums(coherence_schema(loaded, [unit], [_task(frozenset({"example:001"}), {})]))
