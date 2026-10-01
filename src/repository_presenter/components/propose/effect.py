"""The gated README-proposal PR effect (G6-W02) - and, in this project's current environment,
never armed.

This is the write half `docs/EXECUTION_STATE_MACHINE.md` G6 Work item 1 names: `propose.yml` as a
separately authorized write-capable workflow, distinct from `present.yml`/`monitor.yml`'s read-only
scope. Building the mechanism is in scope here; firing it live against a real product repository is
not - `AGENTS.md` is explicit: "Do not perform a target write unless the current execution gate and
exact authorization permit it", and `docs/STATE_MACHINE.md` section 12.1 requires the *first* live
exercise against a real external target to be owner-selected, never agent-selected. No disposable
target is named anywhere in this project's own records as of this item (`project/state.yaml`'s
G6-W01 entry already recorded the identical gap for the issue-filing write path), so this module is
built and tested against injected fakes only - never fired live by this work item.

Two independent conditions must both hold before this module ever calls
`core/github/client.py`'s branch/contents/pull-request functions, mirroring `components/issues/
file.py` and `components/metadata/apply.py`'s own layered discipline (neuter, then verify, then only
proceed):

1. `write_authorized(environment)` - the dedicated, owner-controlled environment variable
   `REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED` is set to a truthy value. Never inferred from a
   credential's presence or scope.
2. A write-scoped token is actually supplied (`GH_PROPOSAL_WRITE_TOKEN` - never the read-only
   `GH_TOKEN`, and never `GH_METADATA_WRITE_TOKEN`/`GH_ISSUES_WRITE_TOKEN` either, even though all
   three are GitHub App installation tokens in principle: each effect mints and uses its own,
   freshly, inside its own job - `docs/STATE_MACHINE.md` section 12).

Past both gates, every bound field of the caller's `core/authorization/proposal.py::
ProposalAuthorization` is re-validated against the exact effect about to be attempted
(`validate_authorization`) - a stale policy version, a candidate that changed since authorization
was minted, or an expired clock all refuse outright, no network call made. Then, mirroring
`AGENTS.md` "Recheck upstream revision immediately before an effect", the caller may supply a
`recheck_source` callable: when given, this module refuses to propose against a repository whose
live current revision no longer matches what the authorization was bound to - a stale source blocks
the effect, never silently proceeds against a moved target.

The effect itself is idempotent by construction, not by a separate duplicate-guard flag: it reads
the presenter branch's current README content and the target's one open presenter PR (if any)
before writing anything, and only ever writes what has actually changed - an unchanged repeat
invocation commits nothing and edits no PR (`ProposalEffectResult.effected` still `True`, but
`commit_written`/`pr_created`/`pr_updated` all `False`, `reason` "no change needed"). A lost
response from the one write call that can go missing in flight (`put_contents`) is never retried
blindly: the caller's `reconcile_write` callable re-observes the branch's real current content, and
this module only re-attempts the write when that observation confirms the prior attempt did not
land - `AGENTS.md` "reconcile uncertain remote effects before retrying".
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from repository_presenter.core.authorization.proposal import (
    ProposalAuthorization,
    validate_authorization,
)
from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import (
    FileContents,
    PullRequestRef,
)
from repository_presenter.core.github.client import (
    create_pull_request as default_create_pull_request,
)
from repository_presenter.core.github.client import (
    create_ref as default_create_ref,
)
from repository_presenter.core.github.client import (
    find_open_pull_request as default_find_open_pull_request,
)
from repository_presenter.core.github.client import (
    get_contents as default_get_contents,
)
from repository_presenter.core.github.client import (
    get_ref as default_get_ref,
)
from repository_presenter.core.github.client import (
    put_contents as default_put_contents,
)
from repository_presenter.core.github.client import (
    update_pull_request as default_update_pull_request,
)
from repository_presenter.core.hashing import sha256_text

AUTHORIZATION_VARIABLE = "REPOSITORY_PRESENTER_PROPOSAL_WRITE_AUTHORIZED"
_AUTHORIZED_VALUES = frozenset({"1", "true", "yes"})

#: The one stable presenter branch this project proposes README updates from, on every target
#: (`docs/STATE_MACHINE.md` section 11.1: "One stable presenter branch and one open PR exist per
#: target repository."). Deliberately a single constant, not derived per-repository - each target
#: repository already has its own separate git namespace, so one fixed name here is already "one
#: stable branch per target", and a fixed name is what lets every invocation find the same branch
#: rather than inventing a new one on each run.
PRESENTER_BRANCH = "repository-presenter/readme-update"


def presenter_branch_name() -> str:
    """The canonical presenter branch name, independent of whatever branch a given authorization
    *claims* - `propose_candidate` validates every authorization's own `branch` field against this
    before trusting it for anything, so an authorization minted for the wrong branch is refused
    rather than silently followed."""
    return PRESENTER_BRANCH


_NOT_AUTHORIZED_REASON = (
    f"not authorized: set {AUTHORIZATION_VARIABLE}=1 (owner-controlled) - a token's presence or "
    "scope is never by itself sufficient"
)
_NO_TOKEN_REASON = "no write-scoped token available (GH_PROPOSAL_WRITE_TOKEN, never GH_TOKEN)"
README_PATH = "README.md"

GetRefFn = Callable[..., "str | None"]
CreateRefFn = Callable[..., None]
GetContentsFn = Callable[..., "FileContents | None"]
PutContentsFn = Callable[..., object]
FindOpenPullRequestFn = Callable[..., "PullRequestRef | None"]
CreatePullRequestFn = Callable[..., PullRequestRef]
UpdatePullRequestFn = Callable[..., PullRequestRef]
RecheckSourceFn = Callable[[], str]
ReconcileWriteFn = Callable[[], "FileContents | None"]
ClockFn = Callable[[], str]


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_authorized(environment: Mapping[str, str]) -> bool:
    """`True` only when the owner has explicitly set `AUTHORIZATION_VARIABLE` to a truthy value.
    Absence, an empty string, or any other value is unauthorized - fail closed."""
    return environment.get(AUTHORIZATION_VARIABLE, "").strip().lower() in _AUTHORIZED_VALUES


@dataclass(frozen=True)
class ProposalEffectResult:
    """The outcome of one `propose_candidate` call. `effected` is `True` only when every gate
    passed and the branch/PR state was confirmed to match the candidate by the end of the call -
    whether or not that needed a new commit or PR edit; every refusal leaves `effected` `False`
    with no network call beyond whatever read was needed to decide the refusal."""

    repository: str
    authorized: bool
    effected: bool
    branch: str
    pr_number: int | None
    pr_url: str | None
    commit_written: bool
    pr_created: bool
    pr_updated: bool
    reason: str


def _commit_message(authorization: ProposalAuthorization) -> str:
    return (
        "Update README via repository-presenter\n\n"
        f"candidate_hash: {authorization.candidate_hash}\n"
        f"source_revision: {authorization.source_revision}\n"
    )


def propose_candidate(
    *,
    repository: str,
    readme_text: str,
    source_revision: str,
    authorization: ProposalAuthorization,
    base_branch: str,
    pr_title: str,
    pr_body: str,
    token: str | None,
    environment: Mapping[str, str],
    branch: str | None = None,
    clock: ClockFn = _utc_now,
    recheck_source: RecheckSourceFn | None = None,
    get_ref: GetRefFn = default_get_ref,
    create_ref: CreateRefFn = default_create_ref,
    get_contents: GetContentsFn = default_get_contents,
    put_contents: PutContentsFn = default_put_contents,
    find_open_pull_request: FindOpenPullRequestFn = default_find_open_pull_request,
    create_pull_request: CreatePullRequestFn = default_create_pull_request,
    update_pull_request: UpdatePullRequestFn = default_update_pull_request,
    reconcile_write: ReconcileWriteFn | None = None,
) -> ProposalEffectResult:
    """Create or update the one stable presenter branch and PR on `repository` - but only past
    every gate in this module's own docstring. Every early return before the "past both gates"
    comment makes no network call at all.
    """
    owner, name = repository.split("/", 1)
    branch = branch if branch is not None else presenter_branch_name()

    def _refuse(authorized: bool, reason: str) -> ProposalEffectResult:
        return ProposalEffectResult(
            repository=repository,
            authorized=authorized,
            effected=False,
            branch=branch,
            pr_number=None,
            pr_url=None,
            commit_written=False,
            pr_created=False,
            pr_updated=False,
            reason=reason,
        )

    if not write_authorized(environment):
        return _refuse(False, _NOT_AUTHORIZED_REASON)

    if not token:
        return _refuse(True, _NO_TOKEN_REASON)

    decision = validate_authorization(
        authorization,
        now=clock(),
        expected_repository=repository,
        expected_candidate_hash=sha256_text(readme_text),
        expected_source_revision=source_revision,
        expected_branch=branch,
    )
    if not decision.granted:
        return _refuse(True, decision.reason)

    # past both gates and authorization validation -----------------------------------------

    if recheck_source is not None:
        live_revision = recheck_source()
        if live_revision != authorization.source_revision:
            return _refuse(
                True,
                "stale source: the target's live current revision "
                f"({live_revision}) no longer matches the authorized source revision "
                f"({authorization.source_revision}) - refusing to propose against a moved "
                "target; recapture and reauthorize",
            )

    try:
        base_sha = get_ref(owner, name, base_branch, token=token)
    except RepositoryMetadataError as exc:
        return _refuse(True, f"could not read base branch {base_branch!r}: {exc}")
    if base_sha is None:
        return _refuse(True, f"base branch {base_branch!r} does not exist")

    try:
        branch_sha = get_ref(owner, name, branch, token=token)
    except RepositoryMetadataError as exc:
        return _refuse(True, f"could not read presenter branch {branch!r}: {exc}")
    if branch_sha is None:
        try:
            create_ref(owner, name, branch, base_sha, token=token)
        except RepositoryMetadataError as exc:
            return _refuse(True, f"could not create presenter branch {branch!r}: {exc}")

    try:
        existing_file = get_contents(owner, name, README_PATH, ref=branch, token=token)
    except RepositoryMetadataError as exc:
        return _refuse(True, f"could not read {README_PATH} on {branch!r}: {exc}")

    commit_written = False
    if existing_file is None or existing_file.text != readme_text:
        file_sha = existing_file.sha if existing_file is not None else None
        try:
            put_contents(
                owner,
                name,
                README_PATH,
                branch=branch,
                message=_commit_message(authorization),
                text=readme_text,
                sha=file_sha,
                token=token,
            )
            commit_written = True
        except RepositoryMetadataError as exc:
            if "unreachable" not in str(exc) or reconcile_write is None:
                return _refuse(True, f"could not write {README_PATH} on {branch!r}: {exc}")
            # Lost-response reconciliation (AGENTS.md "reconcile uncertain remote effects before
            # retrying"): re-observe the branch's real current content before ever retrying.
            reconciled = reconcile_write()
            if reconciled is not None and reconciled.text == readme_text:
                commit_written = True  # the write landed; only the response was lost
            else:
                try:
                    put_contents(
                        owner,
                        name,
                        README_PATH,
                        branch=branch,
                        message=_commit_message(authorization),
                        text=readme_text,
                        sha=reconciled.sha if reconciled is not None else None,
                        token=token,
                    )
                    commit_written = True
                except RepositoryMetadataError as retry_exc:
                    return _refuse(
                        True,
                        f"write to {README_PATH} on {branch!r} failed after reconciliation: "
                        f"{retry_exc}",
                    )

    try:
        existing_pr = find_open_pull_request(owner, name, head_branch=branch, token=token)
    except RepositoryMetadataError as exc:
        return _refuse(True, f"could not list open pull requests for {branch!r}: {exc}")

    pr_created = False
    pr_updated = False
    if existing_pr is None:
        try:
            pr_ref = create_pull_request(
                owner,
                name,
                title=pr_title,
                body=pr_body,
                head=branch,
                base=base_branch,
                token=token,
            )
        except RepositoryMetadataError as exc:
            return _refuse(True, f"could not open the presenter pull request: {exc}")
        pr_created = True
    else:
        pr_ref = existing_pr
        if existing_pr.title != pr_title or existing_pr.body != pr_body:
            try:
                pr_ref = update_pull_request(
                    owner,
                    name,
                    existing_pr.number,
                    title=pr_title,
                    body=pr_body,
                    token=token,
                )
                pr_updated = True
            except RepositoryMetadataError as exc:
                return _refuse(True, f"could not update the presenter pull request: {exc}")

    return ProposalEffectResult(
        repository=repository,
        authorized=True,
        effected=True,
        branch=branch,
        pr_number=pr_ref.number,
        pr_url=pr_ref.url,
        commit_written=commit_written,
        pr_created=pr_created,
        pr_updated=pr_updated,
        reason="proposed" if (commit_written or pr_created or pr_updated) else "no change needed",
    )
