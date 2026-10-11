"""What section_authoring does when its universal re-ask did not converge (wave 3, cut f69f75c7).

Nine of thirty-six repositories ended at ``section_authoring: output rejected twice``. Each was read
from the archived ``rejected-*.json`` of its transaction (copied beside this file as
``fixtures/wave3_*``; the replies and the rejections are the real ones, only the facts around them
are small stand-ins that reproduce the same refusals). Three causes, all in how the single re-ask is
spent:

* the rejection named only the first of several violations of one kind (TeX-Python restated two
  commands and was told about one);
* a reply that fixed what it was told introduced a violation it was not told about (PDF-Cpp,
  Slides-Java), or repeated the same reply byte for byte (Words-Python, temperature zero);
* a reply that was right about everything but one unit still failed the whole section
  (Slides-Java: six of seven limitation units fine, one list item unstated).

The remedy is unit-level: every violation of every unit is listed in one rejection, a third ask is
made for only the units still failing (the accepted ones are kept as the second reply gave them),
and the last-resort deterministic repairs only remove text that restates what the page already
prints.
"""

from __future__ import annotations

import copy
import functools
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from repository_presenter.components.readme.composition.authoring import (
    SectionTask,
    authoring_schema,
    identifier_tokens,
    restated_command_lines,
    slot_records,
    slots_clause,
    unit_checks,
)
from repository_presenter.components.readme.composition.authoring_retry import (
    authoring_narrowing,
    failing_slots,
    recover_restating_sentences,
    repeated_slots,
)
from repository_presenter.components.readme.composition.coherence import (
    recover_coherence_missing_units,
)
from repository_presenter.components.readme.composition.output_bounds import (
    bound_authoring_citations,
)
from repository_presenter.components.readme.composition.type_fallback import (
    recover_section_authoring_with_type_fallback,
)
from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.errors import JobError
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.jobs import CallStore, JobContext, JobResult, run_job
from repository_presenter.core.llm.ledger import Ledger
from repository_presenter.core.llm.prompts import load_manifests
from support import REPO_ROOT, mock_gateway

FIXTURES = Path(__file__).parent / "fixtures"
MANIFEST = load_manifests(REPO_ROOT / "prompts")["section_authoring"]
CONFIG = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")


