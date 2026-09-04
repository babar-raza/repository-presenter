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

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from repository_presenter.components.readme.composition.components.shell import (
    SEMANTIC_SHELL,
    Section,
    section_ids,
    shell_packet,
)
from repository_presenter.components.readme.composition.placement import placements
from repository_presenter.components.readme.composition.policy import (
    DEFAULT_POLICY,
    PlanningPolicy,
    policy_packet,
)
from repository_presenter.components.readme.evidence.facts.product_pages import (
    banner_target,
    enterprise_target,
)
from repository_presenter.core.facts import FACT_KINDS, FactsDocument, bounded_records
from repository_presenter.core.llm.prompts import LoadedManifest, PromptManifest
from repository_presenter.core.registry.models import RegistryEntry

PLAN_FILENAME = "plan.json"
_ASPOSE_DOMAINS = ("aspose.com", "aspose.org")


def _supported(facts: FactsDocument, kind: str) -> list[str]:
    return [fact.id for fact in facts.by_kind(kind) if fact.polarity == "SUPPORTED"]  # type: ignore[arg-type]


def section_conditions(
    facts: FactsDocument, policy: PlanningPolicy = DEFAULT_POLICY
) -> dict[str, bool | None]:
    """Whether each section's condition holds: True, False, or None when the plan decides."""
    links = [
        fact.id
        for fact in facts.by_kind("link_target")
        if fact.polarity == "SUPPORTED" and fact.value.startswith(("http://", "https://"))
    ]
    evaluated: dict[str, bool | None] = {
        "banner": banner_target(facts.facts) is not None,  # README_CONTRACT.md row 3
        # README_CONTRACT.md row 6: a valid plan carries at least three verified core
        # capabilities (the policy minimum), so the diagram always appears; Starting Points
        # follow the verified input formats and are absent without one.
        "at_a_glance": True,
        "dependencies": bool(_supported(facts, "dependency")),
        "additional_examples": len(_supported(facts, "example")) >= 2,
        "api_reference": True,  # README_CONTRACT.md row 14: Required
        "documentation_resources": bool(links),
        "development_testing": bool(facts.by_kind("build_test_asset")),
        "enterprise_relationship": enterprise_target(facts.facts) is not None,
        "third_party_notices": bool(facts.by_kind("third_party_notices")),
    }
    return {
        section.id: True if section.required else evaluated[section.id]
        for section in SEMANTIC_SHELL
    }


def _selectable_dispositions(dispositions: dict[str, Any], facts: FactsDocument) -> dict[str, Any]:
    """The dispositions as the planner may act on them: only the fact IDs a plan may cite.

    A disposition legitimately cites a CONTRADICTED or UNRESOLVED fact - that is why it omits or
    defers its unit - while the plan's own binding admits SUPPORTED facts only. Showing the
    planner an ID its reply may not carry is cause RC1 in docs/RESEARCH_AND_GUIDELINES.md
    section 27.2: the canary's planner copied example:008 from here and was rejected twice, and
    the transaction failed closed. The destinations and unit IDs are untouched; only the
    citations a plan may not reuse are dropped, and plan_checks still sees the whole document.
    """
    supported = {fact.id for fact in facts.facts if fact.polarity == "SUPPORTED"}
    entries = [
        {
            key: ([i for i in value if i in supported] if key == "fact_ids" else value)
            for key, value in entry.items()
        }
        for entry in dispositions.get("dispositions", [])
    ]
    return {**dispositions, "dispositions": entries}


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
        "dispositions": _selectable_dispositions(dispositions, facts),
        "shell": shell,
        "policy": policy_packet(policy),
    }


def _decision(section: Section, holds: bool | None) -> dict[str, Any]:
    """One inclusion decision, composed by code from the shell and the evaluated condition."""
    if section.required:
        return {"section_id": section.id, "include": True, "reason": "the shell requires it"}
    return {
        "section_id": section.id,
        "include": bool(holds),
        "reason": "its condition " + ("holds" if holds else "does not hold"),
    }


def planning_schema(manifest: LoadedManifest, facts: FactsDocument) -> dict[str, Any]:
    """The planning schema specialised for this repository: the example selections carry the
    verified example IDs as an enum, so a schema-valid plan cannot name a contradicted or
    unresolved example (RESEARCH_AND_GUIDELINES.md section 27.5 D1; the canary was rejected
    twice for naming a CONTRADICTED example, which is cause RC1 in section 27.2)."""
    schema = copy.deepcopy(manifest.manifest.output.schema_)
    verified = sorted(fact.id for fact in facts.by_kind("example") if fact.polarity == "SUPPORTED")
    properties = schema["properties"]
    deviations = properties.get("deviations", {}).get("items", {}).get("properties", {})
    if "section_id" in deviations:
        # The canary's planner named a deviation against 'links', which is not a shell section.
        deviations["section_id"] = {"type": "string", "enum": list(section_ids())}
    if not verified:
        return schema
    properties["quick_start_example_id"]["enum"] = verified
    properties["additional_example_ids"]["items"]["enum"] = verified
    for field in ("second_quick_start_example_id", "flagship_example_id"):
        properties[field]["enum"] = [*verified, None]
    return schema


