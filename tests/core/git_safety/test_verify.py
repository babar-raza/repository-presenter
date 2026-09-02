"""Verification re-derives both push controls from disk and passes only when both hold."""

from __future__ import annotations

from pathlib import Path

from repository_presenter.core.git_safety.git import run_git
from repository_presenter.core.git_safety.hooks import install_pre_push_hook
from repository_presenter.core.git_safety.neuter import DISABLED_PUSH_URL, neuter_push
from repository_presenter.core.git_safety.verify import verify_push_blocked
from support import init_git_repository

ORIGIN = "https://github.com/example/example.git"


def _repo_with_origin(tmp_path: Path) -> Path:
    repo = init_git_repository(tmp_path / "repo")
    run_git(["remote", "add", "origin", ORIGIN], cwd=repo)
    return repo


def test_neutered_and_hooked_clone_is_proven_blocked(tmp_path: Path) -> None:
    repo = _repo_with_origin(tmp_path)
    neuter_push(repo)
    install_pre_push_hook(repo)

    proof = verify_push_blocked(repo)

    assert proof.ok
    assert proof.push_url == DISABLED_PUSH_URL
    assert proof.fetch_url == ORIGIN
    assert proof.hook_installed and proof.hook_contains_marker


def test_without_neutering_the_proof_fails(tmp_path: Path) -> None:
    repo = _repo_with_origin(tmp_path)
    install_pre_push_hook(repo)

    proof = verify_push_blocked(repo)

    assert not proof.ok
    assert proof.push_url == ORIGIN


def test_without_the_hook_the_proof_fails(tmp_path: Path) -> None:
    repo = _repo_with_origin(tmp_path)
    neuter_push(repo)

    proof = verify_push_blocked(repo)

    assert not proof.ok
    assert not proof.hook_installed
    assert "hook_installed=False" in proof.detail