def _real(name: str) -> dict[str, Any]:
    """A rejected call exactly as the wave-3 run kept it: job, attempt, rejection, content."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _reply(name: str) -> dict[str, Any]:
    """The reply a rejected call kept, as the output object the model returned."""
    return json.loads(_real(name)["content"])  # type: ignore[no-any-return]


def _fact(fact_id: str, value: str, polarity: str = "SUPPORTED") -> Fact:
    kind = fact_id.split(":", 1)[0]
    return Fact(fact_id, kind, value, (Evidence("x"),), polarity=polarity)  # type: ignore[arg-type]


def _identity() -> list[Fact]:
    return [
        _fact(f"identity:{key}", value)
        for key, value in (
            ("repository", "org/repo"),
            ("platform", "any"),
            ("ecosystem", "any"),
            ("family", "any"),
            ("revision", "a" * 40),
        )
    ]


def _spelled(units: list[dict[str, Any]], *, refused: tuple[str, ...] = ()) -> list[Fact]:
    """One public_symbol fact per identifier the units spell, except ``refused``: the wave-3
    facts accepted every name these replies used apart from the one the run refused, and this is
    the smallest stand-in that reproduces exactly that."""
    tokens: set[str] = set()
    for unit in units:
        tokens |= identifier_tokens(str(unit["text"]).replace("`", ""))
    bare = sorted({t[:-2] if t.endswith("()") else t for t in tokens} - set(refused))
    return [_fact(f"public_symbol:spelled-{index}", name) for index, name in enumerate(bare)]


def _with_cited(facts: list[Fact], *replies: dict[str, Any]) -> list[Fact]:
    """``facts`` plus a plain fact for every ID the replies cite that they lack: the run's facts
    held them all, and the checks only need them to exist."""
    have = {f.id for f in facts}
    cited = {fid for reply in replies for unit in reply["units"] for fid in unit["fact_ids"]}
    return [*facts, *(_fact(fid, fid.split(":", 1)[1]) for fid in sorted(cited - have))]


def _document(facts: list[Fact]) -> FactsDocument:
    return FactsDocument("org/repo", "a" * 40, tuple(facts))


def _packet(section_id: str, slots: tuple[str, ...], facts: list[Fact]) -> dict[str, Any]:
    """A section_authoring packet shaped as ``authoring_tasks`` builds one."""
    return {
        "repository": "org/repo",
        "product_name": "Aspose.Example FOSS",
        "mode": "author",
        "section_id": section_id,
        "objective": f"Write the section. {slots_clause(slots)} Spell identifiers as the facts do.",
        "slots": slot_records(slots, {}, {}),
        "accepted_facts": [{"id": f.id, "kind": f.kind, "value": f.value} for f in facts],
        "do_not_claim": [],
        "length_budget": "one sentence per slot",
        "rendered_document": "",
        "existing_units": [],
    }


def _task(section_id: str, slots: tuple[str, ...], facts: list[Fact], **fields: Any) -> SectionTask:
    return SectionTask(
        section_id,
        _packet(section_id, slots, facts),
        frozenset(f.id for f in facts),
        slots,
        **fields,
    )


NAME = "Aspose.Example FOSS"
SLIDES_NAME = "Aspose.Slides FOSS for Java"


# ---------------------------------------------------------------------------------------------
# TeX-Python: two restated commands, one named.
# ---------------------------------------------------------------------------------------------

_TEX_FACTS = [
    *_identity(),
    _fact("package:python_requires", ">=3.10"),
    _fact("build_test_asset:tests", "tests/"),
    _fact("import_path:aspose_tex", "aspose_tex"),
    _fact("public_symbol:aspose-tex.texjob", "aspose_tex.TeXJob"),
    _fact("inherited_unit:072.paragraph", "Install the development extras and run the test suite:"),
    _fact(
        "inherited_unit:074.paragraph",
        "68 test modules cover the tokenizer, macro expander, box and page builder, font "
        "subsystem, and each output writer, including an automated end-to-end suite that compiles "
        "fixture "
        "documents through the public `TeXJob` API and compares the result against committed "
        "MiKTeX-generated DVI baselines - semantically, not byte-for-byte. Lint with:",
    ),
    _fact(
        "inherited_unit:076.paragraph",
        "The package registers a `logging.NullHandler` on the `aspose_tex` logger, so integrating "
        "applications can opt into standard Python logging without unexpected warnings.",
    ),
]


def _tex_task() -> SectionTask:
    return _task(
        "development_testing",
        ("summary",),
        _TEX_FACTS,
        slot_render_lines={"summary": ("pytest", "ruff check .")},
        must_carry=frozenset({"inherited_unit:072.paragraph", "inherited_unit:074.paragraph"}),
    )


def test_the_real_tex_reply_is_refused_for_both_commands_it_restates_not_one() -> None:
    """Before: ``restated[0]`` - the rejection said ``restates 'pytest'``, the re-ask removed pytest
    and kept ``ruff check .``, and the run died on the second (wave 3, TeX-Python)."""
    first = _real("wave3_tex_summary.rejected-1.json")
    errors = unit_checks(
        _reply("wave3_tex_summary.rejected-1.json"),
        _tex_task(),
        _document(_TEX_FACTS),
        "Aspose.TeX FOSS for Python",
    )
    restated = [e for e in errors if " restates " in e]
    assert len(restated) == 1, errors
    assert "'pytest'" in restated[0] and "'ruff check .'" in restated[0]
    assert restated[0].startswith("unit summary: ")
    # The run recorded the incomplete message; the stray identifier was named in full already.
    assert "restates 'pytest'," in first["rejection"][0]
    assert any("logging.NullHandler" in e for e in errors)


def test_one_restated_command_is_still_named_in_the_original_words() -> None:
    task = _tex_task()
    output = {
        "units": [
            {
                "section": "development_testing",
                "slot": "summary",
                "text": "Run pytest to execute the suite.",
                "fact_ids": ["build_test_asset:tests", "inherited_unit:072.paragraph"],
            }
        ],
        "omitted": [{"fact_id": "inherited_unit:074.paragraph", "reason": "stated elsewhere"}],
    }
    errors = unit_checks(output, task, _document(_TEX_FACTS), NAME)
    assert errors == [
        "unit summary: restates 'pytest', a command the renderer already prints verbatim in a "
        "fenced block right after this unit; write only what the block does not already say, "
        "never the command itself"
    ]


def test_restated_command_lines_are_the_ones_the_guard_matches() -> None:
    assert restated_command_lines(
        "Then run RUFF CHECK . and pytest.", ("pytest", "ruff check .", "tox")
    ) == [
        "pytest",
        "ruff check .",
    ]
    assert restated_command_lines("Nothing here.", ("pytest",)) == []


def test_a_unit_with_several_forbidden_markers_names_each_once() -> None:
    task = _task("quick_start", ("lead_in",), [*_identity()])
    output = {
        "units": [
            {
                "section": "quick_start",
                "slot": "lead_in",
                "text": "See https://x.example and www.x.example, then use <address> | or <b>.",
                "fact_ids": ["identity:repository"],
            }
        ],
        "omitted": [],
    }
    (error,) = [
        e for e in unit_checks(output, task, _document(_identity()), NAME) if "text contains" in e
    ]
    assert error.startswith("unit lead_in: text contains a URL ('https://')")
    assert "HTML ('<')" in error and "a Markdown table ('|')" in error
    assert error.count("a URL") == 1  # one meaning is named once, however many markers match
    # The offending markup is quoted, so the re-ask can find which "<" is meant.
    assert "<address>, <b>" in error


# ---------------------------------------------------------------------------------------------
# Slides-Java: one unit of seven, one list item.
# ---------------------------------------------------------------------------------------------

_SLIDES_LIST = (FIXTURES / "wave3_slides_java_088_list.md").read_text(encoding="utf-8").strip()
_SLIDES_SLOTS = (
    "scope",
    *(f"limitation:{index}" for index in range(1, 8)),
)
_SLIDES_FACTS = _with_cited(
    [
        *_identity(),
        _fact("license:file", "LICENSE"),
        _fact("license:spdx", "MIT"),
        _fact("package:name", "org.aspose:aspose-slides-foss"),
        _fact("package:version", "26.8.0"),
        _fact("inherited_unit:087.paragraph", "This section is the point of this file."),
        _fact("inherited_unit:088.list", _SLIDES_LIST),
    ],
    _reply("wave3_slides_java_scope.rejected-1.json"),
    _reply("wave3_slides_java_scope.rejected-2.json"),
)


def _slides_task() -> SectionTask:
    return _task(
        "scope_limitations",
        _SLIDES_SLOTS,
        _SLIDES_FACTS,
        slot_facts={"limitation:7": frozenset({"inherited_unit:088.list"})},
    )


def _needs_master_clone(output: dict[str, Any]) -> list[str]:
    """A stand-in for any unit-level refusal of slot ``limitation:7``, which is what the narrowed
    ask is for. Wave 3 drove it with the list guard (the seventh unit left one item of the Scope
    list unstated); that guard is gone - placement prints an unstated item, so no reply is refused
    for one (wave-4 triage, cause 1) - but the narrowing is about WHICH slot a refusal names, not
    about what the refusal says, so this refuses the slot until it states the master-cloning
    defect and quotes it whole, as the guard did."""
    unit = next((u for u in output.get("units", []) if u.get("slot") == "limitation:7"), None)
    if unit is None or "cloning a master" in str(unit.get("text", "")):
        return []
    return ["unit limitation:7: must state 'A known defect: cloning a master' (the list item)"]


def _slides_checks(task: SectionTask) -> Any:
    own = functools.partial(
        unit_checks, task=task, facts=_document(_SLIDES_FACTS), name=SLIDES_NAME
    )

    def checks(output: dict[str, Any]) -> list[str]:
        return [*own(output), *_needs_master_clone(output)]

    return checks


# The model's own words for the one item its second reply left out, as a third, narrowed ask
# would write them: the earlier seventh unit kept whole, the master-cloning defect added to it.
_MASTER_CLONE = (
    "A known defect affects cloning a master: the masters collection reports a size of 2 after "
    "a clone is added, yet the saved package contains only one slide master, the clone never "
    "reaches the file, and nothing reports a problem, so do not rely on it."
)


def _slides_third_reply() -> dict[str, Any]:
    kept = next(
        unit
        for unit in _reply("wave3_slides_java_scope.rejected-2.json")["units"]
        if unit["slot"] == "limitation:7"
    )
    return {
        "units": [{**kept, "text": f"{kept['text']} {_MASTER_CLONE}"}],
        "omitted": [],
    }


# ---------------------------------------------------------------------------------------------
# Serving replies through the real gateway path, wired as repair/rounds.py wires section_authoring.
# ---------------------------------------------------------------------------------------------


def _completion(content: Any) -> httpx.Response:
    body = {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1,
        "model": "qwen3-next",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": json.dumps(content)},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    }
    return httpx.Response(200, json=body)


def _serve(monkeypatch: pytest.MonkeyPatch, *replies: Any) -> list[dict[str, Any]]:
    queue = [_completion(reply) for reply in replies]
    requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return queue.pop(0)

    mock_gateway(monkeypatch, handler)
    return requests


def _run(
    tmp_path: Path,
    task: SectionTask,
    facts: list[Fact],
    *,
    name: str = NAME,
    extra: Any = None,
    narrow: bool = True,
) -> JobResult:
    document = _document(facts)
    call_schema = bound_authoring_citations(authoring_schema(MANIFEST, task), task)
    return run_job(
        MANIFEST,
        task.packet,
        config=CONFIG,
        facts=document,
        ledger=Ledger(tmp_path / "calls.jsonl"),
        store=CallStore(tmp_path / "calls"),
        context=JobContext("org/repo", "a" * 40),
        checks=_with_extra(
            functools.partial(unit_checks, task=task, facts=document, name=name), extra
        ),
        call_schema=call_schema,
        recover=functools.partial(
            recover_section_authoring_with_type_fallback,
            slot_titles=task.slot_titles,
            task=task,
            facts=document,
            name=name,
        ),
        narrow=authoring_narrowing(task, MANIFEST) if narrow else None,
    )


def _with_extra(checks: Any, extra: Any) -> Any:
    if extra is None:
        return checks
    return lambda output: [*checks(output), *extra(output)]


def _user_text(request: dict[str, Any]) -> str:
    return "\n".join(str(m["content"]) for m in request["messages"] if m["role"] == "user")


def _units_by_slot(output: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {unit["slot"]: unit for unit in output["units"]}


def test_the_real_slides_java_replies_are_refused_as_the_run_recorded_them_bar_the_list() -> None:
    """The stand-in facts reproduce the run's two rejections, seven faults and then one - except
    the list refusal, which no longer exists: an unstated list item is printed by placement, so the
    second reply (whose only fault was one unstated item) is accepted as it stands."""
    task = _slides_task()
    unit_level = functools.partial(
        unit_checks, task=task, facts=_document(_SLIDES_FACTS), name=SLIDES_NAME
    )
    errors = unit_level(copy.deepcopy(_reply("wave3_slides_java_scope.rejected-1.json")))
    recorded = _real("wave3_slides_java_scope.rejected-1.json")["rejection"]
    kept = [e for e in recorded if "list_item_missing" not in e]
    assert len(kept) == len(recorded) - 1
    assert [e.split(":")[0] for e in errors] == [e.split(":")[0] for e in kept]
    assert unit_level(copy.deepcopy(_reply("wave3_slides_java_scope.rejected-2.json"))) == []
    # The stand-in refuses that second reply the way the list guard did.
    second = _slides_checks(task)(copy.deepcopy(_reply("wave3_slides_java_scope.rejected-2.json")))
    assert len(second) == 1 and "A known defect: cloning a master" in second[0]


def test_only_the_failing_slot_is_named_for_a_third_ask() -> None:
    task = _slides_task()
    content = _real("wave3_slides_java_scope.rejected-2.json")["content"]
    rejection = _slides_checks(task)(json.loads(content))
    assert failing_slots(task, content, rejection) == ["limitation:7"]
    first = _real("wave3_slides_java_scope.rejected-1.json")["content"]
    rejection_first = _slides_checks(task)(json.loads(first))
    # the unit-level faults of the first reply (the list refusal that also named limitation:7 is
    # gone)
    assert failing_slots(task, first, rejection_first) == [
        "limitation:2",
        "limitation:4",
        "limitation:5",
    ]


def test_a_rejection_no_unit_owns_names_no_slot_so_nothing_is_narrowed() -> None:
    task = _task(
        "scope_limitations",
        ("scope", "limitation:1"),
        _SLIDES_FACTS,
        must_carry=frozenset({"inherited_unit:087.paragraph"}),
    )
    output = {
        "units": [
            {
                "section": "scope_limitations",
                "slot": "scope",
                "text": "Scope.",
                "fact_ids": ["license:spdx"],
            },
            {
                "section": "scope_limitations",
                "slot": "limitation:1",
                "text": "No charts.",
                "fact_ids": ["license:file"],
            },
        ],
        "omitted": [],
    }
    content = json.dumps(output)
    rejection = unit_checks(json.loads(content), task, _document(_SLIDES_FACTS), SLIDES_NAME)
    assert rejection and rejection[0].startswith("inherited_unit:087.paragraph: superseded")
    assert failing_slots(task, content, rejection) == []


def test_a_missing_slot_is_the_slot_to_ask_for() -> None:
    task = _task("quick_start", ("lead_in", "second"), [*_identity()])
    output = {
        "units": [
            {
                "section": "quick_start",
                "slot": "lead_in",
                "text": "Start here.",
                "fact_ids": ["identity:repository"],
            }
        ],
        "omitted": [],
    }
    content = json.dumps(output)
    rejection = unit_checks(json.loads(content), task, _document(_identity()), NAME)
    assert rejection and rejection[0].startswith("units must fill exactly these slots once each")
    assert failing_slots(task, content, rejection) == ["second"]


def test_slides_java_third_ask_asks_for_one_unit_and_keeps_the_other_seven_as_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wave 3, Slides-Java: attempt 1 had seven faults, attempt 2 fixed all but one list item and
    the run failed. The one unit still failing is asked for alone; the seven accepted units are
    not rewritten, so the second reply's text for them is what the section has."""
    second = _reply("wave3_slides_java_scope.rejected-2.json")
    requests = _serve(
        monkeypatch,
        _reply("wave3_slides_java_scope.rejected-1.json"),
        second,
        _slides_third_reply(),
    )
    result = _run(
        tmp_path, _slides_task(), _SLIDES_FACTS, name=SLIDES_NAME, extra=_needs_master_clone
    )
    assert result.attempts == result.provider_calls == 3
    accepted = _units_by_slot(result.output)
    assert list(accepted) == list(_SLIDES_SLOTS)  # the task's own order
    before = _units_by_slot(second)
    for slot in _SLIDES_SLOTS[:-1]:
        assert accepted[slot] == before[slot], slot  # untouched, byte for byte
    assert _MASTER_CLONE in accepted["limitation:7"]["text"]
    # The third request is a fresh, narrowed one: this slot alone, in its packet and its schema.
    asked = requests[2]
    assert [m["role"] for m in asked["messages"]] == ["system", "user"]
    user = _user_text(asked)
    assert "Slots to fill, each exactly once: limitation:7." in user
    assert "was accepted for every other slot of this section" in user
    assert "A known defect: cloning a master" in user  # the item still unstated, quoted whole
    assert before["limitation:7"]["text"] in user  # the unit it replaces, so it stays whole
    assert before["limitation:2"]["text"] in user  # accepted units are shown, so none is repeated
    shape = asked["response_format"]["json_schema"]["schema"]["properties"]["units"]
    assert [item["properties"]["slot"]["const"] for item in shape["prefixItems"]] == [
        "limitation:7"
    ]
    assert shape["minItems"] == shape["maxItems"] == 1
    # Every call is attempt 1, 2 or 3 of the one logical call, the third a re-ask.
    records = [
        json.loads(line)
        for line in (tmp_path / "calls.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    calls = [
        r for r in records if r["disposition"] == "provider_call" and r["outcome"] == "success"
    ]
    assert [r["attempt"] for r in calls] == [1, 2, 3]
    assert calls[2]["derived_via_reask"] is True
    # The accepted output is stored under the logical request: the same request later is free.
    mock_gateway(monkeypatch, lambda request: pytest.fail("a stored output made a provider call"))
    again = _run(
        tmp_path, _slides_task(), _SLIDES_FACTS, name=SLIDES_NAME, extra=_needs_master_clone
    )
    assert again.cache_reused and again.output == result.output


def test_a_narrowed_ask_cannot_change_a_unit_that_was_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control: a reply that also returns another slot is outside the narrowed schema."""
    third = _slides_third_reply()
    third["units"].append(
        {
            "section": "scope_limitations",
            "slot": "limitation:2",
            "text": "Charts are not available.",
            "fact_ids": ["license:file"],
        }
    )
    requests = _serve(
        monkeypatch,
        _reply("wave3_slides_java_scope.rejected-1.json"),
        _reply("wave3_slides_java_scope.rejected-2.json"),
        third,
    )
    with pytest.raises(JobError) as caught:
        _run(
            tmp_path,
            _slides_task(),
            _SLIDES_FACTS,
            name=SLIDES_NAME,
            extra=_needs_master_clone,
        )
    assert len(requests) == 3
    assert "narrowed ask" in str(caught.value)


def test_a_unit_still_failing_after_the_narrowed_ask_fails_the_job_naming_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control: nothing is accepted unjudged - the third reply still omits the item."""
    kept = [
        unit
        for unit in _reply("wave3_slides_java_scope.rejected-2.json")["units"]
        if unit["slot"] == "limitation:7"
    ]
    _serve(
        monkeypatch,
        _reply("wave3_slides_java_scope.rejected-1.json"),
        _reply("wave3_slides_java_scope.rejected-2.json"),
        {"units": kept, "omitted": []},
    )
    with pytest.raises(JobError) as caught:
        _run(
            tmp_path,
            _slides_task(),
            _SLIDES_FACTS,
            name=SLIDES_NAME,
            extra=_needs_master_clone,
        )
    message = str(caught.value)
    assert "three times (the third a narrowed ask for the units still failing)" in message
    assert "A known defect: cloning a master" in message
    kept_files = sorted(p.name.split(".", 1)[1] for p in (tmp_path / "calls").iterdir())
    assert kept_files == ["rejected-1.json", "rejected-2.json", "rejected-3.json"]


def test_without_a_narrowing_the_second_rejection_still_fails_after_two_asks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The narrowed ask is opt-in: a caller that passes none is exactly as before."""
    requests = _serve(
        monkeypatch,
        _reply("wave3_slides_java_scope.rejected-1.json"),
        _reply("wave3_slides_java_scope.rejected-2.json"),
    )
    with pytest.raises(JobError, match="output rejected twice"):
        _run(
            tmp_path,
            _slides_task(),
            _SLIDES_FACTS,
            name=SLIDES_NAME,
            extra=_needs_master_clone,
            narrow=False,
        )
    assert len(requests) == 2


def test_a_rejection_no_unit_owns_is_not_narrowed_and_fails_after_two_asks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task = _task(
        "scope_limitations",
        ("scope", "limitation:1"),
        _SLIDES_FACTS,
        must_carry=frozenset({"inherited_unit:087.paragraph"}),
    )
    silent = {
        "units": [
            {
                "section": "scope_limitations",
                "slot": "scope",
                "text": "Scope.",
                "fact_ids": ["license:spdx"],
            },
            {
                "section": "scope_limitations",
                "slot": "limitation:1",
                "text": "No charts.",
                "fact_ids": ["license:file"],
            },
        ],
        "omitted": [],
    }
    requests = _serve(monkeypatch, silent, silent)
    with pytest.raises(JobError, match="output rejected twice"):
        _run(tmp_path, task, _SLIDES_FACTS)
    assert len(requests) == 2


def test_a_reply_that_leaves_a_list_item_out_is_accepted_not_asked_for_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wave-4 triage, cause 1: the authoring call used to refuse a reply for a list item it left
    out (3D .NET: eight items, seven slots; Email .NET: the item names a package no fact spells).
    Placement prints the item as written, so the second reply of Slides-Java - one item short -
    is accepted at once, one provider call."""
    requests = _serve(monkeypatch, _reply("wave3_slides_java_scope.rejected-2.json"))
    result = _run(tmp_path, _slides_task(), _SLIDES_FACTS, name=SLIDES_NAME)
    assert result.attempts == result.provider_calls == 1
    assert len(requests) == 1
    assert "cloning a master" not in " ".join(u["text"] for u in result.output["units"])


# ---------------------------------------------------------------------------------------------
# Wave 4, Slides-Java and Slides-Cpp: the same text three times.
# ---------------------------------------------------------------------------------------------


def test_repeated_slots_are_the_ones_the_second_reply_gave_exactly_as_the_first_did() -> None:
    first = json.dumps(
        {
            "units": [
                {"slot": "a", "text": "same", "fact_ids": ["x"]},
                {"slot": "b", "text": "before", "fact_ids": ["x"]},
                {"slot": "c", "text": "same", "fact_ids": ["x"]},
            ]
        }
    )
    second = json.dumps(
        {
            "units": [
                {"slot": "a", "text": "same", "fact_ids": ["x"]},
                {"slot": "b", "text": "after", "fact_ids": ["x"]},
                {"slot": "c", "text": "same", "fact_ids": ["y"]},  # same words, other citation
            ]
        }
    )
    assert repeated_slots(first, second, ["a", "b", "c"]) == ["a"]
    assert repeated_slots(first, second, ["b"]) == []
    assert repeated_slots(first, "not json", ["a"]) == []
    assert repeated_slots(first, second, ["missing"]) == []  # no unit, nothing repeated


def _stutter_units() -> dict[str, Any]:
    """The Slides-Java stutter: capability:7 stays the same unit in every reply."""
    return {
        "units": [
            {
                "section": "scope_limitations",
                "slot": "limitation:7",
                "text": "Charts are not available.",
                "fact_ids": ["license:file"],
            }
        ],
        "omitted": [],
    }


def test_a_unit_returned_unchanged_is_asked_for_a_third_time_with_the_evidence_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The model returned limitation:7 unchanged after the re-ask named its fault, so the same
    question put again is the third equivalent attempt (AGENTS.md). The narrowed ask is made, and
    differs from the re-ask in what it says: the unit was returned twice and rejected twice, and
    what changing it means."""
    task = _slides_task()
    second = _reply("wave3_slides_java_scope.rejected-2.json")
    first = copy.deepcopy(_reply("wave3_slides_java_scope.rejected-1.json"))
    first["units"] = copy.deepcopy(second["units"])  # slot for slot the same as the second
    fixed = _slides_third_reply()
    requests = _serve(monkeypatch, first, second, fixed)
    result = _run(tmp_path, task, _SLIDES_FACTS, name=SLIDES_NAME, extra=_needs_master_clone)
    assert result.attempts == 3
    asked = _user_text(requests[2])
    assert "Your first two replies gave limitation:7 exactly as shown above" in asked
    assert "that text is not to be returned again" in asked
    assert "A known defect: cloning a master" in asked  # the reason is still quoted whole
    assert requests[2] != requests[1]


def test_a_unit_the_second_reply_changed_gets_the_ordinary_narrowed_ask(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control: where the re-ask moved the unit, nothing is said about repetition."""
    requests = _serve(
        monkeypatch,
        _reply("wave3_slides_java_scope.rejected-1.json"),
        _reply("wave3_slides_java_scope.rejected-2.json"),
        _slides_third_reply(),
    )
    _run(tmp_path, _slides_task(), _SLIDES_FACTS, name=SLIDES_NAME, extra=_needs_master_clone)
    assert "exactly as shown above" not in _user_text(requests[2])


# ---------------------------------------------------------------------------------------------
# TeX-Python replayed: the third ask is a fresh single-slot request with the full defect list.
# ---------------------------------------------------------------------------------------------


def test_tex_python_replayed_names_both_commands_in_the_first_re_ask_and_converges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    second = _reply("wave3_tex_summary.rejected-2.json")
    fixed = copy.deepcopy(second)
    fixed["units"][0]["text"] = fixed["units"][0]["text"].replace(
        "then run ruff check . to enforce linting rules", "then lint the code to enforce the rules"
    )
    assert "ruff check ." not in fixed["units"][0]["text"]
    requests = _serve(monkeypatch, _reply("wave3_tex_summary.rejected-1.json"), second, fixed)
    result = _run(tmp_path, _tex_task(), _TEX_FACTS, name="Aspose.TeX FOSS for Python")
    assert result.attempts == 3
    # The universal re-ask carries the whole defect list: both commands, and the identifier.
    re_ask = "\n".join(str(m["content"]) for m in requests[1]["messages"])
    assert "'pytest', 'ruff check .'" in re_ask
    assert "logging.NullHandler" in re_ask
    # The narrowed ask, one slot of one, is a fresh request that quotes the remaining fault.
    assert "restates 'ruff check .'" in _user_text(requests[2])
    assert "an earlier reply to this request was rejected" in _user_text(requests[2])
    assert len(requests[2]["messages"]) == 2


# ---------------------------------------------------------------------------------------------
# PDF-Cpp: fixing the stray identifier exposed a title restatement the first message never named.
# ---------------------------------------------------------------------------------------------


def _pdf_cpp_setup() -> tuple[SectionTask, list[Fact], dict[str, Any], dict[str, Any]]:
    first = _reply("wave3_pdf_cpp_capabilities.rejected-1.json")
    second = _reply("wave3_pdf_cpp_capabilities.rejected-2.json")
    slots = tuple(unit["slot"] for unit in second["units"])
    facts = [*_identity(), _fact("package:name", "Aspose_PDF_FOSS")]
    cited = {fid for unit in (*first["units"], *second["units"]) for fid in unit["fact_ids"]}
    facts += [
        _fact(fid, fid.split(":", 1)[1])
        for fid in sorted(cited)
        if fid not in {f.id for f in facts}
    ]
    facts += _spelled(second["units"], refused=())
    task = _task(
        "key_capabilities",
        slots,
        facts,
        slot_titles={"capability:8": "No runtime dependencies"},
    )
    return task, facts, first, second


def test_pdf_cpp_third_ask_is_the_one_capability_the_second_reply_broke(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task, facts, first, second = _pdf_cpp_setup()
    errors = unit_checks(copy.deepcopy(second), task, _document(facts), NAME)
    assert [e.split(":")[0] for e in errors] == [
        "unit capability"
    ] and "restates its own title" in errors[0]
    fixed = {
        "units": [
            {
                **second["units"][7],
                "text": "Its raster renderer needs no third-party libraries or external runtime "
                "components.",
            }
        ],
        "omitted": [],
    }
    requests = _serve(monkeypatch, first, second, fixed)
    result = _run(tmp_path, task, facts)
    assert result.attempts == 3
    accepted = _units_by_slot(result.output)
    assert accepted["capability:8"]["text"].startswith("Its raster renderer")
    for unit in second["units"][:7]:
        assert accepted[unit["slot"]]["text"] == unit["text"].replace("`", "")
    user = _user_text(requests[2])
    assert "restates its own title 'No runtime dependencies'" in user
    assert "Slots to fill, each exactly once: capability:8." in user


# ---------------------------------------------------------------------------------------------
# Email-Python and Words-Python: the same refused identifier twice (temperature zero).
# ---------------------------------------------------------------------------------------------


def _email_setup() -> tuple[SectionTask, list[Fact], dict[str, Any], dict[str, Any]]:
    first = _reply("wave3_email_python_scope.rejected-1.json")
    second = _reply("wave3_email_python_scope.rejected-2.json")
    facts = _with_cited(
        [
            *_identity(),
            *_spelled(
                first["units"] + second["units"],
                refused=("email.message.EmailMessage", "load_from_eml", "winmail.dat"),
            ),
        ],
        first,
        second,
    )
    slots = tuple(unit["slot"] for unit in second["units"])
    return _task("scope_limitations", slots, facts), facts, first, second


def test_email_python_third_ask_is_the_one_limitation_naming_a_standard_library_class(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task, facts, first, second = _email_setup()
    fixed_text = (
        "Direct .eml file parsing is not implemented by this library itself; EML support relies "
        "on MapiMessage.from_email_message() and to_email_message() together with Python's own "
        "email parser, not a dedicated method."
    )
    fixed = {"units": [{**second["units"][4], "text": fixed_text}], "omitted": []}
    requests = _serve(monkeypatch, first, second, fixed)
    result = _run(tmp_path, task, facts)
    accepted = _units_by_slot(result.output)
    assert accepted["limitation:4"]["text"] == fixed_text
    assert accepted["limitation:2"]["text"] == second["units"][2]["text"]
    assert "email.message.EmailMessage" in _user_text(requests[2])
    assert "Slots to fill, each exactly once: limitation:4." in _user_text(requests[2])


_WORDS_PDF = "hub:public_symbol:aspose.words_foss.pdf_writer"
_WORDS_MODEL = "hub:public_symbol:aspose.words_foss.light_document_model"


def _words_setup() -> tuple[SectionTask, list[Fact], dict[str, Any], dict[str, Any]]:
    first = _reply("wave3_words_python_api.rejected-1.json")
    second = _reply("wave3_words_python_api.rejected-2.json")
    facts = _with_cited(
        [
            *_identity(),
            *_spelled(
                first["units"] + second["units"], refused=("SaveFormat.PDF", "all_paragraphs")
            ),
        ],
        first,
        second,
    )
    slots = tuple(unit["slot"] for unit in second["units"])
    return _task("api_reference", slots, facts), facts, first, second


def test_words_python_two_identical_failing_replies_get_a_different_third_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wave 3, Words-Python: the re-ask returned the same two refused identifiers byte for byte.
    A third request that names those two units alone, with the exact refusals, is a different
    request, so the model is not asked the same question a third time."""
    task, facts, first, second = _words_setup()
    by_slot = _units_by_slot(second)
    fixed = {
        "units": [
            {
                **by_slot[_WORDS_PDF],
                "text": by_slot[_WORDS_PDF]["text"].replace(
                    "with SaveFormat.PDF", "to save as PDF"
                ),
            },
            {
                **by_slot[_WORDS_MODEL],
                "text": by_slot[_WORDS_MODEL]["text"].replace(
                    "such as all_paragraphs, ", "such as "
                ),
            },
        ],
        "omitted": [],
    }
    requests = _serve(monkeypatch, first, second, fixed)
    result = _run(tmp_path, task, facts)
    assert result.attempts == 3
    assert _units_by_slot(result.output)[_WORDS_PDF]["text"].endswith("to save as PDF.")
    third = _user_text(requests[2])
    assert f"Slots to fill, each exactly once: {_WORDS_PDF}, {_WORDS_MODEL}." in third
    assert "SaveFormat.PDF (nearest accepted: SaveFormat" in third
    assert requests[2] != requests[1]


def test_tex_python_real_replies_end_with_the_sentence_restating_the_command_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wave 3, TeX-Python: with no narrowed ask the two real replies still ended the job at
    ``restates 'ruff check .'``. The last resort now removes that one sentence - the command is
    printed beside the unit anyway - and records the change; every other sentence is untouched."""
    first = _reply("wave3_tex_summary.rejected-1.json")
    second = _reply("wave3_tex_summary.rejected-2.json")
    requests = _serve(monkeypatch, first, second)
    result = _run(
        tmp_path, _tex_task(), _TEX_FACTS, name="Aspose.TeX FOSS for Python", narrow=False
    )
    assert len(requests) == 2
    text = result.output["units"][0]["text"]
    assert "ruff check" not in text and "pytest" not in text
    dropped = (
        " Contributors must install the development extras and run the test suite, then run "
        "ruff check . to enforce linting rules."
    )
    assert dropped in second["units"][0]["text"]
    assert text == second["units"][0]["text"].replace(dropped, "")
    (record,) = sorted((tmp_path / "calls").glob("*.repaired-*.json"))
    (change,) = json.loads(record.read_text(encoding="utf-8"))["changes"]
    assert change["path"] == "units.0.text" and change["slot"] == "summary"
    assert "ruff check ." in change["before"] and "ruff check" not in change["after"]


def _slides_setup() -> tuple[SectionTask, list[Fact], dict[str, Any], dict[str, Any]]:
    return (
        _slides_task(),
        _SLIDES_FACTS,
        _reply("wave3_slides_java_scope.rejected-1.json"),
        _reply("wave3_slides_java_scope.rejected-2.json"),
    )


@pytest.mark.parametrize(
    ("setup", "name", "extra", "unit_named"),
    [
        (_slides_setup, SLIDES_NAME, _needs_master_clone, "A known defect: cloning a master"),
        (_pdf_cpp_setup, NAME, None, "restates its own title 'No runtime dependencies'"),
        (_email_setup, NAME, None, "email.message.EmailMessage"),
        (_words_setup, NAME, None, "SaveFormat.PDF"),
    ],
    ids=["slides-java", "pdf-cpp", "email-python", "words-python"],
)
def test_each_real_wave3_reply_pair_failed_the_job_at_two_asks_and_is_now_asked_a_third_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    setup: Any,
    name: str,
    extra: Any,
    unit_named: str,
) -> None:
    """The baseline: the two replies each repository really got, served to the job as it ran in
    wave 3 (no narrowed ask), end at ``output rejected twice`` naming the fault that was left. The
    same two replies with the narrowed ask make the third request instead of failing."""
    task, facts, first, second = setup()
    _serve(monkeypatch, first, second)
    with pytest.raises(JobError, match="output rejected twice") as caught:
        _run(tmp_path / "before", task, facts, name=name, extra=extra, narrow=False)
    assert unit_named in str(caught.value)
    requests = _serve(monkeypatch, first, second, {"units": [], "omitted": []})
    with pytest.raises(JobError, match="narrowed ask"):
        _run(tmp_path / "after", task, facts, name=name, extra=extra)
    assert len(requests) == 3


# ---------------------------------------------------------------------------------------------
# The deterministic last resort removes only what the page already prints.
# ---------------------------------------------------------------------------------------------


def test_a_sentence_that_only_restates_the_slots_title_is_dropped_when_others_remain() -> None:
    facts = [*_identity()]
    task = _task(
        "key_capabilities", ("capability:1",), facts, slot_titles={"capability:1": "Render pages"}
    )
    output = {
        "units": [
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Render pages. Output is produced one page at a time.",
                "fact_ids": ["identity:repository"],
            }
        ],
        "omitted": [],
    }
    assert unit_checks(copy.deepcopy(output), task, _document(facts), NAME)
    repaired = recover_restating_sentences(output, task=task, facts=_document(facts))
    assert repaired is not None
    assert repaired["units"][0]["text"] == "Output is produced one page at a time."
    assert unit_checks(copy.deepcopy(repaired), task, _document(facts), NAME) == []


def test_a_sentence_restating_a_printed_command_is_dropped_when_others_remain() -> None:
    task = _tex_task()
    output = {
        "units": [
            {
                "section": "development_testing",
                "slot": "summary",
                "text": "The tests live in tests/. Contributors run pytest and then ruff check . "
                "before sending a change. Python 3.10 or later is required.",
                "fact_ids": [
                    "build_test_asset:tests",
                    "package:python_requires",
                    "inherited_unit:072.paragraph",
                    "inherited_unit:074.paragraph",
                ],
            }
        ],
        "omitted": [],
    }
    repaired = recover_restating_sentences(output, task=task, facts=_document(_TEX_FACTS))
    assert repaired is not None
    assert repaired["units"][0]["text"] == (
        "The tests live in tests/. Python 3.10 or later is required."
    )


def test_a_unit_that_is_nothing_but_the_restatement_is_left_alone() -> None:
    facts = [*_identity()]
    task = _task(
        "key_capabilities", ("capability:1",), facts, slot_titles={"capability:1": "Render pages"}
    )
    only = {
        "units": [
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Render pages.",
                "fact_ids": ["identity:repository"],
            }
        ],
        "omitted": [],
    }
    assert (
        recover_restating_sentences(copy.deepcopy(only), task=task, facts=_document(facts)) is None
    )


