"""Per-owner GitHub App installation state for the scheduled drift observation (G7-W06).

`.github/workflows/monitor.yml` mints one read-only installation token per owner. A failed mint
is ambiguous: ``actions/create-github-app-token`` does not expose the HTTP status behind it, and a
revoked key (401), a permission problem (403), a GitHub outage (5xx) and a network error all fail
the same way as a genuinely missing installation (404). Only the last is a notice; the others are
real errors and must keep the owner's leg red.

So a failed mint is never classified from the outcome alone. ``classify`` asks GitHub directly:
``GET /repos/{owner}/{repo}/installation`` (the exact lookup the action performs), authenticated as
the App with a short-lived JWT, for each enabled repository in order. The first non-200 answer
decides:

- ``404``: ``NOT_INSTALLED``, a notice naming the missing install.
- anything else (401, 403, 5xx, an unrecognized status, a transport error): ``MINT_ERROR``.
- every lookup answers 200 although the mint failed: ``MINT_ERROR`` (the failure is unexplained,
  so it is not called benign).
- credentials unavailable, so the lookup cannot run: ``MINT_ERROR``.

The coverage rule stays as a second net: the run is red when no owner at all is ``INSTALLED``.

JWT signing departs from the registry's first choice (a library, ``AGENTS.md`` Implementation
Discipline): PyJWT needs ``cryptography`` and ``cffi``, which would enter the product lock and its
SBOM for ten lines of RS256, and installing them unpinned inside a step that holds the App private
key is worse. The signature is produced by ``openssl dgst -sha256 -sign``, present on every runner,
with the key written to a mode-0600 file that is deleted straight after the call. The key and the
JWT are never printed and never reach the state file (``redact`` covers both).
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from repository_presenter.core.github.read_client import GITHUB_API_ROOT, Fetch, fetch_get
from repository_presenter.core.secrets import redact

APP_SLUG = "repository-presenter"
APP_ID = 5092474
SCHEMA_VERSION = 1
INSTALLED = "INSTALLED"
NOT_INSTALLED = "NOT_INSTALLED"
MINT_ERROR = "MINT_ERROR"
MINT_OUTCOMES: tuple[str, ...] = ("success", "failure")
RECORD_GLOB = "install-*.json"
NOT_FOUND = 404
JWT_LIFETIME_SECONDS = 540
JWT_BACKDATE_SECONDS = 60

Signer = Callable[[bytes, str], bytes]


class InstallStateError(ValueError):
    """A mint outcome this module does not recognize: an internal defect, never a notice."""


@dataclass(frozen=True)
class InstallationState:
    owner: str
    state: str
    repositories: str
    detail: str | None


@dataclass(frozen=True)
class LookupResult:
    """One repository's installation lookup: the HTTP status, or the transport error."""

    repository: str
    status: int | None
    error: str | None = None


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def sign_with_openssl(message: bytes, private_key: str) -> bytes:
    """RS256 signature of ``message`` via ``openssl dgst -sha256 -sign`` (key not on a CLI arg)."""
    descriptor, name = tempfile.mkstemp(suffix=".pem")
    try:
        os.chmod(name, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(private_key if private_key.endswith("\n") else private_key + "\n")
        completed = subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign", name],
            input=message,
            capture_output=True,
            check=True,
            timeout=30,
        )
    finally:
        Path(name).unlink(missing_ok=True)
    return completed.stdout


def app_jwt(app_id: str, private_key: str, *, now: float | None = None, sign: Signer) -> str:
    """The short-lived App JWT (RS256) that authenticates the installation lookup."""
    issued = int(now if now is not None else time.time())
    header = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    claims = {
        "iat": issued - JWT_BACKDATE_SECONDS,
        "exp": issued + JWT_LIFETIME_SECONDS,
        "iss": str(app_id),
    }
    payload = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}"
    return f"{signing_input}.{_b64url(sign(signing_input.encode('ascii'), private_key))}"


