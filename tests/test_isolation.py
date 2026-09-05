"""Isolation: no test, at any fixture scope, can see a real credential or a live gateway."""

from __future__ import annotations

import importlib.util
import os

import pytest

from conftest import AMBIENT_CREDENTIALS
from repository_presenter.core.llm import transport


@pytest.fixture(scope="session")
def credentials_a_session_fixture_can_see() -> list[str]:
    """What the environment offers a session-scoped fixture, which is built before every
    function-scoped one - the window the per-test cleaning could not reach."""
    return sorted(name for name in AMBIENT_CREDENTIALS if name in os.environ)


def test_no_fixture_at_any_scope_sees_an_ambient_credential(
    credentials_a_session_fixture_can_see: list[str],
) -> None:
    """A live gateway belongs to preflight and present, never to pytest.

    With GPT_OSS_ENDPOINT and GPT_OSS_API_KEY in the process environment, a session-scoped
    fixture composed against the real gateway and a rejected reply failed a different test on
    each run; the same tree with both unset passed every test (lane B, 2026-09-06).
    """
    assert credentials_a_session_fixture_can_see == []
    assert [name for name in AMBIENT_CREDENTIALS if name in os.environ] == []


def test_no_install_a_test_drives_reaches_an_index() -> None:
    """The one network call left in the suite was pip's, and it is what broke under -n auto.

    Verifying an example installs the repository into a throwaway venv; with build isolation pip
    fetched its backend from PyPI once per install, and 27 concurrent workers made that fail
    intermittently - a different test red on each run (measured 2026-09-06). The backend is a dev
    dependency now, so nothing is fetched and the suite runs in 76 seconds rather than 118.
    """
    assert os.environ["PIP_NO_BUILD_ISOLATION"] == "1"
    assert os.environ["PIP_NO_INDEX"] == "1"
    # Turning isolation off only works because this environment carries the backend itself.
    assert importlib.util.find_spec("setuptools") is not None


def test_building_a_gateway_client_is_refused_in_tests() -> None:
    """Even with a configuration in hand, the transport a test would use is not the real one."""
    with pytest.raises(RuntimeError, match="unreachable in tests"):
        transport.build_client(object())
