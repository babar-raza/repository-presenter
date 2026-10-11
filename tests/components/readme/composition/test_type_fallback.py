"""The API Reference type-description fallback (composition/type_fallback.py).

The strings are the real final reply of aspose-3d-foss/Aspose.3D-FOSS-for-Java's api_reference
batch in the baseline reseal of 7c5acbf7 (call d4499ff1de77, both attempts byte-identical): one
unit invents ``ArrayList`` from ``ArrayListAdapter`` and the other thirty-nine are fine.
"""

from __future__ import annotations

import copy
import functools
from typing import Any

from repository_presenter.components.readme.composition.authoring import (
    SectionTask,
    unit_checks,
)
from repository_presenter.components.readme.composition.type_fallback import (
    recover_section_authoring_with_type_fallback,
    recover_unevidenced_type_descriptions,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument

NAME = "Aspose.3D FOSS for Java"
REPOSITORY = "aspose-3d-foss/Aspose.3D-FOSS-for-Java"
OBJECT = "public_symbol:com.aspose.threed.a3dobject"
ADAPTER = "public_symbol:com.aspose.threed.arraylistadapter"


def _symbol(fact_id: str, value: str, **attributes: str) -> Fact:
    return Fact(
        fact_id,
        "public_symbol",
        value,
        (
            Evidence(
                "src/main/java/com/aspose/threed/X.java", "line 3; class; public by declaration"
            ),
        ),
        attributes={"symbol_kind": "class", **attributes},
    )


FACTS = FactsDocument(
    REPOSITORY,
    "a" * 40,
    (
        Fact("identity:repository", "identity", REPOSITORY, (Evidence("x"),)),
        _symbol(OBJECT, "com.aspose.threed.A3DObject"),
        _symbol(ADAPTER, "com.aspose.threed.ArrayListAdapter"),
    ),
)
TASK = SectionTask(
    "api_reference",
    {},
    frozenset({OBJECT, ADAPTER}),
    (f"type:{OBJECT}", f"type:{ADAPTER}"),
    key="api_reference#types-1",
    slot_facts={f"type:{OBJECT}": frozenset({OBJECT}), f"type:{ADAPTER}": frozenset({ADAPTER})},
)
OBJECT_TEXT = (
    "A3DObject represents a base class for all 3D objects in Aspose.3D FOSS for Java, providing "
    "common properties and methods for managing object identity and metadata."
)
ADAPTER_TEXT = (
    "ArrayListAdapter provides a wrapper around Java's ArrayList to support list operations "
    "required by Aspose.3D FOSS for Java internally."
)


def _reply(object_text: str = OBJECT_TEXT, adapter_text: str = ADAPTER_TEXT) -> dict[str, Any]:
    return {
        "units": [
            {
                "section": "api_reference",
                "slot": f"type:{fact_id}",
                "text": text,
                "fact_ids": [fact_id],
            }
            for fact_id, text in ((OBJECT, object_text), (ADAPTER, adapter_text))
        ],
        "omitted": [],
    }


def _checks(output: dict[str, Any]) -> list[str]:
    return unit_checks(output, TASK, FACTS, NAME)


def test_the_real_reply_is_refused_for_the_inferred_standard_library_type() -> None:
    assert _checks(_reply()) == [
        f"unit type:{ADAPTER}: identifiers that are not accepted fact values: ArrayList "
        "(nearest accepted: ArrayListAdapter)"
    ]


def test_a_description_refused_only_for_a_stray_identifier_becomes_its_summary() -> None:
    reply = _reply()
    recovered = recover_unevidenced_type_descriptions(reply, task=TASK, facts=FACTS, name=NAME)
    assert recovered is not None
    texts = [unit["text"] for unit in recovered["units"]]
    # The sound description is untouched; the refused one is the symbol's own kind, no new claim.
    assert texts == [OBJECT_TEXT, "Public class."]
    assert recovered["units"][1]["fact_ids"] == [ADAPTER]
    assert _checks(recovered) == []


def test_a_signature_is_the_summary_when_the_unit_checks_accept_it() -> None:
    facts = FactsDocument(
        REPOSITORY,
        "a" * 40,
        (
            *FACTS.facts[:2],
            _symbol(
                ADAPTER, "com.aspose.threed.ArrayListAdapter", signature="class ArrayListAdapter"
            ),
        ),
    )
    recovered = recover_unevidenced_type_descriptions(_reply(), task=TASK, facts=facts, name=NAME)
    assert recovered is not None
    assert recovered["units"][1]["text"] == "Defined as class ArrayListAdapter."


def test_a_unit_with_any_other_defect_is_left_for_the_job_to_fail_on() -> None:
    """Negative controls: a stray identifier AND another refusal, a refusal that is not about
    identifiers, a fact the slot may not cite, and a section other than api_reference."""
    both = _reply(adapter_text=ADAPTER_TEXT + " It is the commercial edition.")
    assert recover_unevidenced_type_descriptions(both, task=TASK, facts=FACTS, name=NAME) is None
    assert both["units"][1]["text"].endswith("commercial edition.")

    markup = _reply(adapter_text="ArrayListAdapter wraps a list <list> of items.")
    assert recover_unevidenced_type_descriptions(markup, task=TASK, facts=FACTS, name=NAME) is None

    outside = _reply()
    outside["units"][1]["fact_ids"] = [OBJECT]
    assert recover_unevidenced_type_descriptions(outside, task=TASK, facts=FACTS, name=NAME) is None

    other = SectionTask(
        "key_capabilities", {}, TASK.accepted_ids, TASK.slots, slot_facts=TASK.slot_facts
    )
    assert (
        recover_unevidenced_type_descriptions(_reply(), task=other, facts=FACTS, name=NAME) is None
    )


def test_only_type_slots_are_summarised() -> None:
    """A hub or intro unit with a stray identifier is prose the model owns: not replaced."""
    task = SectionTask(
        "api_reference",
        {},
        frozenset({ADAPTER}),
        ("intro",),
        slot_facts={"intro": frozenset({ADAPTER})},
    )
    reply = {
        "units": [
            {
                "section": "api_reference",
                "slot": "intro",
                "text": ADAPTER_TEXT,
                "fact_ids": [ADAPTER],
            }
        ],
        "omitted": [],
    }
    assert recover_unevidenced_type_descriptions(reply, task=task, facts=FACTS, name=NAME) is None


def test_nothing_to_recover_returns_none() -> None:
    assert (
        recover_unevidenced_type_descriptions(
            _reply(adapter_text="ArrayListAdapter adapts lists."), task=TASK, facts=FACTS, name=NAME
        )
        is None
    )


def test_the_composed_recovery_keeps_the_existing_corrections() -> None:
    """The wrapper first applies recover_section_authoring_output (here an angle-bracket mention)
    and then the type fallback, and is None only when neither changed anything."""
    recover = functools.partial(
        recover_section_authoring_with_type_fallback,
        slot_titles={},
        task=TASK,
        facts=FACTS,
        name=NAME,
    )
    reply = _reply(object_text="A3DObject is the base of every <node> in a scene.")
    recovered = recover(copy.deepcopy(reply))
    assert recovered is not None
    assert recovered["units"][0]["text"] == "A3DObject is the base of every node in a scene."
    assert recovered["units"][1]["text"] == "Public class."
    assert recover(_reply(adapter_text="ArrayListAdapter adapts lists.")) is None
