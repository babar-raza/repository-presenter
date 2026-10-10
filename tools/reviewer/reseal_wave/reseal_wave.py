# TC-RSL-01 (plans/reseal-and-refresh, 2026-10-10). Owner/reviewer operator tooling (tools/README.md):
# never imported by src/, never read by a gate. Starts real `present` runs (gateway spend) - but only
# inside its own isolated worktrees, and writes nothing to candidates/, project/state.yaml, git history
# or GitHub.
"""Local parallel reseal runner.

For every selected repository: one isolated short-path worktree (scripts/new_worktree.sh, then
detached at the cut sha), `preflight` once, `present` (run 1), `present` again in a fresh process
(run 2, the no-op / adoption run), then `verify-noop-proof`. One result row per repository
(results.jsonl is the append-only source; results.csv and results.json are regenerated from it).

The runner NEVER edits project/state.yaml, never commits, never pushes, never copies a bundle into
the control checkout's candidates/ - the supervisor stages bundles from each worktree into wave PRs.
It never retries a rejected seal and never edits a disposition or plan (plans/healing/
r1-reseal-operations.md hard rules). A failed or timed-out repository leaves its worktree (logs
included) and nothing else.

usage: reseal_wave.py [--cut REF] [--repo OWNER/NAME ...] [--family F] [--platform P]
                      [--max-parallel 4] [--timeout-minutes 45] [--dry-run] [--retry-failed] ...
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MAX_PARALLEL_CEILING = 8
DEFAULT_PARALLEL = 4
DEFAULT_TIMEOUT_MINUTES = 45
DEFAULT_NODE_DIR = r"D:\Program Files\nodejs"
GATEWAY_VARIABLES = ("GPT_OSS_ENDPOINT", "GPT_OSS_API_KEY")

# Stdout line prefixes of `present`, in the order the transaction prints them.
STAGE_PREFIXES = (
    "admitted",
    "snapshot",
    "source",
    "examples",
    "build",
    "facts",
    "evaluation",
    "routing",
    "investigation",
    "dispositions",
    "plan",
    "units",
    "coherence",
    "readme",
    "patch",
    "validation",
    "review",
    "repair",
    "bundle",
)
FINISHED_STATUSES = ("SEALED", "NOT_READY", "NON_PROCESSABLE", "FAILED", "TIMEOUT")
RETRYABLE_STATUSES = ("FAILED", "TIMEOUT", "NOT_READY")
CSV_COLUMNS = (
    "repository",
    "status",
    "exit_preflight",
    "exit_present1",
    "exit_present2",
    "exit_noop",
    "stage_reached",
    "validation_pass",
    "validation_fail",
    "validation_pending",
    "review_verdict",
    "review_findings",
    "provider_calls_run1",
    "provider_calls_run2",
    "minutes",
    "bundle_state",
    "bundle_path",
    "noop_proof",
    "failure_class",
    "failure_stage",
    "failure_detail",
    "cut",
    "worktree",
    "attempt",
    "changed_paths",
    "started_at",
    "finished_at",
)


@dataclass(frozen=True)
class Entry:
    repository: str
    family: str
    platform: str
    mode: str
    active: bool

    @property
    def dirname(self) -> str:
        return self.repository.replace("/", "__")


@dataclass(frozen=True)
class Job:
    entry: Entry
    attempt: int
    name: str  # worktree directory name (short)
    branch: str


# --------------------------------------------------------------------------- pure parts


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_registry(text: str) -> list[Entry]:
    document = json.loads(text)
    return [
        Entry(
            repository=item["repository"],
            family=item["family"],
            platform=item["platform"],
            mode=item["mode"],
            active=bool(item.get("active", True)),
        )
        for item in document["entries"]
    ]


def enabled(entries: list[Entry]) -> list[Entry]:
    """Entries `present` would admit (core/registry/loader.py: mode other than disabled)."""
    return [e for e in entries if e.active and e.mode != "disabled"]


def check_parallelism(value: int) -> int:
    if value < 1:
        raise ValueError("--max-parallel must be at least 1")
    if value > MAX_PARALLEL_CEILING:
        raise ValueError(
            f"--max-parallel {value} refused: the ceiling is {MAX_PARALLEL_CEILING} "
            "(gateway headroom is probed by TC-PRE-01-03, never assumed)"
        )
    return value


def select_entries(
    entries: list[Entry],
    repos: list[str] | None = None,
    families: list[str] | None = None,
    platforms: list[str] | None = None,
) -> list[Entry]:
    """Enabled entries, optionally narrowed. An unknown or disabled --repo is an error, not a skip."""
    pool = enabled(entries)
    if repos:
        known = {e.repository: e for e in pool}
        missing = [r for r in repos if r not in known]
        if missing:
            raise ValueError(f"not an enabled registry entry: {', '.join(missing)}")
        pool = [known[r] for r in dict.fromkeys(repos)]
    if families:
        pool = [e for e in pool if e.family in families]
    if platforms:
        pool = [e for e in pool if e.platform in platforms]
    return pool


def latest_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Last row per repository wins (a retry appends; it never rewrites)."""
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        latest[row["repository"]] = row
    return latest


