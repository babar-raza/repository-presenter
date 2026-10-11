"""The consumed-scope recheck: is a sealed candidate still current under the running code?

A pure read of a sealed bundle (docs/investigations/13-bump-cost-and-recheck-design.md section 6,
G7-W25). Version constants stop being the arbiter of validity and become change signals: a bundle
whose ``dependencies.json`` differs from the running code is *rechecked*, scope by scope, over its
own sealed artifacts, and the deterministic outcome - not the version - says whether the candidate
it sealed still stands. Nothing here invalidates anything, edits a sealed bundle, clones, reaches
the network or calls a provider (AGENTS.md: "Invalidate a candidate only through an input it
consumed"; a validator or reviewer change re-checks and never invalidates blanket).

THE CURRENCY STATES (a currency is computed beside the manifest state; the state is untouched):

- ``CURRENT``: no consumed input differs from the running code.
- ``RECHECKED_CURRENT``: inputs differ and every triggered recheck passed.
- ``UPDATE_OPTIONAL``: only provenance differs - a prompt hash, the policy, a label
  (``contract_version``, ``acceptance_profile_version``). A prompt shapes how a unit was made, not
  whether it is valid (owner decision, doc 13 section 7), so it never stales a candidate.
- ``UPDATE_REQUIRED``: a triggered recheck failed. ``cost`` splits it for planning:
  ``rerender_only`` (only the presentation differs: the re-render passes every deterministic gate,
  so no authoring call and one fresh review read) versus ``recompose`` (a content gate, the
  extraction or the replayed review fails: authoring may run).
- ``UNVERIFIED``: a triggered recheck could not run (a reviewer scope with no retained raw reads,
  an extractor change that needs a clone, a bundle artifact the recheck cannot load). Conservative:
  it is never counted, and it does not count as independently accepted (owner decision).

The headline counts a bundle only for ``CURRENT``, ``RECHECKED_CURRENT`` and ``UPDATE_OPTIONAL``
(:data:`COUNTING`); ``portfolio.py`` partitions the rest into ``update_required`` and
``update_unverified``.

WHAT RUNS PER SCOPE (:data:`RECHECKS`, a table whose lookup miss raises, as ``scope_of`` does):

- ``presentation`` (``components.renderer``, ``components.shell``): ``render_readme`` over the
  sealed facts, plan, content units and dispositions must reproduce ``README.md`` byte for byte.
- ``authoring`` (``components.normalisation``): the BC-04 judge over the sealed units, with the
  tasks rebuilt from the sealed investigation, dispositions and plan, must give the sealed verdict.
- ``validator`` (any check that differs, ``validator_version``, and any check the sealed record
  lacks): every deterministic judge runs, never only the ones whose version moved - 7e56716e
  changed BC-07's meaning moving only ``VALIDATOR_VERSION`` - and a check with no sealed baseline
  must pass. A bundle whose presentation re-renders differently is judged on the re-rendered bytes,
  since those are the README it would become. Judges that cannot see everything a real run sees are
  named in ``partial`` (``tree_approximated``, ``original_unavailable``,
  ``secret_scan_not_rerun``).
- ``reviewer`` (``components.reviewer_logic``): ``review_document`` is replayed from the raw reads
  in ``raw_calls.json`` and must give the same verdict and finding ids; without raw reads it is
  ``UNVERIFIED``, never "unchanged".
- ``extraction`` (``environment.inherited_units_version``, ``environment.extractor_version``): the
  inherited units are regenerated from the original README, recovered by reverse-applying
  ``README.patch`` to ``README.md`` and proven by re-diffing, and must give the sealed fact ids and
  values. The other fact kinds need a clone and are left to the drift monitor: an extractor-version
  difference is ``UNVERIFIED`` for them.
- ``provenance`` (prompts, ``contract_version``, ``acceptance_profile_version``, ``policy``): no
  recheck; reported only.

RECEIPTS are a cache, never an authority: ``candidates/<owner>__<name>/rechecks/<revision>.json``,
keyed by the manifest digest and the running code's consumed inputs; one under any other key, with
a different digest of its own body, or unreadable is ignored and recomputed, and ``verify_bundle``
runs before either, so a tampered bundle fails integrity before any recheck. ``status`` reads
receipts and computes only when asked.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import tempfile
from collections import Counter
from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from repository_presenter.components.readme.bundle.dry_run import (
    code_derived_dependencies,
    unrecorded_inputs,
)
from repository_presenter.components.readme.bundle.evaluation import evaluate
from repository_presenter.components.readme.bundle.invalidation import ScopeError
from repository_presenter.components.readme.bundle.reproducibility import (
    REGISTRY_RELATIVE_PATH,
    _load_facts,
    _read,
)
from repository_presenter.components.readme.composition.authoring import authoring_tasks
from repository_presenter.components.readme.composition.renderer import (
    render_patch,
    render_readme,
    renderer_sentences,
)
from repository_presenter.components.readme.evidence.facts.inherited import inherited_unit_facts
from repository_presenter.components.readme.extractors.platforms.registry import known_ecosystems
from repository_presenter.components.readme.review.independent.review import review_document
from repository_presenter.components.readme.validation import registry as validation
from repository_presenter.core.candidates import (
    BUNDLE_MANIFEST_NAME,
    CANDIDATES_DIRNAME,
    CURRENT_FILENAME,
    DEPENDENCIES_FILENAME,
    BundleError,
    verify_bundle,
)
from repository_presenter.core.errors import ConfigError
from repository_presenter.core.llm.ledger import canonical_hash
from repository_presenter.core.llm.prompts import PROMPTS_DIRNAME, PromptRegistry, load_manifests
from repository_presenter.core.registry.loader import find_entry, load_registry
from repository_presenter.core.registry.models import RegistryEntry

RECHECK_VERSION = "1"
RECHECKS_DIRNAME = "rechecks"
RAW_CALLS_FILENAME = "raw_calls.json"

CURRENT = "CURRENT"
RECHECKED_CURRENT = "RECHECKED_CURRENT"
UPDATE_OPTIONAL = "UPDATE_OPTIONAL"
UPDATE_REQUIRED = "UPDATE_REQUIRED"
UNVERIFIED = "UNVERIFIED"
CURRENCY_STATES: tuple[str, ...] = (
    CURRENT,
    RECHECKED_CURRENT,
    UPDATE_OPTIONAL,
    UPDATE_REQUIRED,
    UNVERIFIED,
)
# The headline counts a bundle only in these (doc 13 section 6.3). UNVERIFIED is deliberately not
# among them: a recheck that could not run is not evidence of currency.
COUNTING: frozenset[str] = frozenset({CURRENT, RECHECKED_CURRENT, UPDATE_OPTIONAL})

COST_RERENDER_ONLY = "rerender_only"
COST_RECOMPOSE = "recompose"

PASSED = "PASSED"
FAILED = "FAILED"
UNVERIFIED_OUTCOME = "UNVERIFIED"
PROVENANCE = "PROVENANCE"

# dependency class -> the recheck scope it triggers. A dotted class (``components.<name>``) is
# looked up by its full name, then its family; a miss raises rather than guessing (a guessed
# recheck is a hidden policy). ``provenance`` is a scope with no recheck: it is reported, never
# judged.
RECHECKS: dict[str, str] = {
    "components.renderer": "presentation",
    "components.shell": "presentation",
    "components.normalisation": "authoring",
    "components.reviewer_logic": "reviewer",
    "validators": "validator",
    "environment.inherited_units_version": "extraction",
    "environment.extractor_version": "extraction",
    "contract_version": "provenance",
    "acceptance_profile_version": "provenance",
    "policy": "provenance",
}
RECHECK_FAMILIES: dict[str, str] = {"prompts": "provenance"}
SCOPE_ORDER: tuple[str, ...] = (
    "extraction",
    "presentation",
    "authoring",
    "validator",
    "reviewer",
    "provenance",
)

# Judges that see less than a real run does, and what they cannot see (doc 13 section 6.5).
PARTIAL_JUDGES: dict[str, str] = {
    "BC-01": "original_unavailable",
    "BC-06": "tree_approximated",
    "BC-09": "secret_scan_not_rerun",
}


def recheck_scope(dependency: str) -> str:
    """The recheck scope a changed dependency class triggers."""
    scope = RECHECKS.get(dependency)
    if scope is None:
        family, _, name = dependency.partition(".")
        if name:
            scope = RECHECK_FAMILIES.get(family)
    if scope is None:
        raise ScopeError(f"no recheck for the dependency {dependency!r}")
    return scope


@dataclass(frozen=True)
class ScopeResult:
    scope: str
    outcome: str  # PASSED, FAILED, UNVERIFIED or PROVENANCE
    triggers: tuple[str, ...]
    detail: str = ""
    failures: tuple[str, ...] = ()
    partial: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "outcome": self.outcome,
            "triggers": list(self.triggers),
            "detail": self.detail,
            "failures": list(self.failures),
            "partial": list(self.partial),
        }


@dataclass(frozen=True)
class Recheck:
    """One bundle's currency, with the scopes that decided it."""

    repository_dir: str
    revision: str
    currency: str
    cost: str | None  # rerender_only or recompose, for UPDATE_REQUIRED only
    differences: tuple[str, ...]
    unrecorded: tuple[str, ...]
    scopes: tuple[ScopeResult, ...]
    key: str = ""
    cached: bool = False
    error: str | None = None  # why no recheck ran at all (integrity, unreadable record)

    @property
    def counted(self) -> bool:
        return self.currency in COUNTING

    def to_json(self) -> dict[str, Any]:
        return {
            "repository_dir": self.repository_dir,
            "revision": self.revision,
            "currency": self.currency,
            "cost": self.cost,
            "differences": list(self.differences),
            "unrecorded": list(self.unrecorded),
            "scopes": [scope.to_json() for scope in self.scopes],
            "error": self.error,
        }


