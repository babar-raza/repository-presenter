"""Extraction parses source with every grammar; none of it may touch the network.

A grammar is a pinned wheel (``core/grammars.py``), so a parse is a local import. Python's socket
layer is closed for every test under this directory so that a future grammar, parser, or probe that
reached for a download fails here instead of on a hosted runner when a release host hiccups.
"""

from __future__ import annotations

import socket
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def extraction_never_opens_a_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("extraction tried to open a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