def worktree_name(entry: Entry, attempt: int) -> str:
    base = f"rs-{entry.family}-{entry.platform}"
    return base if attempt == 1 else f"{base}-{attempt}"


def build_queue(
    selected: list[Entry],
    rows: list[dict[str, Any]],
    cut: str,
    retry_failed: bool = False,
    path_taken: Any = lambda name: False,
) -> tuple[list[Job], list[tuple[Entry, str]]]:
    """(jobs to run, [(entry, reason skipped)]). A repository with a result row is skipped unless
    --retry-failed names its status; a retry takes a fresh worktree name (the first free attempt)."""
    latest = latest_rows(rows)
    jobs: list[Job] = []
    skipped: list[tuple[Entry, str]] = []
    for entry in selected:
        row = latest.get(entry.repository)
        if row is not None and not (retry_failed and row.get("status") in RETRYABLE_STATUSES):
            skipped.append((entry, f"already has a result row ({row.get('status')})"))
            continue
        attempt = 1
        while path_taken(worktree_name(entry, attempt)):
            attempt += 1
        name = worktree_name(entry, attempt)
        jobs.append(Job(entry, attempt, name, f"wt/{name}-{cut[:8]}"))
    return jobs, skipped


_VALIDATION_COUNTS = re.compile(r"pass (\d+), fail (\d+), pending (\d+)")
_REVIEW_LINE = re.compile(r"verdict (\w+), findings (\d+)")
_BUNDLE_LINE = re.compile(r"^bundle: (\S+) \(state ([A-Z_]+)(?:, (\d+) files, provider calls (\d+))?")
_VALIDATION_FAILURE = re.compile(r"validation: (BC-\d+) failed at ([\w ]+?):\s*(.*)")


def parse_present_output(stdout: str, stderr: str = "") -> dict[str, Any]:
    """Facts readable from one `present` log (cli.py prints them; the ledger is the call authority)."""
    out: dict[str, Any] = {"stage_reached": None}
    for line in stdout.splitlines():
        prefix = line.split(":", 1)[0]
        if prefix in STAGE_PREFIXES:
            out["stage_reached"] = prefix
        if line.startswith("NON_PROCESSABLE:"):
            out["stage_reached"] = "NON_PROCESSABLE"
            out["non_processable"] = line[:300]
        if line.startswith("validation:") and (m := _VALIDATION_COUNTS.search(line)):
            out["validation_pass"], out["validation_fail"], out["validation_pending"] = (
                int(g) for g in m.groups()
            )
        if line.startswith("review:") and (m := _REVIEW_LINE.search(line)):
            out["review_verdict"], out["review_findings"] = m.group(1), int(m.group(2))
        if m := _BUNDLE_LINE.match(line):
            out["bundle_path"], out["bundle_state"] = m.group(1), m.group(2)
            if m.group(4) is not None:
                out["reported_provider_calls"] = int(m.group(4))
    for line in stderr.splitlines():
        if m := _VALIDATION_FAILURE.search(line):
            out["failed_check"], out["failed_stage"] = m.group(1), m.group(2).strip()
            out["failed_detail"] = m.group(3)[:300]
    return out


