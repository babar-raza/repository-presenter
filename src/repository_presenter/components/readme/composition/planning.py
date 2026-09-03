"""Stage S5: the presentation_planning job wiring - packet, deterministic guard, and plan.json.

Deterministic code evaluates every shell condition it can from the facts (a verified input
format, dependencies, further verified examples, verified links, build assets, a notices file,
an Enterprise Edition target in policy) and tells the job the result; the job decides only what
a fixed rule cannot: which capabilities are core, which example is minimal, which APIs are hubs,
which limitations are material, which links help which section, and whether the API reference
is useful. The guard then checks every selection against the facts and the policy ceilings
before the plan is used.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    placeable_section_ids,
    section_ids,
    shell_packet,
)
from repository_presenter.components.readme.composition.placement import placements
from repository_presenter.components.readme.composition.policy import (
    DEFAULT_POLICY,
    PlanningPolicy,
    policy_packet,
)
from repository_presenter.core.facts import FACT_KINDS, FactsDocument, bounded_records
from repository_presenter.core.llm.prompts import PromptManifest
from repository_presenter.core.registry.models import RegistryEntry

PLAN_FILENAME = "plan.json"
_ASPOSE_DOMAINS = ("aspose.com", "aspose.org")


def _supported(facts: FactsDocument, kind: str) -> list[str]:
    return [fact.id for fact in facts.by_kind(kind) if fact.polarity == "SUPPORTED"]  # type: ignore[arg-type]


def section_conditions(
    facts: FactsDocument, policy: PlanningPolicy = DEFAULT_POLICY
) -> dict[str, bool | None]:
    """Whether each section's condition holds: True, False, or None when the plan decides."""
    input_formats = [i for i in _supported(facts, "format") if i.startswith("format:input.")]
    links = [
        fact.id
        for fact in facts.by_kind("link_target")
        if fact.polarity == "SUPPORTED" and fact.value.startswith(("http://", "https://"))
    ]
    evaluated: dict[str, bool | None] = {
        "at_a_glance": bool(input_formats),
        "dependencies": bool(_supported(facts, "dependency")),
        "additional_examples": len(_supported(facts, "example")) >= 2,
        "api_reference": None if _supported(facts, "public_symbol") else False,
        "documentation_resources": bool(links),
        "development_testing": bool(facts.by_kind("build_test_asset")),
        "enterprise_relationship": policy.enterprise_target_url is not None,
        "third_party_notices": bool(facts.by_kind("third_party_notices")),
    }
    return {
        section.id: True if section.required else evaluated[section.id]
        for section in SEMANTIC_SHELL
    }


def planning_packet(
    entry: RegistryEntry,
    facts: FactsDocument,
    investigation: dict[str, Any],
    dispositions: dict[str, Any],
    manifest: PromptManifest,
    policy: PlanningPolicy = DEFAULT_POLICY,
) -> dict[str, Any]:
    conditions = section_conditions(facts, policy)
    shell = [
        {**section, "condition_holds": conditions[section["id"]]} for section in shell_packet()
    ]
    kinds = manifest.packet.fact_kinds or FACT_KINDS
    return {
        "repository": entry.repository,
        "facts": bounded_records(facts, kinds),
        "investigation": investigation,
        "dispositions": dispositions,
        "shell": shell,
        "policy": policy_packet(policy),
    }


