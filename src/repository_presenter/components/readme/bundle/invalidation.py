"""Typed invalidation scopes: which stage's inputs changed, the stage to re-enter, and the state.

docs/STATE_MACHINE.md section 9: "A change reopens the earliest affected stage of the candidates
that consumed it and nothing else. A validator or reviewer change re-checks accepted candidates;
it invalidates one only on a factual, safety, or protected-content failure." and "Factual, safety,
protected-content, or severe acceptance defects invalidate an accepted candidate. Non-critical
presentation improvements create ``VALID_UPDATE_AVAILABLE`` without mislabeling the published
README as factually invalid." plans/idea.md: "A non-critical later template version leaves an
accepted README ``VALID_UPDATE_AVAILABLE``; only factual, safety, protected-content, or severe
acceptance defects make it invalid."

A scope is one class of consumed input. Each names the stage it re-enters and the manifest state
a change to it produces, in :data:`SCOPES`, a table. Only the ``facts`` scope - the source
revision and tree, what extraction ran under, and the fact records themselves - is itself a
factual input, so only it invalidates (``INVALIDATED``, the routing state of section 4.1). Every
other scope is an agentic, template, validator or reviewer input: the candidate it sealed under
stays valid and an update is available (``VALID_UPDATE_AVAILABLE``). A factual, safety or
protected-content *failure* found while re-checking is a different path - a failing blocking
check, ``seal.invalidates`` - and is not a scope.

:data:`DEPENDENCY_SCOPES`, :data:`PROMPT_SCOPES` and :data:`COMPONENT_SCOPES` map each
``dependencies.json`` input class (the names ``evaluation.evaluate`` emits) to its scope;
:data:`ARTIFACT_SCOPES` maps a sealed artifact to the
scope of the stage that wrote it, used only when a rerun's bytes differ and no changed input
explains it. Both are tables: a new input class or artifact is one row, and a lookup that finds
none raises rather than guessing a state (a guessed state is a hidden policy).

Nothing here is a hash of anything: a scope is derived from the candidate's own consumed inputs,
so a component the candidate did not consume cannot reopen it and no global control-plane hash
exists (AGENTS.md; docs/STATE_MACHINE.md section 9).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from repository_presenter.core.errors import PresenterError

STATE_INVALIDATED = "INVALIDATED"
STATE_UPDATE_AVAILABLE = "VALID_UPDATE_AVAILABLE"

STATE_ORDER: tuple[str, ...] = (
    "EXTRACTING",
    "INVESTIGATING",
    "RECONCILING",
    "PLANNING",
    "COMPOSING",
    "VALIDATING",
    "REVIEWING",
)


class ScopeError(PresenterError):
    """An input class or artifact has no invalidation scope; the routing fails closed."""

    exit_code = 1


@dataclass(frozen=True)
class Scope:
    name: str
    stage: str  # the earliest stage a change to this scope's inputs re-enters
    state: str  # the manifest state such a change produces
    consumes: str  # what the candidate consumed that this scope covers


SCOPES: tuple[Scope, ...] = (
    Scope(
        "facts",
        "EXTRACTING",
        STATE_INVALIDATED,
        "source revision and tree, the extraction environment, the fact records",
    ),
    Scope(
        "evidence",
        "INVESTIGATING",
        STATE_UPDATE_AVAILABLE,
        "the investigation prompt, route and schema",
    ),
    Scope(
        "reconciliation",
        "RECONCILING",
        STATE_UPDATE_AVAILABLE,
        "the reconciliation prompt, route and contract",
    ),
    Scope(
        "presentation",
        "RECONCILING",
        STATE_UPDATE_AVAILABLE,
        "template components: the semantic shell and the renderer",
    ),
    Scope(
        "planning",
        "PLANNING",
        STATE_UPDATE_AVAILABLE,
        "the planning prompt and route, the composition policy",
    ),
    Scope(
        "authoring",
        "COMPOSING",
        STATE_UPDATE_AVAILABLE,
        "the section-authoring prompt and route, the normalisation logic",
    ),
    Scope(
        "validator",
        "VALIDATING",
        STATE_UPDATE_AVAILABLE,
        "the contract version, each blocking check and the validator version",
    ),
    Scope(
        "reviewer",
        "REVIEWING",
        STATE_UPDATE_AVAILABLE,
        "the review and repair prompts and routes, the review logic, the acceptance profile",
    ),
)
SCOPE_BY_NAME: dict[str, Scope] = {scope.name: scope for scope in SCOPES}
# SCOPES is written in stage order; a tie between scopes that share a stage keeps table order.
_SCOPE_ORDER: dict[str, int] = {scope.name: index for index, scope in enumerate(SCOPES)}

# dependencies.json input class -> scope. An undotted class is one row; a dotted class
# (``prompts.<job>``, ``components.<name>``, ``environment.<field>``) is looked up by its family and
# then by the name after the dot, and a name the family has no row for takes the family default
# (the stages evaluation.py has always defaulted an unknown prompt and component to). A class with
# no row at all raises ScopeError.
DEPENDENCY_SCOPES: dict[str, str] = {
    "source": "facts",
    "facts": "facts",
    "contract_version": "validator",
    "validators": "validator",
    "acceptance_profile_version": "reviewer",
    "policy": "planning",
}
PROMPT_SCOPES: dict[str, str] = {
    "repository_investigation": "evidence",
    "source_reconciliation": "reconciliation",
    "presentation_planning": "planning",
    "section_authoring": "authoring",
    "independent_review": "reviewer",
    "targeted_repair": "reviewer",
}
COMPONENT_SCOPES: dict[str, str] = {
    "shell": "presentation",
    "renderer": "presentation",
    "normalisation": "authoring",
    "reviewer_logic": "reviewer",
}
# family -> (its per-name rows, the scope of a name it has no row for)
FAMILY_SCOPES: dict[str, tuple[dict[str, str], str]] = {
    "environment": ({}, "facts"),
    "prompts": (PROMPT_SCOPES, "evidence"),
    "components": (COMPONENT_SCOPES, "presentation"),
}
# The reviewer's own deterministic logic (``review.py``'s scope_defect, quote_located and
# review_checks) reopens COMPOSING rather than its scope's REVIEWING: composing is upstream of
# reviewing, so nothing under-reopens (docs/STATE_MACHINE.md section 9, EVAL-01, 2026-09-10).
STAGE_OVERRIDES: dict[str, str] = {"components.reviewer_logic": "COMPOSING"}

# A sealed artifact -> the scope of the stage that wrote it. dependencies.json records the
# consumed inputs; the one field no evaluated input covers is the protected-content fingerprint,
# which the accepted dispositions produce.
ARTIFACT_SCOPES: dict[str, str] = {
    "facts.json": "facts",
    "examples.json": "facts",
    "investigation.json": "evidence",
    "dispositions.json": "reconciliation",
    "dependencies.json": "reconciliation",
    "plan.json": "planning",
    "README.md": "authoring",
    "README.patch": "authoring",
    "content_units.json": "authoring",
    "raw_calls.json": "authoring",
    "repairs.json": "authoring",
    "validation.json": "validator",
    "review.json": "reviewer",
}


def scope_of(dependency: str) -> Scope:
    """The scope of one ``dependencies.json`` input class, e.g. ``prompts.section_authoring``."""
    family, _, name = dependency.partition(".")
    scope_name = DEPENDENCY_SCOPES.get(dependency)
    if scope_name is None and name and family in FAMILY_SCOPES:
        rows, default = FAMILY_SCOPES[family]
        scope_name = rows.get(name, default)
    if scope_name is None:
        raise ScopeError(f"no invalidation scope for the dependency {dependency!r}")
    return SCOPE_BY_NAME[scope_name]


def reopening_stage(dependency: str) -> str:
    """The stage a change to this input class re-enters: its scope's, unless overridden."""
    return STAGE_OVERRIDES.get(dependency) or scope_of(dependency).stage


