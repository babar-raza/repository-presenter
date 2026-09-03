"""The seal: a content-addressed bundle, exactly the consumed inputs, and the no-op proof."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from repository_presenter.components.readme.bundle.seal import (
    BundleLeakError,
    SealError,
    SealInputs,
    dependencies_document,
    invalidate_bundle,
    invalidates,
    seal_candidate,
    verify_bundle,
)
from repository_presenter.core.facts import Evidence, Fact, FactsDocument
from repository_presenter.core.llm.prompts import load_manifests
from repository_presenter.core.registry.models import RegistryEntry
from repository_presenter.core.secrets import ConfiguredSecret
from support import REPO_ROOT

ENTRY = RegistryEntry.model_validate(
    {
        "repository": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "family": "3d",
        "platform": "python",
        "ecosystem": "python",
        "mode": "dry_run",
        "policy_profile": "p",
        "active": True,
        "provider_identity": {"provider": "github", "repository_id": 1, "node_id": "R_1"},
    }
)
REVISION = "c" * 40
PROMPTS = load_manifests(REPO_ROOT / "prompts")
FACTS = FactsDocument(
    ENTRY.repository,
    REVISION,
    (
        Fact("identity:repository", "identity", ENTRY.repository, (Evidence("x"),)),
        Fact("format:output.glb", "format", ".glb", (Evidence("x"),)),
    ),
)
SCHEMA = json.loads((REPO_ROOT / "schemas" / "candidate-bundle.schema.json").read_text("utf-8"))


def _validation(pending: bool = True) -> dict[str, Any]:
    eleven = {
        "id": "BC-11",
        "verdict": "PENDING" if pending else "PASS",
        "causal_stage": None,
        "details": ["judged at S12"],
    }
    return {
        "schema_version": 1,
        "validator_version": "1",
        "protected_content_fingerprint": "f" * 64,
        "checks": [{"id": "BC-01", "verdict": "PASS", "causal_stage": None, "details": []}, eleven],
        "advisory": [],
        "summary": {"pass": 1, "fail": 0, "pending": 1 if pending else 0},
    }


def _transaction(tmp_path: Path, readme: str = "# Doc\n", revision: str = REVISION) -> Path:
    transaction = tmp_path / "runs" / "transactions" / "owner__name" / revision
    transaction.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "README.md": readme,
        "README.patch": "--- a\n+++ b\n",
        "facts.json": '{"facts": []}\n',
        "investigation.json": "{}\n",
        "dispositions.json": '{"dispositions": []}\n',
        "plan.json": '{"sections": []}\n',
        "content_units.json": '{"units": []}\n',
        "validation.json": json.dumps(_validation(), indent=2, sort_keys=True) + "\n",
        "review.json": '{"verdict": "ACCEPT"}\n',
        "repairs.json": '{"attempts": {}}\n',
        "calls.jsonl": '{"call_id": "one"}\n',
    }
    for name, text in artifacts.items():
        (transaction / name).write_text(text, encoding="utf-8", newline="\n")
    return transaction


def _inputs(
    tmp_path: Path,
    provider_calls: int,
    secrets: tuple[ConfiguredSecret, ...] = (),
    stage: str | None = None,
    revision: str = REVISION,
) -> SealInputs:
    return SealInputs(
        entry=ENTRY,
        source_revision=revision,
        tree_sha256="t" * 64,
        facts=FACTS,
        prompts=PROMPTS,
        validation=_validation(),
        transaction=tmp_path / "runs" / "transactions" / "owner__name" / revision,
        candidates=tmp_path / "candidates",
        provider_calls=provider_calls,
        secrets=secrets,
        earliest_affected_stage=stage,
    )


def test_dependencies_name_exactly_the_consumed_inputs(tmp_path: Path) -> None:
    _transaction(tmp_path)
    document = dependencies_document(_inputs(tmp_path, 3))
    assert document["source"] == {"revision": REVISION, "tree_sha256": "t" * 64}
    assert list(document["facts"]) == ["format:output.glb", "identity:repository"]
    assert all(len(digest) == 64 for digest in document["facts"].values())
    assert document["prompts"]["independent_review"]["sha256"] == (
        PROMPTS["independent_review"].sha256
    )
    assert document["prompts"]["targeted_repair"]["version"] == "3"
    assert document["contract_version"] == "readme-contract-v1-draft"
    assert document["components"] == {"shell": "3", "renderer": "11"}
    assert document["validators"]["BC-01"] == "1" and len(document["validators"]) == 11
    assert document["acceptance_profile_version"] is None
    assert document["protected_content_fingerprint"] == "f" * 64
    assert len(document["policy"]["sha256"]) == 64 and document["policy"]["version"] == "1"


def test_the_first_seal_is_accepted_and_a_fresh_zero_call_replay_proves_the_no_op(
    tmp_path: Path,
) -> None:
    _transaction(tmp_path)
    first = seal_candidate(_inputs(tmp_path, provider_calls=7))
    bundle = tmp_path / "candidates" / "aspose-3d-foss__Aspose.3D-FOSS-for-Python" / REVISION
    assert first.bundle == bundle and first.state == "ACCEPTED" and first.changed
    assert first.proof is None and first.note.startswith("sealed;")
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    assert manifest["provider_calls"] == 7 and manifest["no_op_proof"] is None
    assert set(manifest["files"]) == set(first.files) and "dependencies.json" in manifest["files"]
    for name, digest in manifest["files"].items():
        data = (bundle / name).read_bytes()
        assert digest == {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    assert (bundle.parent / "CURRENT").read_text("utf-8") == f"{REVISION}\n"

    withheld = seal_candidate(_inputs(tmp_path, provider_calls=1))
    assert withheld.state == "ACCEPTED" and not withheld.changed
    assert "proof withheld" in withheld.note

    # An unproven seal that differs is simply replaced.
    _transaction(tmp_path, readme="# Draft\n")
    replaced = seal_candidate(_inputs(tmp_path, provider_calls=2))
    assert replaced.state == "ACCEPTED" and replaced.proof is None and replaced.changed
    assert replaced.note.startswith("re-sealed: README.md changed")
    _transaction(tmp_path)
    restored = seal_candidate(_inputs(tmp_path, provider_calls=0))
    assert restored.state == "ACCEPTED" and restored.note.startswith("re-sealed")

    (tmp_path / "runs" / "transactions" / "owner__name" / REVISION / "calls.jsonl").write_text(
        '{"call_id": "one"}\n{"call_id": "two"}\n', encoding="utf-8", newline="\n"
    )
    proven = seal_candidate(_inputs(tmp_path, provider_calls=0))
    assert proven.state == "READY_FOR_PROPOSAL" and proven.changed
    assert proven.proof is not None and proven.proof["provider_calls"] == 0
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    assert manifest["state"] == "READY_FOR_PROPOSAL" and manifest["provider_calls"] == 0
    judged = json.loads((bundle / "validation.json").read_text("utf-8"))
    assert judged["checks"][1]["verdict"] == "PASS"
    assert judged["summary"] == {"pass": 2, "fail": 0, "pending": 0}
    assert (bundle / "calls.jsonl").read_text("utf-8").count("\n") == 2

    before = (bundle / "manifest.json").read_bytes()
    again = seal_candidate(_inputs(tmp_path, provider_calls=0))
    assert again.state == "READY_FOR_PROPOSAL" and not again.changed
    assert again.note.startswith("no-op:")
    assert (bundle / "manifest.json").read_bytes() == before

    # A proven candidate stays valid: a differing run records an update and touches no file.
    _transaction(tmp_path, readme="# Changed\n")
    updated = seal_candidate(_inputs(tmp_path, provider_calls=0, stage="COMPOSING"))
    assert updated.state == "READY_FOR_PROPOSAL" and updated.proof is not None and updated.changed
    assert updated.note.startswith("valid update available (presentation): README.md changed")
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    assert manifest["state"] == "READY_FOR_PROPOSAL"
    assert manifest["update"]["classification"] == "presentation"
    assert manifest["update"]["changed"] == ["README.md"]
    assert manifest["update"]["earliest_affected_stage"] == "COMPOSING"
    assert (bundle / "README.md").read_text("utf-8") == "# Doc\n"
    assert manifest["update"]["files"]["README.md"] == hashlib.sha256(b"# Changed\n").hexdigest()
    withheld = seal_candidate(_inputs(tmp_path, provider_calls=1, stage="COMPOSING"))
    assert not withheld.changed  # the same update is not recorded twice, nor adopted unproven
    assert (bundle / "README.md").read_text("utf-8") == "# Doc\n"
    # A fresh zero-call process reproducing the waiting update proves it; the bundle adopts it.
    adopted = seal_candidate(_inputs(tmp_path, provider_calls=0, stage="COMPOSING"))
    assert adopted.state == "READY_FOR_PROPOSAL" and adopted.changed
    assert adopted.note.startswith("update adopted (presentation): a fresh process reproduced")
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    assert "update" not in manifest and manifest["adopted"]["changed"] == ["README.md"]
    assert manifest["adopted"]["previous_proof"]["provider_calls"] == 0
    assert manifest["no_op_proof"]["provider_calls"] == 0 and manifest["provider_calls"] == 0
    assert (bundle / "README.md").read_text("utf-8") == "# Changed\n"
    assert json.loads((bundle / "validation.json").read_text("utf-8"))["summary"]["pending"] == 0
    (tmp_path / "runs" / "transactions" / "owner__name" / REVISION / "facts.json").write_text(
        '{"facts": ["new"]}\n', encoding="utf-8", newline="\n"
    )
    factual = seal_candidate(_inputs(tmp_path, provider_calls=0, stage="EXTRACTING"))
    manifest = json.loads((bundle / "manifest.json").read_text("utf-8"))
    assert factual.changed and manifest["update"]["classification"] == "factual"
    assert manifest["update"]["changed"] == ["facts.json"] and "adopted" in manifest


def test_a_newer_proven_revision_supersedes_the_older_one(tmp_path: Path) -> None:
    _transaction(tmp_path)
    seal_candidate(_inputs(tmp_path, provider_calls=3))
    older = seal_candidate(_inputs(tmp_path, provider_calls=0))
    assert older.state == "READY_FOR_PROPOSAL"
    newer_revision = "d" * 40
    _transaction(tmp_path, readme="# Newer\n", revision=newer_revision)
    seal_candidate(_inputs(tmp_path, provider_calls=5, revision=newer_revision))
    manifest = json.loads((older.bundle / "manifest.json").read_text("utf-8"))
    assert manifest["state"] == "READY_FOR_PROPOSAL"  # an unproven newer seal supersedes nothing
    newer = seal_candidate(_inputs(tmp_path, provider_calls=0, revision=newer_revision))
    assert newer.state == "READY_FOR_PROPOSAL"
    manifest = json.loads((older.bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(manifest)
    assert manifest["state"] == "SUPERSEDED" and manifest["superseded_by"] == newer_revision
    assert manifest["no_op_proof"] is not None  # history stays in place
    assert (older.bundle.parent / "CURRENT").read_text("utf-8") == f"{newer_revision}\n"


def test_a_corrupt_bundle_fails_closed_and_a_factual_failure_invalidates(tmp_path: Path) -> None:
    _transaction(tmp_path)
    sealed = seal_candidate(_inputs(tmp_path, provider_calls=0))
    bundle = sealed.bundle
    assert verify_bundle(bundle) is not None
    assert verify_bundle(tmp_path / "nowhere") is None
    (bundle / "plan.json").write_text('{"sections": ["x"]}\n', encoding="utf-8", newline="\n")
    with pytest.raises(SealError, match=r"bundle artifact plan\.json is corrupt in c{40}"):
        verify_bundle(bundle)
    with pytest.raises(SealError, match=r"plan\.json is corrupt"):
        seal_candidate(_inputs(tmp_path, provider_calls=0))
    (bundle / "plan.json").unlink()
    with pytest.raises(SealError, match=r"bundle artifact plan\.json is missing"):
        verify_bundle(bundle)

    transaction = _transaction(tmp_path)
    with pytest.raises(SealError, match=r"plan\.json is missing"):
        seal_candidate(_inputs(tmp_path, provider_calls=0))  # a bundle never self-heals
    (bundle / "plan.json").write_bytes((transaction / "plan.json").read_bytes())
    assert verify_bundle(bundle) is not None
    failing = {
        "id": "BC-02",
        "verdict": "FAIL",
        "causal_stage": "EXTRACTING",
        "details": ["install_command:pip is CONTRADICTED: package registry: not found"],
    }
    assert invalidates(failing)
    assert not invalidates({"id": "BC-07", "verdict": "FAIL", "details": ["h1"]})
    assert invalidates({"id": "BC-10", "verdict": "FAIL", "details": ["REJECT_FACTUAL"]})
    assert not invalidates({"id": "BC-10", "verdict": "FAIL", "details": ["REJECT_PRESENTATION"]})
    manifest = invalidate_bundle(bundle, failing)
    assert manifest is not None and manifest["state"] == "INVALIDATED"
    stored = json.loads((bundle / "manifest.json").read_text("utf-8"))
    jsonschema.Draft202012Validator(SCHEMA).validate(stored)
    assert stored["invalidated"]["check"] == "BC-02"
    assert stored["invalidated"]["causal_stage"] == "EXTRACTING"
    assert invalidate_bundle(tmp_path / "nowhere", failing) is None


def test_a_missing_artifact_or_a_leaked_secret_fails_the_seal_closed(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path, readme="# Doc with sk-live-secret-value\n")
    secret = ConfiguredSecret("GPT_OSS_API_KEY", b"sk-live-secret-value")
    with pytest.raises(BundleLeakError, match=r"GPT_OSS_API_KEY in README\.md"):
        seal_candidate(_inputs(tmp_path, provider_calls=0, secrets=(secret,)))
    (transaction / "review.json").unlink()
    with pytest.raises(SealError, match=r"no review\.json"):
        seal_candidate(_inputs(tmp_path, provider_calls=0))
