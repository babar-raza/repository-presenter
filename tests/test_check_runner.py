"""tools/runner/check_runner.py: the read-only check of the self-hosted seal runner's machine (D5).

Nothing here touches a network, a real toolchain or the machine's registry: the resolver's answers,
the version probes, the gateway fetch and the platform are injected, and an autouse fixture refuses
any socket connection. What is pinned: each check moves for exactly the defect it names; a missing
required tool, the WSL launcher in place of Git bash, a credential-shaped name in the runner's .env
and a wrong interpreter patch version each fail; no value (secret, path, host detail) reaches the
output; the module has no code path that writes, installs or registers anything.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from support import REPO_ROOT

TOOL_DIR = REPO_ROOT / "tools" / "runner"
sys.path.insert(0, str(TOOL_DIR))

import check_runner as cr  # noqa: E402

from repository_presenter.core import toolchains  # noqa: E402

SENTINEL_SECRET = "sentinel-gateway-key-5512"
EXPECTED = "3.13.2"


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("check_runner reached for a socket in a test")

    monkeypatch.setattr(socket.socket, "connect", refuse)


def stub_platform(version: str = EXPECTED) -> SimpleNamespace:
    return SimpleNamespace(python_version=lambda: version, system=lambda: "Windows")


def by_id(checks: list[cr.Check]) -> dict[str, cr.Check]:
    return {c.id: c for c in checks}


class Probe:
    """A scripted `run_command`: the first matching fragment of the argv wins."""

    def __init__(self, answers: dict[str, tuple[int, str]]) -> None:
        self.answers = answers
        self.seen: list[list[str]] = []

    def __call__(self, argv: list[str]) -> tuple[int, str]:
        self.seen.append(argv)
        joined = " ".join(argv)
        for fragment, answer in self.answers.items():
            if fragment in joined:
                return answer
        return 1, ""


# --- the interpreter and the operating system --------------------------------------------------


def test_the_os_and_interpreter_must_be_the_environment_of_record() -> None:
    assert cr.check_os("Windows").status == cr.OK
    assert cr.check_os("Linux").status == cr.FAIL
    probe = Probe({"platform.python_version": (0, EXPECTED)})
    assert by_id(cr.check_python(EXPECTED, EXPECTED, None, probe))["python"].status == cr.OK
    other = by_id(cr.check_python("3.13.15", EXPECTED, None, probe))["python"]
    assert other.status == cr.FAIL and EXPECTED in other.detail
    pinned = by_id(cr.check_python(EXPECTED, EXPECTED, "D:/py/python.exe", probe))
    assert pinned["python:pinned"].status == cr.OK
    wrong = Probe({"platform.python_version": (0, "3.13.15")})
    assert by_id(cr.check_python(EXPECTED, EXPECTED, "x", wrong))["python:pinned"].status == cr.FAIL
    dead = Probe({})
    assert by_id(cr.check_python(EXPECTED, EXPECTED, "x", dead))["python:pinned"].status == cr.FAIL


def test_the_expected_version_is_read_from_the_workflow(tmp_path: Path) -> None:
    assert cr.expected_python_from_workflow() == EXPECTED
    odd = tmp_path / "present.yml"
    odd.write_text('        env:\n          EXPECTED_PYTHON: "3.14.1"\n', encoding="utf-8")
    assert cr.expected_python_from_workflow(odd) == "3.14.1"
    assert cr.expected_python_from_workflow(tmp_path / "missing.yml") == cr.FALLBACK_PYTHON


# --- bash: Git for Windows, never the WSL launcher ---------------------------------------------


def test_bash_must_be_git_for_windows_bash_ahead_of_the_wsl_launcher() -> None:
    git_bash = "C:\\Program Files\\Git\\bin\\bash.exe"
    good = Probe({"--version": (0, "GNU bash, version 5.2"), "command -v cygpath": (0, "/usr/bin")})
    checks = by_id(cr.check_bash("Windows", good, lambda _: git_bash))
    assert checks["bash"].status == cr.OK and checks["cygpath"].status == cr.OK

    wsl = by_id(cr.check_bash("Windows", good, lambda _: "C:\\Windows\\System32\\bash.exe"))
    assert wsl["bash"].status == cr.FAIL and "WSL" in wsl["bash"].detail
    store = by_id(
        cr.check_bash(
            "Windows",
            good,
            lambda _: "C:\\Users\\x\\AppData\\Local\\Microsoft\\WindowsApps\\bash.exe",
        )
    )
    assert store["bash"].status == cr.FAIL
    assert by_id(cr.check_bash("Windows", good, lambda _: None))["bash"].status == cr.FAIL
    not_bash = Probe({"--version": (0, "something else")})
    assert by_id(cr.check_bash("Windows", not_bash, lambda _: git_bash))["bash"].status == cr.FAIL
    no_cygpath = Probe({"--version": (0, "GNU bash, version 5.2")})
    assert (
        by_id(cr.check_bash("Windows", no_cygpath, lambda _: git_bash))["cygpath"].status == cr.FAIL
    )
    assert by_id(cr.check_bash("Linux", good, lambda _: None))["bash"].status == cr.SKIP


def test_git_must_be_present_and_run() -> None:
    assert (
        cr.check_git(Probe({"--version": (0, "git version 2.55")}), lambda _: "git").status == cr.OK
    )
    assert cr.check_git(Probe({}), lambda _: "git").status == cr.FAIL
    assert cr.check_git(Probe({}), lambda _: None).status == cr.FAIL


# --- the toolchain registry, every tool, and the fingerprint of record -------------------------


def test_the_registry_must_resolve(tmp_path: Path) -> None:
    registry = tmp_path / "TOOLCHAIN_PATHS.txt"
    registry.write_text("cmake=x\n", encoding="utf-8")
    assert cr.check_registry(registry).status == cr.OK
    assert cr.check_registry(None).status == cr.FAIL
    assert cr.check_registry(tmp_path / "missing.txt").status == cr.FAIL
    assert str(tmp_path) not in cr.check_registry(registry).detail


def test_every_known_tool_must_resolve_except_maven() -> None:
    versions = {name: f"{name} 1.0" for name in toolchains.TOOLS}
    resolved: dict[str, str | None] = {name: f"/opt/{name}" for name in toolchains.TOOLS}
    assert {c.status for c in cr.check_tools(versions, resolved)} == {cr.OK}
    resolved["go"] = None
    resolved["mvn"] = None
    rows = by_id(cr.check_tools(versions, resolved))
    assert rows["tool:go"].status == cr.FAIL
    assert rows["tool:mvn"].status == cr.WARN  # no verifier invokes Maven
    assert set(rows) == {f"tool:{name}" for name in toolchains.TOOLS}
    # A version is printed; the path the tool was found at never is.
    assert "/opt/" not in " ".join(c.detail for c in rows.values())


def write_bundle(root: Path, slug: str, recorded: dict[str, str] | None) -> None:
    folder = root / "candidates" / slug
    revision = "a" * 40
    (folder / revision).mkdir(parents=True)
    (folder / "CURRENT").write_text(revision + "\n", encoding="utf-8")
    environment: dict[str, Any] = {"python_version": EXPECTED}
    if recorded is not None:
        environment["toolchains"] = recorded
    (folder / revision / "dependencies.json").write_text(
        json.dumps({"environment": environment}), encoding="utf-8"
    )


def test_the_fingerprint_is_compared_with_the_bundles_that_record_one(tmp_path: Path) -> None:
    machine = {"go": "go1.26", "node": "v24", "npm": "absent"}
    write_bundle(tmp_path, "a__same", dict(machine))
    write_bundle(tmp_path, "b__other", {**machine, "go": "go1.25"})
    write_bundle(tmp_path, "c__unrecorded", None)
    (tmp_path / "candidates" / "d__broken").mkdir()
    (tmp_path / "candidates" / "d__broken" / "CURRENT").write_text("bad\n", encoding="utf-8")
    recorded = cr.bundle_fingerprints(tmp_path)
    assert len(recorded) == 2
    verdict = cr.check_fingerprint(machine, recorded)
    assert verdict.status == cr.WARN
    assert "1 of 2" in verdict.detail and "go (1)" in verdict.detail
    assert cr.check_fingerprint(machine, [dict(machine)]).status == cr.OK
    assert cr.check_fingerprint(machine, []).status == cr.SKIP
    # A tool the machine lacks that a bundle recorded is a difference too.
    lacking = cr.check_fingerprint({"go": "go1.26"}, [dict(machine)])
    assert lacking.status == cr.WARN and "node" in lacking.detail


# --- disk -------------------------------------------------------------------------------------


def test_disk_needs_a_writable_local_folder_with_room(tmp_path: Path) -> None:
    assert cr.check_disk(tmp_path, 0.0).status == cr.OK
    assert cr.check_disk(tmp_path, 10**9).status == cr.FAIL
    assert cr.check_disk(None, 1.0).status == cr.SKIP
    assert cr.check_disk(tmp_path / "missing", 1.0).status == cr.FAIL
    onedrive = tmp_path / "OneDrive" / "Documents"
    onedrive.mkdir(parents=True)
    assert cr.check_disk(onedrive, 0.0).status == cr.FAIL
    assert str(tmp_path) not in cr.check_disk(tmp_path, 0.0).detail


# --- the runner's own .env and .path -----------------------------------------------------------


def runner_dir(tmp_path: Path, env: str, path: str | None = None) -> Path:
    directory = tmp_path / "runner"
    directory.mkdir()
    (directory / ".env").write_text(env, encoding="utf-8")
    if path is not None:
        (directory / ".path").write_text(path, encoding="utf-8")
    return directory


GOOD_PATH = "C:\\Program Files\\Git\\bin;C:\\Windows\\system32;C:\\Windows"


def test_a_credential_shaped_name_in_the_runner_env_fails_without_printing_its_value(
    tmp_path: Path,
) -> None:
    directory = runner_dir(
        tmp_path,
        f"RP_SEAL_PYTHON=D:\\Python313\\python.exe\nRP_TOOLCHAIN_REGISTRY=D:\\t.txt\n"
        f"GPT_OSS_API_KEY={SENTINEL_SECRET}\nGH_TOKEN={SENTINEL_SECRET}\n# a comment\n",
        GOOD_PATH,
    )
    rows = by_id(cr.check_runner_env(directory))
    assert rows["runner-env:secrets"].status == cr.FAIL
    assert "GPT_OSS_API_KEY" in rows["runner-env:secrets"].detail
    assert SENTINEL_SECRET not in json.dumps([vars(c) for c in rows.values()])


def test_the_runner_env_must_name_the_interpreter_and_the_registry(tmp_path: Path) -> None:
    ok = by_id(
        cr.check_runner_env(
            runner_dir(
                tmp_path, "RP_SEAL_PYTHON=a\nRP_TOOLCHAIN_REGISTRY=b\nPYTHONUTF8=1\n", GOOD_PATH
            )
        )
    )
    assert ok["runner-env"].status == cr.OK and ok["runner-env:secrets"].status == cr.OK
    assert ok["runner-path"].status == cr.OK
    bare = tmp_path / "bare"
    bare.mkdir()
    gaps = by_id(cr.check_runner_env(runner_dir(bare, "RP_SEAL_PYTHON=a\n", GOOD_PATH)))
    assert (
        gaps["runner-env"].status == cr.FAIL
        and "RP_TOOLCHAIN_REGISTRY" in gaps["runner-env"].detail
    )
    empty = tmp_path / "empty"
    empty.mkdir()
    assert cr.check_runner_env(empty)[0].status == cr.FAIL  # no .env at all
    assert cr.check_runner_env(None)[0].status == cr.SKIP


def test_the_runner_path_puts_git_for_windows_ahead_of_system32(tmp_path: Path) -> None:
    def verdict(text: str | None) -> cr.Check:
        target = tmp_path / ".path"
        if text is None:
            target.unlink(missing_ok=True)
        else:
            target.write_text(text, encoding="utf-8")
        return cr.check_runner_path(target)

    assert verdict(GOOD_PATH).status == cr.OK
    assert verdict("C:\\Windows\\System32;C:\\Program Files\\Git\\bin").status == cr.FAIL
    assert verdict("C:\\Windows\\System32;C:\\Windows").status == cr.FAIL  # no Git at all
    assert verdict(None).status == cr.WARN


# --- the account, the environment, the gateway -----------------------------------------------


def test_the_account_must_not_be_an_administrator() -> None:
    assert cr.check_account("Windows", lambda: False).status == cr.OK
    assert cr.check_account("Windows", lambda: True).status == cr.WARN
    assert cr.check_account("Linux", lambda: True).status == cr.SKIP


def test_credential_shaped_variables_are_named_never_valued() -> None:
    environment = {
        "GPT_OSS_API_KEY": SENTINEL_SECRET,
        "MY_PASSWORD": SENTINEL_SECRET,
        "ACTIONS_RUNTIME_TOKEN": SENTINEL_SECRET,  # the platform's own
        "GITHUB_TOKEN": SENTINEL_SECRET,
        "PATH": "x",
    }
    check = cr.check_environment(environment)
    assert check.status == cr.WARN
    assert "GPT_OSS_API_KEY" in check.detail and "MY_PASSWORD" in check.detail
    assert "ACTIONS_RUNTIME_TOKEN" not in check.detail and "GITHUB_TOKEN" not in check.detail
    assert SENTINEL_SECRET not in check.detail
    assert cr.check_environment({"PATH": "x"}).status == cr.OK


def test_the_gateway_check_sends_no_key_and_reports_only_the_host() -> None:
    seen: list[str] = []

    def answers(status: int) -> Any:
        def fetch(url: str) -> int:
            seen.append(url)
            return status

        return fetch

    endpoint = "https://gateway.example.test/v1"
    reachable = cr.check_gateway(endpoint, answers(401))
    assert reachable.status == cr.OK and "gateway.example.test" in reachable.detail
    assert "no key sent" in reachable.detail and "/v1" not in reachable.detail
    assert cr.check_gateway(endpoint, answers(200)).status == cr.OK
    assert cr.check_gateway(endpoint, answers(503)).status == cr.FAIL
    assert seen == [endpoint] * 3

    def down(url: str) -> int:
        raise ConnectionRefusedError(SENTINEL_SECRET)

    refused = cr.check_gateway(endpoint, down)
    assert refused.status == cr.FAIL and "ConnectionRefusedError" in refused.detail
    assert SENTINEL_SECRET not in refused.detail
    assert cr.check_gateway(None, answers(200)).status == cr.SKIP
    assert cr.check_gateway("not a url", answers(200)).status == cr.FAIL
    assert cr.check_gateway("ftp://host/v1", answers(200)).status == cr.FAIL


# --- the whole run ------------------------------------------------------------------------------


@pytest.fixture
def machine(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    """A machine whose resolver answers from a dict; the registry is a real file in tmp_path."""
    registry = tmp_path / "TOOLCHAIN_PATHS.txt"
    registry.write_text("cmake=x\n", encoding="utf-8")
    state: dict[str, Any] = {
        "versions": {name: f"{name} 1.0" for name in toolchains.TOOLS},
        "paths": {name: f"/opt/{name}" for name in toolchains.TOOLS},
    }
    monkeypatch.setattr(toolchains, "toolchain_fingerprint", lambda: state["versions"])
    monkeypatch.setattr(toolchains, "resolve_tool", lambda name: state["paths"].get(name))
    monkeypatch.setattr(toolchains, "registry_path", lambda: registry)
    monkeypatch.setattr(cr, "platform", stub_platform())
    state["registry"] = registry
    return state


def namespace(tmp_path: Path, **overrides: Any) -> argparse.Namespace:
    values: dict[str, Any] = {
        "job": False,
        "json": False,
        "no_network": True,
        "work_dir": tmp_path,
        "runner_dir": None,
        "min_free_gib": 0.0,
        "expected_python": EXPECTED,
        "endpoint": None,
        "root": tmp_path,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


GOOD_PROBE = Probe(
    {
        "--version": (0, "GNU bash, version 5.2"),
        "command -v cygpath": (0, "/usr/bin/cygpath"),
        "platform.python_version": (0, EXPECTED),
    }
)


def collect(
    tmp_path: Path, environment: dict[str, str] | None = None, **overrides: Any
) -> list[cr.Check]:
    return cr.collect(
        namespace(tmp_path, **overrides),
        environment or {},
        probe=GOOD_PROBE,
        fetch=lambda _: 401,
        system="Windows",
        is_admin=lambda: False,
        which=lambda name: "C:\\Program Files\\Git\\bin\\" + name + ".exe",
    )


def test_a_healthy_machine_has_no_failing_check(machine: dict[str, Any], tmp_path: Path) -> None:
    checks = collect(tmp_path)
    assert [c for c in checks if c.status == cr.FAIL] == []
    assert by_id(checks)["gateway"].status == cr.SKIP  # no network in this mode


@pytest.mark.parametrize(
    ("defect", "check_id"),
    [
        ("tool", "tool:cargo"),
        ("python", "python"),
        ("registry", "registry"),
    ],
)
def test_each_defect_fails_exactly_the_check_it_belongs_to(
    machine: dict[str, Any],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    defect: str,
    check_id: str,
) -> None:
    if defect == "tool":
        machine["paths"]["cargo"] = None
    elif defect == "python":
        monkeypatch.setattr(cr, "platform", stub_platform("3.13.15"))
    else:
        monkeypatch.setattr(toolchains, "registry_path", lambda: None)
    failed = [c.id for c in collect(tmp_path) if c.status == cr.FAIL]
    assert failed == [check_id]


def test_the_job_mode_derives_the_folders_from_the_runner_and_skips_the_network(
    machine: dict[str, Any], tmp_path: Path
) -> None:
    runner = tmp_path / "runner"
    temp = runner / "_work" / "_temp"
    temp.mkdir(parents=True)
    (runner / ".env").write_text("RP_SEAL_PYTHON=a\nRP_TOOLCHAIN_REGISTRY=b\n", encoding="utf-8")
    (runner / ".path").write_text(GOOD_PATH, encoding="utf-8")
    environment = {"RUNNER_TEMP": str(temp), "GPT_OSS_ENDPOINT": "https://gateway.example.test/v1"}
    checks = by_id(collect(tmp_path, environment, job=True, no_network=False, work_dir=None))
    assert checks["disk"].status == cr.OK
    assert checks["runner-env"].status == cr.OK and checks["runner-path"].status == cr.OK
    assert checks["gateway"].status == cr.SKIP  # --job never reaches the network
    # Without --job the endpoint in the environment is the one probed.
    probed = by_id(collect(tmp_path, environment, no_network=False))
    assert probed["gateway"].status == cr.OK and "gateway.example.test" in probed["gateway"].detail


def test_no_secret_path_or_host_detail_reaches_any_output(
    machine: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = runner_dir(
        tmp_path, f"RP_SEAL_PYTHON=a\nGPT_OSS_API_KEY={SENTINEL_SECRET}\n", GOOD_PATH
    )
    environment = {
        "GPT_OSS_API_KEY": SENTINEL_SECRET,
        "USERNAME": "someone",
        "COMPUTERNAME": "HOST42",
    }
    checks = collect(tmp_path, environment, runner_dir=runner)
    text = cr.render(checks) + json.dumps([vars(c) for c in checks])
    assert SENTINEL_SECRET not in text
    assert str(tmp_path) not in text and "/opt/" not in text
    assert "someone" not in text and "HOST42" not in text
    assert "FAIL: " in cr.render(checks)  # the .env holds a credential-shaped name


def test_main_exit_codes_and_json(
    machine: dict[str, Any], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = [
        "--no-network",
        "--work-dir",
        str(tmp_path),
        "--min-free-gib",
        "0",
        "--root",
        str(tmp_path),
    ]
    base += ["--expected-python", EXPECTED]
    code = cr.main([*base, "--json"], {})
    rows = json.loads(capsys.readouterr().out)
    assert {row["id"] for row in rows} >= {"os", "python", "bash", "registry", "disk", "gateway"}
    assert (code == 0) == all(row["status"] != cr.FAIL for row in rows)
    machine["paths"]["go"] = None
    assert cr.main(base, {}) == 1
    assert "tool:go" in capsys.readouterr().out.split("FAIL:")[-1]
    with pytest.raises(SystemExit) as usage:
        cr.main(["--no-such-flag"], {})
    assert usage.value.code == 2


# --- read-only by construction ------------------------------------------------------------------

WRITE_TOKENS = (
    "write_text(",
    "write_bytes(",
    ".mkdir(",
    "rmtree",
    "os.remove",
    "unlink(",
    "chmod(",
    "os.environ[",
    "putenv",
    "setx",
    "shutil.copy",
    "shutil.move",
    'mode="w',
    "open(",
    "urlretrieve",
    ".send(",
    "Authorization",
    "config.cmd",
    "sc.exe",
    "New-Service",
)


def write_shaped_tokens(source: str) -> list[str]:
    return [token for token in WRITE_TOKENS if token in source]


def test_the_tool_has_no_code_path_that_writes_installs_or_registers() -> None:
    source = (TOOL_DIR / "check_runner.py").read_text(encoding="utf-8")
    body = source.split('"""', 2)[2]  # everything after the module docstring, which may name them
    assert write_shaped_tokens(body) == []


def test_negative_control_the_token_scan_sees_a_write_shaped_snippet() -> None:
    assert write_shaped_tokens('Path("x").write_text("y")') == ["write_text("]
    assert "Authorization" in write_shaped_tokens("headers = {'Authorization': key}")