def test_a_unit_that_restates_nothing_is_not_touched() -> None:
    facts = [*_identity()]
    task = _task(
        "key_capabilities", ("capability:1",), facts, slot_titles={"capability:1": "Render pages"}
    )
    fine = {
        "units": [
            {
                "section": "key_capabilities",
                "slot": "capability:1",
                "text": "Pages come out one at a time. Render pages here.",
                "fact_ids": ["identity:repository"],
            }
        ],
        "omitted": [],
    }
    # The title is present but so is nothing else to condemn it, and a stray identifier is never
    # rewritten into words: that would hide an unevidenced claim, not remove it.
    stray = copy.deepcopy(fine)
    stray["units"][0]["text"] = "Call all_paragraphs for the rest."
    assert recover_restating_sentences(stray, task=task, facts=_document(facts)) is None


def test_a_repaired_reply_is_recorded_beside_the_call_with_what_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Three equal replies, each restating a printed command in a sentence of its own: the model's
    own asks are spent, the last resort drops the sentence, and the change is kept in
    ``repairs.json``'s shape (id, path, before, after) beside the rejected replies."""
    task = _tex_task()
    reply = {
        "units": [
            {
                "section": "development_testing",
                "slot": "summary",
                "text": "The tests live in tests/. Contributors run pytest before each change. "
                "Python 3.10 or later is required.",
                "fact_ids": [
                    "build_test_asset:tests",
                    "package:python_requires",
                    "inherited_unit:072.paragraph",
                    "inherited_unit:074.paragraph",
                ],
            }
        ],
        "omitted": [],
    }
    requests = _serve(monkeypatch, reply, reply, reply)
    result = _run(tmp_path, task, _TEX_FACTS, name="Aspose.TeX FOSS for Python")
    assert len(requests) == 3
    assert result.output["units"][0]["text"] == (
        "The tests live in tests/. Python 3.10 or later is required."
    )
    (record,) = sorted((tmp_path / "calls").glob("*.repaired-*.json"))
    document = json.loads(record.read_text(encoding="utf-8"))
    assert document["job"] == "section_authoring" and document["outcome"] == "repaired"
    (change,) = document["changes"]
    assert change["id"] == "R01" and change["path"] == "units.0.text"
    assert change["slot"] == "summary"
    assert "Contributors run pytest" in change["before"]
    assert change["after"] == "The tests live in tests/. Python 3.10 or later is required."


