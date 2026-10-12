"""The sandbox canary's operator tool: read-only preflight, read-only verification, assembly.

The canary (docs/PROPOSAL_WAVE_RUNBOOK.md section 9) is the one pull request allowed while every
real product repository stays paused: a README correction proposed to the owner's throwaway
repository ``babar-raza/presenter-sandbox``. This tool holds no write path to any GitHub
repository. Its three commands:

``preflight``
    Read-only. Everything the canary needs, one line each, with the OWNER action a missing item
    asks for: the sandbox repository (identity against ``data/registry_sandbox.json``, default
    branch, head, README), the committed bundle and authorization record, the control repository's
    workflow, environment, secrets and the variable that must stay unset. The App installation on
    the sandbox is the one thing a user token cannot read; the line says where to look and that the
    workflow's dry-run job is the proof.

``assemble``
    Local files only, in a control-repository worktree. Takes the bundle ``repository-presenter
    correct-readme --sandbox --repo babar-raza/presenter-sandbox --out DIR`` wrote, validates it
    through the typed correction gate, copies it to ``ops/sandbox-canary/bundle/`` with the pull
    request text the effect will post (``PULL_REQUEST.md``) and ``SHA256SUMS``, sets the sandbox
    registry entry to ``full`` and drafts the authorization record into
    ``ops/proposal-authorizations/``. When ``ops/sandbox-canary/seed.json`` pins the seed commit
    (``seed.py``), the bundle must correct exactly that commit, so it may be merged before the owner
    pushes it. It prints what to review and commit; the owner merges.

``verify``
    Read-only. After a write run: the pull request from ``repository-presenter/readme-update`` is
    the only one, was performed by the Repository Presenter App, changes ``README.md`` alone, and
    its branch holds exactly the bundle's corrected README while the base branch is untouched
    (``--expect open``); or it is closed and not recreated (``--expect closed``); or nothing exists
    (``--expect none``, after a refusal).

Every GitHub call is a GET through ``core/github/client.py``'s ``default_fetch`` (or an injected
fake); the token is read from ``GH_TOKEN`` and never printed.

    PYTHONPATH=src python tools/canary/canary.py preflight --root .
    PYTHONPATH=src python tools/canary/canary.py assemble --root . --bundle DIR --approver LOGIN
    PYTHONPATH=src python tools/canary/canary.py verify --root . --expect open
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from repository_presenter import cli
from repository_presenter.components.propose.effect import PRESENTER_BRANCH
from repository_presenter.components.readme_correction.bundle import MANIFEST_NAME
from repository_presenter.components.readme_correction.committed import (
    PULL_REQUEST_NAME,
    pull_request_text,
    write_sums,
)
from repository_presenter.components.readme_correction.gate import load_proposable_correction
from repository_presenter.components.readme_correction.pull_request import (
    compose_correction_pull_request,
)
from repository_presenter.core.authorization.proposal import (
    AUTHORIZATION_DIRNAME,
    CURRENT_POLICY_VERSION,
    MAX_LIFETIME,
    authorize_proposal,
    load_authorization_file,
    record_filename,
    render_record,
    validate_authorization,
)
from repository_presenter.core.authorization.record_provenance import verify_record_provenance
from repository_presenter.core.authorization.refusals import Refusal, WriteRefusedError
from repository_presenter.core.candidates import ProposableCandidate
from repository_presenter.core.errors import PresenterError
from repository_presenter.core.github.client import (
    API_ROOT,
    FetchFn,
    default_fetch,
    find_pull_requests,
    get_contents,
    get_pull_request_app_id,
    get_ref,
)
from repository_presenter.core.github.token_provenance import EXPECTED_APP_ID
from repository_presenter.core.hashing import sha256_text
from repository_presenter.core.registry.sandbox import (
    SANDBOX_REGISTRY_RELATIVE_PATH,
    load_registry_for,
)
from repository_presenter.core.registry.write_gate import require_write_permitted

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seed  # noqa: E402  (the seeding tool beside this one: its pin is the canary's source revision)

SANDBOX = "babar-raza/presenter-sandbox"
CONTROL = "babar-raza/repository-presenter"
WORKFLOW = "propose-sandbox.yml"
ENVIRONMENT = "sandbox-canary"
BUNDLE_RELATIVE = Path("ops") / "sandbox-canary" / "bundle"
SEED_PIN_RELATIVE = Path("ops") / "sandbox-canary" / "seed.json"
#: Must stay unset for the whole canary: it arms ``sealing-scheduled.yml``'s unattended proposals.
FORBIDDEN_VARIABLE = "REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED"
OK, MISSING, CONFIRM, INFO = "OK", "MISSING", "CONFIRM", "INFO"


@dataclass(frozen=True)
class Line:
    status: str
    check: str
    detail: str
    action: str = ""

    def render(self) -> str:
        tail = f"  -> {self.action}" if self.action else ""
        return f"{self.status:<8} {self.check}: {self.detail}{tail}"


def _json(fetch: FetchFn, url: str, token: str | None) -> tuple[int, Any]:
    return fetch(f"{API_ROOT}{url}", token)


def _seed_pin(root: Path) -> seed.SeedPin | None:
    path = root / SEED_PIN_RELATIVE
    return seed.load_pin(path) if path.is_file() else None


# --- preflight ---------------------------------------------------------------------------------


def preflight(root: Path, *, token: str | None, fetch: FetchFn = default_fetch) -> list[Line]:
    """Read-only readiness of the whole canary; every line names the owner action it asks for."""
    lines: list[Line] = []
    add = lines.append
    try:
        registry = load_registry_for(root, sandbox=True)
        entry = registry.entries[0]
        add(Line(OK, "sandbox registry", f"{entry.repository}, mode {entry.mode}"))
    except PresenterError as exc:
        return [Line(MISSING, "sandbox registry", str(exc))]

    # The sandbox repository itself.
    status, repo = _json(fetch, f"/repos/{SANDBOX}", token)
    head = ""
    branch = "main"
    if status != 200 or not isinstance(repo, dict):
        add(Line(MISSING, "sandbox repository", f"GET returned HTTP {status}"))
    else:
        branch = str(repo.get("default_branch", "main"))
        identity = entry.provider_identity
        same = repo.get("id") == identity.repository_id
        add(
            Line(
                OK if same else MISSING,
                "sandbox identity",
                f"repository id {repo.get('id')} "
                f"{'matches' if same else 'DIFFERS FROM'} the registry's {identity.repository_id}",
                "" if same else "the repository was deleted and recreated: update the registry id",
            )
        )
        usable = not repo.get("archived") and not repo.get("disabled")
        add(
            Line(
                OK if usable else MISSING,
                "sandbox writable",
                f"default branch {branch}, visibility {repo.get('visibility', '?')}, "
                f"archived {repo.get('archived')}",
                "" if usable else "unarchive the repository",
            )
        )
    owner, name = SANDBOX.split("/")
    tip = get_ref(owner, name, branch, token=token or "", fetch=fetch) if status == 200 else None
    if tip:
        head = tip
        add(Line(INFO, "sandbox head", f"{branch} at {tip}"))
        code, tree = _json(fetch, f"/repos/{SANDBOX}/git/trees/{tip}", token)
        names = sorted(str(item.get("path")) for item in (tree or {}).get("tree", [])) if code == 200 else []
        pin = _seed_pin(root)
        if pin is None:
            seeded = len(names) > 2
            add(
                Line(
                    OK if seeded else MISSING,
                    "sandbox seeded",
                    f"top level holds {len(names)} entries"
                    + ("" if seeded else " (README and LICENSE only: a placeholder the pipeline refuses)"),
                    "" if seeded else f"OWNER: seed it (python tools/canary/seed.py --commit), push; the pin {SEED_PIN_RELATIVE.as_posix()} is absent",
                )
            )
        elif tip == pin.commit:
            add(Line(OK, "sandbox seeded", f"{branch} is the pinned seed commit {tip[:12]} ({len(names)} top-level entries)"))
        elif tip == pin.sandbox_parent:
            add(
                Line(
                    MISSING,
                    "sandbox seeded",
                    f"{branch} is still {tip[:12]}, the commit the pinned seed {pin.commit[:12]} builds on",
                    "OWNER: seed it: python tools/canary/seed.py --product product --sandbox sandbox --commit, "
                    "then git -C sandbox push origin seed:main (docs/PROPOSAL_WAVE_RUNBOOK.md section 9.4)",
                )
            )
        else:
            add(
                Line(
                    MISSING,
                    "sandbox seeded",
                    f"{branch} is {tip[:12]}: neither the pinned seed {pin.commit[:12]} nor its parent "
                    f"{pin.sandbox_parent[:12]}; the pin and the bundle no longer fit this repository",
                    "OPERATOR: re-pin (seed.py --write-pin), re-run correct-readme --sandbox, assemble --replace",
                )
            )
        readme = get_contents(owner, name, "README.md", ref=branch, token=token or "", fetch=fetch)
        add(
            Line(
                OK if readme is not None else MISSING,
                "sandbox README.md",
                f"{len(readme.text)} characters" if readme else "absent at the head",
            )
        )
    code, _ = _json(fetch, f"/repos/{SANDBOX}/branches/{branch}/protection", token)
    add(
        Line(
            INFO,
            "default branch protection",
            "none" if code == 404 else f"HTTP {code}: the effect never pushes to it either way",
        )
    )
    try:
        prs = find_pull_requests(owner, name, head_branch=PRESENTER_BRANCH, token=token or "", fetch=fetch)
        states = ", ".join(f"#{p.number} {p.state}" for p in prs) or "none"
        add(Line(INFO, "presenter pull requests", states))
    except PresenterError as exc:
        add(Line(MISSING, "presenter pull requests", str(exc)))

    # The committed bundle and record.
    bundle = root / BUNDLE_RELATIVE
    candidate = None
    if not (bundle / MANIFEST_NAME).is_file():
        add(Line(MISSING, "correction bundle", f"{BUNDLE_RELATIVE.as_posix()} is absent",
                 "run correct-readme --sandbox, then tools/canary/canary.py assemble"))
    else:
        try:
            candidate = load_proposable_correction(
                bundle, SANDBOX, root=root, entry=entry, require_sums=True
            )
            add(Line(OK, "correction bundle", f"intact (SHA256SUMS) and proves a correction of revision {candidate.revision[:12]}"))
            pin = _seed_pin(root)
            if head and candidate.revision == head:
                add(Line(OK, "bundle freshness", "the bundle's revision is the sandbox head"))
            elif head and pin is not None and candidate.revision == pin.commit and head == pin.sandbox_parent:
                add(Line(INFO, "bundle freshness", f"the bundle is for the pinned seed commit {pin.commit[:12]}, which the owner has not pushed yet"))
            elif head:
                add(Line(MISSING, "bundle freshness", f"the sandbox head is {head[:12]}, the bundle was made at {candidate.revision[:12]}",
                         "re-run correct-readme --sandbox and assemble --replace (the effect refuses source_moved)"))
        except WriteRefusedError as exc:
            add(Line(MISSING, "correction bundle", f"{exc.code}: {exc.message}"))
    if candidate is not None:
        record = root / AUTHORIZATION_DIRNAME / record_filename(SANDBOX, candidate.candidate_hash)
        if not record.is_file():
            add(Line(MISSING, "authorization record", f"{record.name} is absent", "run assemble; OWNER merges the pull request"))
        else:
            try:
                authorization = load_authorization_file(record)
                decision = validate_authorization(
                    authorization,
                    now=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    expected_repository=SANDBOX,
                    expected_candidate_hash=candidate.candidate_hash,
                    expected_source_revision=candidate.revision,
                    expected_base_branch=branch,
                    expected_branch=PRESENTER_BRANCH,
                )
                add(Line(OK if decision.granted else MISSING, "authorization record",
                         f"{record.name}: {decision.reason}"))
                provenance = verify_record_provenance(record, control_root=root, trigger_sha="HEAD")
                add(Line(OK, "record on origin/main", f"merged in {provenance.commit[:12]}"))
            except WriteRefusedError as exc:
                add(Line(MISSING, "record on origin/main", f"{exc.code}: {exc.message}", "OWNER: merge the canary pull request"))

    # The control repository: workflow, environment, secrets, the variable that must stay unset.
    for secret in ("GH_APP_ID", "GH_APP_PRIVATE_KEY"):
        code, _ = _json(fetch, f"/repos/{CONTROL}/actions/secrets/{secret}", token)
        add(Line(OK if code == 200 else MISSING, f"secret {secret}", "set" if code == 200 else f"HTTP {code}"))
    code, flow = _json(fetch, f"/repos/{CONTROL}/actions/workflows/{WORKFLOW}", token)
    add(Line(OK if code == 200 and (flow or {}).get("state") == "active" else MISSING, f"workflow {WORKFLOW}",
             "active on the default branch" if code == 200 else f"HTTP {code}", "" if code == 200 else "OWNER: merge the workflow"))
    code, env = _json(fetch, f"/repos/{CONTROL}/environments/{ENVIRONMENT}", token)
    rules = [r.get("type") for r in (env or {}).get("protection_rules", [])] if code == 200 else []
    add(Line(OK if "required_reviewers" in rules else MISSING, f"environment {ENVIRONMENT}",
             "required reviewers set" if "required_reviewers" in rules else
             ("exists without required reviewers" if code == 200 else f"HTTP {code}"),
             "" if "required_reviewers" in rules else "OWNER: Settings > Environments > New environment, add yourself as a required reviewer"))
    code, _ = _json(fetch, f"/repos/{CONTROL}/actions/variables/{FORBIDDEN_VARIABLE}", token)
    add(Line(OK if code == 404 else MISSING, f"variable {FORBIDDEN_VARIABLE}",
             "unset (closed)" if code == 404 else f"HTTP {code}: it is set",
             "" if code == 404 else "OWNER: delete it; it arms the unattended sealing run's proposals"))
    add(Line(CONFIRM, "App installed on the sandbox",
             "a user token cannot read installations",
             "OWNER: https://github.com/settings/installations > Repository Presenter > Configure > "
             "repository access includes presenter-sandbox; the dry-run job's token step is the proof"))
    return lines


# --- assemble ----------------------------------------------------------------------------------


def carriage_return_files(directory: Path) -> list[str]:
    """The files of ``directory`` holding a carriage return: a bundle committed to a repository
    that normalizes line endings would change under its manifest's digests."""
    return [p.name for p in sorted(directory.iterdir()) if p.is_file() and b"\r" in p.read_bytes()]


