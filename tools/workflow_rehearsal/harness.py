"""Run this repository's GitHub workflows locally, in their hosted shape (TC-REF-10-02).

What it does, in order, for ``run``:

1. Builds a *world* (``scenarios.py``): local bare repositories standing in for the upstreams.
2. Generates throwaway TLS material and a FAKE GitHub App private key with ``openssl`` inside the
   runner image (nothing real; nothing leaves ``--work``).
3. Starts a Docker network and one sidecar container running ``fake_github.py`` under the DNS
   names ``api.github.com`` and ``git.rehearsal.local``: the workflow's own REST calls and its git
   clones land on local fakes. Pull requests and issues are recorded, never created anywhere.
4. Clones this checkout into a scratch directory (act cannot run a git worktree's gitfile), applies
   the scenario's fixture registry, and runs the *unmodified* workflow with ``act`` in the same
   image family GitHub's ``ubuntu-latest`` is mapped to, on that network, with the CA trusted and
   ``github.com`` rewritten to the local git host.
5. Writes ``result.json`` (outcome, image, python, duration, request and write counts) and scans
   every output for the fake secret values (a leak would be a harness defect).

Hosted-only things that remain real reads: ``actions/*`` are fetched by ``act`` from GitHub, and
``setup-python`` and ``pip`` fetch Python and the locked packages. No write ever leaves the machine.

Usage: ``python tools/workflow_rehearsal/harness.py {dryrun,run,down} ...`` (see ``--help``).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import scenarios
from inventory import REPO_ROOT, WORKFLOWS_DIR

HERE = Path(__file__).resolve().parent
IMAGE = "catthehacker/ubuntu:act-24.04"
NETWORK = "rp-rehearsal"
SIDECAR = "rp-rehearsal-fake"
GIT_HOST = "git.rehearsal.local"
FAKE_APP_ID = "123456"  # a fake id; the matching key is generated per run
SECRET_PATTERNS = (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"ghs_[A-Za-z0-9]{20,}", r"ghp_[A-Za-z0-9]{20,}")

# What each workflow needs and what the local run can honestly cover (TC-REF-10-02/03). ``event`` is
# the trigger the rehearsal uses. ``mode`` is ``full`` (all jobs run in a container against the
# fakes), ``dryrun`` (act validates and plans the job graph only) or ``replay`` (a hosted-only step
# is replayed by script). ``gap`` states what a local run cannot prove.
WORKFLOW_PLAN: dict[str, dict[str, str]] = {
    "monitor.yml": {
        "event": "schedule",
        "mode": "full",
        "gap": "App-token mint runs against the fake REST service (key and token are fake); the real "
        "mint's server-side permission narrowing is hosted-only; the gateway preflight runs on dispatch only.",
    },
    "ci.yml": {
        "event": "pull_request",
        "mode": "full",
        "gap": "ran under act on 2026-10-04 (DECISION_LOG); not re-run in this slice (three full pytest "
        "legs); runs on python 3.11/3.12/3.13 matrix, hosted image carries toolchains the act image lacks.",
    },
    "sealing-scheduled.yml": {
        "event": "schedule",
        "mode": "dryrun",
        "gap": "plan job downloads the latest monitor run's artifacts with `gh run list/download` (the "
        "Actions API and artifact store are hosted-only services); replayed by feeding monitor's output "
        "to `sealing-plan`. seal/publish/propose call the other workflows (below).",
    },
    "present.yml": {
        "event": "workflow_dispatch",
        "mode": "dryrun",
        "gap": "needs the live LLM gateway (GPT_OSS_*), the repository's toolchains, a read-only App token "
        "scoped to the target and the state-ref token; precedent: act run of 2026-10-04 reached the mint "
        "step and failed closed.",
    },
    "candidates-publish.yml": {
        "event": "workflow_dispatch",
        "mode": "dryrun",
        "gap": "write job mints a write-scoped App token and opens a PR on the control repository: the "
        "fake REST records the PR, but GitHub's own checks, required reviews and branch protection are hosted-only.",
    },
    "propose.yml": {
        "event": "workflow_dispatch",
        "mode": "dryrun",
        "gap": "dry-run job is replayable; write job needs an authorization record merged to main before "
        "the trigger commit and the target's live revision; the fake REST records the PR.",
    },
    "propose-sandbox.yml": {
        "event": "workflow_dispatch",
        "mode": "dryrun",
        "gap": "the sandbox canary: dry-run job is replayable; the write job waits on the "
        "sandbox-canary environment (hosted-only), needs the committed correction bundle and a record "
        "merged to main before the trigger commit, and the App installed on the sandbox repository.",
    },
    "issues-scheduled.yml": {
        "event": "schedule",
        "mode": "dryrun",
        "gap": "analysis reads the upstream through the REST API (fakeable); filing needs an approved "
        "ops/issue_approvals record and the kill-switch variable; GitHub issue semantics are hosted-only.",
    },
    "liveness.yml": {
        "event": "schedule",
        "mode": "dryrun",
        "gap": "reads the Actions run history and pull requests through the hosted API (hosted-only service).",
    },
    "audit-app-installations.yml": {
        "event": "workflow_dispatch",
        "mode": "dryrun",
        "gap": "asks GitHub which organizations installed the App: a hosted-only fact.",
    },
    "verify-app-installation.yml": {
        "event": "workflow_dispatch",
        "mode": "dryrun",
        "gap": "asks GitHub about the live installation: a hosted-only fact.",
    },
    "mirror-gitlab.yml": {
        "event": "workflow_dispatch",
        "mode": "dryrun",
        "gap": "pushes to GitLab with GITLAB_TOKEN: an outbound write, never run locally.",
    },
}


def find_act() -> str:
    explicit = os.environ.get("ACT")
    candidates = [explicit, shutil.which("act"), "C:/dev-tools/act/act.exe", "D:/tools/act/act.exe"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise SystemExit("act not found (set ACT, or put act on PATH)")


def docker(*args: str, check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=check, timeout=timeout)


def _mount(path: Path, target: str, mode: str = "rw") -> list[str]:
    return ["-v", f"{path}:{target}:{mode}"]


def prepare_tls(work: Path) -> dict[str, Path]:
    """Throwaway CA, server certificate, CA bundle and a FAKE App private key, made in the image."""
    tls = work / "tls"
    tls.mkdir(parents=True, exist_ok=True)
    (tls / "san.cnf").write_text(
        "subjectAltName=DNS:api.github.com,DNS:" + GIT_HOST + "\nbasicConstraints=CA:FALSE\n",
        encoding="utf-8", newline="\n",
    )
    script = (
        "set -e; cd /tls; "
        "openssl req -x509 -newkey rsa:2048 -nodes -keyout ca.key -out ca.pem -days 3 -subj /CN=rehearsal-ca 2>/dev/null; "
        "openssl req -newkey rsa:2048 -nodes -keyout server.key -out server.csr -subj /CN=api.github.com 2>/dev/null; "
        "openssl x509 -req -in server.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out server.pem -days 3 -extfile san.cnf 2>/dev/null; "
        "cat server.pem ca.pem > server-chain.pem; "
        "cat /etc/ssl/certs/ca-certificates.crt ca.pem > bundle.pem; "
        "openssl genrsa -out app-key.pem 2048 2>/dev/null; chmod 644 *.key *.pem"
    )
    docker("run", "--rm", *_mount(tls, "/tls"), IMAGE, "bash", "-c", script)
    return {name: tls / name for name in ("ca.pem", "server.pem", "server-chain.pem", "server.key", "bundle.pem", "app-key.pem")}


def write_support_files(work: Path) -> None:
    """The container-side git configuration: github.com is rewritten to the local git host."""
    (work / "gitconfig").write_text(
        f'[url "https://{GIT_HOST}/"]\n\tinsteadOf = https://github.com/\n[safe]\n\tdirectory = *\n',
        encoding="utf-8", newline="\n",
    )


def start_services(work: Path, world: Path) -> None:
    stop_services()
    if docker("network", "inspect", NETWORK, check=False).returncode != 0:
        docker("network", "create", NETWORK)
    docker(
        "run", "-d", "--name", SIDECAR, "--network", NETWORK,
        "--network-alias", "api.github.com", "--network-alias", GIT_HOST,
        *_mount(HERE, "/rehearsal/tools", "ro"), *_mount(world, "/world"), *_mount(work / "tls", "/tls", "ro"),
        IMAGE, "python3", "/rehearsal/tools/fake_github.py", "--world", "/world",
        "--cert", "/tls/server-chain.pem", "--key", "/tls/server.key", "--port", "443",
    )
    time.sleep(2)
    probe = docker("run", "--rm", "--network", NETWORK, *_mount(work / "tls", "/tls", "ro"), IMAGE,
                   "bash", "-c", "curl -s --cacert /tls/ca.pem https://api.github.com/repos/x/y/installation", check=False)
    if '"id"' not in probe.stdout:
        raise SystemExit(f"fake github did not come up: {probe.stdout!r} {probe.stderr!r}")


def stop_services() -> None:
    """Remove only this harness's own sidecar and network."""
    if docker("container", "inspect", SIDECAR, check=False).returncode == 0:
        docker("stop", SIDECAR, check=False)
        docker("rm", SIDECAR, check=False)
    leftovers = docker("ps", "-a", "-q", "--filter", f"network={NETWORK}", check=False).stdout.split()
    if leftovers:  # act leaves a failed job's container behind; it is this harness's own
        docker("rm", "-f", *leftovers, check=False)
    docker("network", "rm", NETWORK, check=False)