def _canonical(document: Mapping[str, Any]) -> bytes:
    return (json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
        "utf-8"
    )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def receipt_key(manifest_sha256: str, current_code: Mapping[str, Any]) -> str:
    """The cache key of a receipt: the manifest digest, the running code's consumed inputs, and the
    recheck's own version. A receipt under any other key is not this bundle under this code."""
    return canonical_hash(
        {
            "manifest_sha256": manifest_sha256,
            "constants": dict(current_code),
            "recheck_version": RECHECK_VERSION,
        }
    )


def receipt_path(root: Path, repository_dir: str, revision: str) -> Path:
    return root / CANDIDATES_DIRNAME / repository_dir / RECHECKS_DIRNAME / f"{revision}.json"


def _receipt_document(result: Recheck, manifest_sha256: str) -> dict[str, Any]:
    body = {
        "schema_version": 1,
        "recheck_version": RECHECK_VERSION,
        "key": result.key,
        "manifest_sha256": manifest_sha256,
        **result.to_json(),
    }
    return {**body, "digest": canonical_hash(body)}


def write_receipt(root: Path, result: Recheck, manifest_sha256: str) -> Path:
    """Write ``result`` as its receipt. The only file this module ever writes, and never inside the
    sealed bundle: a sibling ``rechecks/`` directory, so the manifest's inventory is untouched."""
    path = receipt_path(root, result.repository_dir, result.revision)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(_receipt_document(result, manifest_sha256)))
    return path


