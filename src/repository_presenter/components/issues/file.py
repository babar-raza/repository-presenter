"""Phase 3: file a ``HANDOFF_PENDING`` upstream-defect artifact as a real GitHub issue - gated,
and, in this project's current environment, never armed.

This is the write half ``draft.py``/``redetect.py`` deliberately left unbuilt: `AGENTS.md`
"Security and Effects" and the 2026-09-26 owner ruling recorded in ``docs/DECISION_LOG.md`` both
name the actual ``gh issue create`` call as its own, separately authorized work item. Building the
mechanism is in scope here; firing it live is not - the current execution gate
(``project/state.yaml``) is nowhere near the write-authorization gates this needs, and ``AGENTS.md``
is explicit: "Do not perform a target write unless the current execution gate and exact
authorization permit it."

Two independent conditions must both hold before this module ever calls
``core/github/client.py``'s ``create_issue``, mirroring the layered discipline
``components/metadata/apply.py`` already applies to its own effect (neuter, then verify, then only
proceed):

1. ``write_authorized(environment)`` - the dedicated, owner-controlled environment variable
   ``REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED`` is set to a truthy value. This is deliberately
   never inferred from a credential's presence or scope: ``GH_TOKEN`` alone already grants every
   *read* this project makes (``AGENTS.md`` names this exact trap - "do not invent write access
   that fires just because credentials happen to be present").
2. A write-scoped token is actually supplied (``GH_ISSUES_WRITE_TOKEN`` - never the read-only
   ``GH_TOKEN``, kept as a distinct, separately-provisioned credential per ``AGENTS.md`` "Write
   credentials exist only in a separate effect job and are short-lived and target-scoped").

Neither condition is met by anything this project's own environment sets today, so
``file_handoff`` always resolves to "not authorized" as things stand - built and tested, never
fired. A third, structural guard makes a duplicate filing impossible even with both gates open: a
handoff whose ``status`` is not ``HANDOFF_PENDING`` is refused outright, so a handoff this module
already filed (``FILED``) - or one some other lifecycle stage already claimed
(``HANDOFF_ACKNOWLEDGED``, ``RESOLVED_UPSTREAM``) - can never be filed a second time. And, mirroring
``AGENTS.md`` "Recheck upstream revision immediately before an effect", the caller may supply a
``recheck`` callable: when given, this module refuses to file anything the recheck cannot freshly
confirm still fires - a stale finding (the defect was already fixed upstream, or the recheck itself
is inconclusive) is never turned into a live issue.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from repository_presenter.components.issues.model import Handoff, IssueRef
from repository_presenter.components.issues.redetect import RedetectionResult
from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import WriteFn, create_issue, default_post

AUTHORIZATION_VARIABLE = "REPOSITORY_PRESENTER_ISSUES_WRITE_AUTHORIZED"
_AUTHORIZED_VALUES = frozenset({"1", "true", "yes"})

_NOT_AUTHORIZED_REASON = (
    f"not authorized: set {AUTHORIZATION_VARIABLE}=1 (owner-controlled) - a token's presence or "
    "scope is never by itself sufficient"
)
_NO_TOKEN_REASON = "no write-scoped token available (GH_ISSUES_WRITE_TOKEN, never GH_TOKEN)"


def write_authorized(environment: Mapping[str, str]) -> bool:
    """``True`` only when the owner has explicitly set ``AUTHORIZATION_VARIABLE`` to a truthy
    value. Absence, an empty string, or any other value is unauthorized - fail closed."""
    return environment.get(AUTHORIZATION_VARIABLE, "").strip().lower() in _AUTHORIZED_VALUES


@dataclass(frozen=True)
class FileResult:
    """The outcome of one ``file_handoff`` call. ``filed`` is ``True`` only when a real
    ``POST /repos/{owner}/{repo}/issues`` call succeeded and returned an issue GitHub actually
    created; every other case is a refusal, named in ``reason``, with no network call made."""

    repository: str
    defect_fingerprint: str
    authorized: bool
    filed: bool
    reason: str
    issue_ref: IssueRef | None


def _not_pending_reason(status: str) -> str:
    return (
        f"status is {status!r}, not HANDOFF_PENDING - only a pending handoff may be filed "
        "(this is the duplicate-filing guard: an already-FILED handoff is never re-filed)"
    )


def file_handoff(
    handoff: Handoff,
    *,
    token: str | None,
    environment: Mapping[str, str],
    create: WriteFn = default_post,
    recheck: Callable[[], RedetectionResult] | None = None,
) -> FileResult:
    """File ``handoff`` as a real GitHub issue - but only past every gate in this module's own
    docstring. Every early return below makes no network call at all."""

    def _refuse(authorized: bool, reason: str) -> FileResult:
        return FileResult(
            repository=handoff.repository,
            defect_fingerprint=handoff.defect_fingerprint,
            authorized=authorized,
            filed=False,
            reason=reason,
            issue_ref=None,
        )

    if not write_authorized(environment):
        return _refuse(False, _NOT_AUTHORIZED_REASON)

    if not token:
        return _refuse(True, _NO_TOKEN_REASON)

    if handoff.status != "HANDOFF_PENDING":
        return _refuse(True, _not_pending_reason(handoff.status))

    if recheck is not None:
        result = recheck()
        if result.still_fires is False:
            return _refuse(
                True,
                "recheck: this handoff's own triggering_check no longer fires at the "
                f"repository's current state ({result.note}) - refusing to file a stale finding",
            )
        if result.still_fires is None:
            return _refuse(
                True,
                f"recheck: inconclusive ({result.note}) - refusing to file without a fresh "
                "confirmation that the defect still fires",
            )

    owner, name = handoff.repository.split("/", 1)
    try:
        created = create_issue(
            owner,
            name,
            title=handoff.suggested_issue_title,
            body=handoff.suggested_issue_body,
            token=token,
            write=create,
        )
    except RepositoryMetadataError as exc:
        return _refuse(True, str(exc))

    return FileResult(
        repository=handoff.repository,
        defect_fingerprint=handoff.defect_fingerprint,
        authorized=True,
        filed=True,
        reason="filed",
        issue_ref=IssueRef(number=created.number, url=created.url),
    )