def _capability_facts_apart(capabilities: list[dict[str, Any]]) -> list[str]:
    """Why two capabilities may not rest on the same fact without saying so.

    Overlapping fact sets are why a subset check cannot separate one capability's prose from
    another's even in principle (docs/RESEARCH_AND_GUIDELINES.md section 27.2 RC2). The sets are
    therefore pairwise disjoint unless every capability citing a shared fact declares it, which
    keeps a genuinely shared example usable and leaves the rest of each set discriminating
    (section 27.5 D2).
    """
    errors: list[str] = []
    holders: dict[str, set[int]] = {}
    for index, item in enumerate(capabilities, start=1):
        cited = set(item.get("fact_ids", []))
        stray = sorted(set(item.get("shared_fact_ids") or []) - cited)
        if stray:
            errors.append(
                f"capability {index} declares shared facts it does not cite: {', '.join(stray)}; "
                "shared_fact_ids is a subset of that capability's fact_ids"
            )
        for fact_id in cited:
            holders.setdefault(fact_id, set()).add(index)
    for fact_id, holding in sorted(holders.items()):
        if len(holding) < 2:
            continue
        undeclared = sorted(
            index
            for index in holding
            if fact_id not in set(capabilities[index - 1].get("shared_fact_ids") or [])
        )
        if undeclared:
            errors.append(
                f"fact {fact_id} is cited by capabilities "
                f"{', '.join(str(index) for index in sorted(holding))}; give each capability its "
                "own facts, or list the fact in shared_fact_ids of every capability that cites it "
                f"(missing from {', '.join(str(index) for index in undeclared)})"
            )
    return errors


def plan_checks(
    output: dict[str, Any],
    facts: FactsDocument,
    policy: PlanningPolicy = DEFAULT_POLICY,
    dispositions: dict[str, Any] | None = None,
    ecosystem: str = "",
) -> list[str]:
    """Why the plan may not be used, beyond schema and binding; empty when every rule holds.

    The shell's inclusion decisions are composed here, not asked for: deterministic code already
    evaluates every condition from the facts, so asking the model to restate the decision list and
    then rejecting it for restating it wrongly is RESEARCH_AND_GUIDELINES.md section 27.2's RC1
    (section 27.5 D1). Two rules still normalise or fail closed because planning is where they are
    first knowable: every further verified example belongs in Additional Examples
    (README_CONTRACT.md section 2 row 12), so a missing one is appended and the condition holds;
    and a placed inherited unit whose destination is excluded at this revision is never dropped
    silently (section 3), so the transaction fails closed naming the unit.
    """
    errors: list[str] = []
    conditions = section_conditions(facts, policy)
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
    output["sections"] = [_decision(section, conditions[section.id]) for section in SEMANTIC_SHELL]
    decisions = {entry["section_id"]: entry for entry in output["sections"]}
    included = {section for section, entry in decisions.items() if entry["include"]}
    if dispositions is not None:
        for placement in placements(output, dispositions, facts, ecosystem):
            if placement.outcome == "excluded":
                errors.append(
                    f"section {placement.destination} is excluded at this revision but the "
                    f"reconciliation placed {placement.unit_id} there; place the unit in an "
                    "included section or defer it, or the transaction fails closed naming it"
                )
    capabilities = output.get("core_capabilities", [])
    if not policy.capabilities_min <= len(capabilities) <= policy.capabilities_max:
        errors.append(
            f"core_capabilities must number {policy.capabilities_min} to "
            f"{policy.capabilities_max}; got {len(capabilities)}"
        )
    titles = [item.get("title", "").strip().lower() for item in capabilities]
    if len(set(titles)) != len(titles):
        errors.append("core_capabilities titles must be distinct")
    errors.extend(_capability_facts_apart(capabilities))

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
    if glance is not None:
        titles = glance.get("capability_titles", [])
        if len(titles) < 3:
            errors.append("at_a_glance needs at least three capability titles")
        for title in titles:
            # Geometry-safe labels (README_CONTRACT.md section 2.1): a longer title is
            # shortened here at planning, never clipped at render.
            for token in title.split():
                if len(token) > 28:
                    errors.append(
                        "at_a_glance capability title carries an unbroken token over 28 "
                        f"characters: {token!r}; shorten the title"
                    )

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
    flagship = output.get("flagship_example_id")
    if flagship is not None and flagship not in additional:
        # README_CONTRACT.md row 12: the flagship is one further example shown visibly.
        errors.append(
            f"flagship_example_id must be one of additional_example_ids; got {flagship!r}"
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
