"""What the write token is, checked through the GitHub API before the effect writes anything.

``GH_PROPOSAL_WRITE_TOKEN`` must be a repository-scoped installation token minted for the
Repository Presenter GitHub App (id ``EXPECTED_APP_ID``) - never a hand-set personal access token,
and never a token that can reach more than the one target. The workflow's "App only" wording is a
convention; this module is the code that enforces it.

What GitHub lets a bare installation token prove about itself, before any write:

- ``GET /installation/repositories`` answers only to an installation access token (a personal
  access token is refused), and lists exactly the repositories the token can reach - so one
  request proves both "installation token" and "scoped to the target alone".
- The token prefix (``ghs_``) rules out the other token families before any request is made.

What it cannot prove: *which* App minted it. GitHub exposes an installation token's App only to
that App's own JWT, which the effect job deliberately does not hold. The App is therefore attested
on the artifact the token produces: :func:`verify_pull_request_app` reads the pull request's
``performed_via_github_app`` and refuses unless it is ``EXPECTED_APP_ID`` - before updating an
existing presenter pull request, and immediately after creating one.
"""

from __future__ import annotations

from dataclasses import dataclass

from repository_presenter.core.authorization.refusals import Refusal
from repository_presenter.core.errors import RepositoryMetadataError
from repository_presenter.core.github.client import (
    API_ROOT,
    FetchFn,
    default_fetch,
    get_pull_request_app_id,
)

#: The Repository Presenter GitHub App (``project/state.yaml``; ``docs/STATE_MACHINE.md``).
EXPECTED_APP_ID = 5092474
INSTALLATION_TOKEN_PREFIX = "ghs_"


@dataclass(frozen=True)
class TokenDecision:
    """``ok`` only when the token is an installation token scoped to exactly the target."""

    ok: bool
    code: Refusal | None = None
    reason: str = "token verified"


def _refuse(code: Refusal, reason: str) -> TokenDecision:
    return TokenDecision(False, code, reason)


def verify_installation_token(
    repository: str, token: str, *, fetch: FetchFn = default_fetch
) -> TokenDecision:
    """Refuse unless ``token`` is an installation token whose reach is exactly ``repository``."""
    if not token.startswith(INSTALLATION_TOKEN_PREFIX):
        return _refuse(
            Refusal.TOKEN_NOT_INSTALLATION,
            "the write token is not a GitHub App installation token (expected a "
            f"{INSTALLATION_TOKEN_PREFIX!r} token minted per run; personal access tokens are "
            "never an accepted write credential)",
        )
    url = f"{API_ROOT}/installation/repositories?per_page=100"
    status_code, body = fetch(url, token)
    if status_code == -1:
        return _refuse(Refusal.TOKEN_UNVERIFIABLE, f"could not verify the write token: {body}")
    if status_code in (401, 403):
        return _refuse(
            Refusal.TOKEN_NOT_INSTALLATION,
            f"GitHub refused the write token on the installation endpoint (HTTP {status_code}): "
            "it is not an installation token",
        )
    if status_code != 200 or not isinstance(body, dict):
        return _refuse(
            Refusal.TOKEN_UNVERIFIABLE,
            f"could not verify the write token: HTTP {status_code} from {url}",
        )
    listed = body.get("repositories")
    if not isinstance(listed, list) or body.get("total_count") != len(listed):
        return _refuse(
            Refusal.TOKEN_UNVERIFIABLE,
            "could not verify the write token: the installation repository list is incomplete",
        )
    reachable = sorted(
        str(item.get("full_name", "")).casefold() for item in listed if isinstance(item, dict)
    )
    if reachable != [repository.casefold()]:
        return _refuse(
            Refusal.TOKEN_WRONG_SCOPE,
            f"the write token reaches {len(reachable)} repositories, not exactly {repository} "
            "(mint it with the target repository as its only scope)",
        )
    return TokenDecision(True)


def verify_pull_request_app(
    owner: str,
    name: str,
    number: int,
    *,
    token: str,
    fetch: FetchFn = default_fetch,
    expected_app_id: int = EXPECTED_APP_ID,
) -> TokenDecision:
    """Refuse unless pull request ``number`` was performed by the expected GitHub App."""
    try:
        app_id = get_pull_request_app_id(owner, name, number, token=token, fetch=fetch)
    except RepositoryMetadataError as exc:
        return _refuse(Refusal.TOKEN_UNVERIFIABLE, f"could not attribute pull request: {exc}")
    if app_id != expected_app_id:
        return _refuse(
            Refusal.TOKEN_APP_MISMATCH,
            f"pull request #{number} was performed by GitHub App {app_id}, not the Repository "
            f"Presenter App {expected_app_id}",
        )
    return TokenDecision(True)


def verify_repository_token(
    repository: str, token: str, *, fetch: FetchFn = default_fetch
) -> TokenDecision:
    """Refuse unless ``token`` can read exactly ``repository`` - the control-repository write's
    own provenance check (``components/candidates_publish/effect.py``, G7-W14).

    Deliberately not :func:`verify_installation_token`: that check's ``GET
    /installation/repositories`` call proves a *GitHub App* installation token's reach, but this
    effect's write credential is the ambient per-job ``secrets.GITHUB_TOKEN`` GitHub Actions itself
    mints (already scoped to exactly the one repository the workflow runs in - the control
    repository, never a target product repository, per ``present.yml``'s own identical reasoning
    for its state-ref token) - a different credential family the installation endpoint cannot be
    assumed to answer for. This checks the one thing every GitHub REST credential can prove about
    itself the same way: reading the repository it claims to reach resolves to exactly that
    repository's own ``full_name``, never more, never less, and never merely because the token is
    present."""
    if not token:
        return _refuse(Refusal.TOKEN_UNVERIFIABLE, "no write-scoped token available")
    url = f"{API_ROOT}/repos/{repository}"
    status_code, body = fetch(url, token)
    if status_code == -1:
        return _refuse(Refusal.TOKEN_UNVERIFIABLE, f"could not verify the write token: {body}")
    if status_code in (401, 403):
        return _refuse(
            Refusal.TOKEN_UNVERIFIABLE,
            f"GitHub refused the write token on {repository} (HTTP {status_code})",
        )
    if status_code != 200 or not isinstance(body, dict):
        return _refuse(
            Refusal.TOKEN_UNVERIFIABLE,
            f"could not verify the write token: HTTP {status_code} from {url}",
        )
    full_name = str(body.get("full_name", ""))
    if full_name.casefold() != repository.casefold():
        return _refuse(
            Refusal.TOKEN_WRONG_SCOPE,
            f"the write token resolved {repository!r} to {full_name!r} - refusing a mismatched "
            "repository identity",
        )
    return TokenDecision(True)
