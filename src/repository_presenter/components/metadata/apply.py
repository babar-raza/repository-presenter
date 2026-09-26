"""Phase 2: apply a ``proposal.py`` diff to GitHub's real repository metadata - gated, and, in this
project's current environment, never armed.

This is the write half workstream 2's Phase 0/1 (``capture.py``/``proposal.py``) deliberately left
unbuilt, per the 2026-09-17 17:05 UTC owner ruling recorded in ``docs/DECISION_LOG.md``: "the actual
write calls stay gated on ``OWNER-04``/G5, same as every other write this session." Building the
mechanism is in scope; firing it live is not - the current execution gate (``project/state.yaml``,
``G3_PYTHON_COHORT``) is nowhere near the write-authorization gates (``G6_PROPOSAL_EFFECT_PROOF``,
``G7``), and ``AGENTS.md`` is explicit: "Do not perform a target write unless the current execution
gate and exact authorization permit it."

Two independent conditions must both hold before this module ever calls
``core/github/client.py``'s ``update_repository``/``replace_topics``, mirroring the layered
discipline ``core/git_safety/clone.py`` already applies to its own effect (neuter, then verify,
then only proceed):

1. ``write_authorized(environment)`` - the dedicated, owner-controlled environment variable
   ``REPOSITORY_PRESENTER_METADATA_WRITE_AUTHORIZED`` is set to a truthy value. This is deliberately
   never inferred from a credential's presence or scope: ``GH_TOKEN`` alone already grants every
   *read* this project makes (``AGENTS.md`` names this exact trap - "do not invent write access that
   fires just because credentials happen to be present").
2. A write-scoped token is actually supplied (``GH_METADATA_WRITE_TOKEN`` - never the read-only
   ``GH_TOKEN``, kept as a distinct, separately-provisioned credential per ``AGENTS.md`` "Write
   credentials exist only in a separate effect job and are short-lived and target-scoped").

Neither condition is met by anything this project's own environment sets today, so
``apply_metadata_diff`` always resolves to "not authorized" as things stand - built and tested,
never fired. Even when both hold, this module re-observes GitHub's live state immediately before
writing (mirroring ``AGENTS.md`` "Recheck upstream revision immediately before an effect") and
refuses the entire write, naming which field, if the live state has drifted from what the diff was
computed against - never a blind overwrite of a race it cannot see.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from repository_presenter.components.metadata.proposal import RepoMetadataDiff
from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import (
    ObservedRepository,
    WriteFn,
    default_patch,
    default_put,
    replace_topics,
    update_repository,
)

AUTHORIZATION_VARIABLE = "REPOSITORY_PRESENTER_METADATA_WRITE_AUTHORIZED"
_AUTHORIZED_VALUES = frozenset({"1", "true", "yes"})

_NOT_AUTHORIZED_REASON = (
    f"not authorized: set {AUTHORIZATION_VARIABLE}=1 (owner-controlled) - a token's presence or "
    "scope is never by itself sufficient"
)
_NO_TOKEN_REASON = "no write-scoped token available (GH_METADATA_WRITE_TOKEN, never GH_TOKEN)"
_NO_CHANGE_REASON = "no change needed"


def write_authorized(environment: Mapping[str, str]) -> bool:
    """``True`` only when the owner has explicitly set ``AUTHORIZATION_VARIABLE`` to a truthy
    value. Absence, an empty string, or any other value is unauthorized - fail closed."""
    return environment.get(AUTHORIZATION_VARIABLE, "").strip().lower() in _AUTHORIZED_VALUES


@dataclass(frozen=True)
class FieldOutcome:
    """One field's own outcome: whether the diff wanted a change, and whether it happened."""

    field: str
    changed: bool
    applied: bool
    reason: str