def _make_writable_and_retry(function: Any, path: str, _info: Any) -> None:
    """``rmtree`` handler: git object files are read-only on Windows."""
    os.chmod(path, 0o700)
    function(path)


def prepare_checkout(work: Path, registry_entries: list[str] | None) -> Path:
    """A scratch clone of this checkout's HEAD; a fixture registry replaces data/registry.json."""
    dest = work / "src"
    if dest.exists():
        shutil.rmtree(dest, onerror=_make_writable_and_retry)
    subprocess.run(["git", "clone", "-q", "--no-hardlinks", "-c", "core.longpaths=true", str(REPO_ROOT), str(dest)], check=True)
    if registry_entries is not None:
        path = dest / "data" / "registry.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        document["entries"] = [e for e in document["entries"] if e["repository"] in registry_entries]
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")
    return dest


MONITOR_SCENARIOS = {
    "clean": "two registry repositories: one unchanged since its seal, one whose head moved",
    "mixed": "clean plus a registry repository that no longer exists upstream (its owner's leg goes red)",
}


def monitor_world(world: Path, checkout: Path, scenario: str) -> dict[str, Any]:
    """The monitor rehearsal's world: registry repositories in different upstream states."""
    unchanged = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    moved = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
    gone = "aspose-cells-foss/Aspose.Cells-FOSS-for-Go"
    current = (checkout / "candidates" / unchanged.replace("/", "__") / "CURRENT").read_text(encoding="utf-8").strip()
    # The moved upstream is a real local bare repository with a synthetic history.
    owner, name = moved.split("/")
    history = [
        ("initial", scenarios.BASE_FILES),
        ("change", {"src/synthetic/__init__.py": "x = 1\n"}),
    ]
    scenarios.build_repository(world, name, history, owner=owner)
    meta = {"archived": [], "deleted": [gone] if scenario == "mixed" else [], "heads": {unchanged: current}, "failures": {}}
    (world / "world.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8", newline="\n")
    names = {"unchanged": unchanged, "moved": moved}
    return {**names, "deleted": gone} if scenario == "mixed" else names


