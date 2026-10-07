"""Builders for synthetic project roots, cursors, sealed bundles, and disposable git repos."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
from openai import OpenAI

from repository_presenter.components.issues.approval import (
    approval_relative_path,
    evidence_digest,
    handoff_id,
)
from repository_presenter.components.issues.model import Handoff
from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.git_safety.git import run_git
from repository_presenter.core.github.read_client import DefaultBranchRead
from repository_presenter.core.llm import transport
from repository_presenter.core.state.cas import SaveResult
from repository_presenter.core.state.schema import RepositoryRecord

REPO_ROOT = Path(__file__).resolve().parents[1]


def empty_enum_paths(node: Any, path: str = "$") -> list[str]:
    """Every JSON-schema path whose ``enum`` is an empty list. No value satisfies such a keyword,
    so a strict json_schema request carrying one cannot be decoded (the S5 HTTP 500/502 on
    Aspose.GIS, 2026-10-04, whose three link targets were all shell-owned)."""
    found: list[str] = []
    if isinstance(node, dict):
        if node.get("enum") == []:
            found.append(path)
        for key, value in node.items():
            found.extend(empty_enum_paths(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(empty_enum_paths(value, f"{path}[{index}]"))
    return found


def assert_no_empty_enums(schema: dict[str, Any]) -> None:
    assert empty_enum_paths(schema) == [], "a strict json_schema request cannot carry an empty enum"


class InMemoryStateBackend:
    """A :class:`~repository_presenter.core.state.cas.StateBackend` test double with the real
    compare-and-swap contract (stale-version rejection, no silent lost update) but no git
    subprocess - fast enough for the bulk of ``tests/core/state/`` while ``test_git_backend.py``
    separately proves the real ref-based mechanism against a disposable local repository."""

    def __init__(self) -> None:
        self._records: dict[str, RepositoryRecord] = {}

    def load(self, repository: str) -> RepositoryRecord | None:
        return self._records.get(repository)

    def save(
        self, repository: str, record: RepositoryRecord, expected_version: int | None
    ) -> SaveResult:
        current = self._records.get(repository)
        current_version = current.state_version if current is not None else None
        if current_version != expected_version:
            return SaveResult(outcome="stale", record=current)
        saved = record.model_copy(update={"state_version": (current_version or 0) + 1})
        self._records[repository] = saved
        return SaveResult(outcome="saved", record=saved)


def model_listing(*models: tuple[str, str]) -> httpx.Response:
    """A ``GET /models`` body in the OpenAI list shape, one entry per (id, owned_by)."""
    data = [{"id": model_id, "object": "model", "owned_by": owner} for model_id, owner in models]
    return httpx.Response(200, json={"object": "list", "data": data})


def mock_gateway(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    """Serve the gateway from ``handler`` through the real SDK client, never the network."""

    def build(config: GatewayConfig) -> OpenAI:
        return OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            max_retries=0,
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

    monkeypatch.setattr(transport, "build_client", build)


def write_cursor(
    root: Path,
    *,
    gate: str = "G0_FOUNDATION",
    gate_status: str = "READY",
    work_item: str = "G0-W01",
    work_item_status: str = "READY",
    recorded_candidates: int = 0,
    denominator: int = 34,
    canary: str = "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
) -> Path:
    """Write a minimal cursor with the fields the CLI reports."""
    path = root / "project" / "state.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "schema_version: 1",
        "progress:",
        f"  current_candidates: {recorded_candidates}",
        f"  denominator: {denominator}",
        f"  canary: {canary}",
        "current_gate:",
        f"  id: {gate}",
        f"  status: {gate_status}",
        "active_work_item:",
        f"  id: {work_item}",
        f"  status: {work_item_status}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_bundle(
    root: Path,
    repository_dir: str,
    revision: str,
    state: str | None,
    *,
    raw: str | None = None,
    current: bool = True,
    upstream_blobs: dict[str, str] | None = None,
) -> Path:
    """Create a bundle directory; seal it with a manifest when ``state`` or ``raw`` is given.

    Writes ``CURRENT`` pointing at ``revision`` too (unless ``current=False``), matching what a
    real seal always does - ``count_current_candidates`` (TB-06) only ever resolves a repository
    through its own ``CURRENT`` file, never by scanning revision directories directly.
    ``upstream_blobs`` is recorded on the manifest when given, as a seal records it; omitted, the
    manifest carries no upstream blob ids (a bundle sealed before they were recorded).
    """
    bundle = root / "candidates" / repository_dir / revision
    bundle.mkdir(parents=True, exist_ok=True)
    manifest = bundle / "manifest.json"
    if raw is not None:
        manifest.write_text(raw, encoding="utf-8")
    elif state is not None:
        readme = bundle / "README.md"
        readme.write_bytes(b"")
        digest = {"README.md": {"sha256": hashlib.sha256(b"").hexdigest(), "bytes": 0}}
        recorded = {} if upstream_blobs is None else {"upstream_blobs": upstream_blobs}
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "repository": repository_dir.replace("__", "/", 1),
                    "revision": revision,
                    "state": state,
                    "files": digest,
                    **recorded,
                }
            ),
            encoding="utf-8",
        )
    if current and (raw is not None or state is not None):
        (bundle.parent / "CURRENT").write_text(f"{revision}\n", encoding="utf-8")
    return bundle


def init_git_repository(path: Path, *, with_commit: bool = True) -> Path:
    """A disposable local repository on branch ``main`` with a local identity.

    ``git init``'s exit status is never the evidence: when git already resolves ``path`` inside
    some repository, ``git init`` there is a no-op re-init that still exits 0, and every fixture
    command after it (identity config, ``add``, ``commit``) lands on that repository instead -
    measured 2026-09-11 as fixture commits on live lane branches and this checkout's own identity
    and ``core.bare`` rewritten (RESEARCH_AND_GUIDELINES.md section 29, G4-W17 arrival item 55).
    So the target is refused up front if git resolves any repository for it, and the repository
    just created is verified to be the one at ``path`` before anything is written into it.
    """
    path.mkdir(parents=True, exist_ok=True)
    enclosing = run_git(["rev-parse", "--absolute-git-dir"], cwd=path)
    if enclosing.returncode == 0:
        raise RuntimeError(
            f"refusing to init a fixture repository at {path}: git already resolves it inside"
            f" {enclosing.stdout.strip()}, where `git init` would be a no-op re-init exiting 0"
            " and every fixture command after it would land on that repository"
        )
    for args in (
        ["init", "-q", "-b", "main"],
        ["config", "user.email", "test@example.com"],
        ["config", "user.name", "Test"],
    ):
        result = run_git(args, cwd=path)
        assert result.returncode == 0, result.stderr
    own = run_git(["rev-parse", "--absolute-git-dir"], cwd=path)
    assert own.returncode == 0, own.stderr
    assert Path(own.stdout.strip()).resolve() == (path / ".git").resolve(), (
        f"fixture at {path} resolved to a different repository: {own.stdout.strip()}"
    )
    if with_commit:
        (path / "README.md").write_text("# test\n", encoding="utf-8")
        commit_all(path, "initial")
    return path


def commit_all(path: Path, message: str) -> str:
    """Stage everything, commit, and return the new HEAD revision."""
    assert run_git(["add", "."], cwd=path).returncode == 0
    result = run_git(["commit", "-q", "-m", message], cwd=path)
    assert result.returncode == 0, result.stderr
    return head_revision(path)


def head_revision(path: Path) -> str:
    result = run_git(["rev-parse", "HEAD"], cwd=path)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@dataclass(frozen=True)
class CallStatistics:
    """How often a job's first reply was accepted, from a sealed ledger.

    RESEARCH_AND_GUIDELINES.md section 27.6 control 1: first-attempt acceptance and the re-ask
    share are computed from the sealed calls.jsonl, never estimated. Only provider calls count;
    a reused stored output was accepted when it was first made.
    """

    calls: int
    invalid: int
    rejections: tuple[str, ...] = ()

    @property
    def first_attempt_rate(self) -> float:
        return 100.0 * (self.calls - self.invalid) / self.calls if self.calls else 100.0

    @property
    def reask_share(self) -> float:
        return 100.0 * self.invalid / self.calls if self.calls else 0.0


def call_statistics(calls_jsonl: Path) -> dict[str, CallStatistics]:
    """Per job, plus ``TOTAL``, the provider calls and how many were rejected."""
    calls: Counter[str] = Counter()
    invalid: Counter[str] = Counter()
    rejections: dict[str, list[str]] = {}
    for line in calls_jsonl.read_text("utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("disposition") != "provider_call":
            continue
        for key in (record["job"], "TOTAL"):
            calls[key] += 1
            if record.get("outcome") == "response_invalid":
                invalid[key] += 1
                rejections.setdefault(key, []).extend(record.get("rejection") or ())
    return {
        job: CallStatistics(count, invalid[job], tuple(rejections.get(job, ())))
        for job, count in sorted(calls.items())
    }


def monitor_registry_entry(
    repository: str, *, mode: str = "dry_run", repository_id: int = 1
) -> dict[str, Any]:
    """One registry entry payload for an Aspose FOSS repository (``data/registry.json`` shape)."""
    owner, name = repository.split("/")
    family = owner.removeprefix("aspose-").removesuffix("-foss")
    platform = name.split("-for-")[1].lower()
    platform = "net" if platform == ".net" else platform
    return {
        "repository": repository,
        "family": family,
        "platform": platform,
        "ecosystem": platform,
        "mode": mode,
        "policy_profile": "fixture",
        "active": True,
        "provider_identity": {
            "provider": "github",
            "repository_id": repository_id,
            "node_id": f"R_fixture_{repository_id}",
        },
    }


class FakeDefaultBranchReader:
    """Injected stand-in for ``core/github/read_client.py::fetch_default_branch_sha``.

    Each repository maps to a head sha, a ready ``DefaultBranchRead``, or an exception to raise.
    Every call and the token it was given are recorded, so a test can prove what was read.
    """

    def __init__(self, outcomes: dict[str, str | DefaultBranchRead | Exception]) -> None:
        self.outcomes = outcomes
        self.calls: list[str] = []
        self.tokens: list[str | None] = []

    def __call__(self, repository: str, *, token: str | None = None) -> DefaultBranchRead:
        self.calls.append(repository)
        self.tokens.append(token)
        outcome = self.outcomes[repository]
        if isinstance(outcome, Exception):
            raise outcome
        if isinstance(outcome, DefaultBranchRead):
            return outcome
        return DefaultBranchRead(repository, sha=outcome, branch="main")


def accepting_token_verifier(token: str) -> Any:
    """A token verifier that accepts any token - for tests about the gates other than provenance."""
    from repository_presenter.core.github.token_provenance import TokenDecision

    return TokenDecision(True)


def make_permit(repository: str, *, mode: str = "full", effect: str = "readme_proposal") -> Any:
    """A ``WritePermit`` for a repository that is not a real Aspose FOSS name (the registry model
    validates the name, ``model_construct`` does not) - the effect modules only read ``.effect``
    and ``.entry.repository`` from it."""
    from repository_presenter.core.registry.models import RegistryEntry
    from repository_presenter.core.registry.write_gate import WritePermit

    entry = RegistryEntry.model_construct(
        repository=repository,
        family="fixture",
        platform="fixture",
        ecosystem="fixture",
        mode=mode,
        policy_profile="fixture",
        active=True,
        provider_identity=None,
    )
    return WritePermit(effect=effect, entry=entry)  # type: ignore[arg-type]


def write_registry_file(root: Path, entries: list[dict[str, Any]]) -> Path:
    """``data/registry.json`` under a synthetic project root."""
    path = root / "data" / "registry.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema_version": 1, "entries": entries}), encoding="utf-8")
    return path


def write_proposable_bundle(
    root: Path,
    repository: str,
    revision: str,
    readme_text: str,
    *,
    state: str = "READY_FOR_PROPOSAL",
) -> Path:
    """A sealed bundle with a real README and a manifest that verifies, plus ``CURRENT``."""
    owner, name = repository.split("/", 1)
    bundle = root / "candidates" / f"{owner}__{name}" / revision
    bundle.mkdir(parents=True, exist_ok=True)
    data = readme_text.encode("utf-8")
    (bundle / "README.md").write_bytes(data)
    (bundle / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "repository": repository,
                "revision": revision,
                "state": state,
                "files": {
                    "README.md": {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                },
            }
        ),
        encoding="utf-8",
    )
    (bundle.parent / "CURRENT").write_text(f"{revision}\n", encoding="utf-8")
    return bundle


def merge_to_origin_main(root: Path, message: str = "merge") -> str:
    """Commit everything under ``root`` (initialising a disposable repository on first use) and
    point ``refs/remotes/origin/main`` at the new commit - the state of a control checkout whose
    ``main`` already holds that content. Returns the commit."""
    if not (root / ".git").exists():
        init_git_repository(root, with_commit=False)
    revision = commit_all(root, message)
    assert run_git(["update-ref", "refs/remotes/origin/main", revision], cwd=root).returncode == 0
    return revision


def approval_text(
    handoff: Handoff,
    *,
    digest: str | None = None,
    repository: str | None = None,
    approver: str = "owner-login",
    approved_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> str:
    """An owner approval record (``ops/issue_approvals/<handoff-id>.json``) for ``handoff``,
    valid now unless an argument overrides one field."""
    approved = approved_at or datetime.now(UTC) - timedelta(hours=1)
    expires = expires_at or approved + timedelta(days=7)
    record = {
        "handoff_id": handoff_id(handoff),
        "repository": repository or handoff.repository,
        "evidence_digest": digest or evidence_digest(handoff),
        "approver": approver,
        "approved_at": approved.isoformat(),
        "expires_at": expires.isoformat(),
    }
    return json.dumps(record, indent=2) + chr(10)


class MemoryApprovalStore:
    """An in-memory approval store: ``records`` maps a handoff id to the record text."""

    def __init__(self, records: dict[str, str] | None = None) -> None:
        self.records = records or {}
        self.reads: list[str] = []

    def read(self, identifier: str) -> str | None:
        self.reads.append(identifier)
        return self.records.get(identifier)


def approving_store(handoff: Handoff, **overrides: Any) -> MemoryApprovalStore:
    """A store holding a valid owner approval for exactly ``handoff``."""
    return MemoryApprovalStore({handoff_id(handoff): approval_text(handoff, **overrides)})


def close_approval_text(
    handoff: Handoff,
    *,
    issue_number: int | None = None,
    close_reason: str = "not_planned",
    digest: str | None = None,
    repository: str | None = None,
    approver: str = "owner-login",
    approved_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> str:
    """An owner close-approval record (``ops/issue_close_approvals/<handoff-id>.json``) for the
    issue ``handoff`` filed, valid now unless an argument overrides one field."""
    approved = approved_at or datetime.now(UTC) - timedelta(hours=1)
    expires = expires_at or approved + timedelta(days=7)
    number = issue_number if issue_number is not None else handoff.issue_ref.number  # type: ignore[union-attr]
    record = {
        "handoff_id": handoff_id(handoff),
        "repository": repository or handoff.repository,
        "issue_number": number,
        "close_reason": close_reason,
        "evidence_digest": digest or evidence_digest(handoff),
        "approver": approver,
        "approved_at": approved.isoformat(),
        "expires_at": expires.isoformat(),
    }
    return json.dumps(record, indent=2) + chr(10)


def closing_store(handoff: Handoff, **overrides: Any) -> MemoryApprovalStore:
    """A store holding a valid owner close approval for exactly ``handoff``'s filed issue."""
    return MemoryApprovalStore({handoff_id(handoff): close_approval_text(handoff, **overrides)})


