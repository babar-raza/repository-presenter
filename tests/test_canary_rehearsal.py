"""The sandbox canary, rehearsed end to end against the local fakes (no network, no GitHub write).

The canary (docs/PROPOSAL_WAVE_RUNBOOK.md section 9) opens one README-correction pull request on the
owner's throwaway repository ``babar-raza/presenter-sandbox``. Every step the owner and the
hosted workflow will take is taken here, through the same entry points, in the same order:

1. the owner seeds the sandbox from a product (``tools/canary/seed.py --commit`` on two local
   clones makes the pinned, reproducible seed commit; the sandbox is a local bare remote and the
   owner's push is a push to it). The bundle is reviewed and merged BEFORE that push, so the
   commit it names must be reproducible: ``ops/sandbox-canary/seed.json`` pins it;
2. ``correct-readme --sandbox`` clones the sandbox head and writes the correction bundle;
3. ``tools/canary/canary.py assemble`` validates the bundle through the typed gate, commits it
   under ``ops/sandbox-canary/bundle``, sets the sandbox entry to ``full`` and drafts the record;
   the control repository merges it (a real git history with ``origin/main``);
4. ``propose --sandbox --correction-bundle`` runs as ``propose-sandbox.yml`` runs it, dry-run then
   ``--propose``, with the real GitHub client, effect, token and App-attribution checks bound to
   the stateful fake REST (``tools/workflow_rehearsal/fake_rest.py``);
5. ``tools/canary/canary.py verify`` reads back what the run did, as the owner will.

What the rehearsal proves, each with its negative control: one pull request attributed to the App;
a rerun writes nothing; a closed pull request is not recreated; a moved sandbox head is refused
with nothing written; an interrupted write (branch created, answer lost) converges to exactly one
pull request; no unauthorized path writes; the production registry and its portfolio count are
byte-for-byte untouched; the sandbox cannot be reached without ``--sandbox`` and a product cannot be
reached with it.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest

from repository_presenter import cli
from repository_presenter.cli import EXIT_OK, EXIT_UNSAFE, EXIT_USAGE, main
from repository_presenter.components.propose.effect import (
    AUTHORIZATION_VARIABLE,
    presenter_branch_name,
)
from repository_presenter.components.readme_correction import run as correction_run
from repository_presenter.components.readme_correction.committed import sums_problems
from repository_presenter.core.authorization.proposal import AUTHORIZATION_DIRNAME, record_filename
from repository_presenter.core.authorization.refusals import WriteRefusedError
from repository_presenter.core.facts import Evidence, Fact, FactsDocument, write_facts
from repository_presenter.core.git_safety.clone import pinned_read_only_clone
from repository_presenter.core.github.read_client import DefaultBranchRead
from repository_presenter.core.hashing import sha256_text
from repository_presenter.core.registry.loader import load_registry, require_listed
from repository_presenter.core.registry.sandbox import (
    SANDBOX_REGISTRY_RELATIVE_PATH,
    load_registry_for,
)
from support import REPO_ROOT, merge_to_origin_main, write_cursor

TOOLS = REPO_ROOT / "tools"
sys.path.insert(0, str(TOOLS / "workflow_rehearsal"))
sys.path.insert(0, str(TOOLS / "canary"))

import canary  # noqa: E402
import cycle  # noqa: E402
import fake_rest  # noqa: E402
import scenarios  # noqa: E402
import seed  # noqa: E402

SANDBOX = "babar-raza/presenter-sandbox"
PRODUCT = "aspose-cells-foss/Aspose.Cells-FOSS-for-Go"
SANDBOX_ID = 1412405801  # the live repository id data/registry_sandbox.json records
BRANCH = presenter_branch_name()

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
PRODUCT_FILES = {
    "README.md": README,
    "LICENSE": "MIT License\n",
    "go.mod": "module example.invalid/synthetic\n\ngo 1.24\n",
    "doc.go": "// Package synthetic does one thing.\npackage synthetic\n",
    "docs/usage.md": "Use it.\n",
    ".github/workflows/ci.yml": "name: ci\non: push\njobs: {}\n",
}


def _git(args: list[str], cwd: Path) -> str:
    return scenarios._git(args, cwd)


def _facts(revision: str) -> FactsDocument:
    def fact(fact_id: str, value: str, path: str, detail: str | None = None) -> Fact:
        return Fact(
            id=fact_id,
            kind=fact_id.split(":", 1)[0],  # type: ignore[arg-type]
            value=value,
            evidence=(Evidence(path, detail),),
        )

    return FactsDocument(
        SANDBOX,
        revision,
        (
            fact("identity:repository", SANDBOX, "data/registry_sandbox.json"),
            fact("license:spdx", "MIT", "LICENSE", "license text states this license"),
            fact("license:file", "LICENSE", "LICENSE"),
            fact("dependency:none", "none", "go.mod", "declares none"),
        ),
    )


def closed_registry() -> bytes:
    """The committed sandbox registry as it is before ``assemble`` flips it: the canary's pull
    request commits it at ``full``, so the rehearsal closes it first."""
    text = (REPO_ROOT / SANDBOX_REGISTRY_RELATIVE_PATH).read_text(encoding="utf-8")
    return text.replace('"mode": "full"', '"mode": "dry_run"').encode("utf-8")


@dataclass
class World:
    """One rehearsal: a product, a seeded sandbox (local bare remotes), a control checkout and a
    fake GitHub that remembers every write."""

    tmp: Path
    world: Path
    sandbox_bare: Path
    sandbox_clone: Path
    control: Path
    rest: fake_rest.FakeGitHubRest
    bundle: Path
    seed_plan: seed.SeedPlan
    revision: str
    sandbox_before: Path
    trigger: str = ""

    def head(self) -> str:
        return _git(["rev-parse", "main"], self.sandbox_bare)

    @property
    def pin_path(self) -> Path:
        return self.control / canary.SEED_PIN_RELATIVE

    @property
    def record(self) -> Path:
        corrected = (self.control / canary.BUNDLE_RELATIVE / "README.md").read_text(
            encoding="utf-8"
        )
        return (
            self.control / AUTHORIZATION_DIRNAME / record_filename(SANDBOX, sha256_text(corrected))
        )

    def fresh_rest(self, *, installed: list[str] | None = None) -> fake_rest.FakeGitHubRest:
        """A GitHub that holds the seeded sandbox exactly as the bare remote does now."""
        rest = fake_rest.FakeGitHubRest(
            app_id=canary.EXPECTED_APP_ID,
            installation_scope=[SANDBOX] if installed is None else installed,
        )
        files = {
            path: (self.sandbox_clone / path).read_text(encoding="utf-8")
            for path in _git(["ls-files"], self.sandbox_clone).splitlines()
            if path != "README.md"
        }
        rest.add_repository(
            SANDBOX,
            tip=self.head(),
            repository_id=SANDBOX_ID,
            readme=(self.sandbox_clone / "README.md").read_text(encoding="utf-8"),
            files=files,
        )
        return rest

    def propose(self, *flags: str, record: Path | None = None, trigger: str | None = None) -> int:
        record = self.record if record is None else record
        return main(
            [
                "propose",
                "--sandbox",
                "--repo",
                SANDBOX,
                "--root",
                str(self.control),
                "--correction-bundle",
                str(self.control / canary.BUNDLE_RELATIVE),
                "--authorization-record",
                str(record),
                "--trigger-sha",
                trigger or self.trigger,
                *flags,
            ]
        )

    def write(self, **kwargs: Any) -> int:
        return self.propose("--propose", **kwargs)

    def verify(
        self, expect: str = "open", rest: fake_rest.FakeGitHubRest | None = None
    ) -> list[Any]:
        return canary.verify(
            self.control, expect=expect, token=cycle.FAKE_TOKEN, fetch=(rest or self.rest).fetch
        )


def bind(monkeypatch: pytest.MonkeyPatch, rest: fake_rest.FakeGitHubRest) -> None:
    """Point every GitHub-facing name ``cli`` holds at ``rest``; the real client code runs on it."""
    seams = cycle.propose_seams(rest, SANDBOX)
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
        monkeypatch.setattr(cli, name, seams[target])


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> World:
    # --- the product and the sandbox, as local bare remotes ------------------------------------
    base = tmp_path / "base"
    base.mkdir()
    scenarios.build_repository(
        base, "Aspose.Cells-FOSS-for-Go", [("initial", PRODUCT_FILES)], owner="aspose-cells-foss"
    )
    product = tmp_path / "product"
    _git(
        [
            "clone",
            "-q",
            str(base / "upstreams" / "aspose-cells-foss" / "Aspose.Cells-FOSS-for-Go.git"),
            str(product),
        ],
        tmp_path,
    )
    scenarios.build_repository(
        base,
        "presenter-sandbox",
        [
            (
                "Initial commit",
                {"README.md": "# presenter-sandbox\n\nThrowaway.\n", "LICENSE": "MIT\n"},
            )
        ],
        owner="babar-raza",
    )
    sandbox_bare = base / "upstreams" / "babar-raza" / "presenter-sandbox.git"
    sandbox_before = tmp_path / "sandbox-before.git"  # the sandbox as it is before the seed
    shutil.copytree(sandbox_bare, sandbox_before)
    sandbox_clone = tmp_path / "sandbox"
    _git(["clone", "-q", str(sandbox_bare), str(sandbox_clone)], tmp_path)

    # --- step 1, the owner's seeding: the pinned commit, then one push (to the local bare remote)
    plan = seed.plan_seed(product, sandbox_clone, check_remote=False)
    commit = seed.build_seed_commit(
        plan,
        product,
        sandbox_clone,
        message=seed.seed_message(PRODUCT, plan.product_revision),
    )
    _git(["update-ref", f"refs/heads/{seed.SEED_BRANCH}", commit.sha], sandbox_clone)
    _git(["push", "-q", "origin", f"{seed.SEED_BRANCH}:main"], sandbox_clone)
    _git(["merge", "-q", "--ff-only", seed.SEED_BRANCH], sandbox_clone)
    revision = _git(["rev-parse", "main"], sandbox_bare)
    assert revision == commit.sha

    # --- the control checkout: the real registries and a git history with origin/main ----------
    control = tmp_path / "control"
    write_cursor(control)
    (control / "data").mkdir(exist_ok=True)
    shutil.copyfile(REPO_ROOT / "data" / "registry.json", control / "data" / "registry.json")
    (control / SANDBOX_REGISTRY_RELATIVE_PATH).write_bytes(closed_registry())
    (control / canary.SEED_PIN_RELATIVE).parent.mkdir(parents=True)
    seed.write_pin(
        control / canary.SEED_PIN_RELATIVE, product_repository=PRODUCT, plan=plan, commit=commit
    )
    merge_to_origin_main(control, "the control repository before the canary")

    # --- the local stand-ins for the network ----------------------------------------------------
    monkeypatch.setattr(
        correction_run,
        "pinned_read_only_clone",
        lambda url, destination, **kwargs: pinned_read_only_clone(str(sandbox_bare), destination),
    )
    monkeypatch.setattr(
        cli,
        "fetch_default_branch_sha",
        lambda repo, *, token=None: DefaultBranchRead(
            repo, sha=_git(["rev-parse", "main"], sandbox_bare), branch="main"
        ),
    )

    # --- step 2, the correction bundle for the sandbox head -------------------------------------
    facts = tmp_path / "facts.json"
    write_facts(_facts(revision), facts)
    bundle = tmp_path / "bundle"
    code = main(
        [
            "correct-readme",
            "--sandbox",
            "--repo",
            SANDBOX,
            "--root",
            str(control),
            "--facts",
            str(facts),
            "--out",
            str(bundle),
        ]
    )
    assert code == EXIT_OK

    # --- step 3, assemble and merge -------------------------------------------------------------
    written = canary.assemble(control, bundle, approver="babar-raza")
    assert written[0] == "ops/sandbox-canary/bundle"
    trigger = merge_to_origin_main(control, "merge the canary pull request")

    rest = fake_rest.FakeGitHubRest(app_id=canary.EXPECTED_APP_ID, installation_scope=[SANDBOX])
    built = World(
        tmp_path,
        base,
        sandbox_bare,
        sandbox_clone,
        control,
        rest,
        bundle,
        plan,
        revision,
        sandbox_before,
        trigger,
    )
    built.rest = built.fresh_rest()
    bind(monkeypatch, built.rest)
    monkeypatch.setenv("GH_PROPOSAL_WRITE_TOKEN", cycle.FAKE_TOKEN)
    return built


def allow_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(AUTHORIZATION_VARIABLE, "1")  # what the workflow's write step sets, alone


def statuses(lines: list[Any]) -> dict[str, str]:
    return {line.check: line.status for line in lines}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- seeding ------------------------------------------------------------------------------------


def test_seeding_copies_the_products_committed_tree_and_drops_automation(world: World) -> None:
    plan = world.seed_plan
    assert plan.product_revision
    assert sorted(b.path for b in plan.copy) == [
        "LICENSE",
        "README.md",
        "doc.go",
        "docs/usage.md",
        "go.mod",
    ]
    assert plan.dropped == [".github/workflows/ci.yml"]
    seeded = _git(["ls-files"], world.sandbox_clone).splitlines()
    assert sorted(seeded) == sorted(b.path for b in plan.copy)  # a faithful copy, not a merge
    assert not (world.sandbox_clone / ".github").exists()  # nothing that would run in the sandbox
    assert (world.sandbox_clone / "README.md").read_text(encoding="utf-8") == README
    assert (
        _git(["log", "--format=%s", "-3"], world.sandbox_bare).splitlines()[1] == "Initial commit"
    )


def test_seeding_refuses_the_wrong_remote_a_dirty_sandbox_and_a_readmeless_product(
    world: World, tmp_path: Path
) -> None:
    with pytest.raises(seed.SeedError, match="origin is not babar-raza/presenter-sandbox"):
        seed.plan_seed(tmp_path / "product", world.sandbox_clone)  # origin is a local path
    assert seed.SANDBOX_REMOTE.search("https://github.com/babar-raza/presenter-sandbox.git")
    assert seed.SANDBOX_REMOTE.search("git@github.com:babar-raza/presenter-sandbox")
    assert not seed.SANDBOX_REMOTE.search("https://github.com/babar-raza/repository-presenter.git")
    assert not seed.SANDBOX_REMOTE.search("https://github.com/aspose-cells-foss/x.git")
    (world.sandbox_clone / "stray.txt").write_text("x", encoding="utf-8")
    with pytest.raises(seed.SeedError, match="uncommitted changes"):
        seed.plan_seed(tmp_path / "product", world.sandbox_clone, check_remote=False)
    (world.sandbox_clone / "stray.txt").unlink()
    nothing = tmp_path / "no-readme"
    _git(["init", "-q", "-b", "main", str(nothing)], tmp_path)
    (nothing / "main.go").write_text("package x\n", encoding="utf-8")
    _git(["add", "-A"], nothing)
    _git(["commit", "-q", "-m", "x"], nothing)
    with pytest.raises(seed.SeedError, match=r"no README\.md"):
        seed.plan_seed(nothing, world.sandbox_clone, check_remote=False)


def fresh_clones(world: World, tmp_path: Path, name: str) -> tuple[Path, Path]:
    """A product clone and a clone of the sandbox as it was BEFORE the seed, as a different owner's
    machine would hold them; their ``origin`` URLs read as the real repositories (the tool only
    reads the URL string and never contacts it)."""
    product = tmp_path / f"{name}-product"
    sandbox = tmp_path / f"{name}-sandbox"
    upstream = world.world / "upstreams" / "aspose-cells-foss" / "Aspose.Cells-FOSS-for-Go.git"
    _git(["clone", "-q", str(upstream), str(product)], tmp_path)
    _git(["clone", "-q", str(world.sandbox_before), str(sandbox)], tmp_path)
    _git(["remote", "set-url", "origin", f"https://github.com/{PRODUCT}.git"], product)
    _git(["remote", "set-url", "origin", f"https://github.com/{SANDBOX}.git"], sandbox)
    return product, sandbox


def seed_args(product: Path, sandbox: Path, pin: Path, *flags: str) -> list[str]:
    return ["--product", str(product), "--sandbox", str(sandbox), "--pin", str(pin), *flags]


def test_the_seed_commit_is_the_same_commit_on_any_machine_and_nothing_is_pushed(
    world: World, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pin = seed.load_pin(world.pin_path)
    assert pin.commit == world.revision  # the bundle, the record and the pin name one commit
    product, sandbox = fresh_clones(world, tmp_path, "other")
    for key, value in (  # another identity, signing on with a program that cannot sign, CRLF policy
        ("user.name", "Someone Else"),
        ("user.email", "someone@example.invalid"),
        ("commit.gpgsign", "true"),
        ("gpg.program", "false"),
        ("core.autocrlf", "true"),
        ("core.filemode", "false"),
    ):
        _git(["config", key, value], sandbox)
    assert _git(["rev-parse", "HEAD"], sandbox) == pin.sandbox_parent
    assert seed.main(seed_args(product, sandbox, world.pin_path)) == 0  # plan only
    assert "plan only" in capsys.readouterr().out
    assert _git(["branch", "--list", seed.SEED_BRANCH], sandbox) == ""
    assert seed.main(seed_args(product, sandbox, world.pin_path, "--commit")) == 0
    said = capsys.readouterr().out
    assert _git(["rev-parse", seed.SEED_BRANCH], sandbox) == pin.commit  # byte for byte
    assert f"push origin {seed.SEED_BRANCH}:main" in said and "Nothing is pushed" in said
    assert _git(["rev-parse", "HEAD"], sandbox) == pin.sandbox_parent  # the clone's own branch
    assert _git(["status", "--porcelain"], sandbox) == ""  # and its working tree are untouched
    assert _git(["rev-parse", f"{seed.SEED_BRANCH}^"], sandbox) == pin.sandbox_parent
    # one commit on top of the sandbox's history: the product's history does not travel
    assert _git(["rev-list", "--count", seed.SEED_BRANCH], sandbox) == "2"
    shown = _git(
        ["log", "-1", "--format=%an <%ae>|%cn <%ce>|%at|%ct|%G?", seed.SEED_BRANCH], sandbox
    )
    who = f"{seed.SEED_NAME} <{seed.SEED_EMAIL}>"
    assert shown == f"{who}|{who}|1791763200|1791763200|N"  # never signed
    # the tree is the product's committed tree minus .github/, whatever the clone's filters say
    seeded = _git(["ls-tree", "-r", "--name-only", seed.SEED_BRANCH], sandbox).splitlines()
    assert sorted(seeded) == sorted(b.path for b in world.seed_plan.copy)
    assert ".github/workflows/ci.yml" not in seeded
    assert _git(["rev-parse", f"{seed.SEED_BRANCH}^{{tree}}"], sandbox) == pin.tree


def test_the_seed_commit_refuses_anything_but_the_pinned_inputs(
    world: World, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def refused(product: Path, sandbox: Path, pin: Path, fragment: str) -> None:
        assert seed.main(seed_args(product, sandbox, pin, "--commit")) == 2
        assert fragment in capsys.readouterr().err
        assert _git(["branch", "--list", seed.SEED_BRANCH], sandbox) == ""  # nothing made

    # the product moved on: HEAD is not the pinned revision
    product, sandbox = fresh_clones(world, tmp_path, "moved-product")
    (product / "extra.go").write_text("package x\n", encoding="utf-8")
    _git(["add", "-A"], product)
    _git(["commit", "-q", "-m", "a later product commit"], product)
    refused(product, sandbox, world.pin_path, "the pin seeds")
    # the sandbox moved on since the pin: the pinned commit would not be a fast-forward
    product, sandbox = fresh_clones(world, tmp_path, "moved-sandbox")
    (sandbox / "NOTES.md").write_text("an owner commit\n", encoding="utf-8")
    _git(["add", "-A"], sandbox)
    _git(["commit", "-q", "-m", "an unrelated owner commit"], sandbox)
    refused(product, sandbox, world.pin_path, "moved since the pin")
    # another product's clone
    product, sandbox = fresh_clones(world, tmp_path, "wrong-product")
    other = "https://github.com/aspose-pdf-foss/Aspose.PDF-FOSS-for-Go.git"
    _git(["remote", "set-url", "origin", other], product)
    refused(product, sandbox, world.pin_path, "the pin seeds that product only")
    # a clone of another repository standing in for the sandbox
    product, sandbox = fresh_clones(world, tmp_path, "wrong-sandbox")
    control = "https://github.com/babar-raza/repository-presenter.git"
    _git(["remote", "set-url", "origin", control], sandbox)
    refused(product, sandbox, world.pin_path, "seeding refuses any other repository")
    # a pin that names a commit this tool does not make (an edited tree), or an unpinned message
    product, sandbox = fresh_clones(world, tmp_path, "tampered-pin")
    document = json.loads(world.pin_path.read_text("utf-8"))
    document["seed"]["commit"] = "a" * 40
    tampered = tmp_path / "tampered-seed.json"
    tampered.write_text(json.dumps(document), encoding="utf-8")
    refused(product, sandbox, tampered, "not the pinned")
    document["seed"]["message"] = "Seed the sandbox with something else"
    tampered.write_text(json.dumps(document), encoding="utf-8")
    refused(product, sandbox, tampered, "message")
    # an unreadable pin
    product, sandbox = fresh_clones(world, tmp_path, "no-pin")
    refused(product, sandbox, tmp_path / "absent.json", "cannot be read")


def test_the_committed_canary_assets_agree_with_each_other() -> None:
    """The reviewed pull request's files, as committed: one source revision everywhere. (They are
    not re-derived through the correction gate here: that proof is the operator's `preflight` and
    the hosted dry run, so a later change to the engine cannot turn this suite red.)"""
    pin = seed.load_pin(REPO_ROOT / canary.SEED_PIN_RELATIVE)
    bundle = REPO_ROOT / canary.BUNDLE_RELATIVE
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["repository"] == SANDBOX and manifest["revision"] == pin.commit
    assert sums_problems(bundle) == []  # sha256sum --check agrees with the committed bytes
    entry = load_registry_for(REPO_ROOT, sandbox=True).entries[0]
    product = require_listed(
        load_registry(REPO_ROOT / "data" / "registry.json"), pin.product_repository
    )
    # the sandbox is a copy of this product, so it is read with this product's vocabulary
    assert (entry.family, entry.platform, entry.ecosystem) == (
        product.family,
        product.platform,
        product.ecosystem,
    )
    corrected = (bundle / "README.md").read_text(encoding="utf-8")
    prefix = SANDBOX.replace("/", "__")
    (record,) = sorted((REPO_ROOT / AUTHORIZATION_DIRNAME).glob(f"{prefix}__*"))
    assert record.name == record_filename(SANDBOX, sha256_text(corrected))
    document = json.loads(record.read_text(encoding="utf-8"))
    assert document["source_revision"] == pin.commit and document["repository"] == SANDBOX
    assert document["candidate_hash"] == sha256_text(corrected)
    assert document["approver"] == "babar-raza" and document["branch"] == BRANCH
    assert entry.mode == "full"  # open exactly because the record above is committed with it


# --- the bundle and the assembled pull request ---------------------------------------------------


def test_the_bundle_is_a_correction_of_the_sandbox_head_and_assembly_flips_only_the_sandbox(
    world: World,
) -> None:
    manifest = json.loads(
        (world.control / canary.BUNDLE_RELATIVE / "manifest.json").read_text("utf-8")
    )
    assert manifest["repository"] == SANDBOX and manifest["revision"] == world.revision
    assert manifest["summary"]["DIAGRAM_FIX"] == 1  # the structural fix the canary proposes
    sandbox = json.loads((world.control / SANDBOX_REGISTRY_RELATIVE_PATH).read_text("utf-8"))
    assert [(e["repository"], e["mode"]) for e in sandbox["entries"]] == [(SANDBOX, "full")]
    record = json.loads(world.record.read_text("utf-8"))
    assert record["repository"] == SANDBOX and record["source_revision"] == world.revision
    assert record["branch"] == BRANCH and record["base_branch"] == "main"
    corrected = (world.control / canary.BUNDLE_RELATIVE / "README.md").read_text(encoding="utf-8")
    assert record["candidate_hash"] == sha256_text(corrected)  # the record binds this exact text
    assert record["approver"] == "babar-raza"


def test_assembly_changes_exactly_one_line_of_the_registry_and_refuses_carriage_returns(
    world: World, tmp_path: Path
) -> None:
    before = closed_registry().decode("utf-8")
    assert '"mode": "dry_run"' in before
    after = (world.control / SANDBOX_REGISTRY_RELATIVE_PATH).read_text(encoding="utf-8")
    assert after == before.replace('"mode": "dry_run"', '"mode": "full"')  # the one line to review
    assert after == (REPO_ROOT / SANDBOX_REGISTRY_RELATIVE_PATH).read_text(encoding="utf-8")
    assert canary.carriage_return_files(world.bundle) == []
    crlf = tmp_path / "crlf"
    crlf.mkdir()
    (crlf / "README.md").write_bytes(b"a\r\nb\n")
    (crlf / "tree.txt").write_bytes(b"a\n")
    assert canary.carriage_return_files(crlf) == ["README.md"]


def unassembled_control(world: World, tmp_path: Path) -> Path:
    """A control checkout as it is before ``assemble``: the committed (closed) sandbox registry
    and no ``ops/``."""
    other = tmp_path / "other-control"
    shutil.copytree(world.control, other, ignore=shutil.ignore_patterns(".git"))
    shutil.rmtree(other / canary.BUNDLE_RELATIVE)  # the seed pin, committed earlier, stays
    shutil.rmtree(other / AUTHORIZATION_DIRNAME)
    (other / "data" / "registry_sandbox.json").write_bytes(closed_registry())
    return other


def sandbox_mode(control: Path) -> str:
    document = json.loads((control / SANDBOX_REGISTRY_RELATIVE_PATH).read_text("utf-8"))
    return str(document["entries"][0]["mode"])


def test_assembly_refuses_a_tampered_bundle_and_writes_nothing(
    world: World, tmp_path: Path
) -> None:
    other = unassembled_control(world, tmp_path)
    tampered = tmp_path / "tampered"
    shutil.copytree(world.bundle, tampered)
    (tampered / "README.md").write_text("# not the correction\n", encoding="utf-8")
    with pytest.raises(WriteRefusedError):
        canary.assemble(other, tampered, approver="babar-raza")
    assert not (other / canary.BUNDLE_RELATIVE).exists()
    assert not (other / AUTHORIZATION_DIRNAME).exists()
    assert sandbox_mode(other) == "dry_run"


def test_a_failed_assembly_leaves_the_worktree_as_it_was(
    world: World, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = unassembled_control(world, tmp_path)
    monkeypatch.setattr(  # the owner pushed again between the bundle and the record
        cli,
        "fetch_default_branch_sha",
        lambda repo, *, token=None: DefaultBranchRead(repo, sha="f" * 40, branch="main"),
    )
    with pytest.raises(RuntimeError, match="source_moved"):
        canary.assemble(other, world.bundle, approver="babar-raza")
    assert sandbox_mode(other) == "dry_run"  # not left at full
    assert not (other / canary.BUNDLE_RELATIVE).exists()
    assert not (other / AUTHORIZATION_DIRNAME).exists()


# --- the canary's proofs -------------------------------------------------------------------


def test_p1_the_first_run_opens_exactly_one_pull_request_the_app_performed(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert world.propose() == EXIT_OK  # the workflow's dry-run job: plan, decision, no write
    assert "the authorization record matches this candidate" in capsys.readouterr().out
    assert world.rest.applied_writes() == []
    allow_writes(monkeypatch)
    assert world.write() == EXIT_OK
    said = capsys.readouterr().out
    assert "admitted: babar-raza/presenter-sandbox (mode full, sandbox)" in said
    assert "effected=True" in said and f"/{SANDBOX}/pull/1" in said
    lines = world.verify()
    assert all(line.status != canary.MISSING for line in lines), [line.render() for line in lines]
    assert statuses(lines)["performed by the App"] == canary.OK
    (pull,) = world.rest.pulls(SANDBOX)
    assert pull["title"].startswith("docs(readme): ")  # the correction composer names the change
    assert "kind: correction" in pull["body"] and "### How to decline" in pull["body"]
    assert world.rest.file(SANDBOX, "main", "README.md") == README  # the base branch is untouched
    corrected = world.rest.file(SANDBOX, BRANCH, "README.md")
    assert corrected is not None and "flowchart LR" in corrected and "flowchart TD" not in corrected


def test_p2_a_rerun_writes_and_creates_nothing(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    allow_writes(monkeypatch)
    assert world.write() == EXIT_OK
    writes = len(world.rest.applied_writes())
    capsys.readouterr()
    assert world.write() == EXIT_OK
    assert "no change needed" in capsys.readouterr().out
    assert len(world.rest.applied_writes()) == writes and len(world.rest.pulls(SANDBOX)) == 1
    assert all(line.status != canary.MISSING for line in world.verify())


def test_p3_a_closed_pull_request_is_not_recreated(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    allow_writes(monkeypatch)
    assert world.write() == EXIT_OK
    world.rest.close_pull(SANDBOX, 1)
    writes = len(world.rest.applied_writes())
    capsys.readouterr()
    assert world.write() == EXIT_UNSAFE
    assert "pr_already_closed" in capsys.readouterr().out
    assert len(world.rest.applied_writes()) == writes
    assert all(line.status != canary.MISSING for line in world.verify("closed"))
    assert (
        statuses(world.verify("open"))["exactly one pull request"] == canary.MISSING
    )  # the control


def test_p4_a_moved_sandbox_head_is_refused_and_nothing_is_written(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (world.sandbox_clone / "NOTES.md").write_text("the owner pushes a commit\n", encoding="utf-8")
    _git(["add", "-A"], world.sandbox_clone)
    _git(["commit", "-q", "-m", "an unrelated owner commit"], world.sandbox_clone)
    _git(["push", "-q", "origin", "HEAD:main"], world.sandbox_clone)
    assert world.head() != world.revision
    allow_writes(monkeypatch)
    fresh = world.fresh_rest()  # GitHub's view of the sandbox, with the owner's commit
    bind(monkeypatch, fresh)
    assert world.propose() == EXIT_UNSAFE  # the dry-run job refuses too
    assert "source_moved" in capsys.readouterr().err
    assert world.write() == EXIT_UNSAFE
    assert "source_moved" in capsys.readouterr().out
    assert fresh.applied_writes() == [] and fresh.pulls(SANDBOX) == []
    # Nothing of ours exists on the sandbox. (The owner's own commit moved the base, so the
    # "no direct push" line - base still at the authorized revision - rightly reads MISSING here.)
    lines = statuses(world.verify("none", fresh))
    assert lines["no pull request"] == lines["no presenter branch"] == canary.OK


def test_p5_an_interrupted_write_converges_to_one_pull_request(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    allow_writes(monkeypatch)
    # (a) the owner pre-creates the branch at the base head: the state a run that died after the
    #     branch POST and before the contents PUT leaves behind.
    owner, name = SANDBOX.split("/")
    assert (
        world.rest.post(
            f"{fake_rest.API_ROOT}/repos/{SANDBOX}/git/refs",
            cycle.FAKE_TOKEN,
            {"ref": f"refs/heads/{BRANCH}", "sha": world.revision},
        )[0]
        == 201
    )
    assert world.write() == EXIT_OK
    assert len(world.rest.pulls(SANDBOX)) == 1
    assert all(line.status != canary.MISSING for line in world.verify())
    # (b) the contents PUT lands and its answer is lost: reconciled by reading, never re-PUT.
    rest = world.fresh_rest()
    bind(monkeypatch, rest)
    rest.inject("PUT", r"/contents/README\.md$", "lose_response")
    capsys.readouterr()
    assert world.write() == EXIT_OK
    puts = [w for w in rest.writes if w["method"] == "PUT"]
    assert len(puts) == 1 and puts[0]["applied"] and len(rest.pulls(SANDBOX)) == 1
    assert all(line.status != canary.MISSING for line in world.verify(rest=rest))
    assert (owner, name) == ("babar-raza", "presenter-sandbox")


# --- negative controls: nothing unauthorized writes ----------------------------------------------


def test_no_unauthorized_path_writes(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def refused(code: int, fragment: str, rest: fake_rest.FakeGitHubRest | None = None) -> None:
        assert code != EXIT_OK
        said = capsys.readouterr()
        assert fragment in said.out + said.err
        assert (rest or world.rest).applied_writes() == []

    # the owner switch is closed (the workflow sets it only in its write step)
    refused(world.write(), "write_not_enabled")
    allow_writes(monkeypatch)
    # no token
    monkeypatch.delenv("GH_PROPOSAL_WRITE_TOKEN")
    refused(world.write(), "no_write_token")
    # a personal access token is never a write credential
    monkeypatch.setenv("GH_PROPOSAL_WRITE_TOKEN", "ghp_a_personal_access_token")
    refused(world.write(), "token_not_installation")
    monkeypatch.setenv("GH_PROPOSAL_WRITE_TOKEN", cycle.FAKE_TOKEN)
    # an installation token that reaches more than the sandbox
    wide = world.fresh_rest(installed=[SANDBOX, "babar-raza/repository-presenter"])
    bind(monkeypatch, wide)
    refused(world.write(), "token_wrong_scope", wide)
    bind(monkeypatch, world.rest)
    # a record that is not merged: it exists only in a later, unmerged commit
    record = world.record
    record.write_text(
        record.read_text(encoding="utf-8").replace("babar-raza", "someone-else", 1),
        encoding="utf-8",
    )
    refused(world.write(), "authorization_not_committed")
    _git(["checkout", "--", str(record.relative_to(world.control))], world.control)
    # a bundle edited after the record was merged no longer matches the record's hash
    bundle_readme = world.control / canary.BUNDLE_RELATIVE / "README.md"
    original = bundle_readme.read_bytes()
    bundle_readme.write_bytes(original + b"\nunreviewed\n")
    refused(world.write(), "bundle_inconsistent")
    bundle_readme.write_bytes(original)
    # a record that was never supplied
    missing = world.control / AUTHORIZATION_DIRNAME / "missing.json"
    refused(world.propose("--propose", record=missing), "authorization_missing")
    # sanity: the same fixture succeeds once every precondition holds
    assert world.write() == EXIT_OK
    assert len(world.rest.pulls(SANDBOX)) == 1


def test_the_sandbox_is_reachable_only_through_the_sandbox_flag_and_a_product_never_with_it(
    world: World, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    allow_writes(monkeypatch)
    plain = main(
        [
            "propose",
            "--repo",
            SANDBOX,
            "--root",
            str(world.control),
            "--correction-bundle",
            str(world.control / canary.BUNDLE_RELATIVE),
            "--authorization-record",
            str(world.record),
            "--trigger-sha",
            world.trigger,
            "--propose",
        ]
    )
    assert plain != EXIT_OK and "not in the registry allow-list" in capsys.readouterr().err
    product = main(
        [
            "propose",
            "--sandbox",
            "--repo",
            PRODUCT,
            "--root",
            str(world.control),
            "--correction-bundle",
            str(world.control / canary.BUNDLE_RELATIVE),
            "--authorization-record",
            str(world.record),
            "--trigger-sha",
            world.trigger,
            "--propose",
        ]
    )
    assert product != EXIT_OK and "not in the registry allow-list" in capsys.readouterr().err
    no_bundle = main(["propose", "--sandbox", "--repo", SANDBOX, "--root", str(world.control)])
    assert no_bundle == EXIT_USAGE and "--correction-bundle only" in capsys.readouterr().err
    assert world.rest.applied_writes() == []


def test_a_sandbox_entry_still_at_dry_run_never_reaches_a_write(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = world.control / SANDBOX_REGISTRY_RELATIVE_PATH
    document = json.loads(path.read_text("utf-8"))
    document["entries"][0]["mode"] = "dry_run"
    path.write_text(json.dumps(document), encoding="utf-8")
    allow_writes(monkeypatch)
    assert world.write() == EXIT_UNSAFE
    assert "registry_dry_run" in capsys.readouterr().err
    assert world.rest.applied_writes() == []


def test_the_production_registry_and_its_portfolio_count_are_untouched(world: World) -> None:
    assert digest(world.control / "data" / "registry.json") == digest(
        REPO_ROOT / "data" / "registry.json"
    )
    production = load_registry(REPO_ROOT / "data" / "registry.json")
    assert SANDBOX not in {e.repository for e in production.entries}
    assert len(production.entries) == len(
        load_registry(world.control / "data" / "registry.json").entries
    )


# --- the read-only tools -------------------------------------------------------------------


def _with_control(rest: fake_rest.FakeGitHubRest, **overrides: Any) -> Any:
    """The fake sandbox plus the control repository's Actions endpoints (what preflight reads)."""
    control = f"/repos/{canary.CONTROL}"
    state = {"secrets": True, "workflow": True, "reviewers": True, "variable": False, **overrides}

    def fetch(url: str, token: str | None) -> tuple[int, Any]:
        path = urlsplit(url).path
        if path.startswith(f"{control}/actions/secrets/"):
            return (200, {"name": path.rsplit("/", 1)[1]}) if state["secrets"] else (404, {})
        if path == f"{control}/actions/workflows/{canary.WORKFLOW}":
            return (200, {"state": "active"}) if state["workflow"] else (404, {})
        if path == f"{control}/environments/{canary.ENVIRONMENT}":
            rules = [{"type": "required_reviewers"}] if state["reviewers"] else []
            return 200, {"protection_rules": rules}
        if path == f"{control}/actions/variables/{canary.FORBIDDEN_VARIABLE}":
            return (200, {"value": "1"}) if state["variable"] else (404, {})
        return rest.fetch(url, token)

    return fetch