def secrets_file(work: Path, tls: dict[str, Path]) -> Path:
    key = tls["app-key.pem"].read_text(encoding="utf-8").strip().replace("\n", "\\n")
    path = work / "secrets.env"
    path.write_text(
        f'GH_APP_ID={FAKE_APP_ID}\nGH_APP_PRIVATE_KEY="{key}"\n'
        "GPT_OSS_ENDPOINT=https://gateway.invalid/v1\nGPT_OSS_API_KEY=FAKE_REHEARSAL_GATEWAY_KEY\n",
        encoding="utf-8", newline="\n",
    )
    return path


def act_command(act: str, workflow: str, event: str, checkout: Path, work: Path, *, network: bool, extra: list[str]) -> list[str]:
    command = [
        act, event, "-W", f".github/workflows/{workflow}", "-e", str(work / "event.json"),
        "-P", f"ubuntu-latest={IMAGE}", "--pull=false", "--container-architecture", "linux/amd64",
        "--concurrent-jobs", "1", "--artifact-server-path", str(work / "artifacts"),
        "--secret-file", str(work / "secrets.env"),
    ]
    if network:
        env = {
            "SSL_CERT_FILE": "/rehearsal/tls/bundle.pem",
            "REQUESTS_CA_BUNDLE": "/rehearsal/tls/bundle.pem",
            "NODE_EXTRA_CA_CERTS": "/rehearsal/tls/ca.pem",
            "GIT_SSL_CAINFO": "/rehearsal/tls/bundle.pem",
            "GIT_CONFIG_GLOBAL": "/rehearsal/gitconfig",
        }
        for key, value in env.items():
            command += ["--env", f"{key}={value}"]
        command += ["--network", NETWORK, "--container-options", " ".join(
            [f"-v {work.as_posix()}/tls:/rehearsal/tls:ro",
             f"-v {work.as_posix()}/gitconfig:/rehearsal/gitconfig:ro"])]
    return [*command, *extra]


