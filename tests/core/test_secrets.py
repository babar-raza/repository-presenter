"""Secret canary: a configured secret can never sit inside a candidate bundle unnoticed."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from repository_presenter.cli import EXIT_OK, EXIT_UNSAFE, main
from repository_presenter.core.secrets import (
    ConfiguredSecret,
    SecretLeak,
    configured_secrets,
    find_secret_leaks,
)
from support import REPO_ROOT, write_bundle, write_cursor

CANARY_TOKEN = "ghp_canary_9f2c7e1d4b6a8c0e"
CANARY_KEY = "sk-canary-3a1f9e7c5d2b4a6f"


def test_configured_secrets_are_named_by_convention() -> None:
    environment = {
        "GH_TOKEN": CANARY_TOKEN,
        "GPT_OSS_API_KEY": CANARY_KEY,
        "GPT_OSS_ENDPOINT": "https://gateway.example.com/v1",
        "GPT_OSS_MODEL": "model-name-that-is-long",
        "REGISTRY_PASSWORD": "hunter2hunter2",
        "SHORT_TOKEN": "abc",
        "EMPTY_SECRET": "",
        "PATH": "/usr/bin:/bin",
    }
    secrets = configured_secrets(environment)
    assert [s.variable for s in secrets] == ["GH_TOKEN", "GPT_OSS_API_KEY", "REGISTRY_PASSWORD"]
    assert all(isinstance(s.value, bytes) for s in secrets)


def test_every_secret_in_env_example_is_a_configured_secret() -> None:
    names = re.findall(r"^([A-Z_]+)=", (REPO_ROOT / ".env.example").read_text("utf-8"), re.M)
    assert {"GH_TOKEN", "GPT_OSS_API_KEY"} <= set(names)
    environment = {name: "value-that-is-long-enough" for name in names}
    detected = {s.variable for s in configured_secrets(environment)}
    assert detected == {"GH_TOKEN", "GPT_OSS_API_KEY"}


def test_secret_values_never_appear_in_reprs() -> None:
    secret = ConfiguredSecret("GH_TOKEN", CANARY_TOKEN.encode())
    assert CANARY_TOKEN not in repr(secret)
    assert CANARY_TOKEN not in str(secret)


def test_find_secret_leaks_reports_every_leaking_file(tmp_path: Path) -> None:
    secrets = configured_secrets({"GH_TOKEN": CANARY_TOKEN, "LLM_API_KEY": CANARY_KEY})
    bundle = write_bundle(tmp_path, "owner__alpha", "aaa111", "ACCEPTED")
    (bundle / "calls.jsonl").write_text(f'{{"authorization": "Bearer {CANARY_TOKEN}"}}\n', "utf-8")
    (bundle / "README.md").write_text("# Clean\n", "utf-8")
    nested = bundle / "attachments"
    nested.mkdir()
    (nested / "trace.log").write_bytes(b"key=" + CANARY_KEY.encode() + b"\n")
    assert find_secret_leaks(tmp_path, secrets) == [
        SecretLeak("LLM_API_KEY", nested / "trace.log"),
        SecretLeak("GH_TOKEN", bundle / "calls.jsonl"),
    ]


def test_find_secret_leaks_without_secrets_or_bundles_is_empty(tmp_path: Path) -> None:
    assert find_secret_leaks(tmp_path, ()) == []
    assert find_secret_leaks(tmp_path, configured_secrets({"GH_TOKEN": CANARY_TOKEN})) == []


def test_status_refuses_a_bundle_holding_a_configured_secret(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("GH_TOKEN", CANARY_TOKEN)
    bundle = write_bundle(project, "owner__alpha", "aaa111", "READY_FOR_PROPOSAL")
    (bundle / "facts.json").write_text(f'{{"token": "{CANARY_TOKEN}"}}', "utf-8")
    write_cursor(project, recorded_candidates=1)

    assert main(["status", "--root", str(project)]) == EXIT_UNSAFE

    captured = capsys.readouterr()
    assert (
        "secret canary: value of GH_TOKEN found in candidates/owner__alpha/aaa111/facts.json"
        in captured.err
    )
    assert "candidates:" not in captured.out
    assert CANARY_TOKEN not in captured.out + captured.err


def test_status_accepts_bundles_without_configured_secrets(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("GH_TOKEN", CANARY_TOKEN)
    monkeypatch.setenv("LLM_API_KEY", CANARY_KEY)
    bundle = write_bundle(project, "owner__alpha", "aaa111", "READY_FOR_PROPOSAL")
    (bundle / "facts.json").write_text('{"token": "redacted"}', "utf-8")
    write_cursor(project, recorded_candidates=1)

    assert main(["status", "--root", str(project)]) == EXIT_OK
    assert "candidates: 1/34" in capsys.readouterr().out


def test_redaction_masks_secret_shaped_and_live_values() -> None:
    from repository_presenter.core.secrets import redact

    text = (
        "key sk-abcdefghijklmnop token ghp_abcdefghijklmnop "
        "bearer Bearer abcdefghijklmnopqrstuvwxyz "
        "url https://x/?api_key=abcdefghij literal MY-LIVE-SECRET-VALUE plain text"
    )
    result = redact(text, ["MY-LIVE-SECRET-VALUE", ""])
    assert "sk-abcdefghijklmnop" not in result
    assert "ghp_abcdefghijklmnop" not in result
    assert "Bearer abcdefghijklmnopqrstuvwxyz" not in result
    assert "api_key=abcdefghij" not in result
    assert "MY-LIVE-SECRET-VALUE" not in result
    assert result.count("[REDACTED]") == 5
    assert result.endswith("plain text")
    assert redact("nothing secret here") == "nothing secret here"
