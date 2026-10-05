"""The one write gate: every path that can change a target repository calls this first.

``require_listed`` (loader.py) is the read gate - presence in the registry is all analysis needs.
A write is stricter and has exactly one rule, enforced here and nowhere else: the entry is listed,
active, and its ``mode`` is ``full``. ``dry_run`` may produce a dry-run result and nothing else;
``disabled`` is analyzed and never written to. Callers receive a :class:`WritePermit` they must
hand to the effect they run (``components/propose/effect.py`` takes one as a required argument), so
an effect cannot be reached without having passed this function.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError
from repository_presenter.core.registry.loader import find_entry, is_permitted
from repository_presenter.core.registry.models import Registry, RegistryEntry

WriteEffect = Literal["readme_proposal", "metadata_write", "issue_filing", "issue_close"]


@dataclass(frozen=True)
class WritePermit:
    """Proof that ``effect`` was cleared for ``entry`` by :func:`require_write_permitted`."""

    effect: WriteEffect
    entry: RegistryEntry


def require_write_permitted(
    registry: Registry, repository: str, effect: WriteEffect
) -> WritePermit:
    """Raise :class:`WriteRefusedError` unless ``repository`` may receive ``effect`` right now."""
    entry = is_permitted(registry, repository)
    if entry is None:
        listed = find_entry(registry, repository)
        if listed is None:
            raise WriteRefusedError(
                Refusal.REGISTRY_NOT_LISTED,
                f"{repository} is not in the registry allow-list; {effect} refused",
            )
        raise WriteRefusedError(
            Refusal.REGISTRY_DISABLED,
            f"{repository} is registry mode 'disabled'; {effect} refused",
        )
    if not entry.active:
        raise WriteRefusedError(
            Refusal.REGISTRY_INACTIVE, f"{repository} is not active; {effect} refused"
        )
    if entry.mode != "full":
        raise WriteRefusedError(
            Refusal.REGISTRY_DRY_RUN,
            f"{repository} is registry mode {entry.mode!r}, not 'full'; {effect} refused "
            "(a dry_run entry may produce a dry-run result and nothing else)",
        )
    return WritePermit(effect=effect, entry=entry)
