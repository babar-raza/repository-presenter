"""A stored output is re-judged under the current checks before it is reused."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from repository_presenter.components.readme.investigation.dossier import investigation_packet
from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.facts import Evidence, Fact, FactsDocument, fact_id
from repository_presenter.core.llm.jobs import CallStore, JobContext, run_job
from repository_presenter.core.llm.ledger import Ledger
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.registry.models import RegistryEntry
from support import REPO_ROOT, mock_gateway

CONFIG = GatewayConfig("https://gw.example/v1", "sk-test-key-0123456789")
CONTEXT = JobContext("org/repo", "a" * 40)
FACTS = FactsDocument(
    "org/repo",
    "a" * 40,
    (
        Fact("identity:repository", "identity", "org/repo", (Evidence("data/registry.json"),)),
        Fact("package:name", "package", "widget", (Evidence("setup.py"),)),
    ),
)
MANIFEST = load_manifests(REPO_ROOT / "prompts")["repository_investigation"]
PACKET: dict[str, Any] = {
    "repository": "org/repo",
    "ecosystem": "python",
    "fact_dossier": [{"id": "identity:repository", "kind": "identity", "value": "org/repo"}],
    "inherited_units": [],
}


def _investigation(title: str) -> dict[str, Any]:
    statement = {"text": "It does things.", "fact_ids": ["identity:repository"]}
    return {
        "product_summary": statement,
        "audience": statement,
        "problems_solved": [statement],
        "workflows": [],
        "capabilities": [
            {"title": name, "text": "One sentence.", "fact_ids": [fact_id]}
            for name, fact_id in (
                (title, "package:name"),
                ("Do 2", "identity:repository"),
                ("Do 3", "package:name"),
            )
        ],
        "limitations": [],
        "uncertainties": [],
    }


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


class _Gateway:
    def __init__(self, monkeypatch: pytest.MonkeyPatch, *responses: httpx.Response) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []
        mock_gateway(monkeypatch, self)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        return self.responses.pop(0)


def _run(store: CallStore, ledger: Ledger, checks: Any = None) -> Any:
    return run_job(
        MANIFEST,
        PACKET,
        config=CONFIG,
        facts=FACTS,
        ledger=ledger,
        store=store,
        context=CONTEXT,
        checks=checks,
    )


def test_a_normalising_check_reshapes_the_stored_output_on_reuse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = _Gateway(monkeypatch, _completion(_investigation("do things")))
    ledger = Ledger(tmp_path / "calls.jsonl")
    store = CallStore(tmp_path / "calls")
    first = _run(store, ledger)
    assert first.output["capabilities"][0]["title"] == "do things"

    def capitalise(output: dict[str, Any]) -> list[str]:
        for capability in output["capabilities"]:
            capability["title"] = capability["title"].capitalize()
        return []

    again = _run(store, ledger, checks=capitalise)
    assert (again.provider_calls, again.cache_reused) == (0, True)
    assert again.output["capabilities"][0]["title"] == "Do things"
    assert store.get(first.request_sha256) == again.output
    assert store.record(first.request_sha256)["model_served"] == "qwen3-next"
    assert len(gateway.requests) == 1
    assert [r.disposition for r in ledger.records()] == ["provider_call", "cache_reuse"]


ENTRY = RegistryEntry.model_validate(
    {
        "repository": "org-foss/Aspose.Widget-FOSS-for-Python",
        "family": "widget",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)


def _facts(revision: str) -> FactsDocument:
    return FactsDocument(
        "org/repo",
        revision,
        (
            Fact(fact_id("identity", "repository"), "identity", "org/repo", (Evidence("x"),)),
            Fact(fact_id("identity", "revision"), "identity", revision, (Evidence("x"),)),
            Fact("package:name", "package", "widget", (Evidence("setup.py"),)),
        ),
    )


def test_a_new_revision_with_unchanged_facts_reuses_every_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G5-W02 (27.2 RC4). `identity:revision` is excluded from every job packet
    (`core/facts.py::bounded_records`), so a revision bump that changes no fact a job would
    reason about must not cost a new call. Built through the real `investigation_packet`, not a
    hand-written packet, so the proof exercises the actual exclusion rather than assuming it."""
    gateway = _Gateway(monkeypatch, _completion(_investigation("do things")))
    ledger = Ledger(tmp_path / "calls.jsonl")
    store = CallStore(tmp_path / "calls")
    manifest = load_manifests(REPO_ROOT / "prompts")["repository_investigation"]
    facts_v1 = _facts("a" * 40)
    facts_v2 = _facts("b" * 40)
    assert facts_v1 != facts_v2  # the two revisions really do differ

    packet_v1 = investigation_packet(ENTRY, facts_v1, manifest.manifest)
    packet_v2 = investigation_packet(ENTRY, facts_v2, manifest.manifest)
    assert packet_v1 == packet_v2  # the packet itself is already revision-invariant

    first = run_job(
        manifest,
        packet_v1,
        config=CONFIG,
        facts=facts_v1,
        ledger=ledger,
        store=store,
        context=JobContext("org/repo", "a" * 40),
    )
    assert (first.provider_calls, first.cache_reused) == (1, False)
    second = run_job(
        manifest,
        packet_v2,
        config=CONFIG,
        facts=facts_v2,
        ledger=ledger,
        store=store,
        context=JobContext("org/repo", "b" * 40),
    )
    assert (second.provider_calls, second.cache_reused) == (0, True)
    assert second.request_sha256 == first.request_sha256
    assert len(gateway.requests) == 1


