"""The correction wave, rehearsed end to end against the local fakes (no network, no GitHub write).

The real correction-PR wave (docs/OPERATIONS_RUNBOOK.md section 12) proposes README corrections of
registered product repositories through ``propose.yml``'s correction mode. Every step the owner and
the hosted workflow take is taken here, through the same entry points and in the same order:

1. ``correct-readme`` writes one correction bundle per product into a run directory (two local bare
   upstreams stand in for the products; the run directory also holds files that must never travel);
2. ``tools/corrections/assemble.py`` copies exactly the approved repositories' bundles to
   ``corrections/<run-id>/<slug>/`` with their pull request text and SHA256SUMS, flips exactly those
   registry entries to ``full`` and drafts their authorization records; the control repository
   merges it (a real git history with ``origin/main``);
3. the workflow's OWN steps run: ``propose.yml`` is parsed, every ``env:`` and ``if:`` expression is
   resolved from the dispatch inputs and the earlier steps' outputs, and each ``run:`` script is
   executed under bash (the validation, the SHA256SUMS verification, the record check). Where the
   script calls ``repository-presenter propose`` a shim records the argument list the workflow
   built,
   and that exact list is run through the real CLI in-process, with the real GitHub client, effect,
   token and App-attribution checks bound to the stateful fake REST (``fake_rest.py``).

What it proves, each with its negative control: a dispatch without ``do_propose`` is a dry run that
writes nothing; the write refuses without a merged authorization record, with an edited or missing
one, with the entry still ``dry_run``, with the owner switch closed, with no or a wrong-scope token;
a tampered bundle is refused by the SHA256SUMS step, and a re-sealed forgery by the typed gate; a
moved head is refused (before and between the jobs) with nothing written; one pull request is
created and attributed to the App; a rerun writes nothing; a later correction run updates that same
pull request in place; nothing outside the approved list is assembled, flipped, drafted or proposed.
"""

from __future__ import annotations

import contextlib
import difflib
import io
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
import yaml

from repository_presenter import cli
from repository_presenter.cli import EXIT_OK, EXIT_UNSAFE, main
from repository_presenter.components.propose.effect import (
    AUTHORIZATION_VARIABLE,
    presenter_branch_name,
)
from repository_presenter.components.readme_correction import run as correction_run
from repository_presenter.components.readme_correction.committed import (
    COMMITTED_FILES,
    PULL_REQUEST_NAME,
    SUMS_NAME,
    write_sums,
)
from repository_presenter.core.authorization.proposal import AUTHORIZATION_DIRNAME, record_filename
from repository_presenter.core.facts import Evidence, Fact, FactsDocument, write_facts
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from repository_presenter.core.github.read_client import DefaultBranchRead
from repository_presenter.core.github.token_provenance import EXPECTED_APP_ID
from repository_presenter.core.hashing import sha256_text
from repository_presenter.core.registry.loader import load_registry, require_listed
from support import REPO_ROOT, merge_to_origin_main, write_cursor

TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS / "workflow_rehearsal"))
sys.path.insert(0, str(TOOLS / "corrections"))

import assemble  # noqa: E402
import cycle  # noqa: E402
import fake_rest  # noqa: E402
import scenarios  # noqa: E402

WORKFLOW = yaml.safe_load(
    (REPO_ROOT / ".github" / "workflows" / "propose.yml").read_text(encoding="utf-8")
)
A = "aspose-cells-foss/Aspose.Cells-FOSS-for-Go"
B = "aspose-email-foss/Aspose.JMAP-FOSS-for-Go"
RUN_ID = "2026-10-12"
BRANCH = presenter_branch_name()
APPROVER = "babar-raza"

DIAGRAM = """\
flowchart TD
  subgraph StartingPoints["Starting Points"]
    direction LR
    i1["An existing XLSX workbook"]
  end
  PRODUCT["Synthetic Pkg"]
  subgraph Capabilities["Core Capabilities"]
    direction LR
    subgraph capl[" "]
      direction TB
      c1["Cell read and write"]
      c2["Font and fill styling"]
      c3["Formulas with a built-in engine"]
    end
    subgraph capr[" "]
      direction TB
      c4["CSV import and export"]
      c5["Streaming row-by-row reading"]
      c6["Password protection"]
    end
  end
  subgraph Outputs["Outputs"]
    direction TB
    o1["XLSX workbooks"]
  end
  StartingPoints --> PRODUCT --> Capabilities --> Outputs
"""
README = (
    "# Synthetic Pkg\n\nSynthetic Pkg does one thing.\n\n## At a Glance\n\n```mermaid\n"
    + DIAGRAM
    + "```\n\n## License\n\nMIT.\n"
)
README_V2 = README.replace("does one thing.", "does one thing. Version two.")
PRODUCT_FILES = {
    "README.md": README,
    "LICENSE": "MIT License\n",
    "go.mod": "module example.invalid/synthetic\n\ngo 1.24\n",
    "doc.go": "// Package synthetic does one thing.\npackage synthetic\n",
    "docs/usage.md": "Use it.\n",
}
EXPRESSION = re.compile(r"\$\{\{\s*([^}]+?)\s*\}\}")


def slug(repository: str) -> str:
    return repository.replace("/", "__")


def _git(args: list[str], cwd: Path) -> str:
    return scenarios._git(args, cwd)


def _facts(repository: str, revision: str) -> FactsDocument:
    def fact(fact_id: str, value: str, path: str, detail: str | None = None) -> Fact:
        return Fact(
            id=fact_id,
            kind=fact_id.split(":", 1)[0],  # type: ignore[arg-type]
            value=value,
            evidence=(Evidence(path, detail),),
        )

    return FactsDocument(
        repository,
        revision,
        (
            fact("identity:repository", repository, "data/registry.json"),
            fact("license:spdx", "MIT", "LICENSE", "license text states this license"),
            fact("license:file", "LICENSE", "LICENSE"),
            fact("dependency:none", "none", "go.mod", "declares none"),
        ),
    )


