"""The npm half of every npm verifier: an npm, a clean run directory, a build in a copy."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repository_presenter.components.readme.extractors.surface import npm_build
from repository_presenter.core.examples import ExampleCandidate, MeasuredBuild
from support import fake_npm, npm_calls


def _package(root: Path, scripts: dict[str, str] | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {"name": "widget"}
    if scripts is not None:
        manifest["scripts"] = scripts
    (root / "package.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "index.js").write_text("export {};\n", encoding="utf-8")
    (root / "node_modules" / "left-pad").mkdir(parents=True)
    (root / "node_modules" / "left-pad" / "index.js").write_text("", encoding="utf-8")
    return root


def test_the_build_is_the_install_alone_when_the_manifest_declares_no_build(
    tmp_path: Path,
) -> None:
    npm = fake_npm(tmp_path / "tools")
    measured = npm_build.build_product(_package(tmp_path / "pkg"), tmp_path / "ws", npm, 60.0)
    assert measured == MeasuredBuild(
        True,
        "npm install",
        "succeeded (`npm install` exited 0; the manifest declares no build script, "
        "so nothing was compiled)",
    )
    assert npm_calls(npm) == ["install"]


def test_a_declared_build_script_is_driven_after_the_install(tmp_path: Path) -> None:
    npm = fake_npm(tmp_path / "tools")
    package = _package(tmp_path / "pkg", {"build": "rollup -c"})
    measured = npm_build.build_product(package, tmp_path / "ws", npm, 60.0)
    assert measured.verified and measured.command == "npm install\nnpm run build"
    assert npm_calls(npm) == ["install", "run build"]


def test_a_failing_step_names_itself_and_advertises_no_command(tmp_path: Path) -> None:
    npm = fake_npm(tmp_path / "tools", fail_run=True)
    package = _package(tmp_path / "pkg", {"build": "rollup -c"})
    measured = npm_build.build_product(package, tmp_path / "ws", npm, 60.0)
    assert measured == MeasuredBuild(
        False,
        "",
        "failed (`npm run build` exited 3 after `npm install` exited 0: npm error build exploded)",
    )


def test_the_build_runs_in_a_copy_and_the_clone_is_untouched(tmp_path: Path) -> None:
    package = _package(tmp_path / "pkg")
    npm_build.build_product(package, tmp_path / "ws", fake_npm(tmp_path / "tools"), 60.0)
    copy = tmp_path / "ws" / npm_build.PRODUCT_DIRECTORY
    assert (copy / "package.json").is_file() and (copy / "index.js").is_file()
    # What an earlier install left behind is not carried into the copy.
    assert not (copy / "node_modules").exists()
    assert (package / "node_modules" / "left-pad" / "index.js").is_file()


def test_no_npm_means_nothing_was_measured(tmp_path: Path) -> None:
    measured = npm_build.build_product(_package(tmp_path / "pkg"), tmp_path / "ws", None, 60.0)
    assert measured == MeasuredBuild(False, "", "not attempted (no npm on this machine)")
    assert not (tmp_path / "ws").exists()


def test_a_package_build_gets_its_own_fresh_run_directory(tmp_path: Path) -> None:
    package = _package(tmp_path / "pkg")
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "stale.txt").write_text("left by an earlier run", encoding="utf-8")
    measured = npm_build.verify_package_build(
        package, workspace, fake_npm(tmp_path / "tools"), 60.0
    )
    assert measured.verified
    assert not (workspace / "stale.txt").exists()


def test_a_run_directory_that_will_not_clear_is_reported_not_crashed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OneDrive holds handles on Windows; failing to clean scratch space must never cost a
    repository its candidate."""
    monkeypatch.setattr(npm_build, "fresh_workspace", lambda workspace: None)
    measured = npm_build.verify_package_build(
        _package(tmp_path / "pkg"), tmp_path / "ws", None, 1.0
    )
    assert measured == MeasuredBuild(False, "", "not attempted (no clean workspace to build in)")


