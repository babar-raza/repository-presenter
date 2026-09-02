"""Configured secrets and the canary that keeps them out of candidate bundles.

The process environment names the secrets the runtime is configured with: the variables listed in
``.env.example`` and any variable whose name ends in a secret-bearing suffix. A candidate bundle
is reviewable evidence, so any bundle file that contains one of those values verbatim is a leak.
The leak is reported by variable name and file path only; the value itself is never echoed.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from repository_presenter.core.candidates import CANDIDATES_DIRNAME

SECRET_VARIABLES = frozenset({"LLM_API_KEY", "GH_TOKEN"})
SECRET_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD")
MIN_SECRET_LENGTH = 8


@dataclass(frozen=True)
class ConfiguredSecret:
    """One secret the runtime is configured with. Its value never appears in a repr."""

    variable: str
    value: bytes = field(repr=False)


@dataclass(frozen=True)
class SecretLeak:
    """A configured secret's value found verbatim inside a candidate bundle file."""

    variable: str
    path: Path


def configured_secrets(environment: Mapping[str, str]) -> tuple[ConfiguredSecret, ...]:
    """Return the secrets configured in ``environment``, in variable-name order."""
    found = []
    for name in sorted(environment):
        if name not in SECRET_VARIABLES and not name.endswith(SECRET_SUFFIXES):
            continue
        value = environment[name]
        if len(value) >= MIN_SECRET_LENGTH:
            found.append(ConfiguredSecret(name, value.encode("utf-8")))
    return tuple(found)


_SECRET_LIKE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(sk-[A-Za-z0-9]{10,})"
    r"|(?<![A-Za-z0-9_])(ghp_[A-Za-z0-9]{10,})"
    r"|(?<![A-Za-z0-9_])(ghu_[A-Za-z0-9]{10,})"
    r"|(?<![A-Za-z0-9_])(AIzaSy[A-Za-z0-9_-]{10,})"
    r"|(Bearer\s+[A-Za-z0-9._-]{20,})"
    r"|([?&](api_key|token|key|access_token)=[^\s&]{8,})",
    re.IGNORECASE,
)
REDACTED = "[REDACTED]"


def redact(text: str, live_secret_values: Sequence[str] = ()) -> str:
    """Mask secret-shaped values and every live secret value before text is persisted."""
    result = _SECRET_LIKE_PATTERN.sub(REDACTED, text)
    for secret in live_secret_values:
        if secret:
            result = result.replace(secret, REDACTED)
    return result


def find_secret_leaks(root: Path, secrets: Sequence[ConfiguredSecret]) -> list[SecretLeak]:
    """Return every (variable, file) pair where a secret appears under ``root/candidates``."""
    candidates = root / CANDIDATES_DIRNAME
    if not secrets or not candidates.is_dir():
        return []
    leaks: list[SecretLeak] = []
    for path in sorted(p for p in candidates.rglob("*") if p.is_file()):
        data = path.read_bytes()
        leaks.extend(SecretLeak(s.variable, path) for s in secrets if s.value in data)
    return leaks