def count_provider_calls(ledger_lines: list[str], invocation_id: str | None = None) -> int:
    """`provider_call` ledger records, restricted to one invocation when the records carry its id."""
    total = 0
    for line in ledger_lines:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get("disposition") != "provider_call":
            continue
        stamped = record.get("invocation_id")
        if invocation_id is not None and stamped is not None and stamped != invocation_id:
            continue
        total += 1
    return total


def parse_noop_output(exit_code: int | None, stdout: str, stderr: str) -> str:
    if exit_code is None:
        return "NOT_RUN"
    if exit_code == 0 and "no-op proof verified" in stdout:
        return "VERIFIED"
    if exit_code == 0 and "not applicable" in stdout:
        return "NOT_APPLICABLE"
    m = re.search(r"no-op proof failed \[(\w+)\]", stderr)
    return f"FAILED:{m.group(1)}" if m else f"FAILED:exit{exit_code}"


_TOOLCHAIN = re.compile(
    r"BLOCKED_TOOLCHAIN|toolchain|not found on PATH|FileNotFoundError|WinError 2\b|"
    r"'(javac|dotnet|npm|node|go|cargo|mvn|cmake|g\+\+|tsc)' is not recognized",
    re.I,
)
_GATEWAY = re.compile(
    r"gateway|did not answer|\b(429|502|503|504)\b|rate.?limit|ConnectTimeout|ReadTimeout|"
    r"connection (reset|refused|aborted)|catalog|no model|unavailable",
    re.I,
)
_CLONE = re.compile(r"git ls-remote|clone|authentication failed|repository not found", re.I)


def classify_failure(
    phase: str, exit_code: int | None, timed_out: bool, parsed: dict[str, Any], text: str
) -> tuple[str, str | None, str]:
    """(class, causal stage, detail). A guess for triage (TC-TRI-01), never a verdict."""
    if timed_out:
        return "timeout", None, f"{phase} exceeded the time budget"
    if phase == "noop":
        return "noop_proof", None, text.strip()[-300:]
    if "failed_check" in parsed:
        return parsed["failed_check"], parsed.get("failed_stage"), parsed.get("failed_detail", "")
    tail = text.strip()[-400:]
    if phase == "preflight":
        return "gateway", None, tail
    for label, pattern in (("toolchain", _TOOLCHAIN), ("gateway", _GATEWAY), ("clone", _CLONE)):
        if pattern.search(text):
            return label, None, tail
    return "unknown", None, tail


def row_status(
    exit1: int | None,
    exit2: int | None,
    noop: str,
    parsed2: dict[str, Any],
    parsed1: dict[str, Any],
    timed_out: bool,
) -> str:
    if timed_out:
        return "TIMEOUT"
    if exit1 != 0:
        return "FAILED"
    if parsed1.get("stage_reached") == "NON_PROCESSABLE":
        return "NON_PROCESSABLE"
    if exit2 != 0 or noop.startswith("FAILED") or noop == "NOT_RUN":
        return "FAILED"
    state = parsed2.get("bundle_state") or parsed1.get("bundle_state") or ""
    verdict = parsed2.get("review_verdict") or parsed1.get("review_verdict")
    if "READY_FOR_PROPOSAL" in state and verdict in (None, "ACCEPT"):
        return "SEALED"
    return "NOT_READY"