def test_the_run_directory_falls_back_to_a_sibling_when_the_last_one_will_not_go(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = tmp_path / "ws"
    workspace.mkdir()
    real_rmtree = npm_build.shutil.rmtree

    def stubborn(path: object, *args: object, **kwargs: object) -> None:
        if Path(str(path)) == workspace:
            return  # the directory stays, as an open handle would keep it
        real_rmtree(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(npm_build.shutil, "rmtree", stubborn)
    fresh = npm_build.fresh_workspace(workspace)
    assert fresh == tmp_path / "ws-1" and fresh.is_dir()


def test_blocked_gives_every_candidate_a_not_verified_receipt() -> None:
    candidates = [
        ExampleCandidate(1, "javascript", "a", "README.md", 1, 2, "unit:001"),
        ExampleCandidate(2, "javascript", "b", "README.md", 3, 4, "unit:002"),
    ]
    receipts = npm_build.blocked(candidates, "BLOCKED_TOOLCHAIN: no node on this machine")
    assert [(r.ordinal, r.outcome, r.return_code) for r in receipts] == [
        (1, "NOT_VERIFIED", None),
        (2, "NOT_VERIFIED", None),
    ]
    assert all(r.detail == "BLOCKED_TOOLCHAIN: no node on this machine" for r in receipts)


def test_a_receipt_carries_no_path_of_this_machine(tmp_path: Path) -> None:
    workspace = tmp_path / "run"
    workspace.mkdir()
    for rendered in (str(workspace), workspace.as_posix()):
        text = f"error at {rendered}/example.mjs:3 and {rendered}\\other.mjs"
        cleaned = npm_build.scrub(text, workspace)
        assert str(tmp_path) not in cleaned and tmp_path.as_posix() not in cleaned
        assert "example.mjs:3" in cleaned and "other.mjs" in cleaned


def test_a_long_output_is_clipped() -> None:
    assert npm_build.clip("x" * 10) == "x" * 10
    clipped = npm_build.clip("x" * (npm_build.MAX_OUTPUT_CHARS + 50))
    assert len(clipped) == npm_build.MAX_OUTPUT_CHARS + 3 and clipped.endswith("...")


def test_npm_is_found_beside_node_when_the_registry_and_path_offer_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    node = tmp_path / "bin" / "node"
    node.parent.mkdir()
    node.write_text("", encoding="utf-8")
    sibling = node.with_name("npm.cmd" if npm_build.os.name == "nt" else "npm")
    sibling.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        npm_build, "resolve_tool", lambda name: str(node) if name == "node" else None
    )
    assert npm_build.npm_executable() == str(sibling)
    # Negative control: no node, no registry entry, no npm.
    monkeypatch.setattr(npm_build, "resolve_tool", lambda name: None)
    assert npm_build.npm_executable() is None


def test_the_install_gets_a_path_that_can_find_node_and_the_clone_is_not_touched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Measured 2026-10-19: a dependency's `node install.js` failed with "'node' is not
    recognized" because the machine's Node install was not on the inherited PATH."""
    seen: list[dict[str, str]] = []
    real = npm_build.execute

    def spy(argv, **kwargs):  # type: ignore[no-untyped-def]
        seen.append(dict(kwargs["extra_environment"]))
        return real(argv, **kwargs)

    monkeypatch.setattr(npm_build, "execute", spy)
    monkeypatch.setattr(npm_build, "augmented_path", lambda: "base-path;extra-node-dir")
    npm = fake_npm(tmp_path / "tools")
    measured = npm_build.build_product(_package(tmp_path / "pkg"), tmp_path / "ws", npm, 60.0)
    assert measured.verified
    assert seen and all(env["PATH"] == "base-path;extra-node-dir" for env in seen)


def test_a_failing_install_records_what_npm_said_without_this_machines_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from repository_presenter.core.execution import ExecutionResult

    def failing(argv, **kwargs):  # type: ignore[no-untyped-def]
        return ExecutionResult(
            argv=tuple(argv),
            return_code=1,
            stdout="",
            stderr=(
                "npm error code 1\n"
                "npm error path C:\\Users\\dev\\scratch\\node_modules\\esbuild\n"
                "npm error 'node' is not recognized as an internal or external command,\n"
            ),
            timed_out=False,
        )

    monkeypatch.setattr(npm_build, "execute", failing)
    measured = npm_build.build_product(_package(tmp_path / "pkg"), tmp_path / "ws", "npm", 60.0)
    assert measured.verified is False and measured.command == ""
    assert measured.summary.startswith("failed (`npm install` exited 1: ")
    assert "'node' is not recognized" in measured.summary
    assert "dev" not in measured.summary.replace("node_modules", "")
