"""TC-REV-01 / G3-W08: a returned REJECT stands unless every finding it rested on carries a
recorded deterministic refutation.

Three layers. Unit controls pin each scope rule to its class (a deterministic refutation or a
judgment) and show that a judgment never turns a rejection into an ACCEPT. Negative controls
cover a hallucinated quote, malformed output, a refuted finding that stays refuted, a
judgment-only demotion that no longer flips the verdict, and the mutation "remove a rule and the
rejection stands". The replay layer feeds every sealed review under ``candidates/`` (and the raw
reads of the bundles that keep them) back through the current fold, with the sealed bundle's own
facts, units, dispositions, plan and candidate README, and no provider call.
"""

from __future__ import annotations

import functools
import json
import re
from pathlib import Path
from typing import Any

import pytest

from repository_presenter.components.readme.composition.renderer import renderer_sentences
from repository_presenter.components.readme.extractors.platforms.registry import (
    known_ecosystems,
)
from repository_presenter.components.readme.review.independent import review as review_module
from repository_presenter.components.readme.review.independent.review import (
    ACCEPT,
    DETERMINISTIC_RULES,
    JUDGMENT_RULES,
    Ruling,
    claim_evidence,
    refutation,
    review_checks,
    review_document,
    scope_defect,
    scope_rulings,
    second_read_decision,
    unit_texts,
)
from repository_presenter.components.readme.validation.registry import (
    deferred_on_required_rows,
    record_review_verdict,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument, read_facts
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.registry.loader import load_registry
from support import REPO_ROOT

known_ecosystems()

CANDIDATES = REPO_ROOT / "candidates"
MANIFESTS = load_manifests(REPO_ROOT / "prompts")
REVIEWER = MANIFESTS["independent_review"]
AUTHORING = MANIFESTS["section_authoring"]

# ---- a small world every unit control shares ------------------------------------------------

_LEGACY = "The legacy exporter supports binary glTF output through the binary flag."
_EXAMPLE = "def run_example():\n    return widget.render(canvas, scale=2)\n"
FACTS = FactsDocument(
    "o/r",
    "a" * 40,
    (
        Fact("identity:repository", "identity", "o/r", (Evidence("x"),)),
        Fact("public_symbol:pkg.widget", "public_symbol", "pkg.Widget", (Evidence("x"),)),
        Fact("package:version", "package", "1.2.3", (Evidence("x"),)),
        Fact("example:001", "example", _EXAMPLE, (Evidence("x"),), polarity="CONTRADICTED"),
        Fact("inherited_unit:009.paragraph", "inherited_unit", _LEGACY, (Evidence("x"),)),
    ),
)
BY_ID = {fact.id: fact for fact in FACTS.facts}
CANDIDATE = (
    "# Widget\n\n## Installation\n\nInstall with pip. Version 1.2.3 is current.\n\n"
    "## Key Capabilities\n\nIt renders widgets quickly and everywhere, fast.\n"
)
ORIGINAL = "# Widget\n\nThe widget also exports PDF files.\n"
EVIDENCE = claim_evidence(ORIGINAL, FACTS)
DISPOSITIONS = {
    "dispositions": [{"unit_id": "inherited_unit:009.paragraph", "disposition": "OMIT_UNSUPPORTED"}]
}
RENDERED = ("The verified public surface has 5 types.",)


def finding(label: str = "F01", **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": label,
        "section_id": "key_capabilities",
        "causal_stage": "S6",
        "criterion": "presentation",
        "text": "The section is wrong.",
        "quote": "",
        "fact_ids": [],
        "absent": [],
        "omission": None,
        "repair": "Fix it.",
    }
    return {**base, **overrides}


def omission(
    ids: list[str], quotes: list[str], section: str = "key_capabilities"
) -> dict[str, Any]:
    return {"kind": "omission", "section_id": section, "missing_ids": ids, "missing_quotes": quotes}


def rulings_of(f: dict[str, Any], **kwargs: Any) -> list[Ruling]:
    kwargs.setdefault("rendered", RENDERED)
    kwargs.setdefault("dispositions", DISPOSITIONS)
    kwargs.setdefault("unit_texts", [])
    return scope_rulings(f, CANDIDATE, BY_ID, EVIDENCE, **kwargs)


# One minimal finding per DETERMINISTIC rule. Each is refuted by that rule and by no other
# deterministic one, so removing the rule from DETERMINISTIC_RULES must leave the finding standing.
DETERMINISTIC_EXEMPLARS: dict[str, dict[str, Any]] = {
    "ABSENCE_PRESENT": finding(quote="# Widget", absent=["It renders widgets"]),
    "ABSENCE_UNSUPPORTED": finding(quote="# Widget", absent=["a sentence nobody ever wrote"]),
    "ABSENCE_SETTLED": finding(
        quote="# Widget", absent=["It renders widgets", "a sentence nobody ever wrote"]
    ),
    "OMISSION_PRESENT": finding(
        quote="# Widget",
        omission=omission([], ["It renders widgets quickly and everywhere, fast."]),
    ),
    "OMISSION_UNRESTORABLE": finding(quote="# Widget", omission=omission(["example:001"], [])),
    "OMISSION_SETTLED": finding(
        quote="# Widget",
        omission=omission(["example:001"], ["It renders widgets quickly and everywhere, fast."]),
    ),
    "EXCLUDED_EVIDENCE_QUOTE": finding(
        quote="def run_example(): return widget.render(canvas, scale=2)"
    ),
    "EXCLUDED_EVIDENCE_CITED": finding(
        quote="# Widget", absent=["exports PDF files"], fact_ids=["example:001"]
    ),
    "EXCLUDED_DISPOSITION": finding(quote=_LEGACY),
    "RENDERER_SENTENCE": finding(quote=RENDERED[0]),
    "RENDERER_STRUCTURE": finding(section_id="structure"),
    "RENDERER_HEADING": finding(quote="### Installation"),
    "RENDERER_CHROME": finding(quote="<details>"),
    "RENDERER_UNWRITTEN_FACT": finding(quote="| `pkg.Widget` | A widget. |"),
    "RENDERER_SECTION": finding(section_id="installation", quote="Install with pip."),
    "CITED_FACT_LITERAL": finding(quote="Version 1.2.3 is current.", fact_ids=["package:version"]),
}

# One minimal finding per JUDGMENT rule: the rule matches and annotates, and refutes nothing.
JUDGMENT_EXEMPLARS: dict[str, dict[str, Any]] = {
    "ABSENCE_RESTATED": finding(
        quote="# Widget", absent=["renders widgets quickly everywhere fast"]
    ),
    "OMISSION_UNCHECKABLE": finding(quote="# Widget", omission=omission([], [])),
    "OMISSION_SECTION_MISMATCH": finding(
        quote="# Widget", omission=omission(["example:001"], [], section="installation")
    ),
    "VERIFIED_SYMBOL_NAMED": finding(quote="The `pkg.Widget` class is the only API."),
    "RENDERER_SECTION_FACTUAL": finding(
        criterion="factuality",
        section_id="installation",
        quote="Install with pip.",
        fact_ids=["package:version"],
    ),
    "FACTUALITY_UNCHECKABLE": finding(criterion="factuality", quote="It renders widgets."),
    "FACTUALITY_INHERITED_ONLY": finding(
        criterion="factuality",
        quote="It renders widgets.",
        fact_ids=["inherited_unit:009.paragraph"],
    ),
    # The quote is the renderer's, but the finding says something is MISSING that code cannot
    # settle (it is in the original, not in the section): the omission stands.
    "RENDERER_OWNED_OMISSION_STANDS": finding(
        section_id="installation", quote="Install with pip.", absent=["exports PDF files"]
    ),
    "CITED_FACT_QUOTE_ONLY": finding(
        quote="Version 1.2.3 is current.",
        fact_ids=["package:version"],
        absent=["exports PDF files"],
    ),
    "CITED_SYMBOL_NAMED": finding(
        quote="`pkg.Widget` writes PDF.", fact_ids=["public_symbol:pkg.widget"]
    ),
    "RENDERER_UNWRITTEN_FACT_FACTUAL": finding(
        criterion="factuality",
        quote="| `pkg.Widget` | A widget. |",
        fact_ids=["package:version"],
    ),
}
WRITTEN_BY_A_UNIT = ["The `pkg.Widget` class is the only API."]


def test_every_rule_has_exactly_one_class_and_an_exemplar() -> None:
    assert not DETERMINISTIC_RULES & JUDGMENT_RULES
    assert set(DETERMINISTIC_EXEMPLARS) == DETERMINISTIC_RULES
    # Rules with no tractable one-line exemplar here are exercised by the replay below or by
    # test_independent.py; every other judgment rule must have one.
    untested = JUDGMENT_RULES - set(JUDGMENT_EXEMPLARS)
    assert untested == {"CITED_FACT_PARAPHRASE", "SINGLE_READER_PROSE"}
    with pytest.raises(ValueError):
        Ruling("x", "NOT_A_RULE")


@pytest.mark.parametrize("rule", sorted(DETERMINISTIC_EXEMPLARS))
def test_a_deterministic_rule_refutes_and_is_recorded_with_its_evidence(rule: str) -> None:
    f = DETERMINISTIC_EXEMPLARS[rule]
    rulings = rulings_of(f)
    assert rule in {r.rule for r in rulings}, [r.rule for r in rulings]
    refuted = refutation(rulings)
    assert refuted is not None and refuted.deterministic
    # The ruling is a reason string first, so scope_defect's historical contract holds.
    assert scope_defect(f, CANDIDATE, BY_ID, EVIDENCE, RENDERED, [], None, DISPOSITIONS) == str(
        rulings[0]
    )
    document = review_document(
        {"verdict": "REJECT_PRESENTATION", "findings": [f], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=CANDIDATE,
        facts=FACTS,
        original_readme=ORIGINAL,
        rendered=RENDERED,
        units={"units": []},
        dispositions=DISPOSITIONS,
    )
    (record,) = document["advisory"]
    assert document["findings"] == []
    assert record["refuted_by"]["rule"] == refuted.rule
    assert record["refuted_by"]["evidence"] == refuted.evidence
    assert record["reviewer_scope_defect"] == str(refuted)
    assert document["verdict"] == ACCEPT
    assert document["verdict_as_returned"] == "REJECT_PRESENTATION"
    assert document["verdict_basis"] == "rejection_refuted_deterministically"
    # The record is plain data: it round-trips through JSON.
    assert json.loads(json.dumps(document))["advisory"][0]["refuted_by"] == record["refuted_by"]


@pytest.mark.parametrize("rule", sorted(DETERMINISTIC_EXEMPLARS))
def test_removing_a_deterministic_rule_leaves_the_rejection_standing(
    rule: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The mutation control: take the rule away and the same finding carries the REJECT."""
    f = DETERMINISTIC_EXEMPLARS[rule]
    others = [r.rule for r in rulings_of(f) if r.deterministic and r.rule != rule]
    if others:
        # A second rule also refutes this exemplar; mutate it away as well so the control
        # isolates the first.
        monkeypatch.setattr(review_module, "DETERMINISTIC_RULES", DETERMINISTIC_RULES - set(others))
    monkeypatch.setattr(
        review_module,
        "DETERMINISTIC_RULES",
        review_module.DETERMINISTIC_RULES - {rule},
    )
    document = review_document(
        {"verdict": "REJECT_PRESENTATION", "findings": [f], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=CANDIDATE,
        facts=FACTS,
        original_readme=ORIGINAL,
        rendered=RENDERED,
        units={"units": []},
        dispositions=DISPOSITIONS,
    )
    assert document["verdict"] == "REJECT_PRESENTATION"
    assert document["verdict_basis"] == "rejection_stands"
    assert [x["id"] for x in document["findings"]] == ["F01"]
    assert "refuted_by" not in document["findings"][0]


@pytest.mark.parametrize("rule", sorted(JUDGMENT_EXEMPLARS))
def test_a_judgment_rule_annotates_but_never_flips_a_rejection(rule: str) -> None:
    f = JUDGMENT_EXEMPLARS[rule]
    # A content unit wrote the quoted sentence (so the renderer-owned rules do not apply), except
    # for the one rule that is about text no unit wrote.
    texts = [] if rule == "RENDERER_UNWRITTEN_FACT_FACTUAL" else [f["quote"]]
    rulings = rulings_of(f, unit_texts=texts)
    assert rule in {r.rule for r in rulings}, [r.rule for r in rulings]
    assert refutation(rulings) is None, [(r.rule, r.deterministic) for r in rulings]
    # scope_defect still reports the first match, exactly as before ...
    assert scope_defect(f, CANDIDATE, BY_ID, EVIDENCE, RENDERED, texts, None, DISPOSITIONS)
    # ... but the document no longer folds it: the rejection stands and the repair loop reads it.
    document = review_document(
        {"verdict": "REJECT_PRESENTATION", "findings": [f], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=CANDIDATE,
        facts=FACTS,
        original_readme=ORIGINAL,
        rendered=RENDERED,
        units={"units": [{"section": "key_capabilities", "text": t} for t in texts]},
        dispositions=DISPOSITIONS,
    )
    assert document["verdict"] == "REJECT_PRESENTATION"
    assert document["verdict_basis"] == "rejection_stands"
    (record,) = document["findings"]
    assert "refuted_by" not in record and "reviewer_scope_defect" not in record
    assert rule in {r["rule"] for r in record["unrefuted_scope_rules"]}
    assert record["causal_state"] == "COMPOSING"
    # And the same finding under a returned ACCEPT changes nothing about that verdict.
    accepted = review_document(
        {"verdict": ACCEPT, "findings": [f], "preserve": []},
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=CANDIDATE,
        facts=FACTS,
        original_readme=ORIGINAL,
        rendered=RENDERED,
        units={"units": [{"section": "key_capabilities", "text": t} for t in texts]},
        dispositions=DISPOSITIONS,
    )
    assert accepted["verdict"] == ACCEPT and accepted["verdict_basis"] == "accepted_as_returned"


# ---- the standing rule at document level ------------------------------------------------------


def _document(output: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("candidate_readme", CANDIDATE)
    kwargs.setdefault("facts", FACTS)
    kwargs.setdefault("original_readme", ORIGINAL)
    kwargs.setdefault("rendered", RENDERED)
    kwargs.setdefault("dispositions", DISPOSITIONS)
    return review_document(output, REVIEWER, AUTHORING, "d" * 64, **kwargs)


def test_one_unrefuted_finding_among_refuted_ones_carries_the_rejection() -> None:
    refuted = DETERMINISTIC_EXEMPLARS["ABSENCE_PRESENT"]
    real = finding("F02", quote="# Widget", absent=["exports PDF files"])  # truly absent
    document = _document(
        {
            "verdict": "REJECT_PRESENTATION",
            "findings": [finding("F01", **{k: v for k, v in refuted.items() if k != "id"}), real],
            "preserve": [],
        }
    )
    assert document["verdict"] == "REJECT_PRESENTATION"
    assert [f["id"] for f in document["findings"]] == ["F02"]
    assert [f["id"] for f in document["advisory"]] == ["F01"]
    assert document["advisory"][0]["refuted_by"]["rule"] == "ABSENCE_PRESENT"


def test_a_rejection_with_no_finding_at_all_stands() -> None:
    """Nothing refuted it, so nothing can clear it (it used to fold to ACCEPT)."""
    document = _document({"verdict": "REJECT_FACTUAL", "findings": [], "preserve": []})
    assert document["verdict"] == "REJECT_FACTUAL"
    assert document["verdict_basis"] == "rejection_stands"
    judged = record_review_verdict({"checks": [{"id": "BC-10", "verdict": "PENDING"}]}, document)
    assert judged["checks"][0]["verdict"] == "FAIL"


def test_malformed_findings_cannot_clear_a_rejection() -> None:
    """A finding naming no section or a stage the loop cannot reopen is unrepairable, not
    refuted: the rejection stands and says why."""
    for bad in (
        finding("F01", section_id="", quote="# Widget"),
        finding("F01", causal_stage="unclear", quote="# Widget"),
        finding("F01", causal_stage="S9", quote="# Widget"),
    ):
        document = _document({"verdict": "REJECT_FACTUAL", "findings": [bad], "preserve": []})
        assert document["verdict"] == "REJECT_FACTUAL", bad
        (record,) = document["advisory"]
        assert "refuted_by" not in record and "unrepairable" in record
        assert document["findings"] == []


def test_a_hallucinated_quote_is_dropped_before_the_fold_and_cannot_hold_or_clear_a_verdict() -> (
    None
):
    """review_checks drops a finding whose quote is nowhere in its section (a deterministic
    refutation that never reaches the fold); with no quote located the whole reply is re-asked."""
    invented = finding("F01", quote="This sentence is nowhere in the README at all.")
    real = finding("F02", quote="It renders widgets quickly and everywhere, fast.")
    output: dict[str, Any] = {
        "verdict": "REJECT_PRESENTATION",
        "findings": [invented, real],
        "preserve": [],
    }
    assert review_checks(output, CANDIDATE, FACTS) == []
    assert [f["id"] for f in output["findings"]] == ["F02"]
    only_invented = {"verdict": "REJECT_PRESENTATION", "findings": [invented], "preserve": []}
    assert review_checks(only_invented, CANDIDATE, FACTS) != []


def test_a_refuted_rejection_still_needs_a_second_read() -> None:
    first = _document(
        {
            "verdict": "REJECT_PRESENTATION",
            "findings": [DETERMINISTIC_EXEMPLARS["ABSENCE_PRESENT"]],
            "preserve": [],
        }
    )
    assert first["verdict"] == ACCEPT
    decision = second_read_decision(first, [])
    assert decision.triggered and "REJECTION_REFUTED" in decision.reasons
    # A plain ACCEPT with nothing overturned stays a single read.
    plain = _document({"verdict": ACCEPT, "findings": [], "preserve": []})
    assert not second_read_decision(plain, []).triggered
    # And a standing rejection does not claim to have been refuted.
    standing = _document(
        {
            "verdict": "REJECT_PRESENTATION",
            "findings": [JUDGMENT_EXEMPLARS["FACTUALITY_UNCHECKABLE"]],
            "preserve": [],
        }
    )
    assert "REJECTION_REFUTED" not in second_read_decision(standing, []).reasons


def test_a_standing_rejection_is_repairable_by_the_existing_loop() -> None:
    """The finding is blocking with a named section and a causal state, which is what
    repair/targeted.py::review_defects reads - no change to the loop is needed."""
    from repository_presenter.components.readme.repair.targeted import review_defects

    f = finding(quote="The `pkg.Widget` class is the only API.")
    document = _document(
        {"verdict": "REJECT_PRESENTATION", "findings": [f], "preserve": []},
        units={"units": [{"section": "key_capabilities", "text": WRITTEN_BY_A_UNIT[0]}]},
    )
    assert deferred_on_required_rows(document) == []
    (defect,) = review_defects(document, FACTS, {"key_capabilities"}, "repairer")
    assert defect.repairable and defect.section_id == "key_capabilities"


# ---- replay: every sealed review through the current fold --------------------------------------

DERIVED = {
    "causal_state",
    "reviewer_scope_defect",
    "single_reader_advisory",
    "reader",
    "refuted_by",
    "unrefuted_scope_rules",
    "unrepairable",
    "absent_refuted",
    "absent_invented",
    "absent_remaining",
    "omission_refuted",
    "omission_unrestorable",
    "omission_remaining",
}


def sealed_reviews() -> list[Path]:
    bundles = []
    for current in sorted(CANDIDATES.glob("*/CURRENT")):
        bundle = current.parent / current.read_text("utf-8").strip()
        if (bundle / "review.json").is_file():
            bundles.append(bundle)
    return bundles


def _reverse_patch(new_text: str, patch_text: str) -> str:
    """The upstream README a sealed README.patch was cut against, rebuilt from the candidate."""
    new_lines = new_text.split("\n")
    out: list[str] = []
    pos = 0
    lines = patch_text.split("\n")
    i = 0
    while i < len(lines) and not lines[i].startswith("@@"):
        i += 1
    while i < len(lines):
        header = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[i])
        if not header:
            i += 1
            continue
        start = int(header.group(3)) - 1
        if int(header.group(4) or 1) == 0:
            start += 1
        out.extend(new_lines[pos:start])
        pos = start
        i += 1
        while i < len(lines) and not lines[i].startswith("@@"):
            line = lines[i]
            if line.startswith("+"):
                pos += 1
            elif line.startswith("-"):
                out.append(line[1:])
            elif line.startswith(" "):
                out.append(line[1:])
                pos += 1
            i += 1
    out.extend(new_lines[pos:])
    return "\n".join(out)


@functools.lru_cache(maxsize=1)
def _registry_entries() -> dict[str, Any]:
    registry = load_registry(REPO_ROOT / "data" / "registry.json")
    return {entry.repository: entry for entry in registry.entries}


@functools.lru_cache(maxsize=64)
def _load(bundle: Path) -> dict[str, Any]:
    def read(name: str) -> Any:
        return json.loads((bundle / name).read_text("utf-8"))

    facts = read_facts(bundle / "facts.json")
    readme = (bundle / "README.md").read_text("utf-8")
    entries = _registry_entries()
    plan, units, dispositions = (
        read("plan.json"),
        read("content_units.json"),
        read("dispositions.json"),
    )
    return {
        "facts": facts,
        "readme": readme,
        "original": _reverse_patch(readme, (bundle / "README.patch").read_text("utf-8")),
        "units": units,
        "dispositions": dispositions,
        "rendered": renderer_sentences(entries[facts.repository], facts, plan, units, dispositions),
        "review": read("review.json"),
    }


def _fold(world: dict[str, Any], first: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return review_document(
        first,
        REVIEWER,
        AUTHORING,
        "d" * 64,
        candidate_readme=world["readme"],
        facts=world["facts"],
        original_readme=world["original"],
        rendered=world["rendered"],
        units=world["units"],
        dispositions=world["dispositions"],
        **extra,
    )


def _first_read(review: dict[str, Any]) -> dict[str, Any]:
    """The first reader's reply as review.json lets us rebuild it: its returned verdict and every
    finding no extra read raised, minus what the fold derived."""
    findings = [
        {k: v for k, v in f.items() if k not in DERIVED}
        for f in [*review["findings"], *review["advisory"]]
        if "reader" not in f
    ]
    return {
        "verdict": review["verdict_as_returned"],
        "findings": findings,
        "preserve": review.get("preserve", []),
    }


def _assert_standing_rule(first: dict[str, Any], document: dict[str, Any]) -> str:
    """The invariant: ACCEPT from a returned rejection only when every finding is refuted by a
    deterministic rule; otherwise the rejection stands. Returns which."""
    returned = first["verdict"]
    if returned == ACCEPT:
        assert document["verdict"] == ACCEPT
        return "accepted"
    if document["verdict"] == ACCEPT:
        assert document["findings"] == [] and first["findings"], "an empty rejection cannot clear"
        for record in document["advisory"]:
            assert "unrepairable" not in record
            assert record["refuted_by"]["rule"] in DETERMINISTIC_RULES, record["id"]
            assert record["reviewer_scope_defect"], record["id"]
        return "refuted"
    assert document["verdict"] == returned
    assert (
        document["findings"]
        or any("refuted_by" not in record for record in document["advisory"])
        or not first["findings"]
    )
    return "stands"


def test_there_are_sealed_reviews_to_replay() -> None:
    assert sealed_reviews(), "no sealed review under candidates/; the replay would pass vacuously"


@pytest.mark.parametrize("bundle", sealed_reviews(), ids=lambda b: b.parent.name)
def test_replaying_a_sealed_review_never_lets_a_judgment_clear_a_rejection(bundle: Path) -> None:
    world = _load(bundle)
    first = _first_read(world["review"])
    document = _fold(world, first)
    outcome = _assert_standing_rule(first, document)
    # What the sealed bundle shows is what the old fold did; the new one may only be stricter.
    sealed_accept = world["review"]["verdict"] == ACCEPT
    if outcome in ("stands",):
        assert first["verdict"] != ACCEPT
    if not sealed_accept:
        assert outcome == "stands"
    # Every demotion the sealed review recorded as a reviewer-scope defect is either still
    # refuted (with its rule) or now stands: none is silently both advisory and unrefuted.
    for record in document["advisory"]:
        if record["id"] in {f["id"] for f in first["findings"]} and "reader" not in record:
            assert (
                "refuted_by" in record
                or "unrepairable" in record
                or "single_reader_advisory" in record
            )


def test_replay_summary_partitions_every_sealed_rejection() -> None:
    counts = {"accepted": 0, "refuted": 0, "stands": 0}
    for bundle in sealed_reviews():
        world = _load(bundle)
        first = _first_read(world["review"])
        counts[_assert_standing_rule(first, _fold(world, first))] += 1
    assert sum(counts.values()) == len(sealed_reviews())
    # Printed for the PR description (pytest -s): the replay table in one line.
    print(f"\nTC-REV-01 replay: {counts}")


def _raw_reads(bundle: Path) -> list[dict[str, Any]]:
    raw = json.loads((bundle / "raw_calls.json").read_text("utf-8"))
    return [c["output"] for c in raw.values() if c["job"] == "independent_review"]


def sealed_with_raw_reads() -> list[Path]:
    return [b for b in sealed_reviews() if (b / "raw_calls.json").is_file()]


def test_some_sealed_bundles_keep_their_raw_reads() -> None:
    assert sealed_with_raw_reads()


@pytest.mark.parametrize("bundle", sealed_with_raw_reads(), ids=lambda b: b.parent.name)
def test_replaying_the_raw_reads_agrees_with_replaying_review_json(bundle: Path) -> None:
    """The bundles that keep the readers' own replies: fold the first and second read as the
    live loop would, and require the same standing-rule outcome as the review.json rebuild."""
    world = _load(bundle)
    rebuilt = _first_read(world["review"])
    key = lambda f: (f["id"], f["section_id"], f["quote"])  # noqa: E731
    reads = _raw_reads(bundle)
    wanted = sorted(map(key, rebuilt["findings"]))
    firsts = [r for r in reads if sorted(map(key, r.get("findings", []))) == wanted]
    assert firsts, "no raw read matches the first read recorded in review.json"
    first = firsts[0]
    others = [r for r in reads if r is not first]
    assert first["verdict"] == rebuilt["verdict"]
    alone = _fold(world, first)
    together = _fold(world, first, second=others[0] if others else None)
    assert _assert_standing_rule(first, alone) == _assert_standing_rule(
        rebuilt, _fold(world, rebuilt)
    )
    # A second read can add findings on the accept path but never clears a standing rejection.
    if alone["verdict"] != ACCEPT:
        assert together["verdict"] != ACCEPT
    # The ACCEPT/ACCEPT bundle stays accepted.
    if (
        first["verdict"] == ACCEPT
        and not first.get("findings")
        and all(r["verdict"] == ACCEPT and not r.get("findings") for r in others)
    ):
        assert together["verdict"] == ACCEPT


def test_unit_texts_helper_is_unchanged_for_the_replay() -> None:
    assert unit_texts(None) is None