def scan_for_secrets(paths: list[Path], literals: list[str]) -> list[str]:
    """Names of files that contain a fake secret value or a credential-shaped string."""
    hits = []
    for root in paths:
        for path in ([root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())):
            if path.name in ("secrets.env", "app-key.pem", "ca.key", "server.key"):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(lit and lit in text for lit in literals) or any(re.search(p, text) for p in SECRET_PATTERNS):
                hits.append(str(path))
    return hits


def summarize_act_log(log: str) -> dict[str, Any]:
    jobs = re.findall(r"Job (succeeded|failed)", log)
    return {
        "jobs_succeeded": jobs.count("succeeded"),
        "jobs_failed": jobs.count("failed"),
        "python_versions": sorted(set(re.findall(r"CPython \((3\.\d+\.\d+)\)", log))),
    }


def cmd_dryrun(args: argparse.Namespace) -> int:
    """``act -n`` over the workflows: parses each, resolves reusable calls and plans the job graph."""
    act = find_act()
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    event_file = work / "event-dry.json"
    event_file.write_text(json.dumps({"inputs": {"repository": "o/r", "repo": "o/r"}}), encoding="utf-8")
    out = []
    for workflow, plan in sorted(WORKFLOW_PLAN.items()):
        if args.only and workflow not in args.only:
            continue
        started = time.time()
        command = [act, plan["event"], "-n", "-W", f".github/workflows/{workflow}", "-e", str(event_file),
                   "-P", f"ubuntu-latest={IMAGE}", "--container-architecture", "linux/amd64"]
        try:
            result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False,
                                    timeout=args.per_workflow_timeout)
            exit_code, text = result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired as exc:
            exit_code, text = 124, str(exc.stdout or "") + str(exc.stderr or "")
        out.append({"workflow": workflow, "event": plan["event"], "exit": exit_code,
                    "seconds": round(time.time() - started, 1),
                    "jobs_planned": len(re.findall(r"Job (?:succeeded|failed)", text)),
                    "tail": text.strip().splitlines()[-1:]})
    print(json.dumps(out, indent=2))
    return 0 if all(row["exit"] == 0 for row in out) else 1


def cmd_run_monitor(args: argparse.Namespace) -> int:
    work = Path(args.work or REPO_ROOT / "runs" / "rehearsal" / f"monitor-{args.scenario}").resolve()
    work.mkdir(parents=True, exist_ok=True)
    world = work / "world"
    if world.exists():
        shutil.rmtree(world, onerror=_make_writable_and_retry)
    world.mkdir()
    started = time.time()
    tls = prepare_tls(work)
    write_support_files(work)
    entries = ["aspose-3d-foss/Aspose.3D-FOSS-for-Python", "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"]
    if args.scenario == "mixed":
        entries.append("aspose-cells-foss/Aspose.Cells-FOSS-for-Go")
    checkout = prepare_checkout(work, entries)
    names = monitor_world(world, checkout, args.scenario)
    secrets_file(work, tls)
    (work / "event.json").write_text(json.dumps({"schedule": "17 */6 * * *"}), encoding="utf-8")
    (work / "artifacts").mkdir(exist_ok=True)
    start_services(work, world)
    try:
        command = act_command(find_act(), "monitor.yml", "schedule", checkout, work, network=True, extra=[])
        log_path = work / "monitor.act.log"
        with log_path.open("w", encoding="utf-8") as log:
            result = subprocess.run(command, cwd=checkout, stdout=log, stderr=subprocess.STDOUT, text=True, check=False, timeout=args.timeout)
    finally:
        stop_services()
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    requests = [json.loads(line) for line in (world / "requests.jsonl").read_text(encoding="utf-8").splitlines()] if (world / "requests.jsonl").is_file() else []
    writes = (world / "writes.jsonl").read_text(encoding="utf-8").splitlines() if (world / "writes.jsonl").is_file() else []
    leaks = scan_for_secrets([work / "monitor.act.log", work / "artifacts", world], ["FAKE_REHEARSAL_GATEWAY_KEY"])
    summary = {
        "workflow": "monitor.yml", "event": "schedule", "image": IMAGE, "act_exit": result.returncode,
        "seconds": round(time.time() - started), **summarize_act_log(log_text),
        "scenario": {"name": args.scenario, **names}, "fake_requests": len(requests),
        "fake_requests_by_kind": {k: sum(1 for r in requests if r["kind"] == k) for k in ("rest", "git")},
        "fake_writes_recorded": len(writes), "secret_leaks": leaks,
        "act": subprocess.run([find_act(), "--version"], capture_output=True, text=True, check=False).stdout.strip(),
    }
    (work / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))
    return 0 if result.returncode == 0 and not leaks else 1


