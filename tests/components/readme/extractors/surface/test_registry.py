"""The registry façade observes, and says plainly when it did not."""

from __future__ import annotations

import json
from typing import Any

import pytest

from repository_presenter.components.readme.extractors.surface.registry import (
    REGISTRY_TYPES,
    TRANSIENT_STATUSES,
    RegistryObservation,
    observe,
    registry_type,
)
from repository_presenter.core.retry import RETRY_POLICIES

_POLICY = RETRY_POLICIES["package_registry"]


def _no_sleep(_seconds: float) -> None:
    """The policy's backoff, skipped: a test measures the replays, never waits on them."""


class _Response:
    """What the vendored probe expects a fetch to return."""

    def __init__(self, status: int, payload: dict[str, Any] | None = None) -> None:
        self.status = status
        self.status_code = status
        self.text = json.dumps(payload or {})
        self.body = self.text
        self._payload = payload or {}

    def json(self) -> dict[str, Any]:
        return self._payload


def _answers(*first: int | None, then: Any) -> tuple[list[str], Any]:
    """A fetch that gives ``first`` in order - a status, or None for a connection failure the
    way the vendored ``default_fetch`` reports one - and ``then`` to every later call."""
    queue: list[int | None] = list(first)
    calls: list[str] = []

    def fetch(url: str, **kwargs: Any) -> Any:
        calls.append(url)
        if queue:
            answer = queue.pop(0)
            return None if answer is None else _Response(answer)
        return then

    return calls, fetch


def test_every_ecosystem_the_portfolio_uses_names_its_registry() -> None:
    """Section 29.12: one probe, every registry - and C++ honestly has none."""
    assert registry_type("python") == "pypi" and registry_type("net") == "nuget"
    assert registry_type("java") == "maven" and registry_type("rust") == "cargo"
    # G4-W17 arrival item 8: the vendored adapter table is keyed "go_modules", not "goproxy" -
    # the wrong key took probe_publication's "unknown registry" branch and never issued a
    # request at all, so install_command:go could never leave UNRESOLVED.
    assert registry_type("go") == "go_modules"
    assert registry_type("cpp") == "", "C++ has no package registry; the façade must not invent one"
    assert set(REGISTRY_TYPES) == {"python", "net", "java", "typescript", "go", "rust"}


def test_a_go_module_path_reaches_the_proxy_under_the_key_the_adapter_reads() -> None:
    """G4-W17 arrival item 8. `check_published` (package_registries/go.py) reads
    candidate["module_path"], never candidate["name"] alone - passing only "name" is an
    uncaught KeyError, not a graceful miss. Measured 2026-09-06 on both Go repositories in the
    cohort: this crashed the facts stage outright once the registry key above was fixed alone."""
    calls: list[str] = []

    def fetch(url: str, **kwargs: Any) -> _Response:
        calls.append(url)
        return _Response(200, {}) if url.endswith("/@v/list") else _Response(404)

    module_path = "github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-Go"
    reading = observe("go", module_path, fetch=fetch)
    assert calls, "the Go proxy was never reached"
    assert "proxy.golang.org" in calls[0]
    assert reading.registry == "go_modules"


def test_a_maven_coordinate_splits_into_the_group_and_artifact_the_probe_needs() -> None:
    """G4-W17 arrival item 12 (lane C's PROPOSAL A). `_maven_check` addresses
    repo1.maven.org/maven2/{group_path}/{artifact_id}/maven-metadata.xml and returns ambiguous
    before fetching anything when group_id or artifact_id is missing; Java's package:name fact
    is already the "group:artifact" coordinate a reader writes, so no plugin needs a fact of its
    own to supply what observe() can derive by splitting on the one colon."""
    calls: list[str] = []

    def fetch(url: str, **kwargs: Any) -> _Response:
        calls.append(url)
        return _Response(200)

    reading = observe("java", "org.aspose:aspose-3d-foss", fetch=fetch)
    assert calls, "Maven Central was never reached"
    assert "org/aspose/aspose-3d-foss/maven-metadata.xml" in calls[0]
    assert reading.conclusive and reading.published is True


