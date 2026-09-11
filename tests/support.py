"""Builders for synthetic project roots, cursors, sealed bundles, and disposable git repos."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
from openai import OpenAI

from repository_presenter.core.config import GatewayConfig
from repository_presenter.core.git_safety.git import run_git
from repository_presenter.core.llm import transport

REPO_ROOT = Path(__file__).resolve().parents[1]


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
) -> Path:
    """Create a bundle directory; seal it with a manifest when ``state`` or ``raw`` is given.

    Writes ``CURRENT`` pointing at ``revision`` too (unless ``current=False``), matching what a
    real seal always does - ``count_current_candidates`` (TB-06) only ever resolves a repository
    through its own ``CURRENT`` file, never by scanning revision directories directly.
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
        manifest.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "repository": repository_dir.replace("__", "/", 1),
                    "revision": revision,
                    "state": state,
                    "files": digest,
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
