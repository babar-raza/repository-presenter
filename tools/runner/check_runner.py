"""Self-hosted seal runner: a read-only check of the machine (owner decision D5).

Production sealing may run on the owner's Windows machine (docs/SELF_HOSTED_RUNNER.md): the
environment the sealed bundles were produced in. This script says whether this machine still is that
environment, before a job spends a provider call on it. It reads; it writes nothing, installs
nothing, registers nothing, and starts nothing but short, bounded version probes (the toolchains'
own `--version`, as `core/toolchains.py` already runs them, plus bash, git and the pinned
interpreter). It prints names, versions and verdicts, never a secret, never an environment dump,
never a path of the host, and sends no credential anywhere.

    python tools/runner/check_runner.py [--job] [--json] [--work-dir DIR] [--runner-dir DIR]
        [--min-free-gib N] [--expected-python X.Y.Z] [--endpoint URL] [--no-network] [--root DIR]

Checks (each OK, WARN, FAIL or SKIP):

    os, python        the operating system and the interpreter the bundles record (3.13.2 on Windows)
    bash, cygpath     Git for Windows' bash ahead of WSL's launcher: every workflow script is bash
    git               present
    registry          the toolchain registry (RP_TOOLCHAIN_REGISTRY) resolves
    tool:<name>       every tool a verifier invokes resolves through core/toolchains.py (mvn is
                      optional: no verifier invokes Maven)
    fingerprint       this machine's toolchain fingerprint against the sealed bundles that record one
    disk              free space and write access on the work directory's drive
    runner-env        the runner's own .env names the interpreter and the registry and holds no
                      credential-shaped name; its .path puts Git for Windows ahead of System32
    account           the account is not an administrator
    environment       no credential-shaped variable is set in this process
    gateway           the gateway answers over TLS; no key is sent (the workflow's own preflight step
                      is the authenticated check)

`--job` is the mode the workflow runs (present.yml, self-hosted only): no network, and the work
directory and runner directory come from the runner's own variables. Exit 0: no check failed.
Exit 1: at least one check failed. Exit 2: the command line was wrong.

Standard library plus `repository_presenter.core.toolchains` (the project's one resolver).
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "present.yml"

try:
    from repository_presenter.core import toolchains
except ImportError:  # run from a checkout without the package installed
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from repository_presenter.core import toolchains

OK, WARN, FAIL, SKIP = "OK", "WARN", "FAIL", "SKIP"
FALLBACK_PYTHON = "3.13.2"  # what the sealed bundles record; present.yml's EXPECTED_PYTHON agrees
EXPECTED_OS = "Windows"
OPTIONAL_TOOLS = frozenset({"mvn"})  # no verifier invokes Maven (present.yml)
DEFAULT_MIN_FREE_GIB = 40.0
REQUIRED_RUNNER_ENV = ("RP_SEAL_PYTHON", "RP_TOOLCHAIN_REGISTRY")
GATEWAY_ENDPOINT_VARIABLE = "GPT_OSS_ENDPOINT"
# The same shape core/execution.py strips from an example's environment.
SECRET_NAME = re.compile(
    r"(?:TOKEN|SECRET|PASSWORD|PASSWD|PRIVATE_KEY|API_KEY|CREDENTIAL)", re.IGNORECASE
)
# Variables a runner and GitHub set themselves; they are not a credential someone put on the host.
PLATFORM_NAME = re.compile(r"^(?:ACTIONS_|GITHUB_|RUNNER_)")
WSL_LAUNCHERS = ("\\windows\\system32\\", "\\windowsapps\\")

Fetch = Callable[[str], int]
Run = Callable[[list[str]], tuple[int, str]]


@dataclass
class Check:
    id: str
    status: str
    detail: str = ""


def run_command(argv: list[str]) -> tuple[int, str]:
    """(exit code, first line of output) of a short, bounded, read-only command."""
    try:
        done = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    lines = [line.strip() for line in (done.stdout + "\n" + done.stderr).splitlines() if line.strip()]
    return done.returncode, (lines[0][:120] if lines else "")


def expected_python_from_workflow(path: Path = WORKFLOW) -> str:
    """The interpreter version present.yml pins (its EXPECTED_PYTHON literal), else the fallback."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return FALLBACK_PYTHON
    found = re.search(r"^\s*EXPECTED_PYTHON:\s*\"?(\d+\.\d+\.\d+)\"?\s*$", text, re.MULTILINE)
    return found.group(1) if found else FALLBACK_PYTHON