# --- running the workflow's own steps ---------------------------------------------------------


def truthy(condition: str, ctx: dict[str, str], do_propose: bool) -> bool:
    """The value of a step or job ``if:`` of the forms propose.yml uses."""
    match = EXPRESSION.search(condition)
    expression = match.group(1) if match else condition

    def reference(found: re.Match[str]) -> str:
        return repr(ctx.get(found.group(0), ""))

    expression = re.sub(
        r"\b(?:steps|needs)\.[\w-]+\.(?:outputs\.[\w-]+|result)", reference, expression
    )
    expression = re.sub(r"\binputs\.do_propose\b", repr(do_propose), expression)
    expression = expression.replace("&&", " and ").replace("||", " or ")
    return bool(eval(expression, {"__builtins__": {}}, {}))  # our own workflow file's conditions


def resolve(text: str, ctx: dict[str, str]) -> str:
    def substitute(found: re.Match[str]) -> str:
        key = found.group(1).strip()
        if key.startswith(("steps.", "needs.")):
            return ctx.get(key, "")  # the output of a step that did not run is the empty string
        assert key in ctx, f"unmodelled workflow expression: {key}"
        return ctx[key]

    return EXPRESSION.sub(substitute, text)


@dataclass
class Run:
    """What one dispatch did: each job's verdict, the failing step, the log, the tokens minted."""

    dry_run_ok: bool = False
    write_ran: bool = False
    write_ok: bool = False
    failed_step: str = ""
    cli_exit: dict[str, int] = field(default_factory=dict)
    argv: dict[str, list[str]] = field(default_factory=dict)
    mints: list[dict[str, str]] = field(default_factory=list)
    log: str = ""
    outputs: dict[str, str] = field(default_factory=dict)


def _bash() -> str:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not available to execute the workflow's steps")
    return bash