def cmd_replay_plan(args: argparse.Namespace) -> int:
    """Replay the hosted-only hand-off of ``sealing-scheduled.yml``'s ``plan`` job.

    On GitHub the plan job downloads the latest successful monitor run's ``drift-*`` artifacts with
    ``gh run download`` (the Actions API is a hosted-only service). Here the artifacts are the ones
    act's local artifact server kept from the monitor rehearsal; the two CLI steps that follow
    (``monitor-drift-contract`` then ``sealing-plan``) run exactly as the workflow runs them.
    """
    import zipfile

    work = Path(args.work or REPO_ROOT / "runs" / "rehearsal" / "monitor-clean").resolve()
    checkout = work / "src"
    evidence = work / "replay" / "monitor"
    if evidence.exists():
        shutil.rmtree(evidence, onerror=_make_writable_and_retry)
    evidence.mkdir(parents=True)
    archives = sorted((work / "artifacts").rglob("drift-*.zip"))
    for archive in archives:
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(evidence)
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src"), "PYTHONUTF8": "1"}
    env.pop("REPOSITORY_PRESENTER_SEALING_PAUSED", None)
    (checkout / "drift").mkdir(exist_ok=True)
    contract = subprocess.run(
        [sys.executable, "-m", "repository_presenter", "monitor-drift-contract", str(evidence),
         "--out", "drift/drift.json", "--root", str(checkout)],
        capture_output=True, text=True, check=False, env=env, cwd=checkout)
    outputs = work / "replay" / "github_output.txt"
    plan = subprocess.run(
        [sys.executable, "-m", "repository_presenter", "sealing-plan", "--root", str(checkout),
         "--drift-file", "drift/drift.json", "--github-output", str(outputs)],
        capture_output=True, text=True, check=False, env=env, cwd=checkout)
    summary = {
        "artifacts": [a.name for a in archives],
        "monitor_drift_contract_exit": contract.returncode,
        "monitor_drift_contract": (contract.stdout + contract.stderr).strip().splitlines()[-6:],
        "sealing_plan_exit": plan.returncode,
        "sealing_plan": (plan.stdout + plan.stderr).strip().splitlines()[-12:],
        "github_output": outputs.read_text(encoding="utf-8").splitlines() if outputs.is_file() else [],
    }
    (work / "replay" / "result.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(summary, indent=2))
    return 0 if contract.returncode == 0 and plan.returncode == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    dry = sub.add_parser("dryrun", help="act -n over every workflow (no containers)")
    dry.add_argument("--work", default=str(REPO_ROOT / "runs" / "rehearsal"))
    dry.add_argument("--only", nargs="*", help="restrict to these workflow files")
    dry.add_argument("--per-workflow-timeout", type=int, default=120)
    run = sub.add_parser("monitor", help="run monitor.yml end to end against the fakes")
    run.add_argument("--work", help="default: runs/rehearsal/monitor-<scenario>")
    run.add_argument("--timeout", type=int, default=3000)
    run.add_argument("--scenario", choices=sorted(MONITOR_SCENARIOS), default="clean",
                     help="; ".join(f"{k}: {v}" for k, v in sorted(MONITOR_SCENARIOS.items())))
    replay = sub.add_parser("replay-plan", help="replay sealing-scheduled.yml's plan hand-off")
    replay.add_argument("--work", help="a monitor run's work directory (default: monitor-clean)")
    sub.add_parser("down", help="remove this harness's sidecar and network")
    sub.add_parser("table", help="print the per-workflow plan table")
    args = parser.parse_args(argv)
    if args.command == "dryrun":
        return cmd_dryrun(args)
    if args.command == "monitor":
        return cmd_run_monitor(args)
    if args.command == "replay-plan":
        return cmd_replay_plan(args)
    if args.command == "down":
        stop_services()
        return 0
    for name in sorted(WORKFLOW_PLAN):
        plan = WORKFLOW_PLAN[name]
        print(f"{name}\t{plan['event']}\t{plan['mode']}\t{plan['gap']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