def read_receipt(root: Path, repository_dir: str, revision: str, key: str) -> Recheck | None:
    """The cached recheck for ``key``, or None when there is none or it cannot be trusted: absent,
    unreadable, under another key, or whose body no longer hashes to its own digest."""
    try:
        document = json.loads(receipt_path(root, repository_dir, revision).read_text("utf-8"))
        digest = document.pop("digest")
        if document.get("key") != key or digest != canonical_hash(document):
            return None
        if document["currency"] not in CURRENCY_STATES:
            return None
        return Recheck(
            repository_dir=document["repository_dir"],
            revision=document["revision"],
            currency=document["currency"],
            cost=document["cost"],
            differences=tuple(document["differences"]),
            unrecorded=tuple(document["unrecorded"]),
            scopes=tuple(
                ScopeResult(
                    row["scope"],
                    row["outcome"],
                    tuple(row["triggers"]),
                    row["detail"],
                    tuple(row["failures"]),
                    tuple(row["partial"]),
                )
                for row in document["scopes"]
            ),
            key=key,
            cached=True,
            error=document.get("error"),
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def reverse_apply(new_text: str, patch: str) -> str:
    """The text ``patch`` (a ``render_patch`` unified diff) was made from, given the text it made.

    Lines the patch removes come back, lines it adds go. The result is only trusted after
    :func:`original_readme` re-diffs it to the same patch.
    """
    new_lines = new_text.splitlines(keepends=True)
    old: list[str] = []
    position = 0
    lines = patch.splitlines(keepends=True)
    index = 0
    while index < len(lines) and not lines[index].startswith("@@"):
        index += 1
    while index < len(lines):
        header = _HUNK.match(lines[index])
        if header is None:
            index += 1
            continue
        count = int(header.group(4)) if header.group(4) is not None else 1
        new_start = int(header.group(3))
        start = new_start if count == 0 else new_start - 1
        old.extend(new_lines[position:start])
        position = start
        index += 1
        while index < len(lines) and not lines[index].startswith("@@"):
            tag, body = lines[index][:1], lines[index][1:]
            if tag == " ":
                old.append(body)
                position += 1
            elif tag == "-":
                old.append(body)
            elif tag == "+":
                position += 1
            index += 1
    old.extend(new_lines[position:])
    return "".join(old)


def original_readme(readme: str, patch: str) -> str | None:
    """The upstream README the candidate was made from, recovered from the sealed patch, or None
    when the recovery does not round-trip (re-diffing it must reproduce the sealed patch)."""
    candidate = reverse_apply(readme, patch)
    return candidate if render_patch(candidate, readme) == patch else None


class _UnavailableError(Exception):
    """A scope's recheck could not run; carries the reason that goes in the receipt."""


@dataclass
class _Material:
    """One bundle's sealed artifacts, loaded lazily so a scope pays only for what it reads."""

    root: Path
    bundle: Path
    entry: RegistryEntry
    sealed: dict[str, Any]  # dependencies.json
    _memo: dict[str, Any]

    def get(self, name: str, load: Callable[[], Any]) -> Any:
        if name not in self._memo:
            try:
                self._memo[name] = load()
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise _UnavailableError(f"cannot load {name}: {exc}") from exc
        return self._memo[name]

    def facts(self) -> Any:
        return self.get("facts", lambda: _load_facts(self.bundle / "facts.json"))

    def json(self, filename: str) -> dict[str, Any]:
        return cast("dict[str, Any]", self.get(filename, lambda: _read(self.bundle, filename)))

    def text(self, filename: str) -> str:
        loaded = self.get(filename, lambda: (self.bundle / filename).read_text(encoding="utf-8"))
        return str(loaded)

    def original(self) -> str:
        recovered = self.get(
            "original",
            lambda: original_readme(self.text("README.md"), self.text("README.patch")),
        )
        if recovered is None:
            raise _UnavailableError("the original README is not recoverable from README.patch")
        return str(recovered)

    def rendered(self) -> str:
        return str(
            self.get(
                "rendered",
                lambda: render_readme(
                    self.entry,
                    self.facts(),
                    self.json("plan.json"),
                    self.json("content_units.json"),
                    self.json("dispositions.json"),
                ),
            )
        )


def _tree_approximation(readme: str, facts: Any) -> list[str]:
    """The tree BC-06's relative links resolve against, approximated by what the sealed candidate
    already resolved: the README's own relative targets plus every evidence path. The source tree
    itself is not sealed, so a link this misses is a link the real run would also have flagged."""
    paths: set[str] = set()
    for target in re.findall(r"\]\((?!https?:|#|mailto:)([^)\s]+)\)", readme):
        paths.add(target.split("#")[0].strip("/").removeprefix("./"))
    for fact in facts.facts:
        for evidence in fact.evidence:
            if getattr(evidence, "path", None):
                paths.add(str(evidence.path))
    return sorted(paths)


class _Judges:
    """The deterministic judges, run once per candidate text however many scopes read them."""

    def __init__(self, material: _Material) -> None:
        self.material = material
        self.by_text: dict[str, dict[str, dict[str, Any]]] = {}

    def run(self, readme: str) -> dict[str, dict[str, Any]]:
        if readme in self.by_text:
            return self.by_text[readme]
        material = self.material
        try:
            facts = material.facts()
            tasks = authoring_tasks(
                material.entry,
                facts,
                material.json("investigation.json"),
                material.json("dispositions.json"),
                material.json("plan.json"),
            )
            candidate = validation.Candidate(
                material.entry,
                facts,
                material.json("plan.json"),
                material.json("content_units.json"),
                material.json("dispositions.json"),
                readme,
                None,
                facts.source_revision,
                None,
                _tree_approximation(readme, facts),
                tasks,
            )
            with tempfile.TemporaryDirectory() as scratch:
                document = validation.validate_candidate(candidate, Path(scratch), [])
        except _UnavailableError:
            raise
        except Exception as exc:
            raise _UnavailableError(f"the judges raised {type(exc).__name__}: {exc}") from exc
        self.by_text[readme] = {
            str(check["id"]): check for check in document["checks"] if check["verdict"] != "PENDING"
        }
        return self.by_text[readme]


def _failure_lines(check: Mapping[str, Any], limit: int = 3) -> list[str]:
    details = [str(detail) for detail in check.get("details") or ()]
    return [f"{check['id']}: {detail[:160]}" for detail in details[:limit]] or [
        f"{check['id']}: {check['verdict']}"
    ]


def _recheck_presentation(
    material: _Material, triggers: tuple[str, ...], _judges: _Judges
) -> ScopeResult:
    sealed = material.text("README.md")
    rendered = material.rendered()
    if rendered == sealed:
        return ScopeResult("presentation", PASSED, triggers, "re-render equals the sealed README")
    differing = sum(
        1
        for before, after in itertools.zip_longest(sealed.splitlines(), rendered.splitlines())
        if before != after
    )
    return ScopeResult(
        "presentation",
        FAILED,
        triggers,
        f"re-render differs from the sealed README on {differing} line(s)",
        (f"README.md: {differing} line(s) differ after a re-render",),
    )


def _candidate_text(material: _Material, presentation_triggered: bool) -> str:
    """The README the judges read: the re-render when presentation re-rendered differently (that is
    the README the bundle would become), otherwise the sealed bytes."""
    sealed = material.text("README.md")
    if presentation_triggered:
        rendered = material.rendered()
        if rendered != sealed:
            return rendered
    return sealed


def _sealed_verdicts(material: _Material) -> dict[str, dict[str, Any]]:
    document = material.json("validation.json")
    return {str(check["id"]): check for check in document["checks"]}


def _same_judgement(new: Mapping[str, Any], sealed: Mapping[str, Any] | None) -> bool:
    """A check holds when it gives the sealed verdict (and, when both fail, the sealed failures); a
    check the sealed record lacks has no baseline and must pass."""
    if sealed is None:
        return bool(new["verdict"] == "PASS")
    if new["verdict"] != sealed["verdict"]:
        return False
    return new["verdict"] != "FAIL" or list(new.get("details") or ()) == list(
        sealed.get("details") or ()
    )


def _recheck_authoring(
    material: _Material, triggers: tuple[str, ...], judges: _Judges, presentation: bool
) -> ScopeResult:
    checks = judges.run(_candidate_text(material, presentation))
    new = checks["BC-04"]
    if _same_judgement(new, _sealed_verdicts(material).get("BC-04")):
        return ScopeResult("authoring", PASSED, triggers, "BC-04 holds over the sealed units")
    return ScopeResult(
        "authoring",
        FAILED,
        triggers,
        f"BC-04 is {new['verdict']} over the sealed units",
        tuple(_failure_lines(new)),
    )


def _recheck_validator(
    material: _Material, triggers: tuple[str, ...], judges: _Judges, presentation: bool
) -> ScopeResult:
    checks = judges.run(_candidate_text(material, presentation))
    sealed = _sealed_verdicts(material)
    failed = [
        check
        for check_id, check in sorted(checks.items())
        if not _same_judgement(check, sealed.get(check_id))
    ]
    partial = tuple(
        f"{check_id}:{why}" for check_id, why in PARTIAL_JUDGES.items() if check_id in checks
    )
    unbaselined = sorted(set(checks) - set(sealed))
    note = f"; no sealed baseline, must pass: {', '.join(unbaselined)}" if unbaselined else ""
    if not failed:
        return ScopeResult(
            "validator",
            PASSED,
            triggers,
            f"{len(checks)} deterministic judges give the sealed verdicts{note}",
            partial=partial,
        )
    return ScopeResult(
        "validator",
        FAILED,
        triggers,
        f"{len(failed)} of {len(checks)} deterministic judges differ from the sealed record{note}",
        tuple(line for check in failed for line in _failure_lines(check)),
        partial,
    )


def _recheck_reviewer(
    material: _Material,
    triggers: tuple[str, ...],
    _judges: _Judges,
    manifests: PromptRegistry | None,
) -> ScopeResult:
    if not (material.bundle / RAW_CALLS_FILENAME).is_file():
        return ScopeResult(
            "reviewer",
            UNVERIFIED_OUTCOME,
            triggers,
            f"{RAW_CALLS_FILENAME} is not retained, so the review cannot be replayed",
        )
    if manifests is None:
        raise _UnavailableError("the prompt manifests are not loadable")
    raw = material.json(RAW_CALLS_FILENAME)
    calls = raw.get("calls", raw)
    reads = [
        call["output"]
        for call in calls.values()
        if isinstance(call, dict) and call.get("job") == "independent_review"
    ]
    sealed = material.json("review.json")
    reader = sealed.get("second_reader") or {}
    wanted = int(reader.get("read") or 1)
    if not reads or len(reads) < wanted:
        return ScopeResult(
            "reviewer",
            UNVERIFIED_OUTCOME,
            triggers,
            f"{len(reads)} retained review read(s) of the {wanted} the sealed review used",
        )
    facts = material.facts()
    readme = material.text("README.md")
    original = material.original()
    sentences = renderer_sentences(
        material.entry,
        facts,
        material.json("plan.json"),
        material.json("content_units.json"),
        material.json("dispositions.json"),
    )

    def signature(document: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            document.get("verdict"),
            document.get("verdict_as_returned"),
            sorted(str(f["id"]) for f in document.get("findings", [])),
            sorted(str(f["id"]) for f in document.get("advisory", [])),
        )

    expected = signature(sealed)
    replays: list[tuple[Any, ...]] = []
    # raw_calls.json is keyed by request hash, not by read order, so every order of the retained
    # reads is a candidate for "first, second, third"; one that reproduces the sealed review proves
    # the fold stack still gives it.
    for order in itertools.permutations(range(len(reads)), wanted):
        document = review_document(
            reads[order[0]],
            manifests["independent_review"],
            manifests["section_authoring"],
            str(sealed["readme_sha256"]),
            candidate_readme=readme,
            facts=facts,
            original_readme=original,
            rendered=sentences,
            second=reads[order[1]] if wanted > 1 else None,
            third=reads[order[2]] if wanted > 2 else None,
            units=material.json("content_units.json"),
            dispositions=material.json("dispositions.json"),
            second_failure=reader.get("failed"),
            trigger=reader.get("trigger"),
        )
        signature_now = signature(document)
        if signature_now == expected:
            return ScopeResult(
                "reviewer", PASSED, triggers, "the replayed review gives the sealed verdict"
            )
        replays.append(signature_now)
    return ScopeResult(
        "reviewer",
        FAILED,
        triggers,
        f"no order of the {len(reads)} retained read(s) replays to the sealed review",
        (f"sealed {expected[0]} {expected[2]}; replay {replays[0][0]} {replays[0][2]}",),
    )


def _recheck_extraction(
    material: _Material, triggers: tuple[str, ...], _judges: _Judges
) -> ScopeResult:
    facts = material.facts()
    sealed_units = {f.id: f.value for f in facts.facts if f.kind == "inherited_unit"}
    symbols = [f for f in facts.facts if f.kind == "public_symbol"]
    evidence_path = next(
        (e.path for f in facts.facts if f.kind == "inherited_unit" for e in f.evidence), "README.md"
    )
    regenerated = {
        f.id: f.value
        for f in inherited_unit_facts(
            evidence_path, material.original().encode("utf-8"), tuple(symbols)
        )
    }
    partial = ("tree_unavailable", "other_fact_kinds_need_a_clone")
    needs_clone = [t for t in triggers if t.endswith("extractor_version")]
    if regenerated != sealed_units:
        added = len(set(regenerated) - set(sealed_units))
        removed = len(set(sealed_units) - set(regenerated))
        altered = sum(
            1
            for key in set(regenerated) & set(sealed_units)
            if regenerated[key] != sealed_units[key]
        )
        return ScopeResult(
            "extraction",
            FAILED,
            triggers,
            "regenerated inherited units differ: "
            f"{added} added, {removed} removed, {altered} altered (would re-extract)",
            (f"{added} added, {removed} removed, {altered} altered inherited units",),
            partial,
        )
    if needs_clone:
        return ScopeResult(
            "extraction",
            UNVERIFIED_OUTCOME,
            triggers,
            "inherited units regenerate identically, but the other fact kinds need a clone to "
            "recheck an extractor-version difference",
            partial=partial,
        )
    return ScopeResult(
        "extraction",
        PASSED,
        triggers,
        f"{len(sealed_units)} inherited units regenerate identically",
        partial=partial,
    )


def _provenance(triggers: tuple[str, ...]) -> ScopeResult:
    return ScopeResult(
        "provenance",
        PROVENANCE,
        triggers,
        "prompts, policy and labels shape how a candidate was made, not whether it is valid",
    )


def _triggers(
    sealed: dict[str, Any], current_code: Mapping[str, Any]
) -> tuple[dict[str, list[str]], tuple[str, ...], tuple[str, ...]]:
    """(scope -> the dependency classes that triggered it, every difference, the unrecorded inputs).

    A check or extraction version the sealed record lacks triggers its scope exactly as a differing
    one does: absence is not "unchanged" (doc 13 section 6.4)."""
    changes = evaluate(sealed, code_derived_dependencies(sealed, current_code)).changes
    differences = tuple(change.dependency for change in changes)
    unrecorded = unrecorded_inputs(sealed, current_code)
    triggered: dict[str, list[str]] = {}
    for dependency in (*differences, *(f for f in unrecorded)):
        # an unrecorded check is a validator-scope input; the class is the family, not the check
        klass = "validators" if dependency.startswith("validators.") else dependency
        triggered.setdefault(recheck_scope(klass), []).append(dependency)
    return triggered, differences, unrecorded


def classify(scopes: Sequence[ScopeResult]) -> tuple[str, str | None]:
    """(currency, cost) from the scope results: a failure outranks an unverifiable scope, which
    outranks provenance; only passed rechecks (with or without provenance) are current."""
    rechecked = [s for s in scopes if s.outcome != PROVENANCE]
    if any(s.outcome == FAILED for s in rechecked):
        recompose = any(s.outcome == FAILED and s.scope != "presentation" for s in rechecked)
        return UPDATE_REQUIRED, COST_RECOMPOSE if recompose else COST_RERENDER_ONLY
    if any(s.outcome == UNVERIFIED_OUTCOME for s in rechecked):
        return UNVERIFIED, None
    if rechecked:
        return RECHECKED_CURRENT, None
    return (UPDATE_OPTIONAL if scopes else CURRENT), None


def _bundle_for(root: Path, repository_dir: str) -> tuple[str, Path, dict[str, Any]]:
    """(revision, bundle, manifest) of the CURRENT bundle, after ``verify_bundle`` - integrity
    comes first, so a tampered or half-written bundle never reaches a recheck."""
    pointer = root / CANDIDATES_DIRNAME / repository_dir / CURRENT_FILENAME
    try:
        revision = pointer.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise BundleError(f"{repository_dir}: no CURRENT pointer: {exc}") from exc
    bundle = pointer.parent / revision
    manifest = verify_bundle(bundle)
    if manifest is None:
        raise BundleError(f"{repository_dir}: CURRENT names {revision!r} with no sealed bundle")
    return revision, bundle, manifest


def recheck_bundle(
    root: Path,
    repository_dir: str,
    current_code: Mapping[str, Any],
    *,
    entry: RegistryEntry | None = None,
    manifests: PromptRegistry | None = None,
    use_receipts: bool = True,
) -> Recheck:
    """The currency of one CURRENT bundle under ``current_code`` (``seal.code_dependencies``).

    Raises :class:`BundleError` when the bundle fails integrity - before any scope runs. A scope
    that cannot run is ``UNVERIFIED``, never a pass.
    """
    revision, bundle, manifest = _bundle_for(root, repository_dir)
    manifest_sha = _sha256((bundle / BUNDLE_MANIFEST_NAME).read_bytes())
    key = receipt_key(manifest_sha, current_code)
    if use_receipts:
        cached = read_receipt(root, repository_dir, revision, key)
        if cached is not None:
            return cached
    try:
        sealed = json.loads((bundle / DEPENDENCIES_FILENAME).read_text(encoding="utf-8"))
        if not isinstance(sealed, dict):
            raise ValueError("not a JSON object")
    except (OSError, ValueError) as exc:
        return Recheck(
            repository_dir,
            revision,
            UNVERIFIED,
            None,
            (),
            (),
            (),
            key,
            error=f"{DEPENDENCIES_FILENAME} is unreadable: {exc}",
        )
    triggered, differences, unrecorded = _triggers(sealed, current_code)
    if not triggered:
        return Recheck(repository_dir, revision, CURRENT, None, differences, unrecorded, (), key)
    if entry is None:
        try:
            entry = find_entry(
                load_registry(root / REGISTRY_RELATIVE_PATH), str(manifest.get("repository"))
            )
        except ConfigError:
            entry = None
    runners: dict[str, Callable[[tuple[str, ...]], ScopeResult]] = {}
    if entry is not None:
        known_ecosystems()
        material = _Material(root, bundle, entry, sealed, {})
        judges = _Judges(material)
        presentation = "presentation" in triggered
        runners = {
            "presentation": lambda t: _recheck_presentation(material, t, judges),
            "authoring": lambda t: _recheck_authoring(material, t, judges, presentation),
            "validator": lambda t: _recheck_validator(material, t, judges, presentation),
            "reviewer": lambda t: _recheck_reviewer(material, t, judges, manifests),
            "extraction": lambda t: _recheck_extraction(material, t, judges),
        }
    results: list[ScopeResult] = []
    for scope in SCOPE_ORDER:
        if scope not in triggered:
            continue
        names = tuple(triggered[scope])
        if scope == "provenance":
            results.append(_provenance(names))
        elif scope not in runners:
            reason = (
                "the repository is not in the registry; its sealed artifacts cannot be rendered"
            )
            results.append(ScopeResult(scope, UNVERIFIED_OUTCOME, names, reason))
        else:
            try:
                results.append(runners[scope](names))
            except _UnavailableError as exc:
                results.append(ScopeResult(scope, UNVERIFIED_OUTCOME, names, str(exc)))
    ordered = tuple(sorted(results, key=lambda s: SCOPE_ORDER.index(s.scope)))
    currency, cost = classify(ordered)
    return Recheck(repository_dir, revision, currency, cost, differences, unrecorded, ordered, key)


def _load_manifests(root: Path) -> PromptRegistry | None:
    try:
        return load_manifests(root / PROMPTS_DIRNAME)
    except ConfigError:
        return None


def recheck_portfolio(
    root: Path,
    current_code: Mapping[str, Any],
    *,
    repositories: Collection[str] | None = None,
    write_receipts: bool = False,
    use_receipts: bool = True,
    compute: bool = True,
) -> list[Recheck]:
    """Recheck every CURRENT bundle under ``root`` (or the named ``owner/name`` repositories).

    ``compute=False`` reads receipts only and reports a bundle with none as ``UNVERIFIED`` with
    ``error`` saying so - the cheap path ``status`` takes. A bundle that fails integrity is
    ``UNVERIFIED`` with the integrity error; it is never rechecked.
    """
    candidates = root / CANDIDATES_DIRNAME
    if not candidates.is_dir():
        return []
    wanted = {r.replace("/", "__") for r in repositories} if repositories else None
    try:
        registry = load_registry(root / REGISTRY_RELATIVE_PATH)
    except ConfigError:
        registry = None
    manifests = _load_manifests(root) if compute else None
    rows: list[Recheck] = []
    for repository_dir in sorted(p for p in candidates.iterdir() if p.is_dir()):
        if wanted is not None and repository_dir.name not in wanted:
            continue
        if not (repository_dir / CURRENT_FILENAME).is_file():
            continue
        try:
            revision, bundle, manifest = _bundle_for(root, repository_dir.name)
            key = receipt_key(_sha256((bundle / BUNDLE_MANIFEST_NAME).read_bytes()), current_code)
            cached = (
                read_receipt(root, repository_dir.name, revision, key) if use_receipts else None
            )
            if cached is not None:
                rows.append(cached)
                continue
            if not compute:
                rows.append(
                    Recheck(
                        repository_dir.name,
                        revision,
                        UNVERIFIED,
                        None,
                        (),
                        (),
                        (),
                        key,
                        error="no receipt for this bundle under the running code; run `recheck`",
                    )
                )
                continue
            entry = (
                find_entry(registry, str(manifest.get("repository")))
                if registry is not None
                else None
            )
            result = recheck_bundle(
                root,
                repository_dir.name,
                current_code,
                entry=entry,
                manifests=manifests,
                use_receipts=False,
            )
            if write_receipts:
                write_receipt(root, result, _sha256((bundle / BUNDLE_MANIFEST_NAME).read_bytes()))
            rows.append(result)
        except (BundleError, OSError, ValueError, ScopeError) as exc:
            # a bundle that fails integrity, or a difference with no recheck row, is reported - and
            # never counted - rather than taking the rest of the portfolio down with it
            kind = "integrity" if isinstance(exc, BundleError | OSError | ValueError) else "recheck"
            revision_text = _safe_revision(repository_dir)
            rows.append(
                Recheck(
                    repository_dir.name,
                    revision_text,
                    UNVERIFIED,
                    None,
                    (),
                    (),
                    (),
                    "",
                    error=f"{kind}: {exc}",
                )
            )
    return rows


def _safe_revision(repository_dir: Path) -> str:
    try:
        return (repository_dir / CURRENT_FILENAME).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def currency_map(rows: Iterable[Recheck]) -> dict[str, str]:
    """``owner__name`` -> currency, the shape ``portfolio.assess_portfolio`` takes."""
    return {row.repository_dir: row.currency for row in rows}


def currency_counts(rows: Iterable[Recheck]) -> dict[str, int]:
    tally = Counter(row.currency for row in rows)
    return {state: tally.get(state, 0) for state in CURRENCY_STATES}


def render_lines(rows: Sequence[Recheck], *, verbose: bool = True) -> list[str]:
    """The plain-text table the ``recheck`` command prints."""
    lines = [
        f"recheck: {len(rows)} current bundle(s), offline, no provider call, no writes to bundles"
    ]
    for row in rows:
        cost = f" ({row.cost})" if row.cost else ""
        cached = " [receipt]" if row.cached else ""
        lines.append(f"  {row.repository_dir} @ {row.revision[:12]}: {row.currency}{cost}{cached}")
        if row.error:
            lines.append(f"    {row.error}")
        if not verbose:
            continue
        for scope in row.scopes:
            lines.append(f"    {scope.scope}: {scope.outcome} - {scope.detail}")
            lines.extend(f"      {failure}" for failure in scope.failures[:4])
        if row.unrecorded:
            lines.append(f"    ran inputs the sealed record lacks: {', '.join(row.unrecorded)}")
    counts = currency_counts(rows)
    split = Counter(row.cost for row in rows if row.currency == UPDATE_REQUIRED)
    lines.append(
        "currency: "
        + ", ".join(f"{state} {counts[state]}" for state in CURRENCY_STATES)
        + f" (UPDATE_REQUIRED: rerender_only {split.get(COST_RERENDER_ONLY, 0)}, "
        f"recompose {split.get(COST_RECOMPOSE, 0)}); counted "
        f"{sum(counts[s] for s in COUNTING)} of {len(rows)}"
    )
    return lines