def write_outputs(results_dir: Path, rows: list[dict[str, Any]], cut: str) -> None:
    """results.csv and results.json from the append-only results.jsonl rows (last row wins)."""
    latest = list(latest_rows(rows).values())
    results_dir.mkdir(parents=True, exist_ok=True)
    with (results_dir / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in latest:
            flat = dict(row)
            flat["changed_paths"] = ";".join(row.get("changed_paths") or [])
            writer.writerow(flat)
    document = {"cut": cut, "generated_at": utc_now(), "rows": latest}
    (results_dir / "results.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def load_rows(results_dir: Path) -> list[dict[str, Any]]:
    path = results_dir / "results.jsonl"
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("{")
    ]


# ------------------------------------------------------------------------ process handling


@dataclass
class Runner:
    control_root: Path  # the checkout whose scripts/new_worktree.sh is used
    main_root: Path  # the main checkout; worktrees live under <main_root>/runs/wt
    python: str
    bash: str
    cut: str
    results_dir: Path
    timeout_seconds: float
    extra_path: list[str]
    gh_token: str | None
    lock: threading.Lock = field(default_factory=threading.Lock)
    worktree_lock: threading.Lock = field(default_factory=threading.Lock)
    live: set[subprocess.Popen[bytes]] = field(default_factory=set)

    def worktree_path(self, name: str) -> Path:
        return self.main_root / "runs" / "wt" / name

    def env_for(self, worktree: Path) -> dict[str, str]:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(worktree / "src")
        env["PYTHONUTF8"] = "1"
        env["PYTHONUNBUFFERED"] = "1"  # logs are files: without this a killed run loses its stages
        env["PYTHONIOENCODING"] = "utf-8"
        extra = [p for p in self.extra_path if Path(p).is_dir()]
        if extra:  # subprocess PATH only; the machine's PATH is never edited
            env["PATH"] = os.pathsep.join([*extra, env.get("PATH", "")])
        if self.gh_token:
            env["GH_TOKEN"] = self.gh_token
        return env

    def run(
        self,
        argv: list[str],
        cwd: Path,
        env: dict[str, str],
        stdout_path: Path,
        stderr_path: Path,
        deadline: float,
    ) -> tuple[int | None, bool]:
        """(exit code, timed_out). Output goes to files, never pipes, so a chatty run cannot stall."""
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None, True
        kwargs: dict[str, Any] = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True
        with stdout_path.open("wb") as out, stderr_path.open("wb") as err:
            proc = subprocess.Popen(
                argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err, **kwargs
            )
            with self.lock:
                self.live.add(proc)
            try:
                return proc.wait(timeout=remaining), False
            except subprocess.TimeoutExpired:
                kill_tree(proc)
                return None, True
            finally:
                with self.lock:
                    self.live.discard(proc)

    def kill_all(self) -> None:
        with self.lock:
            procs = list(self.live)
        for proc in procs:
            kill_tree(proc)

    def create_worktree(self, job: Job) -> Path:
        """scripts/new_worktree.sh, then detach at the cut (the script branches from origin/main's
        tip, the cut is a pinned sha). Serialised: it fetches and touches the shared git dir."""
        path = self.worktree_path(job.name)
        with self.worktree_lock:
            made = subprocess.run(
                [self.bash, "scripts/new_worktree.sh", job.name, job.branch],
                cwd=self.control_root,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
            )
            if made.returncode != 0:
                raise RuntimeError(f"new_worktree.sh {job.name}: {made.stdout.strip()[-300:]}")
            git = subprocess.run(
                ["git", "-C", str(path), "checkout", "--detach", self.cut],
                capture_output=True,
                text=True,
            )
            if git.returncode != 0:
                raise RuntimeError(f"checkout --detach {self.cut[:8]}: {git.stderr.strip()[-300:]}")
        return path


def kill_tree(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=60
            )
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        proc.kill()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        pass


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def ledger_calls(worktree: Path, record_path: Path) -> int | None:
    """Provider calls of one invocation, counted from the ledger its invocation record names."""
    record = read_json(record_path)
    ledger = record.get("ledger")
    if not ledger:
        return None
    path = worktree / ledger
    if not path.is_file():
        return None
    return count_provider_calls(path.read_text(encoding="utf-8").splitlines(), record.get("invocation_id"))


def changed_paths(worktree: Path) -> list[str]:
    """What the run changed in its own worktree (the supervisor stages candidate paths from here)."""
    status = subprocess.run(
        ["git", "-C", str(worktree), "status", "--porcelain", "--untracked-files=all"],
        capture_output=True,
        text=True,
    )
    return [line[3:] for line in status.stdout.splitlines() if line.strip()]


def run_job(runner: Runner, job: Job) -> dict[str, Any]:
    entry = job.entry
    started = time.monotonic()
    row: dict[str, Any] = {
        "repository": entry.repository,
        "family": entry.family,
        "platform": entry.platform,
        "cut": runner.cut,
        "attempt": job.attempt,
        "worktree": str(runner.worktree_path(job.name)),
        "started_at": utc_now(),
        "exit_preflight": None,
        "exit_present1": None,
        "exit_present2": None,
        "exit_noop": None,
        "noop_proof": "NOT_RUN",
        "failure_class": "",
        "failure_stage": "",
        "failure_detail": "",
    }
    deadline = started + runner.timeout_seconds
    timed_out = False
    parsed1: dict[str, Any] = {}
    parsed2: dict[str, Any] = {}
    try:
        worktree = runner.create_worktree(job)
        env = runner.env_for(worktree)
        logs = worktree / "runs" / "reseal-logs"
        cli = [runner.python, "-m", "repository_presenter"]

        # The venv is shared; PYTHONPATH must make it import THIS worktree's src.
        probe = subprocess.run(
            [runner.python, "-c", "import repository_presenter as r;print(r.__file__)"],
            cwd=worktree, env=env, capture_output=True, text=True,
        )
        imported = Path(probe.stdout.strip() or ".").resolve()
        if worktree.resolve() not in imported.parents:
            raise RuntimeError(f"repository_presenter imports {imported}, not the worktree's src")

        def phase(name: str, args: list[str]) -> tuple[int | None, bool, str, str]:
            code, late = runner.run(
                [*cli, *args], worktree, env, logs / f"{name}.out", logs / f"{name}.err", deadline
            )
            return code, late, read_text(logs / f"{name}.out"), read_text(logs / f"{name}.err")

        code, timed_out, out, err = phase("preflight", ["preflight"])
        row["exit_preflight"] = code
        if code != 0:
            raise PhaseFailure("preflight", code, timed_out, {}, out + "\n" + err)

        record1, record2 = logs / "invocation-1.json", logs / "invocation-2.json"
        repo = entry.repository
        code, timed_out, out, err = phase(
            "present-1", ["present", "--repo", repo, "--invocation-record", str(record1)]
        )
        row["exit_present1"] = code
        parsed1 = parse_present_output(out, err)
        row["provider_calls_run1"] = ledger_calls(worktree, record1)  # spend counts on failure too
        if code != 0 or timed_out:
            raise PhaseFailure("present-1", code, timed_out, parsed1, out + "\n" + err)

        if parsed1.get("stage_reached") != "NON_PROCESSABLE":
            code, timed_out, out, err = phase(
                "present-2", ["present", "--repo", repo, "--invocation-record", str(record2)]
            )
            row["exit_present2"] = code
            parsed2 = parse_present_output(out, err)
            row["provider_calls_run2"] = ledger_calls(worktree, record2)
            if code != 0 or timed_out:
                raise PhaseFailure("present-2", code, timed_out, parsed2, out + "\n" + err)

        if parsed1.get("stage_reached") == "NON_PROCESSABLE":
            row["noop_proof"] = "NOT_APPLICABLE"  # no candidate, so no second run and no ledger
        else:
            code, timed_out, out, err = phase(
                "noop", ["verify-noop-proof", "--first", str(record1), "--second", str(record2)]
            )
            row["exit_noop"] = code
            row["noop_proof"] = "TIMEOUT" if timed_out else parse_noop_output(code, out, err)
            if timed_out or row["noop_proof"].startswith("FAILED"):
                raise PhaseFailure("noop", code, timed_out, {}, out + "\n" + err)
    except PhaseFailure as failure:
        timed_out = failure.timed_out
        parsed = failure.parsed
        row["failure_class"], row["failure_stage"], row["failure_detail"] = classify_failure(
            failure.phase, failure.code, failure.timed_out, parsed, failure.text
        )
    except Exception as exc:  # worktree / environment failures: recorded, never raised past the pool
        row["failure_class"], row["failure_detail"] = "runner", f"{type(exc).__name__}: {exc}"[:300]

    final = {**parsed1, **parsed2}  # run 2 (the adoption run) overrides run 1 where it reports
    row["stage_reached"] = final.get("stage_reached") or ""
    for key in ("validation_pass", "validation_fail", "validation_pending", "review_verdict",
                "review_findings", "bundle_state", "bundle_path"):
        row[key] = final.get(key, "")
    worktree_path = runner.worktree_path(job.name)
    if worktree_path.is_dir():
        row["changed_paths"] = changed_paths(worktree_path)
        if row["bundle_path"]:
            row["bundle_path"] = str(worktree_path / row["bundle_path"])
    if row["failure_class"]:
        row["status"] = "TIMEOUT" if timed_out else "FAILED"
    else:
        row["status"] = row_status(
            row["exit_present1"], row["exit_present2"], row["noop_proof"], parsed2, parsed1, timed_out
        )
    row["minutes"] = round((time.monotonic() - started) / 60, 1)
    row["finished_at"] = utc_now()
    return row


class PhaseFailure(Exception):
    def __init__(self, phase: str, code: int | None, timed_out: bool, parsed: dict[str, Any], text: str):
        super().__init__(phase)
        self.phase, self.code, self.timed_out, self.parsed, self.text = (
            phase, code, timed_out, parsed, text
        )


# ------------------------------------------------------------------------------ entry point


def git_out(root: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {done.stderr.strip()[-300:]}")
    return done.stdout.strip()


def find_bash(explicit: str | None) -> str:
    candidates = [explicit, os.environ.get("RESEAL_BASH"), r"C:\Program Files\Git\bin\bash.exe"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    found = shutil.which("bash")
    if found is None:
        raise RuntimeError("no bash found; pass --bash (Git for Windows bash, not the WSL one)")
    return found


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--cut", default="origin/main", help="cut ref or sha (default origin/main, pinned to its sha)")
    p.add_argument("--repo", action="append", metavar="OWNER/NAME", help="repeatable; default all enabled")
    p.add_argument("--family", action="append")
    p.add_argument("--platform", action="append")
    p.add_argument("--max-parallel", type=int, default=DEFAULT_PARALLEL)
    p.add_argument("--timeout-minutes", type=float, default=DEFAULT_TIMEOUT_MINUTES)
    p.add_argument("--results-dir", type=Path, default=None, help="default <main>/runs/reseal/<cut8>")
    p.add_argument("--retry-failed", action="store_true", help="re-queue FAILED/TIMEOUT/NOT_READY rows")
    p.add_argument("--dry-run", action="store_true", help="print the plan; start nothing")
    p.add_argument("--python", default=None, help="default <main>/.venv/Scripts/python.exe")
    p.add_argument("--bash", default=None)
    p.add_argument("--extra-path", action="append", default=None, help=f"prepended to the SUBPROCESS PATH (default {DEFAULT_NODE_DIR})")
    p.add_argument("--gh-token-from-gh", action="store_true", help="read GH_TOKEN from `gh auth token` into the subprocess env only")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        parallel = check_parallelism(args.max_parallel)
    except ValueError as exc:
        print(f"reseal_wave: {exc}", file=sys.stderr)
        return 2
    control_root = Path(git_out(Path(__file__).parent, "rev-parse", "--show-toplevel"))
    common = Path(git_out(control_root, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    main_root = common.parent
    git_out(control_root, "fetch", "origin", "--quiet")
    cut = git_out(control_root, "rev-parse", "--verify", f"{args.cut}^{{commit}}")
    entries = parse_registry(git_out(control_root, "show", f"{cut}:data/registry.json"))
    try:
        selected = select_entries(entries, args.repo, args.family, args.platform)
    except ValueError as exc:
        print(f"reseal_wave: {exc}", file=sys.stderr)
        return 2
    results_dir = args.results_dir or main_root / "runs" / "reseal" / cut[:8]
    rows = load_rows(results_dir)
    taken = lambda name: (main_root / "runs" / "wt" / name).exists()  # noqa: E731
    jobs, skipped = build_queue(selected, rows, cut, args.retry_failed, taken)

    venv_python = main_root / ".venv" / "Scripts" / "python.exe"
    python = args.python or (str(venv_python) if venv_python.is_file() else sys.executable)
    extra_path = args.extra_path if args.extra_path is not None else [DEFAULT_NODE_DIR]
    print(f"cut {cut}; {len(selected)} selected, {len(jobs)} to run, {len(skipped)} skipped; "
          f"max_parallel {parallel}; timeout {args.timeout_minutes:g} min; results {results_dir}")
    for entry, reason in skipped:
        print(f"  skip {entry.repository}: {reason}")
    for job in jobs:
        print(f"  run  {job.entry.repository} -> runs/wt/{job.name} (branch {job.branch}, attempt {job.attempt})")
    if args.dry_run:
        print("dry run: no worktree created, no process started, nothing written")
        return 0
    if not jobs:
        write_outputs(results_dir, rows, cut)
        return 0
    absent = [v for v in GATEWAY_VARIABLES if not os.environ.get(v)]
    if absent:
        print(f"reseal_wave: gateway variable(s) not set: {', '.join(absent)}", file=sys.stderr)
        return 2
    token = os.environ.get("GH_TOKEN") or None
    if args.gh_token_from_gh and token is None:
        got = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        token = got.stdout.strip() or None
    if token is None:
        print("reseal_wave: warning: GH_TOKEN not set; clones are unauthenticated", file=sys.stderr)

    runner = Runner(
        control_root=control_root, main_root=main_root, python=python, bash=find_bash(args.bash),
        cut=cut, results_dir=results_dir, timeout_seconds=args.timeout_minutes * 60,
        extra_path=extra_path, gh_token=token,
    )
    results_dir.mkdir(parents=True, exist_ok=True)
    jsonl = results_dir / "results.jsonl"

    def work(job: Job) -> None:
        row = run_job(runner, job)
        with runner.lock:  # append-only; one line per finished repository
            with jsonl.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
            write_outputs(results_dir, load_rows(results_dir), cut)
        print(f"  done {row['repository']}: {row['status']} {row['minutes']} min "
              f"stage {row['stage_reached'] or '-'} class {row['failure_class'] or '-'}", flush=True)

    try:
        with ThreadPoolExecutor(parallel) as pool:
            list(pool.map(work, jobs))
    except KeyboardInterrupt:
        runner.kill_all()
        print("interrupted: running children killed; unfinished repositories have no row and rerun on resume")
        return 130
    rows = load_rows(results_dir)
    print(json.dumps({s: sum(1 for r in latest_rows(rows).values() if r["status"] == s)
                      for s in FINISHED_STATUSES}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