def test_preflight_is_all_green_once_the_canary_is_ready_and_names_the_owner_action_otherwise(
    world: World,
) -> None:
    lines = canary.preflight(world.control, token=cycle.FAKE_TOKEN, fetch=_with_control(world.rest))
    found = statuses(lines)
    missing = [line.render() for line in lines if line.status == canary.MISSING]
    assert missing == [], missing
    assert found["sandbox seeded"] == canary.OK and found["bundle freshness"] == canary.OK
    assert found["record on origin/main"] == canary.OK
    assert (
        found["App installed on the sandbox"] == canary.CONFIRM
    )  # the one thing a token cannot read

    broken = canary.preflight(
        world.control,
        token=cycle.FAKE_TOKEN,
        fetch=_with_control(
            world.rest, reviewers=False, variable=True, workflow=False, secrets=False
        ),
    )
    by_check = {line.check: line for line in broken}
    assert by_check[f"environment {canary.ENVIRONMENT}"].status == canary.MISSING
    assert "required reviewer" in by_check[f"environment {canary.ENVIRONMENT}"].action
    assert by_check[f"variable {canary.FORBIDDEN_VARIABLE}"].status == canary.MISSING
    assert by_check[f"workflow {canary.WORKFLOW}"].status == canary.MISSING
    assert by_check["secret GH_APP_ID"].status == canary.MISSING