@dataclass
class World:
    tmp: Path
    control: Path
    run_dir: Path
    bares: dict[str, Path]
    works: dict[str, Path]
    rests: dict[str, fake_rest.FakeGitHubRest]
    monkeypatch: pytest.MonkeyPatch
    trigger: str = ""
    sequence: int = 0

    # --- the upstreams ---------------------------------------------------------------------------

    def head(self, repository: str) -> str:
        return _git(["rev-parse", "main"], self.bares[repository])

    def sync_rest(self, repository: str) -> fake_rest.FakeGitHubRest:
        """GitHub as the bare upstream holds it now, for a token reaching this repository alone."""
        entry = require_listed(load_registry(REPO_ROOT / "data" / "registry.json"), repository)
        rest = fake_rest.FakeGitHubRest(app_id=EXPECTED_APP_ID, installation_scope=[repository])
        work = self.works[repository]
        files = {
            path: (work / path).read_text(encoding="utf-8")
            for path in _git(["ls-files"], work).splitlines()
            if path != "README.md"
        }
        rest.add_repository(
            repository,
            tip=self.head(repository),
            repository_id=entry.provider_identity.repository_id,
            readme=(work / "README.md").read_text(encoding="utf-8"),
            files=files,
        )
        self.rests[repository] = rest
        return rest

    def advance_upstream(self, repository: str, files: dict[str, str]) -> str:
        """The maintainers push a commit; GitHub's model of it moves too (the open PR survives)."""
        work = self.works[repository]
        for relative, content in files.items():
            (work / relative).write_text(content, encoding="utf-8", newline="\n")
        _git(["add", "-A"], work)
        _git(["commit", "-q", "-m", "maintainers push"], work)
        _git(["push", "-q", "origin", "HEAD:main"], work)
        revision = self.head(repository)
        rest = self.rests.get(repository)
        if rest is not None:
            rest.set_branch(repository, "main", revision)
            for relative, content in files.items():
                rest.set_file(repository, "main", relative, content)
        return revision

    # --- the correction run and the assembled pull request ---------------------------------------

    def correct(self, repositories: list[str], run_dir: Path | None = None) -> Path:
        """``correct-readme`` for each repository, into one run directory."""
        run_dir = run_dir or self.run_dir
        shutil.rmtree(self.control / "runs", ignore_errors=True)  # a fresh pinned clone each run
        for repository in repositories:
            facts = self.tmp / f"facts-{slug(repository)}-{self.head(repository)[:8]}.json"
            write_facts(_facts(repository, self.head(repository)), facts)
            code = main(
                [
                    "correct-readme",
                    "--repo",
                    repository,
                    "--root",
                    str(self.control),
                    "--facts",
                    str(facts),
                    "--out",
                    str(run_dir / slug(repository)),
                ]
            )
            assert code == EXIT_OK
        return run_dir

    def merge(self, message: str = "merge the correction wave pull request") -> str:
        self.trigger = merge_to_origin_main(self.control, message)
        return self.trigger

    def bundle(self, repository: str, run_id: str = RUN_ID) -> Path:
        return self.control / "corrections" / run_id / slug(repository)

    def record(self, repository: str, run_id: str = RUN_ID) -> str:
        corrected = (self.bundle(repository, run_id) / "README.md").read_text(encoding="utf-8")
        name = record_filename(repository, sha256_text(corrected))
        return (AUTHORIZATION_DIRNAME / name).as_posix()

    # --- the workflow ----------------------------------------------------------------------------

    def dispatch(
        self,
        repository: str,
        *,
        record: str | None = None,
        do_propose: bool = False,
        run_id: str = RUN_ID,
        candidate_artifact: str = "",
        between: Callable[[], None] | None = None,
        write_env: dict[str, str | None] | None = None,
    ) -> Run:
        """``gh workflow run propose.yml -f repo=... -f correction_run=...``: both jobs' steps."""
        cycle_seams = cycle.propose_seams(self.rests[repository], repository)
        for name, target in (
            ("default_verify_installation_token", "verify_token"),
            ("default_verify_pull_request_app", "verify_pull_request_app"),
            ("default_get_ref", "get_ref"),
            ("default_create_ref", "create_ref"),
            ("default_get_contents", "get_contents"),
            ("default_put_contents", "put_contents"),
            ("default_find_pull_requests", "find_pull_requests"),
            ("default_create_pull_request", "create_pull_request"),
            ("default_update_pull_request", "update_pull_request"),
        ):
            self.monkeypatch.setattr(cli, name, cycle_seams[target])
        inputs = {
            "repo": repository,
            "base_branch": "",
            "authorization_record": record or "",
            "do_propose": "true" if do_propose else "false",
            "candidate_artifact": candidate_artifact,
            "correction_run": run_id,
        }
        ctx = {f"inputs.{key}": value for key, value in inputs.items()}
        ctx["github.sha"] = self.trigger
        ctx["runner.temp"] = str(self.tmp / "runner-temp")
        ctx["secrets.GH_APP_ID"] = "123456"  # the fakes: nothing real is ever named here
        ctx["secrets.GH_APP_PRIVATE_KEY"] = "not-a-key"
        run = Run()
        run.dry_run_ok = self._job("dry-run", ctx, run, do_propose, {})
        for key, expression in WORKFLOW["jobs"]["dry-run"]["outputs"].items():
            ctx[f"needs.dry-run.outputs.{key}"] = resolve(expression, ctx)
        ctx["needs.dry-run.result"] = "success" if run.dry_run_ok else "failure"
        run.outputs = {
            key.rsplit(".", 1)[1]: value
            for key, value in ctx.items()
            if key.startswith("needs.dry-run.outputs.")
        }
        if run.dry_run_ok and between is not None:
            between()
        write = WORKFLOW["jobs"]["write"]
        if truthy(write["if"], ctx, do_propose):
            run.write_ran = True
            run.write_ok = self._job("write", ctx, run, do_propose, write_env or {})
        return run

    def _job(
        self,
        name: str,
        ctx: dict[str, str],
        run: Run,
        do_propose: bool,
        extra_env: dict[str, str | None],
    ) -> bool:
        job = WORKFLOW["jobs"][name]
        bin_dir = self.tmp / "shim-bin"
        bin_dir.mkdir(exist_ok=True)
        shim = bin_dir / "repository-presenter"
        shim.write_text(
            '#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$RP_ARGV_FILE"\n', newline="\n"
        )
        shim.chmod(0o755)
        for index, step in enumerate(job["steps"]):
            label = str(step.get("name") or step.get("uses"))
            if "if" in step and not truthy(str(step["if"]), ctx, do_propose):
                continue
            if "uses" in step:
                if str(step["uses"]).startswith("actions/create-github-app-token@"):
                    ctx[f"steps.{step['id']}.outputs.token"] = cycle.FAKE_TOKEN
                    run.mints.append(
                        {key: resolve(str(value), ctx) for key, value in step["with"].items()}
                    )
                continue
            if label == "Install from the lock":
                continue
            env = {key: resolve(str(value), ctx) for key, value in step.get("env", {}).items()}
            output = self.tmp / f"output-{name}-{index}-{self.sequence}"
            self.sequence += 1
            output.write_text("", encoding="utf-8")
            argv_file = self.tmp / f"argv-{name}-{index}-{self.sequence}"
            process_env = {
                key: value
                for key, value in os.environ.items()
                if not key.startswith(("INPUT_", "GITHUB_", "GH_", "REPOSITORY_PRESENTER_"))
            }
            process_env.update(env)
            process_env["GITHUB_OUTPUT"] = str(output)
            process_env["RP_ARGV_FILE"] = str(argv_file)
            process_env["PATH"] = f"{bin_dir.as_posix()}{os.pathsep}{process_env['PATH']}"
            done = subprocess.run(
                [_bash(), "-c", str(step["run"])],
                cwd=self.control,
                env=process_env,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            run.log += done.stdout + done.stderr
            if done.returncode != 0:
                run.failed_step = label
                return False
            if "id" in step:
                for line in output.read_text(encoding="utf-8").splitlines():
                    key, _, value = line.partition("=")
                    ctx[f"steps.{step['id']}.outputs.{key}"] = value
            if argv_file.exists():  # the step ran `repository-presenter ...`: run those arguments
                argv = argv_file.read_text(encoding="utf-8").splitlines()
                run.argv[name] = argv
                patched = {k: v for k, v in {**env, **extra_env}.items() if v is not None}
                buffer = io.StringIO()
                with (
                    mock.patch.dict(os.environ, patched),
                    contextlib.redirect_stdout(buffer),
                    contextlib.redirect_stderr(buffer),
                ):
                    code = main(argv)
                run.log += buffer.getvalue()
                run.cli_exit[name] = code
                if code != 0:
                    run.failed_step = label
                    return False
        return True


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> World:
    base = tmp_path / "base"
    base.mkdir()
    bares: dict[str, Path] = {}
    works: dict[str, Path] = {}
    for repository in (A, B):
        owner, name = repository.split("/")
        scenarios.build_repository(base, name, [("initial", PRODUCT_FILES)], owner=owner)
        bares[repository] = base / "upstreams" / owner / f"{name}.git"
        works[repository] = tmp_path / "work" / slug(repository)
        _git(["clone", "-q", str(bares[repository]), str(works[repository])], tmp_path)

    control = tmp_path / "control"
    write_cursor(control)
    (control / ".gitignore").write_text("/runs/\n", encoding="utf-8")
    (control / "data").mkdir(exist_ok=True)
    shutil.copyfile(REPO_ROOT / "data" / "registry.json", control / "data" / "registry.json")
    merge_to_origin_main(control, "the control repository before the correction wave")

    registry = load_registry(REPO_ROOT / "data" / "registry.json")
    urls = {
        require_listed(registry, repository).clone_url: bares[repository] for repository in bares
    }
    monkeypatch.setattr(
        correction_run,
        "pinned_read_only_clone",
        lambda url, destination, **kwargs: pinned_read_only_clone(str(urls[url]), destination),
    )
    built = World(tmp_path, control, tmp_path / "run", bares, works, {}, monkeypatch)
    monkeypatch.setattr(
        cli,
        "fetch_default_branch_sha",
        lambda repository, *, token=None: DefaultBranchRead(
            repository, sha=built.head(repository), branch="main"
        ),
    )
    monkeypatch.delenv(AUTHORIZATION_VARIABLE, raising=False)
    monkeypatch.delenv("GH_PROPOSAL_WRITE_TOKEN", raising=False)
    monkeypatch.chdir(control)
    for repository in (A, B):
        built.sync_rest(repository)
    return built


SWITCH = "REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED"  # the write step sets it, alone
TOKEN = "GH_PROPOSAL_WRITE_TOKEN"  # the write step receives the minted token as this


def add_internal_files(world: World) -> None:
    """What a correction run directory holds besides the bundles: nothing of it may be committed."""
    for repository in (A, B):
        (world.run_dir / slug(repository) / "run.log").write_text("internal\n", encoding="utf-8")
        scratch = world.run_dir / slug(repository) / "scratch"
        scratch.mkdir()
        (scratch / "notes.txt").write_text("internal\n", encoding="utf-8")
    (world.run_dir / "driver.log").write_text("internal\n", encoding="utf-8")
    nothing = world.run_dir / "aspose-pdf-foss__Aspose-PDF-FOSS-for-Go"
    nothing.mkdir()
    (nothing / "status.json").write_text(
        json.dumps({"status": "no_detector_fired", "reason": "nothing to correct"}),
        encoding="utf-8",
    )


@pytest.fixture
def ready(world: World) -> World:
    """The wave pull request merged: bundles, registry flips and records for A and B on main."""
    world.correct([A, B])
    add_internal_files(world)
    rows = assemble.assemble(world.control, world.run_dir, RUN_ID, [A, B], approver=APPROVER)
    assert [row.repository for row in rows] == [A, B]
    world.merge()
    return world


def pulls(world: World, repository: str) -> list[dict[str, Any]]:
    return world.rests[repository].pulls(repository)


# --- assembly ------------------------------------------------------------------------------------


def test_assembly_commits_exactly_the_bundles_files_and_nothing_internal(ready: World) -> None:
    for repository in (A, B):
        directory = ready.bundle(repository)
        assert {p.name for p in directory.iterdir()} == COMMITTED_FILES | {SUMS_NAME}
    assert [p.name for p in (ready.control / "corrections" / RUN_ID).iterdir()] == sorted(
        slug(r) for r in (A, B)
    )  # no run-level file, and the repository with only a status.json was never named
    committed = _git(["ls-files", "corrections"], ready.control).splitlines()
    assert len(committed) == 2 * (len(COMMITTED_FILES) + 1)
    assert not any(
        "run.log" in path or "notes.txt" in path or "status.json" in path for path in committed
    )


def test_the_committed_bundles_pass_the_platforms_own_sha256sum(ready: World) -> None:
    tool = shutil.which("sha256sum")
    if tool is None:
        pytest.skip("sha256sum is not available")
    for repository in (A, B):
        done = subprocess.run(
            [tool, "--check", "--strict", "--quiet", SUMS_NAME],
            cwd=ready.bundle(repository),
            capture_output=True,
            text=True,
            check=False,
        )
        assert done.returncode == 0, done.stdout + done.stderr


def test_git_keeps_the_committed_bytes_exactly_so_the_digests_hold_on_any_checkout(
    ready: World,
) -> None:
    attributes = _git(
        ["check-attr", "text", "eol", "--", f"corrections/{RUN_ID}/x/README.md"], REPO_ROOT
    )
    assert "text: unset" in attributes
    crlf = ready.bundle(A) / "README.original.md"
    assert b"\r" not in crlf.read_bytes()  # the fixture is LF; the attribute is what protects CRLF


def test_the_registry_flip_changes_one_line_per_approved_repository_and_nothing_else(
    ready: World,
) -> None:
    before = (REPO_ROOT / "data" / "registry.json").read_text(encoding="utf-8").splitlines()
    after = (ready.control / "data" / "registry.json").read_text(encoding="utf-8").splitlines()
    changed = [
        line
        for line in difflib.unified_diff(before, after, lineterm="", n=0)
        if line[:1] in "+-" and line[:3] not in ("+++", "---")
    ]
    assert sorted(changed) == sorted(
        ['-      "mode": "dry_run",'] * 2 + ['+      "mode": "full",'] * 2
    )
    modes = {e["repository"]: e["mode"] for e in json.loads("\n".join(after))["entries"]}
    assert modes[A] == modes[B] == "full"
    assert modes["aspose-pdf-foss/Aspose-PDF-FOSS-for-Go"] == "dry_run"  # named in no list


def test_each_record_binds_the_exact_corrected_readme_the_head_and_the_presenter_branch(
    ready: World,
) -> None:
    records = sorted(p.name for p in (ready.control / AUTHORIZATION_DIRNAME).iterdir())
    assert len(records) == 2
    for repository in (A, B):
        document = json.loads(
            (ready.control / ready.record(repository)).read_text(encoding="utf-8")
        )
        corrected = (ready.bundle(repository) / "README.md").read_text(encoding="utf-8")
        assert document["repository"] == repository and document["approver"] == APPROVER
        assert document["candidate_hash"] == sha256_text(corrected)
        assert document["source_revision"] == ready.head(repository)
        assert document["branch"] == BRANCH and document["base_branch"] == "main"


def test_the_committed_pull_request_text_is_what_the_effect_posts(ready: World) -> None:
    text = (ready.bundle(A) / PULL_REQUEST_NAME).read_text(encoding="utf-8")
    run = ready.dispatch(A, record=ready.record(A), do_propose=True)
    assert run.write_ok, run.log
    (pull,) = pulls(ready, A)
    assert text == f"Title: {pull['title']}\n\n{pull['body']}"


def test_assembly_writes_nothing_for_a_repository_the_owner_did_not_name(world: World) -> None:
    world.correct([A, B])
    assemble.assemble(world.control, world.run_dir, RUN_ID, [A], approver=APPROVER)
    assert not world.bundle(B).exists()
    modes = {
        e["repository"]: e["mode"]
        for e in json.loads((world.control / "data" / "registry.json").read_text("utf-8"))[
            "entries"
        ]
    }
    assert modes[A] == "full" and modes[B] == "dry_run"
    assert len(list((world.control / AUTHORIZATION_DIRNAME).iterdir())) == 1


def worktree_state(world: World) -> tuple[bytes, list[str]]:
    registry = (world.control / "data" / "registry.json").read_bytes()
    listing = sorted(
        str(p.relative_to(world.control))
        for p in world.control.rglob("*")
        if ".git" not in p.parts and "runs" not in p.parts
    )
    return registry, listing


def test_a_failed_assembly_leaves_the_worktree_exactly_as_it_was(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    world.correct([A, B])
    before = worktree_state(world)
    heads = {A: world.head(A), B: "f" * 40}  # B moved between the run and the record
    monkeypatch.setattr(
        cli,
        "fetch_default_branch_sha",
        lambda repository, *, token=None: DefaultBranchRead(
            repository, sha=heads[repository], branch="main"
        ),
    )
    with pytest.raises(assemble.AssemblyError, match="draft-proposal-authorization ended"):
        assemble.assemble(world.control, world.run_dir, RUN_ID, [A, B], approver=APPROVER)
    assert worktree_state(world) == before  # not even A's record, bundle or flip is left behind


@pytest.mark.parametrize(
    ("run_id", "repositories", "message"),
    [
        ("../escape", [A], "must be 1-64"),
        ("a;b", [A], "must be 1-64"),
        ("", [A], "must be 1-64"),
        ("x" * 65, [A], "must be 1-64"),
        ("ok", [], "name the approved repositories"),
        ("ok", [A, A], "twice"),
        ("ok", ["acme/not-registered"], "allow-list"),
        ("ok", ["aspose-pdf-foss/Aspose-PDF-FOSS-for-Go"], "no correction bundle"),
    ],
)
def test_assembly_refuses_a_bad_run_id_a_bad_list_and_a_repository_without_a_bundle(
    world: World, run_id: str, repositories: list[str], message: str
) -> None:
    world.correct([A, B])
    before = worktree_state(world)
    with pytest.raises((assemble.AssemblyError, Exception), match=message):
        assemble.assemble(world.control, world.run_dir, run_id, repositories, approver=APPROVER)
    assert worktree_state(world) == before


def test_assembly_refuses_a_run_id_that_exists_a_held_repository_and_a_tampered_source_bundle(
    ready: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = worktree_state(ready)
    with pytest.raises(assemble.AssemblyError, match="exists: a committed run is never rewritten"):
        assemble.assemble(ready.control, ready.run_dir, RUN_ID, [A], approver=APPROVER)
    monkeypatch.setattr(
        assemble,
        "load_holds",
        lambda: {
            A: {
                "reason_code": "UPSTREAM_DEFECT",
                "reason": "file the defect first",
                "pair_with": "issue 12",
                "recorded": "2026-10-11",
            }
        },
    )
    with pytest.raises(assemble.AssemblyError, match="is held: UPSTREAM_DEFECT"):
        assemble.assemble(ready.control, ready.run_dir, "run-2", [A], approver=APPROVER)
    monkeypatch.setattr(assemble, "load_holds", lambda: {})
    (ready.run_dir / slug(A) / "README.md").write_text("# not the correction\n", encoding="utf-8")
    with pytest.raises(Exception, match=r"bundle artifact README\.md is corrupt"):
        assemble.assemble(ready.control, ready.run_dir, "run-2", [A], approver=APPROVER)
    assert worktree_state(ready) == before


def test_assembly_without_records_writes_the_bundles_only(world: World) -> None:
    world.correct([A])
    registry = (world.control / "data" / "registry.json").read_bytes()
    rows = assemble.assemble(world.control, world.run_dir, RUN_ID, [A], approver="", records=False)
    assert rows[0].record is None
    assert (world.control / "data" / "registry.json").read_bytes() == registry
    assert not (world.control / AUTHORIZATION_DIRNAME).exists()
    assert assemble.dispatch_plan(RUN_ID, rows) == [
        "# --- dry runs (do_propose omitted: plan and authorization decision, no write)",
        "# --- the real dispatches (do_propose=true), one at a time, after the dry runs are green",
    ]


def test_the_dispatch_plan_lists_every_dry_run_before_any_real_dispatch(ready: World) -> None:
    plan = assemble.dispatch_plan(
        RUN_ID,
        [
            assemble.Row(
                r,
                ready.head(r),
                "h" * 64,
                {},
                1,
                f"corrections/{RUN_ID}/{slug(r)}",
                ready.record(r),
            )
            for r in (A, B)
        ],
    )
    gh = [line for line in plan if line.startswith("gh workflow run")]
    assert len(gh) == 4 and all(f"-f correction_run={RUN_ID}" in line for line in gh)
    assert all("do_propose" not in line for line in gh[:2]) and all(
        line.endswith("-f do_propose=true") for line in gh[2:]
    )
    assert all("propose.yml -R babar-raza/repository-presenter --ref main" in line for line in gh)


def test_the_tools_main_prints_the_review_list_and_reports_a_refusal(
    world: World, capsys: pytest.CaptureFixture[str]
) -> None:
    world.correct([A])
    code = assemble.main(
        [
            "--root",
            str(world.control),
            "--run",
            str(world.run_dir),
            "--run-id",
            RUN_ID,
            "--repo",
            A,
            "--approver",
            APPROVER,
        ]
    )
    said = capsys.readouterr().out
    assert (
        code == 0
        and f"git add corrections/{RUN_ID}" in said
        and "gh workflow run propose.yml" in said
    )
    assert "authorize nothing until that pull request is merged" in said
    again = assemble.main(
        [
            "--root",
            str(world.control),
            "--run",
            str(world.run_dir),
            "--run-id",
            RUN_ID,
            "--repo",
            A,
            "--approver",
            APPROVER,
        ]
    )
    assert again == 2 and "never rewritten" in capsys.readouterr().err


# --- the dispatch ---------------------------------------------------------------------------------


def test_a_dispatch_without_do_propose_is_a_dry_run_that_writes_nothing_and_mints_one_read_token(
    ready: World,
) -> None:
    run = ready.dispatch(A, record=ready.record(A))
    assert run.dry_run_ok and not run.write_ran, run.log
    assert "the authorization record matches this candidate" in run.log
    assert "correction bundle" in run.log and "SHA256SUMS and pull request text verified" in run.log
    assert run.argv["dry-run"][:3] == ["propose", "--repo", A]
    assert "--correction-bundle" in run.argv["dry-run"] and "--require-sums" in run.argv["dry-run"]
    assert "--propose" not in run.argv["dry-run"]
    assert run.outputs["correction_bundle"] == f"corrections/{RUN_ID}/{slug(A)}"
    assert ready.rests[A].applied_writes() == [] and ready.rests[A].pulls(A) == []
    assert len(run.mints) == 1 and run.mints[0]["permission-contents"] == "read"


def test_a_dry_run_needs_no_record_and_says_so(ready: World) -> None:
    run = ready.dispatch(A)
    assert run.dry_run_ok, run.log
    assert "no --authorization-record given (required for --propose)" in run.log
    assert ready.rests[A].applied_writes() == []


def test_p1_the_write_opens_exactly_one_pull_request_the_app_performed(ready: World) -> None:
    run = ready.dispatch(A, record=ready.record(A), do_propose=True)
    assert run.dry_run_ok and run.write_ran and run.write_ok, run.log
    assert "effected=True" in run.log and f"/{A}/pull/1" in run.log
    assert "--propose" in run.argv["write"] and "--require-sums" in run.argv["write"]
    rest = ready.rests[A]
    (pull,) = pulls(ready, A)
    assert pull["state"] == "open" and "kind: correction" in pull["body"]
    assert pull["performed_via_github_app"]["id"] == EXPECTED_APP_ID
    corrected = (ready.bundle(A) / "README.md").read_text(encoding="utf-8")
    assert rest.file(A, BRANCH, "README.md") == corrected
    assert rest.file(A, "main", "README.md") == README  # the base branch is untouched
    assert f"candidate_hash: {sha256_text(corrected)}" in pull["body"]
    assert f"source_revision: {ready.head(A)}" in pull["body"]
    assert [w["method"] for w in rest.applied_writes()] == ["POST", "PUT", "POST"]  # ref, file, PR
    # the token the write job minted reaches this repository alone, with exactly the effect's scopes
    owner, name = A.split("/")
    read_mint, write_mint = run.mints
    assert (write_mint["owner"], write_mint["repositories"]) == (owner, name)
    assert {k: v for k, v in write_mint.items() if k.startswith("permission-")} == {
        "permission-contents": "write",
        "permission-metadata": "read",
        "permission-pull-requests": "write",
    }
    assert read_mint["permission-contents"] == "read"
    assert (
        ready.rests[B].applied_writes() == [] and ready.rests[B].pulls(B) == []
    )  # B was not dispatched


def test_p2_a_rerun_writes_and_creates_nothing(ready: World) -> None:
    first = ready.dispatch(A, record=ready.record(A), do_propose=True)
    assert first.write_ok, first.log
    writes = len(ready.rests[A].applied_writes())
    again = ready.dispatch(A, record=ready.record(A), do_propose=True)
    assert again.write_ok, again.log
    assert "no change needed" in again.log
    assert len(ready.rests[A].applied_writes()) == writes and len(pulls(ready, A)) == 1


def test_p3_the_second_repository_of_the_wave_is_its_own_pull_request(ready: World) -> None:
    for repository in (A, B):
        run = ready.dispatch(repository, record=ready.record(repository), do_propose=True)
        assert run.write_ok, run.log
    assert [len(pulls(ready, r)) for r in (A, B)] == [1, 1]
    for repository in (A, B):
        corrected = (ready.bundle(repository) / "README.md").read_text(encoding="utf-8")
        assert ready.rests[repository].file(repository, BRANCH, "README.md") == corrected


def test_p4_a_later_correction_run_updates_the_open_pull_request_in_place(ready: World) -> None:
    first = ready.dispatch(A, record=ready.record(A), do_propose=True)
    assert first.write_ok, first.log
    (first_pull,) = [dict(p) for p in pulls(ready, A)]  # a snapshot: the fake mutates in place
    ready.advance_upstream(A, {"README.md": README_V2})  # the maintainers changed the README
    # the next wave: a new correction run at the new head, a new bundle, a new record
    second_dir = ready.tmp / "run-2"
    ready.correct([A], second_dir)
    assemble.assemble(ready.control, second_dir, "2026-10-13", [A], approver=APPROVER)
    ready.merge("merge the second correction pull request")
    assert ready.record(A, "2026-10-13") != ready.record(A)  # a different corrected README
    run = ready.dispatch(
        A, record=ready.record(A, "2026-10-13"), do_propose=True, run_id="2026-10-13"
    )
    assert run.write_ok, run.log
    (pull,) = pulls(ready, A)  # still exactly one pull request: the same one
    assert pull["number"] == first_pull["number"] == 1 and pull["state"] == "open"
    corrected = (ready.bundle(A, "2026-10-13") / "README.md").read_text(encoding="utf-8")
    assert "Version two." in corrected
    assert ready.rests[A].file(A, BRANCH, "README.md") == corrected
    assert pull["body"] != first_pull["body"]  # the provenance block names the new head
    assert f"source_revision: {ready.head(A)}" in pull["body"]
    assert f"candidate_hash: {sha256_text(corrected)}" in pull["body"]
    assert ready.rests[A].file(A, "main", "README.md") == README_V2  # still no push to the base


def test_the_old_record_cannot_authorize_the_new_head(ready: World) -> None:
    ready.advance_upstream(A, {"README.md": README_V2})
    run = ready.dispatch(A, record=ready.record(A), do_propose=True)
    assert not run.dry_run_ok and "source_moved" in run.log
    assert ready.rests[A].applied_writes() == []


# --- refusals: nothing is written ----------------------------------------------------------------


def refused(world: World, run: Run, fragment: str, repository: str = A) -> None:
    assert not (run.dry_run_ok and run.write_ok), run.log
    assert fragment in run.log, run.log
    assert world.rests[repository].applied_writes() == [] and pulls(world, repository) == []


def test_a_write_dispatch_without_an_authorization_record_fails_at_validation(ready: World) -> None:
    run = ready.dispatch(A, do_propose=True)
    assert not run.dry_run_ok and run.failed_step.startswith("Validate every dispatch input")
    refused(ready, run, "authorization_record")


def test_a_record_that_is_not_in_the_checkout_fails_before_anything_is_installed(
    ready: World,
) -> None:
    missing = "ops/proposal-authorizations/does-not-exist.json"
    run = ready.dispatch(A, record=missing, do_propose=True)
    assert run.failed_step.startswith("Confirm the authorization record")
    refused(ready, run, "authorization record is missing")


def test_a_record_edited_after_it_was_merged_is_not_the_merged_record(ready: World) -> None:
    path = ready.control / ready.record(A)
    path.write_text(
        path.read_text(encoding="utf-8").replace(APPROVER, "someone-else", 1), encoding="utf-8"
    )
    run = ready.dispatch(A, record=ready.record(A), do_propose=True)
    assert not run.dry_run_ok
    refused(ready, run, "authorization_not_committed")


def test_a_record_for_another_repositorys_correction_does_not_authorize_this_one(
    ready: World,
) -> None:
    run = ready.dispatch(A, record=ready.record(B), do_propose=True)
    assert not run.dry_run_ok
    refused(ready, run, "authorization")


def test_an_expired_record_is_refused(ready: World, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_cli_utc_now", lambda: "2099-01-01T00:00:00Z")
    run = ready.dispatch(A, record=ready.record(A), do_propose=True)
    assert not run.dry_run_ok
    refused(ready, run, "expired")


def set_mode(world: World, repository: str, mode: str) -> None:
    path = world.control / "data" / "registry.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    for entry in document["entries"]:
        if entry["repository"] == repository:
            entry["mode"] = mode
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def test_an_entry_still_at_dry_run_never_reaches_a_write(ready: World) -> None:
    set_mode(ready, A, "dry_run")
    run = ready.dispatch(A, record=ready.record(A), do_propose=True)
    assert run.dry_run_ok and run.write_ran and not run.write_ok  # the dry run only reports
    refused(ready, run, "registry_dry_run")


def test_the_owner_switch_closed_and_no_token_and_a_wrong_scope_token_write_nothing(
    ready: World,
) -> None:
    record = ready.record(A)
    # the write step sets the switch and receives the minted token; take each away in turn
    closed = ready.dispatch(A, record=record, do_propose=True, write_env={SWITCH: None})
    refused(ready, closed, "write_not_enabled")
    no_token = ready.dispatch(A, record=record, do_propose=True, write_env={TOKEN: None})
    refused(ready, no_token, "no_write_token")
    personal = ready.dispatch(
        A, record=record, do_propose=True, write_env={TOKEN: "ghp_a_personal_access_token"}
    )
    refused(ready, personal, "token_not_installation")
    wide = fake_rest.FakeGitHubRest(app_id=EXPECTED_APP_ID, installation_scope=[A, B])
    wide._repos[A] = ready.rests[A]._repos[A]  # the same repository, reached by a token that also
    ready.rests[A] = wide  # reaches B: more than the one target
    broad = ready.dispatch(A, record=record, do_propose=True)
    refused(ready, broad, "token_wrong_scope")


def test_a_dispatch_naming_a_run_that_is_not_committed_is_refused(ready: World) -> None:
    run = ready.dispatch(A, record=ready.record(A), do_propose=True, run_id="no-such-run")
    assert run.failed_step.startswith("Verify the committed correction bundle")
    refused(ready, run, "the correction bundle is not in this checkout")


def test_a_run_that_does_not_hold_this_repository_is_refused(ready: World) -> None:
    shutil.rmtree(ready.bundle(B))
    run = ready.dispatch(B, record=ready.record(A), do_propose=True)
    refused(ready, run, "the correction bundle is not in this checkout", B)


def test_a_correction_cannot_be_combined_with_a_sealed_candidates_artifact(ready: World) -> None:
    run = ready.dispatch(A, record=ready.record(A), candidate_artifact=f"sealed-{slug(A)}")
    assert run.failed_step.startswith("Validate every dispatch input")
    refused(ready, run, "cannot be combined with candidate_artifact")


@pytest.mark.parametrize("name", sorted(COMMITTED_FILES))
def test_editing_any_committed_file_is_refused_by_the_sha256sums_step(
    ready: World, name: str
) -> None:
    record = ready.record(A)  # the merged record, named for the corrected README as reviewed
    path = ready.bundle(A) / name
    path.write_bytes(path.read_bytes() + b"\n")
    run = ready.dispatch(A, record=record, do_propose=True)
    assert run.failed_step.startswith("Verify the committed correction bundle")
    refused(ready, run, "does not match its SHA256SUMS")


def test_a_missing_sums_file_is_refused(ready: World) -> None:
    (ready.bundle(A) / SUMS_NAME).unlink()
    run = ready.dispatch(A, record=ready.record(A), do_propose=True)
    refused(ready, run, "has no SHA256SUMS")


def test_a_forger_who_recomputes_the_sums_is_refused_by_the_typed_gate_and_the_record(
    ready: World,
) -> None:
    record = ready.record(A)
    readme = ready.bundle(A) / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8") + "\nA forged paragraph.\n", encoding="utf-8"
    )
    write_sums(ready.bundle(A))  # the platform's check now passes
    run = ready.dispatch(A, record=record, do_propose=True)
    assert run.failed_step.startswith("Propose") or run.failed_step.startswith("Dry run")
    assert "the committed bundle is not intact" not in run.log  # the digests agree with the forgery
    refused(ready, run, "bundle_inconsistent")


def test_an_extra_file_in_a_committed_bundle_is_refused_by_the_command_though_sha256sum_passes(
    ready: World,
) -> None:
    (ready.bundle(A) / "run.log").write_text("internal\n", encoding="utf-8")
    run = ready.dispatch(A, record=ready.record(A), do_propose=True)
    assert run.failed_step.startswith("Dry run")  # step one (sha256sum) passed; the command refused
    refused(ready, run, "run.log is not part of a committed correction bundle")


def test_pull_request_text_edited_after_review_is_refused(ready: World) -> None:
    path = ready.bundle(A) / PULL_REQUEST_NAME
    path.write_text(
        path.read_text(encoding="utf-8").replace("### How to decline", "### Ignore"),
        encoding="utf-8",
    )
    write_sums(ready.bundle(A))
    run = ready.dispatch(A, record=ready.record(A), do_propose=True)
    refused(ready, run, "not the pull request text")


def test_a_moved_head_is_refused_in_the_dry_run_and_nothing_is_written(ready: World) -> None:
    ready.advance_upstream(A, {"NOTES.md": "an unrelated maintainer commit\n"})
    run = ready.dispatch(A, record=ready.record(A), do_propose=True)
    assert not run.dry_run_ok and not run.write_ran
    refused(ready, run, "source_moved")
    assert run.cli_exit["dry-run"] == EXIT_UNSAFE


def test_a_head_that_moves_between_the_dry_run_and_the_write_is_refused_by_the_effect(
    ready: World,
) -> None:
    run = ready.dispatch(
        A,
        record=ready.record(A),
        do_propose=True,
        between=lambda: ready.advance_upstream(A, {"NOTES.md": "moved after the dry run\n"}),
    )
    assert run.dry_run_ok and run.write_ran and not run.write_ok
    assert run.cli_exit["write"] == EXIT_UNSAFE
    refused(ready, run, "source_moved")


def test_a_closed_pull_request_is_not_recreated(ready: World) -> None:
    first = ready.dispatch(A, record=ready.record(A), do_propose=True)
    assert first.write_ok, first.log
    ready.rests[A].close_pull(A, 1)
    writes = len(ready.rests[A].applied_writes())
    again = ready.dispatch(A, record=ready.record(A), do_propose=True)
    assert not again.write_ok and "pr_already_closed" in again.log
    assert len(ready.rests[A].applied_writes()) == writes and len(pulls(ready, A)) == 1


def test_the_scheduled_path_and_the_sealed_candidate_path_are_unchanged_when_no_run_is_named(
    ready: World,
) -> None:
    run = ready.dispatch(A, record=ready.record(A), run_id="")
    assert run.outputs["correction_bundle"] == ""
    assert "--correction-bundle" not in run.argv.get("dry-run", []) or not run.dry_run_ok
    assert "Verify the committed correction bundle" not in run.log
    # without a correction the command looks for a sealed candidate, which this control repository
    # does not hold: nothing is proposed
    assert not run.dry_run_ok and ready.rests[A].applied_writes() == []


def test_the_tools_main_reads_a_repos_file_and_writes_bundles_only_on_request(
    world: World, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    world.correct([A, B])
    listing = tmp_path / "wave.txt"
    listing.write_text(f"# the approved list\n{A}  # first\n\n{B}\n", encoding="utf-8")
    code = assemble.main(
        [
            "--root",
            str(world.control),
            "--run",
            str(world.run_dir),
            "--run-id",
            RUN_ID,
            "--repos-file",
            str(listing),
            "--no-records",
        ]
    )
    said = capsys.readouterr().out
    assert code == 0 and "assembled 2 correction(s)" in said and "gh workflow run" not in said
    assert world.bundle(A).is_dir() and world.bundle(B).is_dir()
    assert not (world.control / AUTHORIZATION_DIRNAME).exists()


def test_the_tools_main_wants_an_approver_unless_it_writes_no_records(world: World) -> None:
    world.correct([A])
    with pytest.raises(SystemExit):
        assemble.main(
            [
                "--root",
                str(world.control),
                "--run",
                str(world.run_dir),
                "--run-id",
                RUN_ID,
                "--repo",
                A,
            ]
        )
    assert not (world.control / "corrections").exists()
