"""Per-owner GitHub App installation state (G7-W06).

A failed token mint is classified by an explicit installation lookup, never by the mint outcome
alone: only a confirmed 404 is a notice (NOT_INSTALLED); 401, 403, 5xx, an unrecognized status, a
transport error, an unexplained failure and unavailable credentials each keep the owner's leg red
(MINT_ERROR). No test reaches GitHub: the lookup's HTTP call and the JWT signer are injected.
"""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
from pathlib import Path

import httpx
import pytest

from repository_presenter.cli import EXIT_INCONSISTENT, EXIT_OK, main, run_monitor_install_record
from repository_presenter.components.monitor.install_state import (
    INSTALLED,
    MINT_ERROR,
    NOT_INSTALLED,
    InstallStateError,
    LookupResult,
    app_jwt,
    lookup_installations,
    record_state,
    sign_with_openssl,
    summarize_installs,
    write_state,
)

HTML = "aspose-html-foss"
PDF = "aspose-pdf-foss"
HTML_REPOS = "Aspose.HTML-FOSS-for-Python"
PDF_REPOS = "Aspose.PDF-FOSS-for-Go"


def _lookup_404() -> LookupResult:
    return LookupResult(HTML_REPOS, 404)


FAKE_KEY = "-----BEGIN RSA PRIVATE KEY-----\nFAKEKEYMATERIALFORTESTS\n-----END RSA PRIVATE KEY-----"


def _fake_sign(message: bytes, private_key: str) -> bytes:
    return b"signature-of-" + message[:4]


class _Fetch:
    """Serve one scripted answer per URL (an int status or an exception); record every call."""

    def __init__(self, answers: dict[str, int | Exception]) -> None:
        self.answers = answers
        self.calls: list[tuple[str, str | None]] = []

    def __call__(self, url: str, token: str | None) -> httpx.Response:
        self.calls.append((url, token))
        answer = self.answers[
            url.rsplit("/repos/", 1)[1].split("/installation")[0].split("/", 1)[1]
        ]
        if isinstance(answer, Exception):
            raise answer
        return httpx.Response(answer)


def _lookup_with(answers: dict[str, int | Exception]):  # type: ignore[no-untyped-def]
    fetch = _Fetch(answers)

    def lookup(owner: str, names: list[str], *, app_id: str, private_key: str):  # type: ignore[no-untyped-def]
        return lookup_installations(
            owner, names, app_id=app_id, private_key=private_key, fetch=fetch, sign=_fake_sign
        )

    return lookup, fetch


def _record(directory: Path, owner: str, outcome: str, repositories: str) -> None:
    write_state(
        record_state(owner, outcome, repositories),
        directory / "runs" / "monitor" / f"install-{owner}.json",
    )


def _run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    answers: dict[str, int | Exception],
    *,
    credentials: bool = True,
) -> tuple[int, dict[str, str | None]]:
    if credentials:
        monkeypatch.setenv("GH_APP_ID", "5092474")
        monkeypatch.setenv("GH_APP_PRIVATE_KEY", FAKE_KEY)
    else:
        monkeypatch.delenv("GH_APP_ID", raising=False)
        monkeypatch.delenv("GH_APP_PRIVATE_KEY", raising=False)
    lookup, _ = _lookup_with(answers)
    out = tmp_path / f"install-{HTML}.json"
    code = run_monitor_install_record(HTML, "failure", HTML_REPOS, out, lookup=lookup)
    return code, json.loads(out.read_text(encoding="utf-8"))


def test_a_successful_mint_is_installed_with_no_detail_and_needs_no_lookup() -> None:
    state = record_state(PDF, "success", PDF_REPOS)

    assert (state.state, state.detail) == (INSTALLED, None)