RECONCILIATION = load_manifests(REPO_ROOT / "prompts")["source_reconciliation"]
S4_ENTRY = RegistryEntry.model_validate(
    {
        "repository": "org/Aspose.Widget-FOSS-for-Python",
        "family": "widget",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "widget",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)
S4_FACTS = FactsDocument(
    "org/Aspose.Widget-FOSS-for-Python",
    "a" * 40,
    (
        Fact(
            "identity:repository",
            "identity",
            "org/Aspose.Widget-FOSS-for-Python",
            (Evidence("data/registry.json"),),
        ),
        Fact("identity:revision", "identity", "a" * 40, (Evidence("git"),)),
        Fact("package:name", "package", "widget", (Evidence("setup.py"),)),
        Fact("inherited_unit:001.heading", "inherited_unit", "# Widget", (Evidence("README.md"),)),
    ),
)


def _s4_call() -> tuple[dict[str, Any], dict[str, Any], Any]:
    """The real S4 packet, call schema, and checks for S4_FACTS' one inherited unit."""
    import functools

    from repository_presenter.components.readme.reconciliation.dispositions import (
        reconcile_checks,
        reconciliation_packet,
        reconciliation_schema,
    )

    batch = list(S4_FACTS.by_kind("inherited_unit"))
    packet = reconciliation_packet(S4_ENTRY, S4_FACTS, {}, RECONCILIATION.manifest, batch)
    schema = reconciliation_schema(RECONCILIATION, batch, S4_FACTS, {})
    return packet, schema, functools.partial(reconcile_checks, facts=S4_FACTS)


def _s4_run(store: CallStore, ledger: Ledger) -> Any:
    packet, schema, checks = _s4_call()
    return run_job(
        RECONCILIATION,
        packet,
        config=CONFIG,
        facts=S4_FACTS,
        ledger=ledger,
        store=store,
        context=CONTEXT,
        checks=checks,
        call_schema=schema,
    )


def test_a_stored_folded_reply_is_reused_without_the_decoder_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G4-W17 arrival item 60 (lane C PROPOSAL V, lane D PROPOSAL P24, lane B on PDF-Cpp and
    Email-Cpp; four repositories at ACCEPTED with BC-11 unreachable). The call schema constrains
    what a decoder may emit - S4's fact_ids enum lists the packet's own IDs - but what the store
    holds is the folded output: normalize() writes identity:revision (no packet ever shows it) into
    every supersession by identity or navigation, and an UNRESOLVED example behind a deferred
    block. Re-judging the stored reply under the decoder schema rejected what the live path had
    accepted: cache_stale, a fresh call, a different document - on request digests the same
    sealing run had itself stored. The reuse path re-judges under the manifest's base schema, the
    binding, and the checks, never the decoder constraint; the digest still carries the call
    schema, so a changed schema still misses the store and calls afresh."""
    from repository_presenter.core.llm.jobs import request_hash

    gateway = _Gateway(monkeypatch)  # no response: any provider call here is the defect
    ledger = Ledger(tmp_path / "calls.jsonl")
    store = CallStore(tmp_path / "calls")
    packet, schema, _checks = _s4_call()
    enum = schema["properties"]["dispositions"]["items"]["properties"]["fact_ids"]["items"]["enum"]
    assert "identity:revision" not in enum and "identity:repository" in enum
    folded = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:001.heading",
                "disposition": "SUPERSEDE_REDUNDANT",
                "destination_section": "identity",
                "fact_ids": ["identity:repository", "identity:revision", "package:name"],
                "rationale": "the shell renders the title",
            }
        ]
    }
    digest = request_hash(RECONCILIATION, packet, schema)
    store.put(digest, "source_reconciliation", "qwen3-next", folded)

    reused = _s4_run(store, ledger)
    assert (reused.provider_calls, reused.cache_reused) == (0, True)
    assert reused.request_sha256 == digest
    assert reused.output == folded
    assert store.get(digest) == folded
    assert [(r.disposition, r.outcome) for r in ledger.records()] == [
        ("cache_reuse", "cache_reuse")
    ]
    assert gateway.requests == []


def test_a_stored_reply_the_base_schema_or_binding_rejects_is_still_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reuse path drops only the decoder constraint: the manifest's own schema, the binding,
    and the checks still re-judge a stored reply, so a corrected rule takes effect without a
    call and a stored reply they reject is replaced exactly as before."""
    from repository_presenter.core.llm.jobs import request_hash

    fresh = {
        "dispositions": [
            {
                "unit_id": "inherited_unit:001.heading",
                "disposition": "VERIFIED_PRESERVE",
                "destination_section": "identity",
                "fact_ids": ["identity:repository"],
                "rationale": "kept",
            }
        ]
    }
    gateway = _Gateway(monkeypatch, _completion(fresh))
    ledger = Ledger(tmp_path / "calls.jsonl")
    store = CallStore(tmp_path / "calls")
    packet, schema, _checks = _s4_call()
    digest = request_hash(RECONCILIATION, packet, schema)
    # Cites a fact that does not exist: the base schema admits the string, the binding does not.
    store.put(
        digest,
        "source_reconciliation",
        "qwen3-next",
        {
            "dispositions": [
                {
                    "unit_id": "inherited_unit:001.heading",
                    "disposition": "SUPERSEDE_REDUNDANT",
                    "destination_section": "identity",
                    "fact_ids": ["identity:nope"],
                    "rationale": "r",
                }
            ]
        },
    )
    replaced = _s4_run(store, ledger)
    assert (replaced.provider_calls, replaced.cache_reused) == (1, False)
    assert [(r.disposition, r.outcome) for r in ledger.records()] == [
        ("cache_stale", "cache_stale"),
        ("provider_call", "success"),
    ]
    # The fresh call went out under the decoder constraint, enum and all.
    sent = gateway.requests[0]["response_format"]["json_schema"]["schema"]
    assert sent["properties"]["dispositions"]["items"]["properties"]["fact_ids"]["items"]["enum"]


def test_a_stored_output_the_rules_reject_is_replaced_by_a_new_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateway = _Gateway(
        monkeypatch,
        _completion(_investigation("do things")),
        _completion(_investigation("Do better things")),
    )
    ledger = Ledger(tmp_path / "calls.jsonl")
    store = CallStore(tmp_path / "calls")
    first = _run(store, ledger)

    def reject_lowercase(output: dict[str, Any]) -> list[str]:
        return [
            f"title {c['title']!r} must start with a capital"
            for c in output["capabilities"]
            if not c["title"][:1].isupper()
        ]

    replaced = _run(store, ledger, checks=reject_lowercase)
    assert (replaced.provider_calls, replaced.cache_reused) == (1, False)
    assert replaced.output["capabilities"][0]["title"] == "Do better things"
    assert replaced.request_sha256 == first.request_sha256
    assert store.get(first.request_sha256) == replaced.output
    assert len(gateway.requests) == 2
    records = ledger.records()
    assert [(r.disposition, r.outcome, r.error_class) for r in records] == [
        ("provider_call", "success", None),
        ("cache_stale", "cache_stale", "OutputRejected"),
        ("provider_call", "success", None),
    ]
    assert ledger.summary().provider_calls == 2 and ledger.summary().cache_reuses == 0


def test_a_rejected_reply_is_kept_beside_the_store(tmp_path: Path) -> None:
    from repository_presenter.core.llm.jobs import CallStore

    store = CallStore(tmp_path / "calls")
    path = store.reject("a" * 64, 2, "independent_review", "{bad json", ["quote is not the text"])
    assert path == tmp_path / "calls" / ("a" * 12 + ".rejected-2.json")
    record = json.loads(path.read_text("utf-8"))
    assert record == {
        "attempt": 2,
        "content": "{bad json",
        "job": "independent_review",
        "rejection": ["quote is not the text"],
    }


def test_the_rejected_filename_fits_where_the_old_one_crossed_max_path(tmp_path: Path) -> None:
    """G4-W17 arrival item 2. Measured 2026-09-06 on Aspose.Cells for TypeScript: a
    `<24-char-hash>.rejected-1.json` name, the longest path any transaction writes, crossed
    Windows' 260-character limit by one character from that lane's checkout root. `path` and
    `reject` share the same 12-character prefix - accepted and rejected records are the same
    kind of thing, just one further stage - so a lookup never has to guess which length a given
    record was written with."""
    store = CallStore(tmp_path / "calls")
    accepted = store.path("b" * 64)
    rejected = store.reject("b" * 64, 1, "independent_review", "{}", [])
    assert accepted.name == "b" * 12 + ".json"
    assert rejected.name == "b" * 12 + ".rejected-1.json"
    # Twelve characters shorter than the previous 24-character prefix on the one name that used
    # to cross the limit: 261 measured then becomes 249, twelve characters of headroom restored.
    assert len(rejected.name) == 12 + len(".rejected-1.json")
    assert store.get("a" * 64) is None  # a rejection is never an accepted output