def _draft_record(
    root: Path,
    candidate: ProposableCandidate,
    pin: seed.SeedPin | None,
    *,
    approver: str,
    hours: int,
    replace: bool,
) -> None:
    """Write the authorization record into ``root``: what ``draft-proposal-authorization`` writes,
    for a correction bundle, with one difference that exists only for the canary.

    That command refuses unless the target's live head IS the bundle's revision. The canary's
    bundle is made, reviewed and merged BEFORE the owner pushes the seed commit it corrects, so
    here the live head may also be the parent the pinned seed commit is built on. Nothing else
    loosens: the record binds the seed commit as ``source_revision``, so ``propose`` (the dry run
    and the write alike) refuses ``source_moved`` until the sandbox head IS that commit."""
    if not 0 < hours <= MAX_LIFETIME // timedelta(hours=1):
        raise RuntimeError(f"--hours must be 1..{MAX_LIFETIME.days * 24}")
    registry = load_registry_for(root, sandbox=True)  # the entry was just opened to `full`
    require_write_permitted(registry, SANDBOX, "readme_proposal")
    live = cli.fetch_default_branch_sha(SANDBOX, token=os.environ.get("GH_TOKEN") or None)
    if live.error is not None or live.sha is None or live.branch is None:
        raise RuntimeError(f"could not read the sandbox: {live.error}")
    waiting_for_seed = (
        pin is not None and candidate.revision == pin.commit and live.sha == pin.sandbox_parent
    )
    if live.sha != candidate.revision and not waiting_for_seed:
        raise RuntimeError(
            f"{Refusal.SOURCE_MOVED}: the bundle's revision {candidate.revision} is neither the "
            f"sandbox's current head {live.sha} nor a pinned seed commit built on it"
        )
    issued = datetime.now(UTC)
    authorization = authorize_proposal(
        repository=SANDBOX,
        candidate_hash=candidate.candidate_hash,
        source_revision=candidate.revision,
        base_branch=live.branch,
        branch=PRESENTER_BRANCH,
        approver=approver,
        issued_at=issued.strftime("%Y-%m-%dT%H:%M:%SZ"),
        expires_at=(issued + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    path = root / AUTHORIZATION_DIRNAME / record_filename(SANDBOX, candidate.candidate_hash)
    if path.exists() and not replace:
        raise FileExistsError(f"{path.relative_to(root).as_posix()} exists; pass --replace to re-draft")
    path.unlink(missing_ok=True)  # a re-draft of the same candidate: a fresh window
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_record(authorization), encoding="utf-8", newline="\n")
    print(
        f"drafted: {path.relative_to(root).as_posix()} (expires {authorization.expires_at}) - "
        "commit it through a reviewed pull request; it authorizes nothing until it is merged"
    )


def assemble(root: Path, bundle: Path, *, approver: str, hours: int = 168, replace: bool = False) -> list[str]:
    """Validate ``bundle`` and write the canary pull request's files into ``root`` (a worktree)."""
    registry_path = root / SANDBOX_REGISTRY_RELATIVE_PATH
    entry = load_registry_for(root, sandbox=True).entries[0]
    candidate = load_proposable_correction(bundle, SANDBOX, root=root, entry=entry)
    pin = _seed_pin(root)
    if pin is not None and candidate.revision != pin.commit:
        raise RuntimeError(
            f"the bundle corrects revision {candidate.revision}, but the pinned seed commit "
            f"({SEED_PIN_RELATIVE.as_posix()}) is {pin.commit}: make the bundle from the sandbox "
            "at the pinned seed commit, or re-pin the seed"
        )
    carriage = carriage_return_files(bundle)
    if carriage:
        raise RuntimeError(
            f"{', '.join(carriage)} contain carriage returns: the control repository normalizes "
            "line endings to LF on commit (.gitattributes), so the committed bundle would no longer "
            "match its manifest. Seed the sandbox from a product whose files are LF"
        )
    destination = root / BUNDLE_RELATIVE
    if destination.exists():
        if any(destination.iterdir()) and not replace:
            raise FileExistsError(f"{destination} exists; pass --replace to overwrite it")
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    original_registry = registry_path.read_bytes()
    try:
        shutil.copytree(bundle, destination)
        # The committed shape of tools/corrections/assemble.py: the text the effect will post, for
        # the reviewer to read in the diff, and SHA256SUMS over every file (sha256sum --check).
        text = pull_request_text(
            compose_correction_pull_request(
                bundle=destination,
                repository=SANDBOX,
                candidate_hash=candidate.candidate_hash,
                source_revision=candidate.revision,
                policy_version=CURRENT_POLICY_VERSION,
            )
        )
        (destination / PULL_REQUEST_NAME).write_bytes(text.encode("utf-8"))
        write_sums(destination)
        load_proposable_correction(destination, SANDBOX, root=root, entry=entry, require_sums=True)
        document = json.loads(original_registry.decode("utf-8"))
        for item in document["entries"]:
            if item["repository"] == SANDBOX:
                item["mode"] = "full"
        registry_path.write_text(
            json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        _draft_record(root, candidate, pin, approver=approver, hours=hours, replace=replace)
    except BaseException:  # leave the worktree as it was: no half-assembled pull request
        registry_path.write_bytes(original_registry)
        shutil.rmtree(destination, ignore_errors=True)
        raise
    record = (AUTHORIZATION_DIRNAME / record_filename(SANDBOX, candidate.candidate_hash)).as_posix()
    return [
        BUNDLE_RELATIVE.as_posix(),
        SANDBOX_REGISTRY_RELATIVE_PATH.as_posix(),
        record,
    ]


# --- verify ------------------------------------------------------------------------------------


def verify(
    root: Path, *, expect: str, token: str | None, fetch: FetchFn = default_fetch
) -> list[Line]:
    """Read-only proof of what the last write run did (or, after a refusal, did not do)."""
    owner, name = SANDBOX.split("/")
    bundle = root / BUNDLE_RELATIVE
    manifest = json.loads((bundle / MANIFEST_NAME).read_text(encoding="utf-8"))
    corrected = (bundle / "README.md").read_text(encoding="utf-8")
    lines: list[Line] = []
    add = lines.append
    token = token or ""
    status, repo = _json(fetch, f"/repos/{SANDBOX}", token)
    base = str((repo or {}).get("default_branch", "main")) if status == 200 else "main"
    base_head = get_ref(owner, name, base, token=token, fetch=fetch)
    add(Line(OK if base_head == manifest["revision"] else MISSING, "no direct push",
             f"{base} is at {str(base_head)[:12]}; the authorized source revision is {manifest['revision'][:12]}"))
    base_readme = get_contents(owner, name, "README.md", ref=base, token=token, fetch=fetch)
    add(Line(OK if base_readme is not None and sha256_text(base_readme.text) == sha256_text(
        (bundle / "README.original.md").read_text(encoding="utf-8")) else MISSING,
        "base README untouched", "equals the bundle's original README"))
    prs = find_pull_requests(owner, name, head_branch=PRESENTER_BRANCH, token=token, fetch=fetch)
    opened = [p for p in prs if p.state == "open"]
    if expect == "none":
        branch_sha = get_ref(owner, name, PRESENTER_BRANCH, token=token, fetch=fetch)
        add(Line(OK if not prs else MISSING, "no pull request", f"{len(prs)} found"))
        add(Line(OK if branch_sha is None else MISSING, "no presenter branch", str(branch_sha)))
        return lines
    if expect == "closed":
        add(Line(OK if len(prs) == 1 and not opened else MISSING, "closed and not recreated",
                 ", ".join(f"#{p.number} {p.state}" for p in prs) or "no pull request"))
        return lines
    add(Line(OK if len(opened) == 1 and len(prs) == 1 else MISSING, "exactly one pull request",
             ", ".join(f"#{p.number} {p.state}" for p in prs) or "none"))
    if len(opened) != 1:
        return lines
    pr = opened[0]
    app = get_pull_request_app_id(owner, name, pr.number, token=token, fetch=fetch)
    add(Line(OK if app == EXPECTED_APP_ID else MISSING, "performed by the App", f"app id {app}, expected {EXPECTED_APP_ID}"))
    code, pull = _json(fetch, f"/repos/{SANDBOX}/pulls/{pr.number}", token)
    pull = pull if code == 200 and isinstance(pull, dict) else {}
    head_repo = ((pull.get("head") or {}).get("repo") or {}).get("full_name")
    same_repo = head_repo in (None, SANDBOX)
    right_refs = (pull.get("head") or {}).get("ref") == PRESENTER_BRANCH and (pull.get("base") or {}).get("ref") == base
    add(Line(OK if same_repo and right_refs else MISSING, "branch to default branch, same repository",
             f"{PRESENTER_BRANCH} -> {base}"))
    code, files = _json(fetch, f"/repos/{SANDBOX}/pulls/{pr.number}/files", token)
    changed = sorted(str(f.get("filename")) for f in files) if code == 200 and isinstance(files, list) else []
    add(Line(OK if changed == ["README.md"] else MISSING, "one file changed", ", ".join(changed) or f"HTTP {code}"))
    branch_readme = get_contents(owner, name, "README.md", ref=PRESENTER_BRANCH, token=token, fetch=fetch)
    same = branch_readme is not None and sha256_text(branch_readme.text) == sha256_text(corrected)
    add(Line(OK if same else MISSING, "branch README is the bundle's", "byte for byte" if same else "differs"))
    candidate_hash = sha256_text(corrected)
    carries = f"candidate_hash: {candidate_hash}" in pr.body and f"source_revision: {manifest['revision']}" in pr.body
    add(Line(OK if carries else MISSING, "body provenance", "candidate_hash and source_revision match the bundle"))
    add(Line(INFO, "pull request", pr.url))
    return lines


def _print(lines: Sequence[Line]) -> int:
    for line in lines:
        print(line.render())
    return 1 if any(line.status == MISSING for line in lines) else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("preflight", "assemble", "verify"):
        sub = commands.add_parser(name)
        sub.add_argument("--root", type=Path, default=Path.cwd(), help="the control repository checkout")
        if name == "assemble":
            sub.add_argument("--bundle", type=Path, required=True)
            sub.add_argument("--approver", required=True, help="the owner's GitHub login")
            sub.add_argument("--hours", type=int, default=168, help="record lifetime, at most 168")
            sub.add_argument("--replace", action="store_true")
        if name == "verify":
            sub.add_argument("--expect", choices=("open", "closed", "none"), default="open")
    args = parser.parse_args(argv)
    token = os.environ.get("GH_TOKEN") or None
    root = args.root.resolve()
    try:
        if args.command == "preflight":
            return _print(preflight(root, token=token))
        if args.command == "verify":
            return _print(verify(root, expect=args.expect, token=token))
        written = assemble(root, args.bundle, approver=args.approver, hours=args.hours, replace=args.replace)
    except (PresenterError, seed.SeedError, FileExistsError, RuntimeError, OSError) as exc:
        print(f"canary: {args.command}: {exc}", file=sys.stderr)
        return 2
    print("canary: assembled; review the diff, then commit these paths in one pull request:")
    for path in written:
        print(f"  git add {path}")
    print("canary: the record authorizes nothing until that pull request is merged to main")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
