"""The judge: is one sealed README bundle authorizable? A pure function of the sealed files.

``judge_bundle(bundle, live_is_standard=...)`` reads the files of one sealed bundle directory and
nothing else: no network, no provider call, no clock, and no language model. The independent
reviewer's verdict (``review.json``) is ADVISORY: it is recorded as ``reviewer_advisory`` and can
never change ``authorizable`` in either direction. Integrity of the sealed files (``verify_bundle``)
is the caller's check, made before the judge is asked; the judge only reads.

THE CLAUSES. Each is PASS, FAIL, NOT_APPLICABLE or UNEVALUATED (the input it needs cannot be read).
UNEVALUATED counts as not passing: ``authorizable`` is true exactly when every clause is PASS or
NOT_APPLICABLE. ``failing`` lists the ids of the others, and each clause's ``detail`` names the
check, section, unit or element at fault.

``J1_FACTS``
    Blocking checks BC-01, 02, 03, 06, 08 and 09 are PASS in ``validation.json``.
``J2_STANDARD``
    BC-07 (structure) is PASS and the README's heading skeleton contains every element the
    repository's archetype marks ``required`` (``data/readme_standard``: ``assignments.yaml`` names
    the archetype; a repository with no assignment is held to the common core, ``common.yaml``). An
    element with a heading matches a README heading of the same text (case, ``&``/``and`` and
    punctuation aside); an unheaded element matches through ``ELEMENT_MATCHERS``; an element with
    neither is UNEVALUATED, never guessed.
``J3_CLAIMS``
    BC-04 is PASS: every public claim cites an accepted fact (BC-02 and BC-03 are J1's).
``J4_DISPOSITIONS``
    BC-05 is PASS; every inherited unit of ``facts.json`` has exactly one disposition and no
    disposition names an unknown unit; and the text of every unit a disposition keeps
    (``VERIFIED_PRESERVE``, ``VERIFIED_MOVE``) appears in ``README.md`` verbatim, whitespace runs
    aside. A kept heading counts when its words appear as a heading of any level in any letter case:
    the renderer re-levels and title-cases headings (BC-07), which is not a loss of the text.
``J5_RERUN``
    The manifest's ``no_op_proof`` is a byte-identical, fresh-process rerun with zero provider calls
    and BC-11 is PASS.
``J6_NOT_WORSE_THAN_LIVE``
    Applies only when ``live_is_standard`` is True (the live README follows the standard;
    ``live_is_standard_for`` derives it from ``survey.json``); False is NOT_APPLICABLE and None
    (applicability unknown) is UNEVALUATED. The live README is recovered from the sealed
    ``README.patch`` (``recheck.original_readme``); a recovery that does not round-trip is
    UNEVALUATED. THE RULE: the candidate loses nothing of the live README that a disposition does
    not account for. Lost means

    * a live heading (any level) whose text no candidate heading has;
    * a live fenced code block whose content no candidate fence contains;
    * a live link or image target that no candidate link or image has (a trailing ``/`` aside);
    * a live line equal to a SUPPORTED ``install_command`` fact (a verified command) that the
      candidate does not contain.

    A loss is accounted for when the disposition of an inherited unit holding that heading, block,
    target or command is ``SUPERSEDE_REDUNDANT``, ``CORRECT_WITH_EVIDENCE``, ``VERIFIED_REWRITE`` or
    ``OMIT_UNSUPPORTED`` AND cites at least one fact (``fact_ids`` not empty) AND states a
    rationale. A kept, deferred or non-content disposition, or a missing one, accounts for nothing.

Validation evidence must belong to the bundle: a ``validation.json`` whose ``source_revision`` is
not the manifest's revision, or whose ``readme_sha256`` is not the hash of ``README.md``, judged
some other document, so every clause that reads it is FAIL.

A clause is a row of ``CLAUSES``; adding one is adding a row. Parsing uses the project's own
helpers: ``markdown-it-py`` for headings, fences and the opening, ``extract_links`` for targets.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from markdown_it import MarkdownIt
from markdown_it.token import Token

from repository_presenter.components.readme.bundle.recheck import original_readme
from repository_presenter.components.readme.evidence.facts.links import extract_links
from repository_presenter.core.candidates import BUNDLE_MANIFEST_NAME

PASS = "PASS"
FAIL = "FAIL"
NOT_APPLICABLE = "NOT_APPLICABLE"
UNEVALUATED = "UNEVALUATED"
STATUSES: tuple[str, ...] = (PASS, FAIL, NOT_APPLICABLE, UNEVALUATED)

J1 = "J1_FACTS"
J2 = "J2_STANDARD"
J3 = "J3_CLAIMS"
J4 = "J4_DISPOSITIONS"
J5 = "J5_RERUN"
J6 = "J6_NOT_WORSE_THAN_LIVE"

FACTS_CHECKS: tuple[str, ...] = ("BC-01", "BC-02", "BC-03", "BC-06", "BC-08", "BC-09")
STRUCTURE_CHECK = "BC-07"
CLAIMS_CHECK = "BC-04"
DISPOSITIONS_CHECK = "BC-05"
RERUN_CHECK = "BC-11"

KEPT: frozenset[str] = frozenset({"VERIFIED_PRESERVE", "VERIFIED_MOVE"})
# A disposition that may account for a loss when it also cites a fact and states a rationale.
ACCOUNTING: frozenset[str] = frozenset(
    {"SUPERSEDE_REDUNDANT", "CORRECT_WITH_EVIDENCE", "VERIFIED_REWRITE", "OMIT_UNSUPPORTED"}
)

README_FILENAME = "README.md"
PATCH_FILENAME = "README.patch"
FACTS_FILENAME = "facts.json"
VALIDATION_FILENAME = "validation.json"
REVIEW_FILENAME = "review.json"
DISPOSITIONS_FILENAME = "dispositions.json"
DATA_DIR = Path(__file__).resolve().parents[5] / "data" / "readme_standard"
FAILURE_TEXT_LIMIT = 220


@dataclass(frozen=True)
class Clause:
    id: str
    status: str
    detail: str

    def to_json(self) -> dict[str, str]:
        return {"id": self.id, "status": self.status, "detail": self.detail}


@dataclass(frozen=True)
class JudgeVerdict:
    authorizable: bool
    clauses: tuple[Clause, ...]
    failing: tuple[str, ...]
    reviewer_advisory: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "authorizable": self.authorizable,
            "failing": list(self.failing),
            "clauses": [clause.to_json() for clause in self.clauses],
            "reviewer_advisory": self.reviewer_advisory,
        }

    def clause(self, clause_id: str) -> Clause:
        return next(clause for clause in self.clauses if clause.id == clause_id)

    def passes(self, clause_id: str) -> bool:
        return self.clause(clause_id).status == PASS

    def refusal(self, ignore: Collection[str] = ()) -> str | None:
        """Why the bundle is not authorizable, naming each failing clause (but those in
        ``ignore``), or None."""
        failing = [
            clause
            for clause in self.clauses
            if clause.id in self.failing and clause.id not in ignore
        ]
        if not failing:
            return None
        return "the judge does not authorize this bundle: " + "; ".join(
            f"{clause.id} {clause.status}: {clause.detail}" for clause in failing
        )


# --- reading the sealed files ------------------------------------------------------------------


def _read_text(path: Path) -> str | None:
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, ValueError):
        return None


def _read_object(path: Path) -> dict[str, Any] | None:
    text = _read_text(path)
    if text is None:
        return None
    try:
        loaded = json.loads(text)
    except ValueError:
        return None
    return loaded if isinstance(loaded, dict) else None


@dataclass(frozen=True)
class _Bundle:
    """The sealed files of one bundle, each None when it cannot be read."""

    readme: str | None
    patch: str | None
    manifest: dict[str, Any] | None
    validation: dict[str, Any] | None
    review: dict[str, Any] | None
    facts: dict[str, Any] | None
    dispositions: dict[str, Any] | None

    @classmethod
    def load(cls, bundle: Path) -> _Bundle:
        return cls(
            _read_text(bundle / README_FILENAME),
            _read_text(bundle / PATCH_FILENAME),
            _read_object(bundle / BUNDLE_MANIFEST_NAME),
            _read_object(bundle / VALIDATION_FILENAME),
            _read_object(bundle / REVIEW_FILENAME),
            _read_object(bundle / FACTS_FILENAME),
            _read_object(bundle / DISPOSITIONS_FILENAME),
        )

    @property
    def repository(self) -> str | None:
        value = (self.manifest or {}).get("repository")
        return value if isinstance(value, str) else None

    def inherited_units(self) -> dict[str, str] | None:
        """unit id -> its text, for every ``inherited_unit`` fact; None if facts cannot be read."""
        rows = (self.facts or {}).get("facts")
        if not isinstance(rows, list):
            return None
        return {
            str(row["id"]): str(row.get("value", ""))
            for row in rows
            if isinstance(row, dict) and row.get("kind") == "inherited_unit" and "id" in row
        }

    def disposition_rows(self) -> list[dict[str, Any]] | None:
        rows = (self.dispositions or {}).get("dispositions")
        if not isinstance(rows, list):
            return None
        return [row for row in rows if isinstance(row, dict)]


@dataclass(frozen=True)
class _Evidence:
    """``validation.json`` as the judge may use it: the verdict of each check, or why it may not be
    (``status`` is then UNEVALUATED for a file that cannot be read, FAIL for one that is not this
    bundle's)."""

    verdicts: Mapping[str, tuple[str, str]]
    status: str = PASS
    problem: str = ""


def _verdicts(sealed: _Bundle) -> _Evidence:
    """The evidence must be the bundle's own: the revision and the README hash it records must be
    the manifest's and the sealed README's."""
    validation = sealed.validation
    if validation is None:
        return _Evidence({}, UNEVALUATED, f"{VALIDATION_FILENAME} cannot be read")
    revision = (sealed.manifest or {}).get("revision")
    if revision is not None and validation.get("source_revision") != revision:
        return _Evidence(
            {},
            FAIL,
            f"{VALIDATION_FILENAME} judged revision {validation.get('source_revision')!r}, "
            f"not the bundle's {revision!r}",
        )
    if sealed.readme is not None and validation.get("readme_sha256") not in (
        None,
        hashlib.sha256(sealed.readme.encode("utf-8")).hexdigest(),
    ):
        return _Evidence(
            {}, FAIL, f"{VALIDATION_FILENAME} judged a different README than {README_FILENAME}"
        )
    checks = validation.get("checks")
    if not isinstance(checks, list):
        return _Evidence({}, UNEVALUATED, f"{VALIDATION_FILENAME} records no checks")
    verdicts: dict[str, tuple[str, str]] = {}
    for check in checks:
        if isinstance(check, dict) and "id" in check:
            verdicts[str(check["id"])] = (str(check.get("verdict")), _failure_text(check))
    return _Evidence(verdicts)


def _failure_text(check: Mapping[str, Any]) -> str:
    failures = check.get("failures")
    if isinstance(failures, list) and failures:
        first = failures[0]
        if isinstance(first, Mapping):
            detail = str(first.get("detail") or first.get("message") or first)
            where = first.get("section") or first.get("unit")
            text = f"{detail} (section {where})" if where else detail
        else:
            text = str(first)
        more = f" (+{len(failures) - 1} more)" if len(failures) > 1 else ""
        return text[:FAILURE_TEXT_LIMIT] + more
    sections = check.get("sections")
    return f"sections {sections}" if sections else "no failure recorded"


def _require_checks(sealed: _Bundle, ids: Sequence[str]) -> tuple[list[str], list[str], _Evidence]:
    """(failing lines, unrecorded lines, the evidence) for the named checks."""
    evidence = _verdicts(sealed)
    if evidence.problem:
        return [], [], evidence
    failing: list[str] = []
    missing: list[str] = []
    for check in ids:
        found = evidence.verdicts.get(check)
        if found is None:
            missing.append(f"{check} is not recorded")
        elif found[0] != PASS:
            failing.append(f"{check} {found[0]}: {found[1]}")
    return failing, missing, evidence


def _checks_clause(clause_id: str, sealed: _Bundle, ids: Sequence[str]) -> Clause:
    failing, missing, evidence = _require_checks(sealed, ids)
    if evidence.problem:
        return Clause(clause_id, evidence.status, evidence.problem)
    if failing:
        return Clause(clause_id, FAIL, "; ".join(failing + missing))
    if missing:
        return Clause(clause_id, UNEVALUATED, "; ".join(missing))
    return Clause(clause_id, PASS, f"{', '.join(ids)} PASS")


# --- markdown reading (markdown-it-py) ---------------------------------------------------------

_MARKDOWN = MarkdownIt("commonmark").enable(["table", "strikethrough"])
_WORDS = re.compile(r"\w")
_NON_ALNUM = re.compile(r"[^0-9a-z]+")
_HTML_TAG = re.compile(r"(?is)^</?(a|img)\b[^>]*>$")


@dataclass(frozen=True)
class _Doc:
    """A README read once: its headings, fences and the shape of what precedes its first H2."""

    headings: tuple[tuple[int, str], ...]
    fences: tuple[str, ...]
    lead: tuple[str, ...]  # the kinds of the blocks before the first H2: "badges" or "prose"
    text: str


def heading_key(text: str) -> str:
    """A heading's comparison form: letters and digits only, lower case, ``&`` read as ``and``."""
    return _NON_ALNUM.sub(" ", text.casefold().replace("&", " and ")).strip()


def _inline_text(inline: Token) -> str:
    parts: list[str] = []
    for child in inline.children or []:
        if child.type in {"text", "code_inline", "image"}:
            parts.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            parts.append(" ")
    return "".join(parts).strip()


def _block_kind(inline: Token) -> str | None:
    """``badges`` for a paragraph of images (each possibly linked), ``prose`` for one with words."""
    images = 0
    words = False
    for child in inline.children or []:
        if child.type == "image":
            images += 1
        elif child.type in {"link_open", "link_close", "softbreak", "hardbreak"}:
            continue
        elif child.type == "html_inline":
            if _HTML_TAG.match(child.content.strip()) is None:
                words = True
            elif child.content.lstrip().lower().startswith("<img"):
                images += 1
        elif _WORDS.search(child.content):
            words = True
    if words:
        return "prose"
    return "badges" if images else None


def read_doc(text: str) -> _Doc:
    tokens = _MARKDOWN.parse(text)
    headings: list[tuple[int, str]] = []
    fences: list[str] = []
    lead: list[str] = []
    in_lead = True
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            level = int(token.tag[1:])
            headings.append((level, _inline_text(tokens[index + 1])))
            if level >= 2:
                in_lead = False
        elif token.type == "fence":
            fences.append(_normalized(token.content))
        elif in_lead and token.type == "inline" and token.level == 1:
            if index and tokens[index - 1].type == "paragraph_open":
                kind = _block_kind(token)
                if kind is not None:
                    lead.append(kind)
    return _Doc(tuple(headings), tuple(fences), tuple(lead), text)


def _normalized(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").splitlines()).strip()


def _squeezed(text: str) -> str:
    return " ".join(text.split())


# --- J2: the standard --------------------------------------------------------------------------

# Unheaded elements of data/readme_standard/common.yaml, each a predicate over the README read once.
# An unheaded element with no row here cannot be matched deterministically and is UNEVALUATED.
ELEMENT_MATCHERS: dict[str, Callable[[_Doc], bool]] = {
    "identity_h1": lambda doc: sum(1 for level, _ in doc.headings if level == 1) == 1,
    "badge_row": lambda doc: "badges" in doc.lead,
    "opening": lambda doc: "prose" in doc.lead,
}


@dataclass(frozen=True)
class Standard:
    """What ``data/readme_standard`` requires: element id -> heading (None if unheaded), and the
    required element ids of each archetype plus the repository -> archetype assignments."""

    headings: Mapping[str, str | None]
    common_required: tuple[str, ...]
    archetype_required: Mapping[str, tuple[str, ...]]
    assignments: Mapping[str, str]

    def required_for(self, repository: str) -> tuple[str, tuple[str, ...]]:
        archetype = self.assignments.get(repository)
        if archetype is None or archetype not in self.archetype_required:
            return "common core", self.common_required
        return archetype, self.archetype_required[archetype]


@lru_cache(maxsize=8)
def load_standard(data_dir: Path = DATA_DIR) -> Standard:
    def load(path: Path) -> Any:
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    common = load(data_dir / "common.yaml")
    elements = [row for row in common["elements"] if isinstance(row, dict)]
    headings = {str(row["id"]): row.get("heading") for row in elements}
    common_required = tuple(
        str(row["id"]) for row in elements if row.get("requirement") == "required"
    )
    archetypes: dict[str, tuple[str, ...]] = {}
    for path in sorted((data_dir / "archetypes").glob("*.yaml")):
        profile = load(path)
        archetypes[str(profile["id"])] = tuple(
            str(element)
            for element, requirement in profile["elements"].items()
            if requirement == "required"
        )
    assigned = load(data_dir / "assignments.yaml")["assignments"]
    assignments = {str(row["repository"]): str(row["archetype"]) for row in assigned}
    return Standard(headings, common_required, archetypes, assignments)


def _standard_clause(sealed: _Bundle, standard_dir: Path) -> Clause:
    failing, missing, evidence = _require_checks(sealed, (STRUCTURE_CHECK,))
    if evidence.problem:
        return Clause(J2, evidence.status, evidence.problem)
    if sealed.readme is None or sealed.repository is None:
        return Clause(
            J2, UNEVALUATED, f"{README_FILENAME} or the manifest's repository cannot be read"
        )
    try:
        standard = load_standard(standard_dir)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        return Clause(J2, UNEVALUATED, f"the README standard cannot be read: {exc}")
    archetype, required = standard.required_for(sealed.repository)
    doc = read_doc(sealed.readme)
    present = {heading_key(text) for _, text in doc.headings}
    absent: list[str] = []
    unmatched: list[str] = []
    for element in required:
        heading = standard.headings.get(element)
        if heading is not None:
            if heading_key(heading) not in present:
                absent.append(f"{element} (heading {heading!r})")
        elif element in ELEMENT_MATCHERS:
            if not ELEMENT_MATCHERS[element](doc):
                absent.append(f"{element} (unheaded element)")
        else:
            unmatched.append(element)
    if failing or absent:
        reasons = failing + (
            [f"required by {archetype}, missing: {', '.join(absent)}"] if absent else []
        )
        return Clause(J2, FAIL, "; ".join(reasons))
    if missing or unmatched:
        reasons = missing + (
            [f"no deterministic match for element(s) {', '.join(unmatched)}"] if unmatched else []
        )
        return Clause(J2, UNEVALUATED, "; ".join(reasons))
    return Clause(J2, PASS, f"BC-07 PASS and every element {archetype} requires is present")


# --- J4: dispositions --------------------------------------------------------------------------


def _kept_text_present(unit: str, text: str, readme: str, doc: _Doc) -> bool:
    if _squeezed(text) in _squeezed(readme):
        return True
    if unit.endswith(".heading"):
        words = text.lstrip("#").strip()
        return heading_key(words) in {heading_key(heading) for _, heading in doc.headings}
    return False


def _dispositions_clause(sealed: _Bundle) -> Clause:
    failing, missing, evidence = _require_checks(sealed, (DISPOSITIONS_CHECK,))
    if evidence.problem:
        return Clause(J4, evidence.status, evidence.problem)
    units = sealed.inherited_units()
    rows = sealed.disposition_rows()
    if units is None or rows is None or sealed.readme is None:
        return Clause(J4, UNEVALUATED, "facts.json, dispositions.json or README.md cannot be read")
    counts = Counter(str(row.get("unit_id", "")) for row in rows)
    problems = list(failing)
    problems += [
        f"{unit} has {counts.get(unit, 0)} dispositions"
        for unit in units
        if counts.get(unit, 0) != 1
    ]
    problems += [f"{unit} is not an inherited unit" for unit in counts if unit not in units]
    doc = read_doc(sealed.readme)
    for row in rows:
        unit = str(row.get("unit_id", ""))
        if (
            row.get("disposition") in KEPT
            and unit in units
            and not _kept_text_present(unit, units[unit], sealed.readme, doc)
        ):
            problems.append(
                f"{unit} is kept ({row.get('disposition')}) but its text is not in README.md: "
                f"{_squeezed(units[unit])[:80]!r}"
            )
    if problems:
        return Clause(J4, FAIL, _joined(problems))
    if missing:
        return Clause(J4, UNEVALUATED, "; ".join(missing))
    return Clause(
        J4,
        PASS,
        f"BC-05 PASS, {len(units)} inherited units each with one disposition, kept text printed",
    )


def _joined(problems: Sequence[str], limit: int = 4) -> str:
    shown = "; ".join(problems[:limit])
    return shown + (f"; (+{len(problems) - limit} more)" if len(problems) > limit else "")


# --- J5: rerun ---------------------------------------------------------------------------------


def no_op_proven(manifest: Mapping[str, Any] | None) -> bool:
    """The manifest records a fresh-process, byte-identical rerun with zero provider calls."""
    proof = (manifest or {}).get("no_op_proof")
    return (
        isinstance(proof, dict)
        and proof.get("byte_identical") is True
        and proof.get("fresh_process") is True
        and proof.get("provider_calls") == 0
    )


def _rerun_clause(sealed: _Bundle) -> Clause:
    if sealed.manifest is None:
        return Clause(J5, UNEVALUATED, f"{BUNDLE_MANIFEST_NAME} cannot be read")
    reasons: list[str] = []
    if not no_op_proven(sealed.manifest):
        reasons.append(
            "the manifest records no byte-identical, fresh-process, zero-provider-call rerun"
        )
    failing, missing, evidence = _require_checks(sealed, (RERUN_CHECK,))
    reasons += failing
    if reasons or evidence.status == FAIL:
        return Clause(J5, FAIL, "; ".join(reasons + [evidence.problem] * bool(evidence.problem)))
    if evidence.problem or missing:
        return Clause(J5, UNEVALUATED, "; ".join(missing) or evidence.problem)
    return Clause(J5, PASS, "no_op_proof is byte-identical with zero provider calls and BC-11 PASS")


# --- J6: not worse than the live README --------------------------------------------------------


def _accounts(row: Mapping[str, Any]) -> bool:
    return (
        row.get("disposition") in ACCOUNTING
        and bool(row.get("fact_ids"))
        and bool(str(row.get("rationale", "")).strip())
    )


@dataclass(frozen=True)
class _Accounting:
    """The text of every inherited unit whose disposition accounts for a loss."""

    units: Sequence[str]

    def heading(self, text: str) -> bool:
        return any(
            unit.startswith("#") and heading_key(unit.lstrip("#")) == heading_key(text)
            for unit in self.units
        )

    def contains(self, needle: str) -> bool:
        return any(needle in _normalized(unit) for unit in self.units)


def _live_clause(sealed: _Bundle, live_is_standard: bool | None) -> Clause:
    if live_is_standard is False:
        return Clause(J6, NOT_APPLICABLE, "the live README does not follow the standard")
    if live_is_standard is None:
        return Clause(J6, UNEVALUATED, "whether the live README follows the standard is unknown")
    if sealed.readme is None or sealed.patch is None:
        return Clause(J6, UNEVALUATED, f"{README_FILENAME} or {PATCH_FILENAME} cannot be read")
    try:
        live = original_readme(sealed.readme, sealed.patch)
    except (ValueError, IndexError):
        live = None
    if live is None:
        return Clause(J6, UNEVALUATED, "the live README cannot be recovered from README.patch")
    units = sealed.inherited_units()
    rows = sealed.disposition_rows()
    if units is None or rows is None:
        return Clause(J6, UNEVALUATED, "facts.json or dispositions.json cannot be read")
    accounting = _Accounting(
        [
            units[str(row.get("unit_id"))]
            for row in rows
            if _accounts(row) and str(row.get("unit_id")) in units
        ]
    )
    old, new = read_doc(live), read_doc(sealed.readme)
    lost: list[str] = []
    new_headings = {heading_key(text) for _, text in new.headings}
    for _, text in old.headings:
        if heading_key(text) not in new_headings and not accounting.heading(text):
            lost.append(f"heading {text!r}")
    for fence in old.fences:
        if not any(fence in other for other in new.fences) and not accounting.contains(fence):
            lost.append(f"code block {fence.splitlines()[0][:50] if fence else ''!r}")
    new_targets = {_target(link.href) for link in extract_links(sealed.readme)}
    for link in extract_links(live):
        if _target(link.href) not in new_targets and not accounting.contains(link.href):
            lost.append(f"link {link.href}")
    candidate_text = _normalized(sealed.readme)
    for command in _verified_commands(sealed, live):
        if command not in candidate_text and not accounting.contains(command):
            lost.append(f"command {command!r}")
    if lost:
        return Clause(J6, FAIL, f"{len(lost)} lost without a disposition: {_joined(lost, 5)}")
    return Clause(J6, PASS, "no live heading, code block, link or verified command is lost")


def _target(href: str) -> str:
    return href.rstrip("/")


def _verified_commands(sealed: _Bundle, live: str) -> list[str]:
    rows = (sealed.facts or {}).get("facts")
    if not isinstance(rows, list):
        return []
    text = _normalized(live)
    commands = {
        _normalized(str(row.get("value", "")))
        for row in rows
        if isinstance(row, dict)
        and row.get("kind") == "install_command"
        and row.get("polarity") == "SUPPORTED"
    }
    return sorted(command for command in commands if command and command in text)


# --- the judge ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Inputs:
    sealed: _Bundle
    live_is_standard: bool | None
    standard_dir: Path


# The clause table: id -> how it is judged. Adding a clause is adding a row.
CLAUSES: tuple[tuple[str, Callable[[_Inputs], Clause]], ...] = (
    (J1, lambda i: _checks_clause(J1, i.sealed, FACTS_CHECKS)),
    (J2, lambda i: _standard_clause(i.sealed, i.standard_dir)),
    (J3, lambda i: _checks_clause(J3, i.sealed, (CLAIMS_CHECK,))),
    (J4, lambda i: _dispositions_clause(i.sealed)),
    (J5, lambda i: _rerun_clause(i.sealed)),
    (J6, lambda i: _live_clause(i.sealed, i.live_is_standard)),
)
NOT_PASSING: frozenset[str] = frozenset({FAIL, UNEVALUATED})


def judge_bundle(
    bundle: Path, *, live_is_standard: bool | None, standard_dir: Path | None = None
) -> JudgeVerdict:
    """The verdict on one sealed bundle directory. See the module docstring for every clause."""
    sealed = _Bundle.load(bundle)
    inputs = _Inputs(sealed, live_is_standard, standard_dir or DATA_DIR)
    clauses = tuple(judge(inputs) for _, judge in CLAUSES)
    failing = tuple(clause.id for clause in clauses if clause.status in NOT_PASSING)
    advisory = (sealed.review or {}).get("verdict")
    return JudgeVerdict(
        authorizable=not failing,
        clauses=clauses,
        failing=failing,
        reviewer_advisory=advisory if isinstance(advisory, str) else None,
    )


# --- is the live README standard? --------------------------------------------------------------


@lru_cache(maxsize=8)
def _survey_rows(data_dir: Path) -> Mapping[str, Mapping[str, Any]]:
    loaded = json.loads((data_dir / "survey.json").read_text(encoding="utf-8"))
    rows = loaded.get("rows")
    return rows if isinstance(rows, dict) else {}


def live_is_standard_for(repository: str, *, standard_dir: Path | None = None) -> bool:
    """The live README follows the standard, as ``survey.json`` recorded it: it exists, it draws an
    At a Glance (``glance_form`` is not null) and it carries the product banner. A repository the
    survey does not list, or a survey that cannot be read, is not standard."""
    try:
        row = _survey_rows(standard_dir or DATA_DIR).get(repository)
    except (OSError, ValueError):
        return False
    if not isinstance(row, Mapping):
        return False
    return row.get("readme") is True and bool(row.get("glance_form")) and row.get("banner") is True


def judge_repository_bundle(
    bundle: Path, repository: str, *, standard_dir: Path | None = None
) -> JudgeVerdict:
    """The production call: the live-README question answered from the survey for ``repository``."""
    return judge_bundle(
        bundle,
        live_is_standard=live_is_standard_for(repository, standard_dir=standard_dir),
        standard_dir=standard_dir,
    )