# ---------------------------------------------------------------------------------------------
# Coherence: a unit the revision leaves out is the accepted unit, unrevised.
# ---------------------------------------------------------------------------------------------


def test_a_unit_the_coherence_reply_skipped_is_restored_from_the_accepted_one() -> None:
    """Wave 3, PDF-Java: the coherence reply filled preview and every workflow slot but
    workflow:example:007, and the exact-slot-set rule failed the run. The pass revises units and
    returns every one it was given, so a skipped unit is the accepted S6 unit unrevised."""
    task = _task(
        "additional_examples",
        ("preview", "workflow:example:006", "workflow:example:007"),
        [*_identity()],
    )
    existing = [
        {
            "section": "additional_examples",
            "slot": slot,
            "text": f"Accepted {slot}.",
            "fact_ids": ["identity:repository"],
        }
        for slot in task.slots
    ]
    revised = [
        {**existing[0], "text": "Revised preview."},
        {**existing[1], "text": "Revised six."},
    ]
    output = {"units": copy.deepcopy(revised), "omitted": []}
    fixed = recover_coherence_missing_units(output, existing_units=existing, tasks=[task])
    assert fixed is not None
    assert [(u["slot"], u["text"]) for u in fixed["units"]] == [
        ("preview", "Revised preview."),
        ("workflow:example:006", "Revised six."),
        ("workflow:example:007", "Accepted workflow:example:007."),
    ]
    # Nothing is invented for a unit the pass never was given, and a complete reply is untouched.
    assert (
        recover_coherence_missing_units(
            {"units": copy.deepcopy(existing), "omitted": []}, existing_units=existing, tasks=[task]
        )
        is None
    )
    assert (
        recover_coherence_missing_units(
            {"units": copy.deepcopy(revised), "omitted": []},
            existing_units=existing[:2],
            tasks=[task],
        )
        is None
    )