def lookup_installations(
    owner: str,
    repositories: list[str],
    *,
    app_id: str,
    private_key: str,
    fetch: Fetch = fetch_get,
    sign: Signer = sign_with_openssl,
) -> list[LookupResult]:
    """Ask GitHub, as the App, whether it is installed for each repository. One GET each."""
    token = app_jwt(app_id, private_key, sign=sign)
    results: list[LookupResult] = []
    for name in repositories:
        url = f"{GITHUB_API_ROOT}/repos/{owner}/{name}/installation"
        try:
            response = fetch(url, token)
        except httpx.HTTPError as exc:
            message = redact(f"{type(exc).__name__}: {exc}", [token, private_key])
            results.append(LookupResult(name, None, message))
            continue
        results.append(LookupResult(name, response.status_code))
    return results


def classify(owner: str, repositories: str, lookups: list[LookupResult]) -> InstallationState:
    """Decide a FAILED mint's meaning from the lookups. Only a confirmed 404 is a notice."""
    for lookup in lookups:
        if lookup.status == 200:
            continue
        if lookup.status == NOT_FOUND:
            detail = (
                f"GitHub App '{APP_SLUG}' (id {APP_ID}) has no installation on '{owner}' "
                f"covering '{lookup.repository}' (GET /repos/{owner}/{lookup.repository}/"
                f"installation answered 404), so no read-only token could be minted for the "
                f"enabled repositories ({repositories}). Install the App on '{owner}' with these "
                "repositories selected. Until then this owner is not observed; this is a notice, "
                "not a failure."
            )
            return InstallationState(owner, NOT_INSTALLED, repositories, detail)
        what = lookup.error if lookup.status is None else f"HTTP {lookup.status}"
        return _mint_error(
            owner, repositories, f"the installation lookup for '{lookup.repository}' failed: {what}"
        )
    return _mint_error(
        owner,
        repositories,
        "the token mint failed although every installation lookup answered 200; "
        "the failure is unexplained, so it is not treated as a missing installation",
    )


def _mint_error(owner: str, repositories: str, reason: str) -> InstallationState:
    detail = (
        f"The read-only token for '{owner}' could not be minted and this is NOT a missing "
        f"installation: {reason}. This leg fails."
    )
    return InstallationState(owner, MINT_ERROR, repositories, detail)


def record_state(
    owner: str,
    outcome: str,
    repositories: str,
    *,
    lookup: Callable[[], list[LookupResult]] | None = None,
) -> InstallationState:
    """Classify one owner's mint outcome. ``success`` means the App is installed for these repos.

    A ``failure`` is classified from ``lookup`` (the live lookup). With no lookup possible it is a
    ``MINT_ERROR``: an unexplained failure is never presumed to be a missing installation.
    """
    if outcome not in MINT_OUTCOMES:
        raise InstallStateError(f"unrecognized token mint outcome {outcome!r} for {owner}")
    if outcome == "success":
        return InstallationState(owner, INSTALLED, repositories, None)
    if lookup is None:
        return _mint_error(
            owner, repositories, "no installation lookup was possible (App credentials unavailable)"
        )
    return classify(owner, repositories, lookup())


def write_state(state: InstallationState, path: Path) -> Path:
    """Write one owner's state as deterministic JSON. No token is ever an input to this file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {"schema_version": SCHEMA_VERSION, **asdict(state)}
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


@dataclass(frozen=True)
class Summary:
    exit_code: int
    notices: tuple[str, ...]
    markdown: str
    problem: str | None


def summarize_installs(directory: Path) -> Summary:
    """Read every owner's state under ``directory``. Exit 1 only when no owner was observable."""
    records: list[dict[str, str | None]] = []
    for path in sorted(directory.rglob(RECORD_GLOB)):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    if not records:
        return Summary(
            1,
            (),
            "",
            "no installation records were found: the observation did not run for any owner",
        )
    installed = [r for r in records if r.get("state") == INSTALLED]
    missing = [r for r in records if r.get("state") == NOT_INSTALLED]
    rows = ["| Owner | Installation | Enabled repositories |", "| --- | --- | --- |"]
    rows += [f"| {r['owner']} | {r['state']} | {r['repositories']} |" for r in records]
    markdown = "\n".join(["## Monitor installation coverage", "", *rows, ""])
    notices = tuple(
        f"::notice title=GitHub App not installed on {r['owner']}::{r['detail']}" for r in missing
    )
    if not installed:
        return Summary(
            1,
            notices,
            markdown,
            "no owner's token could be minted, so the App credentials are the likely cause, "
            "not a per-owner installation gap; check GH_APP_ID and GH_APP_PRIVATE_KEY",
        )
    return Summary(0, notices, markdown, None)