# --- the checks -------------------------------------------------------------------------------


def check_os(system: str, expected: str = EXPECTED_OS) -> Check:
    if system == expected:
        return Check("os", OK, system)
    return Check("os", FAIL, f"{system}; the sealed bundles record {expected}")


def check_python(running: str, expected: str, pinned: str | None, probe: Run) -> list[Check]:
    checks = [
        Check("python", OK, running)
        if running == expected
        else Check("python", FAIL, f"{running}; the sealed bundles record {expected}")
    ]
    if pinned:
        code, line = probe([pinned, "-c", "import platform; print(platform.python_version())"])
        if code != 0 or not line:
            checks.append(Check("python:pinned", FAIL, "RP_SEAL_PYTHON does not run"))
        elif line != expected:
            checks.append(Check("python:pinned", FAIL, f"RP_SEAL_PYTHON is {line}, not {expected}"))
        else:
            checks.append(Check("python:pinned", OK, line))
    return checks


def check_bash(system: str, probe: Run, which: Callable[[str], str | None]) -> list[Check]:
    if system != "Windows":
        return [Check("bash", SKIP, "not Windows; the workflow shell is the platform's bash")]
    found = which("bash")
    if not found:
        return [Check("bash", FAIL, "no bash on PATH; install Git for Windows")]
    lowered = found.lower().replace("/", "\\")
    if any(marker in lowered for marker in WSL_LAUNCHERS):
        return [
            Check(
                "bash",
                FAIL,
                "bash resolves to the WSL launcher; put Git for Windows' bin ahead of System32 "
                "in the runner's .path (docs/SELF_HOSTED_RUNNER.md section 3)",
            )
        ]
    code, line = probe([found, "--version"])
    if code != 0 or "GNU bash" not in line:
        return [Check("bash", FAIL, "bash on PATH is not GNU bash")]
    checks = [Check("bash", OK, line)]
    code, _ = probe([found, "-c", "command -v cygpath"])
    checks.append(
        Check("cygpath", OK, "available to bash")
        if code == 0
        else Check("cygpath", FAIL, "bash cannot find cygpath; the workflow's path steps need it")
    )
    return checks


def check_git(probe: Run, which: Callable[[str], str | None]) -> Check:
    found = which("git")
    if not found:
        return Check("git", FAIL, "no git on PATH")
    code, line = probe([found, "--version"])
    return Check("git", OK, line) if code == 0 else Check("git", FAIL, "git does not run")


def check_registry(registry: Path | None) -> Check:
    if registry is None:
        return Check(
            "registry",
            FAIL,
            f"no toolchain registry: set {toolchains.REGISTRY_VARIABLE} in the runner's .env",
        )
    if not registry.is_file():
        return Check("registry", FAIL, f"{toolchains.REGISTRY_VARIABLE} names a missing file")
    return Check("registry", OK, "resolves")


def check_tools(fingerprint: Mapping[str, str], resolved: Mapping[str, str | None]) -> list[Check]:
    """One row per known tool: its version when it resolves, else FAIL (WARN when optional)."""
    checks = []
    for name in sorted(toolchains.TOOLS):
        if resolved.get(name):
            checks.append(Check(f"tool:{name}", OK, fingerprint.get(name, toolchains.UNVERSIONED)))
        else:
            status = WARN if name in OPTIONAL_TOOLS else FAIL
            checks.append(Check(f"tool:{name}", status, "not resolved (core/toolchains.py)"))
    return checks