def test_an_offline_probe_is_inconclusive_rather_than_negative() -> None:
    """ "We could not check" is not "we checked and it is false" (section 29.6 E5).

    A caller that took an offline reading as CONTRADICTED would write a disposition saying the
    package is unpublished, on no evidence at all.
    """

    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("a probe reached the network while offline")

    reading = observe("net", "Aspose.Widget", fetch=refuse, offline=True)
    assert reading.published is None and reading.ambiguous is True
    assert not reading.conclusive
    assert "offline" in reading.source


def test_an_ecosystem_without_a_registry_never_reaches_the_network() -> None:
    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("C++ has no registry to reach")

    reading = observe("cpp", "aspose-widget", fetch=refuse)
    assert reading.registry == "" and not reading.conclusive


def test_a_published_package_reads_as_published_through_an_injected_fetch() -> None:
    """No test touches a real registry; the fetch is the seam the façade exposes."""
    calls: list[str] = []

    def fetch(url: str, **kwargs: Any) -> _Response:
        calls.append(url)
        return _Response(200, {"id": "Aspose.Widget", "versions": ["1.0.0"]})

    reading = observe("net", "Aspose.Widget", fetch=fetch)
    assert calls and "nuget" in calls[0].lower()
    assert reading.registry == "nuget" and reading.name == "Aspose.Widget"
    assert reading.published is not None


@pytest.mark.parametrize("status", [404, 500])
def test_a_registry_that_answers_nothing_useful_stays_inconclusive_or_unpublished(
    status: int,
) -> None:
    """A 404 may mean unpublished; a 500 means we do not know. Neither may be silently the other."""

    def fetch(url: str, **kwargs: Any) -> _Response:
        return _Response(status)

    reading = observe("net", "Aspose.Widget", fetch=fetch, sleep=_no_sleep)
    assert reading.published is not True
    if status == 500:
        assert not reading.conclusive


@pytest.mark.parametrize(
    "transient",
    [None, *sorted(TRANSIENT_STATUSES)],
    ids=lambda answer: "no-response" if answer is None else f"http-{answer}",
)
def test_a_transient_registry_answer_is_asked_again_and_the_recovered_reading_stands(
    transient: int | None,
) -> None:
    """G4-W17 arrival item 57 (lane F's PROPOSAL F9). `observe()` probed once, while
    `RETRY_POLICIES["package_registry"]` existed and only `python_registry.py` used it - every
    other ecosystem got one shot. Measured 2026-09-11: 5 of 10 NuGet reads in one lane run came
    back unreadable, each `install_command:dotnet` UNRESOLVED -> BC-02 FAIL at EXTRACTING,
    recorded unrepairable, for a package three direct requests proved published (1
    ConnectTimeout, 2 x HTTP 200). One transient answer must cost one replay, not the seal."""
    calls, fetch = _answers(transient, then=_Response(200, {"versions": ["1.0.0"]}))
    sleeps: list[float] = []

    reading = observe("net", "Aspose.Widget", fetch=fetch, sleep=sleeps.append)

    assert reading.conclusive and reading.published is True, reading
    assert len(sleeps) == 1, "one transient answer is exactly one replay"
    assert 0 <= sleeps[0] <= _POLICY.maximum_seconds
    # The replay asks the same URL again - the read that failed, not a different one.
    assert len(calls) >= 2 and calls[1] == calls[0]


