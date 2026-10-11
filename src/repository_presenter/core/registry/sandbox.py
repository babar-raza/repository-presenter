"""The sandbox allow-list: a second, narrower registry for the owner's throwaway canary target.

The production registry (``data/registry.json``) is the hard allow-list of governed Aspose FOSS
products; its denominators, its monitor, its sealing run and its portfolio counts all read it, and
its name gate (``naming.py``) refuses anything that is not an
``Aspose.{Family}-FOSS-for-{Platform}`` repository. The owner's sandbox canary (owner decision D6,
2026-10-11: a pull request against the throwaway repository ``babar-raza/presenter-sandbox`` is
the only push; every product repository stays paused) needs a write-permitted target that is none
of those things, and it must not disturb any of them. So the sandbox lives in its own file,
``data/registry_sandbox.json``, which only an explicit ``--sandbox`` command line reads. By
construction:

* no scheduled workflow, monitor, sealing plan, wave-readiness table or status count ever sees the
  sandbox, because none of them is given the file;
* the production loader keeps refusing the sandbox repository (name gate; ``extra="forbid"`` also
  refuses a ``sandbox`` key), so it cannot be smuggled into ``data/registry.json``;
* the set of repositories this file may name is a constant in this module, so adding a second
  sandbox target is a reviewed code change, never a data edit;
* a sandbox entry is README-proposal only (``issues_mode`` must be ``off``) and may not also be in
  the production registry, by name or by provider repository id.

Everything past the registry is unchanged: the same write gate (``write_gate.py``: listed, active,
``mode: full``), the same authorization record, token provenance, source recheck and idempotent
branch/commit/pull-request effect (``components/propose/effect.py``) run against the sandbox as
against a product. Removing the sandbox afterwards is deleting this module's file, its data file
and the ``--sandbox`` flag; nothing else refers to it.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError, model_validator

from repository_presenter.core.errors import ConfigError
from repository_presenter.core.registry.loader import REGISTRY_RELATIVE_PATH, load_registry
from repository_presenter.core.registry.models import Registry, RegistryEntry

SANDBOX_REGISTRY_RELATIVE_PATH = Path("data") / "registry_sandbox.json"

#: The only repositories a sandbox registry may name. A constant, not data: widening it is a code
#: change that goes through review, so a data edit can never aim a write at a product repository.
SANDBOX_REPOSITORIES: frozenset[str] = frozenset({"babar-raza/presenter-sandbox"})


class SandboxRegistryEntry(RegistryEntry):
    """A registry entry for a sandbox target: no Aspose name gate, a pinned repository, and
    README proposals only."""

    # Replaces the parent's validator of the same name (pydantic keeps the subclass's), which is
    # the Aspose name gate. A sandbox is no Aspose product; it is pinned to the repositories above.
    @model_validator(mode="after")
    def _name_matches_coordinates(self) -> SandboxRegistryEntry:
        if self.repository not in SANDBOX_REPOSITORIES:
            raise ValueError(
                f"{self.repository!r} is not a sandbox target (allowed: "
                f"{', '.join(sorted(SANDBOX_REPOSITORIES))}); the sandbox registry cannot name it"
            )
        if self.issues_mode != "off":
            raise ValueError("a sandbox entry must set issues_mode 'off': README proposals only")
        return self


class SandboxRegistry(Registry):
    """The sandbox allow-list: the production registry's shape, every entry a sandbox entry."""

    entries: tuple[SandboxRegistryEntry, ...]


def load_sandbox_registry(path: Path, *, production: Registry) -> Registry:
    """Load and validate the sandbox registry at ``path``; raise :class:`ConfigError` if unfit.

    ``production`` is the loaded production registry: a repository named by both (by name, ignoring
    case, or by provider repository id) is refused, so a target is never both a governed product
    and a sandbox."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"sandbox registry not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"sandbox registry is not valid JSON: {path}: {exc}") from exc
    try:
        sandbox = SandboxRegistry.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"sandbox registry is malformed: {path}: {exc}") from exc
    names = {entry.repository.casefold() for entry in production.entries}
    identities = {entry.provider_identity.repository_id for entry in production.entries}
    for entry in sandbox.entries:
        if (
            entry.repository.casefold() in names
            or entry.provider_identity.repository_id in identities
        ):
            raise ConfigError(
                f"{entry.repository} is in the production registry; a target is never both a "
                "governed product and a sandbox"
            )
    return sandbox


def load_registry_for(root: Path, *, sandbox: bool = False) -> Registry:
    """The registry a command consults: the production allow-list, or (``sandbox``) the sandbox
    allow-list read beside it and checked against it. Never the two merged."""
    production = load_registry(root / REGISTRY_RELATIVE_PATH)
    if not sandbox:
        return production
    return load_sandbox_registry(root / SANDBOX_REGISTRY_RELATIVE_PATH, production=production)
