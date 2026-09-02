"""Canonical hashing ignores line endings and nothing else."""

from __future__ import annotations

import hashlib

from repository_presenter.core.hashing import sha256_text


def test_line_endings_hash_alike_and_content_does_not() -> None:
    expected = hashlib.sha256(b"a\nb\n").hexdigest()
    assert sha256_text("a\nb\n") == expected
    assert sha256_text("a\r\nb\r\n") == expected
    assert sha256_text("a\rb\r") == expected
    assert sha256_text("a\nb") != expected