@pytest.mark.parametrize("transient", [None, 503], ids=["no-response", "http-503"])
def test_a_registry_that_stays_down_is_given_up_after_the_policy_attempts_and_stays_unread(
    transient: int | None,
) -> None:
    """Negative control for the retry: bounded, and never a false negative. A registry that
    answers transiently on every attempt is asked exactly `max_attempts` times, then the reading
    is the same inconclusive one a single failed read always gave - "we could not check" is
    still not "we checked and it is false" (section 29.6 E5) - and no exception reaches the
    facts stage."""
    calls, fetch = _answers(then=None if transient is None else _Response(transient))
    sleeps: list[float] = []

    reading = observe("net", "Aspose.Widget", fetch=fetch, sleep=sleeps.append)

    assert len(calls) == _POLICY.max_attempts, calls
    assert len(sleeps) == _POLICY.max_attempts - 1
    assert reading.published is None and reading.ambiguous and not reading.conclusive
    assert reading.summary == "package registry: nuget could not be read"
    assert reading.method == "nuget-flatcontainer-api", "the adapter's own reading, unchanged"


@pytest.mark.parametrize(
    ("status", "conclusive"),
    [(404, True), (403, False), (401, False)],
    ids=["404-not-published", "403-ambiguous", "401-ambiguous"],
)
def test_a_registry_that_answered_is_never_asked_again(status: int, conclusive: bool) -> None:
    """Negative control for the classification: a 404 is the registry's answer (not published)
    and a 403 or 401 is the adapter's own ambiguous reading; neither is transient, so neither
    is replayed - the retry never turns "distribution not found" into three requests."""
    calls, fetch = _answers(then=_Response(status))
    sleeps: list[float] = []

    reading = observe("net", "Aspose.Widget", fetch=fetch, sleep=sleeps.append)

    assert len(calls) == 1 and sleeps == []
    assert reading.conclusive is conclusive
    if conclusive:
        assert reading.published is False


@pytest.mark.parametrize(
    ("ecosystem", "name"),
    [
        ("net", "Aspose.Widget"),
        ("java", "org.aspose:aspose-widget-foss"),
        ("typescript", "@asposefoss/widget"),
        ("go", "github.com/aspose-widget-foss/Aspose.Widget-FOSS-for-Go"),
        ("rust", "aspose-widget-foss"),
    ],
)
def test_every_registry_the_facade_serves_is_asked_again_after_one_transient_answer(
    ecosystem: str, name: str
) -> None:
    """The retry lives in the façade, not in one adapter: NuGet was where lane F measured it,
    but Maven, npm, the Go proxy and crates.io reach the network through the same single call,
    and item 57 names every one of them."""
    calls, fetch = _answers(None, then=_Response(200, {"versions": ["1.0.0"]}))
    sleeps: list[float] = []

    reading = observe(ecosystem, name, fetch=fetch, sleep=sleeps.append)

    assert reading.registry == REGISTRY_TYPES[ecosystem]
    assert reading.conclusive and reading.published is True, (ecosystem, reading)
    assert len(sleeps) == 1 and len(calls) >= 2


def test_the_reading_summarises_itself_in_the_vocabulary_a_check_expects() -> None:
    """BC-02 asks an install command to show a manifest reading and a package-registry reading.

    Measured 2026-09-06: the .NET install fact said "published on nuget" and BC-02 failed
    Aspose.3D for .NET outright at EXTRACTING. The phrase belongs to the shared reading, so no
    plugin has to remember it.
    """
    found = RegistryObservation("nuget", "Aspose.3D.FOSS", True, False, "https://x", "api", "s")
    missing = RegistryObservation("nuget", "Aspose.Slides.FOSS", False, False, None, "api", "s")
    unread = RegistryObservation("nuget", "x", None, False, None, None, "s")
    ambiguous = RegistryObservation("nuget", "x", True, True, None, "api", "s")

    assert found.summary == "package registry: found on nuget"
    assert missing.summary == "package registry: distribution not found on nuget"
    assert unread.summary == "package registry: nuget could not be read"
    assert ambiguous.summary == "package registry: nuget answered ambiguously"
    # The registry's current version is never in the evidence: it is the registry's state.
    assert all("version" not in o.summary for o in (found, missing, unread, ambiguous))