def bundle_fingerprints(root: Path) -> list[dict[str, str]]:
    """The toolchain fingerprint each current sealed bundle under ``root/candidates`` records."""
    found: list[dict[str, str]] = []
    for current in sorted((root / "candidates").glob("*/CURRENT")):
        try:
            revision = current.read_text(encoding="utf-8").strip()
            payload = json.loads(
                (current.parent / revision / "dependencies.json").read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            continue
        recorded = (payload.get("environment") or {}).get("toolchains")
        if isinstance(recorded, dict) and recorded:
            found.append({str(k): str(v) for k, v in recorded.items()})
    return found


def check_fingerprint(fingerprint: Mapping[str, str], recorded: list[dict[str, str]]) -> Check:
    if not recorded:
        return Check("fingerprint", SKIP, "no sealed bundle records a toolchain fingerprint")
    differing: dict[str, int] = {}
    matching = 0
    for bundle in recorded:
        tools = sorted(
            name for name in set(bundle) | set(fingerprint) if bundle.get(name) != fingerprint.get(name)
        )
        if not tools:
            matching += 1
        for name in tools:
            differing[name] = differing.get(name, 0) + 1
    if not differing:
        return Check("fingerprint", OK, f"identical to all {len(recorded)} recording bundle(s)")
    names = ", ".join(f"{name} ({count})" for name, count in sorted(differing.items()))
    return Check(
        "fingerprint",
        WARN,
        f"{matching} of {len(recorded)} recording bundle(s) match; a difference reopens "
        f"EXTRACTING for that candidate: {names}",
    )


def check_disk(work_dir: Path | None, minimum_gib: float) -> Check:
    if work_dir is None:
        return Check("disk", SKIP, "no work directory given (--work-dir)")
    try:
        free_gib = shutil.disk_usage(work_dir).free / 2**30
    except OSError:
        return Check("disk", FAIL, "the work directory cannot be read")
    if "onedrive" in str(work_dir).lower():
        return Check("disk", FAIL, "the work directory is under OneDrive; use a local folder")
    if not os.access(work_dir, os.W_OK):
        return Check("disk", FAIL, "the work directory is not writable by this account")
    if free_gib < minimum_gib:
        return Check("disk", FAIL, f"{free_gib:.0f} GiB free, minimum {minimum_gib:.0f}")
    return Check("disk", OK, f"{free_gib:.0f} GiB free (minimum {minimum_gib:.0f})")


def parse_env_file(text: str) -> dict[str, str]:
    """NAME=value lines of a runner .env file (comments and blank lines ignored)."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        values[name.strip()] = value.strip()
    return values


def check_runner_env(runner_dir: Path | None) -> list[Check]:
    if runner_dir is None:
        return [Check("runner-env", SKIP, "no runner directory given (--runner-dir)")]
    checks = []
    try:
        values = parse_env_file((runner_dir / ".env").read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return [Check("runner-env", FAIL, "the runner has no .env file")]
    secret_names = sorted(name for name in values if SECRET_NAME.search(name))
    if secret_names:
        checks.append(
            Check(
                "runner-env:secrets",
                FAIL,
                "credential-shaped names in the runner's .env (a secret never lives on disk): "
                + ", ".join(secret_names),
            )
        )
    else:
        checks.append(Check("runner-env:secrets", OK, "no credential-shaped name"))
    missing = [name for name in REQUIRED_RUNNER_ENV if not values.get(name)]
    checks.append(
        Check("runner-env", FAIL, f"the runner's .env lacks: {', '.join(missing)}")
        if missing
        else Check("runner-env", OK, ", ".join(REQUIRED_RUNNER_ENV) + " named")
    )
    checks.append(check_runner_path(runner_dir / ".path"))
    return checks


def check_runner_path(path_file: Path) -> Check:
    """The runner's .path puts Git for Windows' bash ahead of System32 (where WSL's launcher is)."""
    try:
        entries = [e.strip().lower().rstrip("\\") for e in path_file.read_text(encoding="utf-8").split(";")]
    except OSError:
        return Check("runner-path", WARN, "the runner has no .path file; it takes the service PATH")
    git = [i for i, e in enumerate(entries) if e.endswith("\\git\\bin") or e.endswith("\\git\\cmd")]
    system32 = [i for i, e in enumerate(entries) if e.endswith("\\windows\\system32")]
    if not git:
        return Check("runner-path", FAIL, "the runner's .path has no Git for Windows entry")
    if system32 and min(system32) < min(git):
        return Check("runner-path", FAIL, "System32 precedes Git for Windows in the runner's .path")
    return Check("runner-path", OK, "Git for Windows precedes System32")


def check_account(system: str, is_admin: Callable[[], bool]) -> Check:
    if system != "Windows":
        return Check("account", SKIP, "not Windows")
    return (
        Check("account", WARN, "this account is an administrator; the runner must not be")
        if is_admin()
        else Check("account", OK, "standard user")
    )


def windows_is_admin() -> bool:
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return False


def check_environment(environment: Mapping[str, str]) -> Check:
    names = sorted(
        name for name in environment if SECRET_NAME.search(name) and not PLATFORM_NAME.match(name)
    )
    if names:
        return Check(
            "environment",
            WARN,
            "credential-shaped variables are set in this process (the gateway key is a "
            "repository secret and never on the host): " + ", ".join(names),
        )
    return Check("environment", OK, "no credential-shaped variable")


def https_status(url: str) -> int:
    """The HTTP status of an unauthenticated GET of ``url``; raises on a transport failure."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    context = ssl.create_default_context()
    connection: http.client.HTTPConnection
    if parts.scheme == "https":
        connection = http.client.HTTPSConnection(host, parts.port, timeout=15, context=context)
    else:
        connection = http.client.HTTPConnection(host, parts.port, timeout=15)
    try:
        connection.request("GET", (parts.path or "/").rstrip("/") + "/models", headers={"Accept": "*/*"})
        return connection.getresponse().status
    finally:
        connection.close()


def check_gateway(endpoint: str | None, fetch: Fetch = https_status) -> Check:
    """Reachability only: DNS, TCP, TLS and an HTTP answer. No key is sent or read."""
    if not endpoint:
        return Check(
            "gateway",
            SKIP,
            f"{GATEWAY_ENDPOINT_VARIABLE} is not set here (it is a repository secret; "
            "the workflow's preflight step reaches the gateway with it)",
        )
    parts = urlsplit(endpoint)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return Check("gateway", FAIL, "the endpoint is not an absolute http(s) URL")
    try:
        status = fetch(endpoint)
    except (OSError, ssl.SSLError, http.client.HTTPException) as error:
        return Check("gateway", FAIL, f"{parts.hostname} unreachable: {type(error).__name__}")
    if status >= 500:
        return Check("gateway", FAIL, f"{parts.hostname} answered HTTP {status}")
    return Check("gateway", OK, f"{parts.hostname} answers (HTTP {status}; no key sent)")


# --- the run ----------------------------------------------------------------------------------


def collect(
    args: argparse.Namespace,
    environment: Mapping[str, str],
    *,
    probe: Run = run_command,
    fetch: Fetch = https_status,
    system: str | None = None,
    is_admin: Callable[[], bool] = windows_is_admin,
    which: Callable[[str], str | None] = shutil.which,
) -> list[Check]:
    system = system or platform.system()
    expected = args.expected_python or expected_python_from_workflow()
    pinned = (environment.get("RP_SEAL_PYTHON") or "").strip() or None
    work_dir = args.work_dir
    runner_dir = args.runner_dir
    if args.job:
        temp = (environment.get("RUNNER_TEMP") or "").strip()
        if temp:
            work_dir = work_dir or Path(temp)
            runner_dir = runner_dir or Path(temp).parents[1]
    fingerprint = toolchains.toolchain_fingerprint()
    resolved = {name: toolchains.resolve_tool(name) for name in toolchains.TOOLS}
    checks = [
        check_os(system),
        *check_python(platform.python_version(), expected, pinned, probe),
        *check_bash(system, probe, which),
        check_git(probe, which),
        check_registry(toolchains.registry_path()),
        *check_tools(fingerprint, resolved),
        check_fingerprint(fingerprint, bundle_fingerprints(args.root)),
        check_disk(work_dir, args.min_free_gib),
        *check_runner_env(runner_dir),
        check_account(system, is_admin),
        check_environment(environment),
    ]
    if args.job or args.no_network:
        checks.append(Check("gateway", SKIP, "no network in this mode"))
    else:
        endpoint = args.endpoint or (environment.get(GATEWAY_ENDPOINT_VARIABLE) or "").strip()
        checks.append(check_gateway(endpoint or None, fetch))
    return checks


def render(checks: list[Check]) -> str:
    width = max(len(c.id) for c in checks)
    lines = ["Self-hosted seal runner check (read-only; no value, path or secret is printed)", ""]
    lines += [f"{c.status:<5} {c.id:<{width}}  {c.detail}".rstrip() for c in checks]
    failed = [c.id for c in checks if c.status == FAIL]
    lines += ["", "FAIL: " + ", ".join(failed) if failed else "no check failed"]
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--job", action="store_true", help="the workflow's mode: no network")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--runner-dir", type=Path)
    parser.add_argument("--min-free-gib", type=float, default=DEFAULT_MIN_FREE_GIB)
    parser.add_argument("--expected-python")
    parser.add_argument("--endpoint")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, environment: Mapping[str, str] | None = None) -> int:
    args = parse_args(argv)
    checks = collect(args, os.environ if environment is None else environment)
    if args.json:
        print(json.dumps([asdict(c) for c in checks], indent=2))
    else:
        sys.stdout.write(render(checks))
    return 1 if any(c.status == FAIL for c in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