@dataclass(frozen=True)
class ApplyResult:
    """The outcome of one ``apply_metadata_diff`` call, one :class:`FieldOutcome` per field.

    ``description``/``homepage`` share a single ``PATCH`` call (GitHub's own endpoint accepts both
    together); ``topics`` is a separate ``PUT`` call to a different endpoint. A failure in one call
    never blocks the other.
    """

    repository: str
    authorized: bool
    description: FieldOutcome
    homepage: FieldOutcome
    topics: FieldOutcome

    @property
    def wrote_anything(self) -> bool:
        return self.description.applied or self.homepage.applied or self.topics.applied


def _drifted_fields(diff: RepoMetadataDiff, live: ObservedRepository) -> tuple[str, ...]:
    """Which of the fields this diff intends to change have moved on GitHub since Phase 0 captured
    ``diff``'s own baseline - checked only for fields the diff actually proposes changing."""
    drifted = []
    if diff.description_changed and live.description != diff.observed_description:
        drifted.append("description")
    if diff.homepage_changed and live.homepage != diff.observed_homepage:
        drifted.append("homepage")
    if diff.topics_changed and set(live.topics) != set(diff.observed_topics):
        drifted.append("topics")
    return tuple(drifted)


def apply_metadata_diff(
    diff: RepoMetadataDiff,
    owner: str,
    name: str,
    *,
    token: str | None,
    environment: Mapping[str, str],
    patch: WriteFn = default_patch,
    put: WriteFn = default_put,
    refetch: Callable[[], ObservedRepository] | None = None,
) -> ApplyResult:
    """Apply ``diff`` to the real repository - but only past both gates in this module's own
    docstring. Every early return below makes no network call at all; a field the diff did not
    propose changing is reported ``changed=False`` and is never touched either way.
    """

    def _skip(field: str, changed: bool, reason: str) -> FieldOutcome:
        return FieldOutcome(field=field, changed=changed, applied=False, reason=reason)

    def _skip_all(authorized: bool, reason: str) -> ApplyResult:
        return ApplyResult(
            repository=diff.repository,
            authorized=authorized,
            description=_skip("description", diff.description_changed, reason),
            homepage=_skip("homepage", diff.homepage_changed, reason),
            topics=_skip("topics", diff.topics_changed, reason),
        )

    if not write_authorized(environment):
        return _skip_all(False, _NOT_AUTHORIZED_REASON)

    if not token:
        return _skip_all(True, _NO_TOKEN_REASON)

    if not diff.has_changes:
        return _skip_all(True, _NO_CHANGE_REASON)

    if refetch is not None:
        live = refetch()
        drifted = _drifted_fields(diff, live)
        if drifted:
            reason = (
                "GitHub's live metadata changed since this diff was captured "
                f"({', '.join(drifted)}) - re-run metadata capture before applying; nothing written"
            )
            return _skip_all(True, reason)

    description = _skip("description", diff.description_changed, _NO_CHANGE_REASON)
    homepage = _skip("homepage", diff.homepage_changed, _NO_CHANGE_REASON)
    topics = _skip("topics", diff.topics_changed, _NO_CHANGE_REASON)

    if diff.description_changed or diff.homepage_changed:
        try:
            update_repository(
                owner,
                name,
                description=diff.proposed.description if diff.description_changed else None,
                homepage=diff.proposed.homepage if diff.homepage_changed else None,
                token=token,
                write=patch,
            )
        except RepositoryMetadataError as exc:
            failure_reason = str(exc)
            if diff.description_changed:
                description = FieldOutcome("description", True, False, failure_reason)
            if diff.homepage_changed:
                homepage = FieldOutcome("homepage", True, False, failure_reason)
        else:
            if diff.description_changed:
                description = FieldOutcome("description", True, True, "written")
            if diff.homepage_changed:
                homepage = FieldOutcome("homepage", True, True, "written")

    if diff.topics_changed:
        try:
            replace_topics(owner, name, topics=diff.proposed.topics, token=token, write=put)
        except RepositoryMetadataError as exc:
            topics = FieldOutcome("topics", True, False, str(exc))
        else:
            topics = FieldOutcome("topics", True, True, "written")

    return ApplyResult(diff.repository, True, description, homepage, topics)