def test_a_reply_the_last_resort_could_fix_is_still_fixed_when_the_narrowed_ask_made_it_worse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The narrowed ask never costs a job that was saved before it existed: the second reply's
    unit carried a command the last resort rewrites; the narrowed reply for it names an
    identifier no fact carries, which nothing rewrites - so the second reply is corrected."""
    facts = [*_identity()]
    task = _task("quick_start", ("lead_in", "second"), facts)

    def reply(first_text: str) -> dict[str, Any]:
        return {
            "units": [
                {
                    "section": "quick_start",
                    "slot": slot,
                    "text": text,
                    "fact_ids": ["identity:repository"],
                }
                for slot, text in (("lead_in", first_text), ("second", "Then open the file."))
            ],
            "omitted": [],
        }

    bad = reply("Start with pip install example-pkg to begin.")
    worse = {"units": [reply("Start with the bad_name helper.")["units"][0]], "omitted": []}
    requests = _serve(monkeypatch, bad, bad, worse)
    result = _run(tmp_path, task, facts)
    assert len(requests) == 3
    assert _units_by_slot(result.output)["lead_in"]["text"] == (
        "Start with the package as documented in the Installation section above to begin."
    )
    names = sorted(path.name.split(".", 1)[1] for path in (tmp_path / "calls").iterdir())
    assert names == [
        "json",
        "rejected-1.json",
        "rejected-2.json",
        "rejected-3.json",
        "repaired-3.json",
    ]