def scope_of_artifact(artifact: str) -> Scope:
    name = ARTIFACT_SCOPES.get(artifact)
    if name is None:
        raise ScopeError(f"no invalidation scope for the sealed artifact {artifact!r}")
    return SCOPE_BY_NAME[name]


@dataclass(frozen=True)
class Routing:
    """Where a change lands: every scope that changed, the one that decided, and the result."""

    scopes: tuple[str, ...]  # in stage order
    triggering_scope: str | None  # an invalidating scope if any changed, else the earliest
    state: str | None  # None when nothing changed
    stage: str | None  # the earliest stage to re-enter
    basis: str  # "inputs" (changed dependencies) or "artifacts" (drift with no changed input)

    @property
    def invalidates(self) -> bool:
        return self.state == STATE_INVALIDATED


def _stage_index(stage: str) -> int:
    return STATE_ORDER.index(stage)


def route(dependencies: Iterable[str], artifacts: Iterable[str] = ()) -> Routing:
    """Route a change by the inputs that changed, or by the artifacts that differ when no input
    explains the difference (a rerun whose bytes moved with every consumed input unchanged).

    Inputs win when there are any: a changed prompt rewrites the README downstream of it, and
    attributing that rewrite to a second scope would name a cause the candidate did not consume.
    """
    changed = sorted(set(dependencies))
    if changed:
        basis = "inputs"
        stages = {dependency: reopening_stage(dependency) for dependency in changed}
        scopes = {scope_of(dependency).name for dependency in changed}
    else:
        basis = "artifacts"
        differing = sorted(set(artifacts))
        stages = {name: scope_of_artifact(name).stage for name in differing}
        scopes = {scope_of_artifact(name).name for name in differing}
    if not scopes:
        return Routing((), None, None, None, basis)
    ordered = sorted(scopes, key=_SCOPE_ORDER.__getitem__)
    decisive = [name for name in ordered if SCOPE_BY_NAME[name].state == STATE_INVALIDATED]
    triggering = (decisive or ordered)[0]
    earliest = min(stages.values(), key=_stage_index)
    return Routing(tuple(ordered), triggering, SCOPE_BY_NAME[triggering].state, earliest, basis)