def test_preflight_notices_an_unseeded_sandbox_a_stale_bundle_and_a_renamed_repository(
    world: World,
) -> None:
    moved = world.fresh_rest()
    moved.set_branch(SANDBOX, "main", "f" * 40)
    stale = statuses(
        canary.preflight(world.control, token=cycle.FAKE_TOKEN, fetch=_with_control(moved))
    )
    assert stale["bundle freshness"] == canary.MISSING

    placeholder = fake_rest.FakeGitHubRest(
        app_id=canary.EXPECTED_APP_ID, installation_scope=[SANDBOX]
    )
    placeholder.add_repository(
        SANDBOX, repository_id=SANDBOX_ID + 1, readme="# x\n", files={"LICENSE": "MIT\n"}
    )
    lines = statuses(
        canary.preflight(world.control, token=cycle.FAKE_TOKEN, fetch=_with_control(placeholder))
    )
    assert lines["sandbox seeded"] == canary.MISSING
    assert lines["sandbox identity"] == canary.MISSING


def test_preflight_before_the_seed_names_the_owner_step_and_calls_the_bundle_pending_not_stale(
    world: World,
) -> None:
    pin = seed.load_pin(world.pin_path)
    before = world.fresh_rest()
    before.set_branch(SANDBOX, "main", pin.sandbox_parent)  # the owner has not pushed yet
    lines = canary.preflight(world.control, token=cycle.FAKE_TOKEN, fetch=_with_control(before))
    by_check = {line.check: line for line in lines}
    seeded = by_check["sandbox seeded"]
    assert seeded.status == canary.MISSING
    assert "seed.py" in seeded.action and "--commit" in seeded.action
    assert by_check["bundle freshness"].status == canary.INFO  # waiting for the seed, not stale
    assert by_check["correction bundle"].status == canary.OK  # intact (SHA256SUMS) and proven
    assert by_check["record on origin/main"].status == canary.OK
    assert by_check["authorization record"].status == canary.OK