def test_a_confirmed_404_is_a_notice_naming_the_owner_the_app_and_the_missing_install(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    code, document = _run(monkeypatch, tmp_path, {HTML_REPOS: 404})

    assert code == EXIT_OK
    assert document["state"] == NOT_INSTALLED
    detail = document["detail"] or ""
    assert f"'{HTML}'" in detail
    assert "'repository-presenter' (id 5092474)" in detail
    assert HTML_REPOS in detail
    assert "answered 404" in detail
    assert "not a failure" in detail


@pytest.mark.parametrize("status", [401, 403, 500, 502, 503, 418, 302])
def test_any_other_status_keeps_the_leg_red_with_its_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: int
) -> None:
    # Negative control: a revoked key (401), missing permission (403), an outage (5xx) and an
    # unrecognized status must never read as a harmless "not installed" notice.
    code, document = _run(monkeypatch, tmp_path, {HTML_REPOS: status})

    assert code == EXIT_INCONSISTENT
    assert document["state"] == MINT_ERROR
    assert f"HTTP {status}" in (document["detail"] or "")
    assert "NOT a missing installation" in (document["detail"] or "")


def test_a_network_error_keeps_the_leg_red(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    code, document = _run(
        monkeypatch, tmp_path, {HTML_REPOS: httpx.ConnectError("connection refused")}
    )

    assert code == EXIT_INCONSISTENT
    assert document["state"] == MINT_ERROR
    assert "ConnectError" in (document["detail"] or "")


def test_a_failed_mint_with_every_lookup_ok_is_unexplained_and_red(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    code, document = _run(monkeypatch, tmp_path, {HTML_REPOS: 200})

    assert code == EXIT_INCONSISTENT
    assert document["state"] == MINT_ERROR
    assert "unexplained" in (document["detail"] or "")


def test_unavailable_credentials_cannot_confirm_a_404_so_the_leg_is_red(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    code, document = _run(monkeypatch, tmp_path, {HTML_REPOS: 404}, credentials=False)

    assert code == EXIT_INCONSISTENT
    assert document["state"] == MINT_ERROR


def test_the_first_non_200_decides_across_several_repositories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lookup, _ = _lookup_with({"a": 200, "b": 404, "c": 500})

    state = record_state(
        "o",
        "failure",
        "a,b,c",
        lookup=lambda: lookup("o", ["a", "b", "c"], app_id="1", private_key=FAKE_KEY),
    )

    assert state.state == NOT_INSTALLED
    assert "'b'" in (state.detail or "")
    # A 500 on an earlier repository wins over a later 404.
    lookup2, _ = _lookup_with({"a": 500, "b": 404})
    state2 = record_state(
        "o",
        "failure",
        "a,b",
        lookup=lambda: lookup2("o", ["a", "b"], app_id="1", private_key=FAKE_KEY),
    )
    assert state2.state == MINT_ERROR


def test_a_signing_failure_is_red_and_leaks_neither_key_nor_jwt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GH_APP_ID", "5092474")
    monkeypatch.setenv("GH_APP_PRIVATE_KEY", FAKE_KEY)

    def broken(owner: str, names: list[str], **_: str):  # type: ignore[no-untyped-def]
        raise subprocess.CalledProcessError(1, ["openssl"], stderr=FAKE_KEY.encode())

    out = tmp_path / "install.json"
    code = run_monitor_install_record(HTML, "failure", HTML_REPOS, out, lookup=broken)

    text = out.read_text(encoding="utf-8")
    assert code == EXIT_INCONSISTENT
    assert json.loads(text)["state"] == MINT_ERROR
    assert "FAKEKEYMATERIAL" not in text


def test_the_lookup_authenticates_as_the_app_and_never_stores_the_jwt() -> None:
    lookup, fetch = _lookup_with({HTML_REPOS: 404})

    results = lookup(HTML, [HTML_REPOS], app_id="5092474", private_key=FAKE_KEY)

    ((url, token),) = fetch.calls
    assert url == f"https://api.github.com/repos/{HTML}/{HTML_REPOS}/installation"
    header, payload, signature = (token or "").split(".")
    assert json.loads(base64.urlsafe_b64decode(header + "==")) == {"alg": "RS256", "typ": "JWT"}
    claims = json.loads(base64.urlsafe_b64decode(payload + "=="))
    assert claims["iss"] == "5092474"
    assert claims["exp"] - claims["iat"] == 600
    assert signature
    assert [(r.repository, r.status) for r in results] == [(HTML_REPOS, 404)]


def test_an_unrecognized_mint_outcome_is_an_internal_error_never_a_notice() -> None:
    # Negative control: 'cancelled' or an empty outcome means the workflow wiring is broken, and
    # must fail loudly rather than be recorded as a quiet "not installed".
    with pytest.raises(InstallStateError):
        record_state(HTML, "cancelled", HTML_REPOS)
    with pytest.raises(InstallStateError):
        record_state(HTML, "", HTML_REPOS)


def test_a_failure_with_no_lookup_is_never_presumed_a_missing_installation() -> None:
    state = record_state(HTML, "failure", HTML_REPOS)

    assert state.state == MINT_ERROR


@pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl not installed")
def test_the_openssl_signature_verifies_against_the_public_key(tmp_path: Path) -> None:
    key = tmp_path / "key.pem"
    pub = tmp_path / "pub.pem"
    subprocess.run(["openssl", "genrsa", "-out", str(key), "2048"], check=True, capture_output=True)
    subprocess.run(
        ["openssl", "rsa", "-in", str(key), "-pubout", "-out", str(pub)],
        check=True,
        capture_output=True,
    )
    jwt = app_jwt("5092474", key.read_text(encoding="utf-8"), now=1_000_000, sign=sign_with_openssl)

    signing_input, _, signature = jwt.rpartition(".")
    sig_file = tmp_path / "sig.bin"
    sig_file.write_bytes(base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4)))
    verified = subprocess.run(
        ["openssl", "dgst", "-sha256", "-verify", str(pub), "-signature", str(sig_file)],
        input=signing_input.encode("ascii"),
        capture_output=True,
    )
    assert verified.returncode == 0, verified.stderr


def test_one_missing_install_among_observed_owners_is_a_notice_and_exits_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _record(tmp_path, PDF, "success", PDF_REPOS)
    write_state(
        record_state(HTML, "failure", HTML_REPOS, lookup=lambda: [_lookup_404()]),
        tmp_path / "runs" / "monitor" / f"install-{HTML}.json",
    )

    code = main(["monitor-install-summary", str(tmp_path / "runs" / "monitor")])

    captured = capsys.readouterr()
    assert code == EXIT_OK
    assert f"::notice title=GitHub App not installed on {HTML}::" in captured.out
    assert f"| {HTML} | {NOT_INSTALLED} |" in captured.out
    assert f"| {PDF} | {INSTALLED} |" in captured.out


def test_the_summary_is_appended_to_the_step_summary_file(tmp_path: Path) -> None:
    _record(tmp_path, PDF, "success", PDF_REPOS)
    step_summary = tmp_path / "summary.md"

    code = main(
        [
            "monitor-install-summary",
            str(tmp_path / "runs" / "monitor"),
            "--summary",
            str(step_summary),
        ]
    )

    assert code == EXIT_OK
    assert "## Monitor installation coverage" in step_summary.read_text(encoding="utf-8")


def test_no_owner_observable_is_red_because_the_credentials_are_the_likely_cause(
    tmp_path: Path,
) -> None:
    # Negative control: when every mint fails, a notice per owner would hide a broken App key.
    write_state(
        record_state(HTML, "failure", HTML_REPOS, lookup=lambda: [_lookup_404()]),
        tmp_path / f"install-{HTML}.json",
    )
    _record(tmp_path, PDF, "failure", PDF_REPOS)

    result = summarize_installs(tmp_path)

    assert result.exit_code == 1
    assert result.problem is not None
    assert "GH_APP_PRIVATE_KEY" in result.problem


def test_no_records_at_all_is_red_because_nothing_was_observed(tmp_path: Path) -> None:
    result = summarize_installs(tmp_path)

    assert result.exit_code == 1
    assert result.problem is not None
    assert "did not run" in result.problem


def test_record_command_rejects_an_outcome_outside_the_mint_vocabulary(tmp_path: Path) -> None:
    # argparse rejects a value outside its choices before any state is written.
    with pytest.raises(SystemExit):
        main(
            [
                "monitor-install-record",
                "--owner",
                HTML,
                "--outcome",
                "cancelled",
                "--repositories",
                HTML_REPOS,
                "--out",
                str(tmp_path / "x.json"),
            ]
        )
    assert not (tmp_path / "x.json").exists()