def plan_checks(
    output: dict[str, Any],
    facts: FactsDocument,
    policy: PlanningPolicy = DEFAULT_POLICY,
    dispositions: dict[str, Any] | None = None,
    ecosystem: str = "",
) -> list[str]:
    """Why the plan may not be used, beyond schema and binding; empty when every rule holds.

    Two rules normalise or fail closed here because planning is where they are first knowable:
    every further verified example belongs in Additional Examples (README_CONTRACT.md section 2
    row 12), so a missing one is appended and the section included; and a placed inherited unit
    whose destination the plan excludes is never dropped silently (section 3), so the plan is
    asked to include the destination, and a second refusal fails the transaction naming the unit.
    """
    errors: list[str] = []
    conditions = section_conditions(facts, policy)
    required = {section.id for section in SEMANTIC_SHELL if section.required}
    decisions = {entry["section_id"]: entry for entry in output.get("sections", [])}
    ids = [entry["section_id"] for entry in output.get("sections", [])]
    if sorted(ids) != sorted(section_ids()) or len(ids) != len(set(ids)):
        errors.append("sections must carry exactly one decision for every shell section")
    included = {section for section, entry in decisions.items() if entry.get("include")}
    verified_examples = sorted(
        fact.id for fact in facts.by_kind("example") if fact.polarity == "SUPPORTED"
    )
    quick = output.get("quick_start_example_id")
    second = output.get("second_quick_start_example_id")
    starts = {quick, second} - {None}
    additional = [i for i in output.get("additional_example_ids", []) if i not in starts]
    missing = [i for i in verified_examples if i not in starts and i not in additional]
    # The facts-only condition counts every verified example; the plan's quick starts consume
    # some, so Additional Examples holds only when a further example remains.
    conditions["additional_examples"] = bool(set(verified_examples) - starts)
    if missing:
        output["additional_example_ids"] = additional + missing
        entry = decisions.get("additional_examples")
        if entry is not None and not entry.get("include"):
            entry["include"] = True
            entry["reason"] = "every further verified example is presented"
            included.add("additional_examples")
    if dispositions is not None:
        for placement in placements(output, dispositions, facts, ecosystem):
            if placement.outcome == "excluded":
                errors.append(
                    f"section {placement.destination} is excluded but the reconciliation placed "
                    f"{placement.unit_id} there; include it, or the transaction fails closed "
                    "naming the unit"
                )
        placeable = placeable_section_ids()
        for entry in dispositions.get("dispositions", []):
            destination = entry.get("destination_section")
            unit_type = str(entry.get("unit_id", "")).rsplit(".", 1)[-1]
            if (
                entry.get("disposition") == "SUPERSEDE_REDUNDANT"
                and destination in placeable
                and destination not in included
                and conditions.get(destination) is not False  # reconciliation defers those
                and unit_type not in ("heading", "badge_row")  # the shell owns these anyway
            ):
                errors.append(
                    f"section {destination} is excluded but the reconciliation relies on its "
                    f"content to supersede {entry.get('unit_id')}; include it, or the "
                    "transaction fails closed naming the unit"
                )
    for section, holds in conditions.items():
        if section not in decisions:
            continue
        if section in required and section not in included:
            errors.append(f"section {section} is required and cannot be omitted")
        elif holds is False and section in included:
            errors.append(f"section {section}: its condition does not hold, so it is omitted")
        elif holds is True and section not in required and section not in included:
            errors.append(f"section {section}: its condition holds, so it is included")

    capabilities = output.get("core_capabilities", [])
    if not policy.capabilities_min <= len(capabilities) <= policy.capabilities_max:
        errors.append(
            f"core_capabilities must number {policy.capabilities_min} to "
            f"{policy.capabilities_max}; got {len(capabilities)}"
        )
    titles = [item.get("title", "").strip().lower() for item in capabilities]
    if len(set(titles)) != len(titles):
        errors.append("core_capabilities titles must be distinct")

    supported = {fact.id for fact in facts.facts if fact.polarity == "SUPPORTED"}
    input_formats = {i for i in supported if i.startswith("format:input.")}
    output_formats = {i for i in supported if i.startswith("format:output.")}
    glance = output.get("at_a_glance")
    if "at_a_glance" in included:
        if glance is None:
            errors.append("at_a_glance is included, so its formats and capabilities are given")
        else:
            bad_inputs = set(glance.get("input_format_ids", [])) - input_formats
            bad_outputs = set(glance.get("output_format_ids", [])) - output_formats
            bad_titles = set(glance.get("capability_titles", [])) - {
                item.get("title", "") for item in capabilities
            }
            if bad_inputs:
                errors.append(
                    f"at_a_glance inputs are not verified input formats: {sorted(bad_inputs)}"
                )
            if bad_outputs:
                errors.append(
                    f"at_a_glance outputs are not verified output formats: {sorted(bad_outputs)}"
                )
            if bad_titles:
                errors.append(
                    f"at_a_glance capabilities are not core capabilities: {sorted(bad_titles)}"
                )
    elif glance is not None:
        errors.append("at_a_glance is omitted, so it is null")

    examples = {i for i in supported if i.startswith("example:")}
    quick = output.get("quick_start_example_id")
    if quick not in examples:
        errors.append(f"quick_start_example_id must be a SUPPORTED example; got {quick!r}")
    second = output.get("second_quick_start_example_id")
    if second is not None and (second not in examples or second == quick):
        errors.append(
            "second_quick_start_example_id must be a SUPPORTED example other than the first; "
            f"got {second!r}"
        )
    additional = output.get("additional_example_ids", [])
    if quick in additional or second in additional or len(set(additional)) != len(additional):
        errors.append("additional_example_ids must be distinct and exclude the quick start")
    if ("additional_examples" in included) != bool(additional):
        errors.append(
            "additional_example_ids are given exactly when additional_examples is included"
        )

    hubs = output.get("api_hubs", [])
    symbols = {i for i in supported if i.startswith("public_symbol:")}
    hub_ids = [hub.get("symbol_fact_id") for hub in hubs]
    if len(hubs) > policy.api_hubs_max:
        errors.append(f"api_hubs exceed the ceiling of {policy.api_hubs_max}")
    if len(set(hub_ids)) != len(hub_ids) or any(hub not in symbols for hub in hub_ids):
        errors.append("api_hubs must be distinct public_symbol facts")
    if ("api_reference" in included) != bool(hubs):
        errors.append("api_hubs are given exactly when api_reference is included")

    for item in output.get("material_limitations", []):
        if not item.get("fact_ids") and not item.get("unit_ids"):
            errors.append("a material limitation cites at least one fact or inherited unit")

    link_facts = {
        fact.id: fact.value for fact in facts.by_kind("link_target") if fact.polarity == "SUPPORTED"
    }
    aspose = 0
    targets = [link.get("link_fact_id") for link in output.get("links", [])]
    for target in sorted({t for t in targets if targets.count(t) > 1}):
        errors.append(f"link {target!r} is assigned more than once; never the same target twice")
    for link in output.get("links", []):
        target = link.get("link_fact_id")
        section = link.get("section_id")
        if target not in link_facts:
            errors.append(f"link {target!r} is not a verified link target")
        elif any(domain in link_facts[target] for domain in _ASPOSE_DOMAINS):
            aspose += 1
        if section not in included:
            errors.append(
                f"link {target!r} is assigned to a section that is not included: {section!r}"
            )
    if aspose > policy.aspose_links_max:
        errors.append(f"Aspose links exceed the ceiling of {policy.aspose_links_max}: {aspose}")
    for deviation in output.get("deviations", []):
        if deviation.get("section_id") not in section_ids():
            errors.append(f"deviation names an unknown section {deviation.get('section_id')!r}")
    return errors


def summarize_plan(output: dict[str, Any]) -> str:
    included = [entry["section_id"] for entry in output.get("sections", []) if entry.get("include")]
    return (
        f"sections {len(included)}/{len(section_ids())}, "
        f"capabilities {len(output.get('core_capabilities', []))}, "
        f"hubs {len(output.get('api_hubs', []))}, "
        f"examples 1+{len(output.get('additional_example_ids', []))}, "
        f"links {len(output.get('links', []))}, "
        f"limitations {len(output.get('material_limitations', []))}"
    )


def write_plan(output: dict[str, Any], path: Path) -> str:
    """Write the accepted plan as deterministic JSON; returns its SHA-256."""
    data = (json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()
