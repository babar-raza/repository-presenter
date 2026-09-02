"""Canonical text hashing: one SHA-256 for one text regardless of its line endings.

Extracted from the legacy ``readme/facts.py``: line endings are normalised to LF before hashing
so a manifest or a rendered document hashes the same on every platform.
"""

from __future__ import annotations

import hashlib


def sha256_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