def committed_approval_path(handoff: Handoff) -> str:
    return approval_relative_path(handoff_id(handoff))


def fake_npm(directory: Path, fail_run: bool = False) -> str:
    """A stand-in `npm` that records its arguments and exits 0 - or 3 on `npm run ...` when asked.

    The real one needs the network and a minute; what the verifier is tested on is what it does
    with an exit code. Written per platform because `execute` runs argv[0] directly: a `.cmd`
    where Windows resolves batch files, a `sh` script with its mode bit where the hosted runner
    (ubuntu) does not.
    """
    directory.mkdir(parents=True, exist_ok=True)
    if fail_run:
        (directory / "fail_run").write_text("", encoding="utf-8")
    if os.name == "nt":
        path = directory / "npm.cmd"
        path.write_text(
            "@echo off\r\n"
            'echo %*>>"%~dp0npm.log"\r\n'
            'if "%1"=="run" if exist "%~dp0fail_run" exit /b 3\r\n'
            "exit /b 0\r\n",
            encoding="utf-8",
        )
    else:
        path = directory / "npm"
        path.write_text(
            "#!/bin/sh\n"
            'd=$(dirname "$0")\n'
            'echo "$@" >> "$d/npm.log"\n'
            'if [ "$1" = "run" ] && [ -f "$d/fail_run" ]; then exit 3; fi\n'
            "exit 0\n",
            encoding="utf-8",
        )
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(path)


def npm_calls(npm: str) -> list[str]:
    log = Path(npm).parent / "npm.log"
    return [line.strip() for line in log.read_text("utf-8").splitlines()] if log.is_file() else []


def distinct_process_identities(patch: pytest.MonkeyPatch) -> None:
    """Make every ``Invocation.begin()`` under ``patch`` record a different process.

    A test that calls ``main`` twice stands in for two fresh processes, and the no-op proof
    refuses an invocation that shares a process with the one that sealed the bundle
    (``core/noop_proof.py``) while one pytest worker is one process. The identity reading itself,
    and a pair that really is one process, are tested in ``tests/core/test_noop_proof.py``.
    """
    from repository_presenter.core import noop_proof

    real = noop_proof.current_process_identity
    numbers = iter(range(1, 10**9))

    def distinct() -> noop_proof.ProcessIdentity:
        number = next(numbers)
        base = real()
        return noop_proof.ProcessIdentity(
            base.pid, f"{base.started}#{number}", base.boot_id, f"{base.nonce}#{number}"
        )

    patch.setattr(noop_proof, "current_process_identity", distinct)