def test_assembly_refuses_a_bundle_that_is_not_for_the_pinned_seed_commit(
    world: World, tmp_path: Path
) -> None:
    other = unassembled_control(world, tmp_path)
    document = json.loads(world.pin_path.read_text("utf-8"))
    document["seed"]["commit"] = "b" * 40
    (other / canary.SEED_PIN_RELATIVE).write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(RuntimeError, match="pinned seed commit"):
        canary.assemble(other, world.bundle, approver="babar-raza")
    assert not (other / canary.BUNDLE_RELATIVE).exists()
    assert sandbox_mode(other) == "dry_run"


def test_the_assembled_bundle_is_the_committed_shape_with_the_text_the_effect_posts(
    world: World,
) -> None:
    bundle = world.control / canary.BUNDLE_RELATIVE
    assert sums_problems(bundle) == []
    names = sorted(p.name for p in bundle.iterdir())
    assert "SHA256SUMS" in names and "PULL_REQUEST.md" in names
    text = (bundle / "PULL_REQUEST.md").read_text(encoding="utf-8")
    assert text.startswith("Title: docs(readme): ") and "### How to decline" in text
    (bundle / "README.original.md").write_bytes(b"edited\n")  # a reviewer's tamper check
    assert any("README.original.md does not match" in p for p in sums_problems(bundle))


def test_verify_notices_a_pull_request_that_is_not_ours_or_not_the_bundles(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    allow_writes(monkeypatch)
    assert world.write() == EXIT_OK
    assert statuses(world.verify())["performed by the App"] == canary.OK
    world.rest.pulls(SANDBOX)[0]["performed_via_github_app"] = {"id": 1}  # some other App's
    assert statuses(world.verify())["performed by the App"] == canary.MISSING
    world.rest.pulls(SANDBOX)[0]["title"] = "an edited title"
    world.rest.pulls(SANDBOX)[0]["body"] = "a body without the provenance block"
    assert statuses(world.verify())["body provenance"] == canary.MISSING
    world.rest.close_pull(SANDBOX, 1)
    assert statuses(world.verify())["exactly one pull request"] == canary.MISSING
