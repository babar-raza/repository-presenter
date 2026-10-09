"""The write token must be a repository-scoped installation token (and its PRs must come from the
expected App). Every GitHub call is an injected fake."""

from __future__ import annotations

from typing import Any

from repository_presenter.core.authorization.refusals import Refusal
from repository_presenter.core.github.token_provenance import (
    EXPECTED_APP_ID,
    verify_installation_token,
    verify_pull_request_app,
    verify_repository_token,
)

TARGET = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
INSTALLATION_TOKEN = "ghs_installationtokenfortestsonly"
CONTROL_REPOSITORY = "babar-raza/repository-presenter"
ACTIONS_TOKEN = "ghs_actionsjobtokenfortestsonly"


def _repos(*names: str) -> dict[str, Any]:
    return {
        "total_count": len(names),
        "repositories": [{"full_name": name} for name in names],
    }


def _fetch(status: int, body: Any, seen: list[str] | None = None):  # type: ignore[no-untyped-def]
    def fetch(url: str, token: str | None) -> tuple[int, Any]:
        if seen is not None:
            seen.append(url)
        return status, body

    return fetch


def test_an_installation_token_scoped_to_exactly_the_target_is_accepted() -> None:
    seen: list[str] = []
    decision = verify_installation_token(
        TARGET, INSTALLATION_TOKEN, fetch=_fetch(200, _repos(TARGET), seen)
    )
    assert decision.ok is True
    assert decision.code is None
    assert seen and "/installation/repositories" in seen[0]


def test_the_scope_comparison_ignores_case() -> None:
    decision = verify_installation_token(
        TARGET, INSTALLATION_TOKEN, fetch=_fetch(200, _repos(TARGET.lower()))
    )
    assert decision.ok is True


def test_a_personal_access_token_is_refused_without_any_request() -> None:
    for pat in ("ghp_hand_set_pat", "github_pat_11AAAA", "gho_oauth", "ghu_user", "plain-secret"):
        seen: list[str] = []
        decision = verify_installation_token(TARGET, pat, fetch=_fetch(200, _repos(TARGET), seen))
        assert decision.ok is False
        assert decision.code is Refusal.TOKEN_NOT_INSTALLATION
        assert seen == []  # refused on the prefix alone; the token was never sent anywhere


def test_a_token_github_refuses_on_the_installation_endpoint_is_not_an_installation_token() -> None:
    for status in (401, 403):
        decision = verify_installation_token(
            TARGET, INSTALLATION_TOKEN, fetch=_fetch(status, {"message": "nope"})
        )
        assert decision.ok is False
        assert decision.code is Refusal.TOKEN_NOT_INSTALLATION


def test_a_token_that_reaches_more_than_the_target_is_refused() -> None:
    decision = verify_installation_token(
        TARGET, INSTALLATION_TOKEN, fetch=_fetch(200, _repos(TARGET, "aspose-3d-foss/other"))
    )
    assert decision.ok is False
    assert decision.code is Refusal.TOKEN_WRONG_SCOPE


def test_a_token_scoped_to_a_different_repository_is_refused() -> None:
    decision = verify_installation_token(
        TARGET, INSTALLATION_TOKEN, fetch=_fetch(200, _repos("aspose-3d-foss/other"))
    )
    assert decision.ok is False
    assert decision.code is Refusal.TOKEN_WRONG_SCOPE


def test_a_token_that_reaches_nothing_is_refused() -> None:
    decision = verify_installation_token(TARGET, INSTALLATION_TOKEN, fetch=_fetch(200, _repos()))
    assert decision.code is Refusal.TOKEN_WRONG_SCOPE


def test_an_unverifiable_answer_refuses_rather_than_assuming_ok() -> None:
    for fetch in (
        _fetch(-1, "ConnectError"),
        _fetch(500, None),
        _fetch(200, ["not", "a", "dict"]),
        _fetch(200, {"total_count": 5, "repositories": [{"full_name": TARGET}]}),  # truncated
        _fetch(200, {"total_count": 1}),
    ):
        decision = verify_installation_token(TARGET, INSTALLATION_TOKEN, fetch=fetch)
        assert decision.ok is False
        assert decision.code is Refusal.TOKEN_UNVERIFIABLE


def test_the_expected_app_is_the_repository_presenter_app() -> None:
    assert EXPECTED_APP_ID == 5092474


def test_a_pull_request_performed_by_the_expected_app_is_accepted() -> None:
    body = {"performed_via_github_app": {"id": EXPECTED_APP_ID, "slug": "repository-presenter"}}
    decision = verify_pull_request_app(
        "o", "n", 4, token=INSTALLATION_TOKEN, fetch=_fetch(200, body)
    )
    assert decision.ok is True


def test_a_pull_request_from_another_app_or_from_no_app_is_refused() -> None:
    for body in (
        {"performed_via_github_app": {"id": 15368}},
        {"performed_via_github_app": None},
        {},
    ):
        decision = verify_pull_request_app(
            "o", "n", 4, token=INSTALLATION_TOKEN, fetch=_fetch(200, body)
        )
        assert decision.ok is False
        assert decision.code is Refusal.TOKEN_APP_MISMATCH


def test_an_unreadable_pull_request_is_unverifiable() -> None:
    decision = verify_pull_request_app(
        "o", "n", 4, token=INSTALLATION_TOKEN, fetch=_fetch(404, {"message": "Not Found"})
    )
    assert decision.ok is False
    assert decision.code is Refusal.TOKEN_UNVERIFIABLE


# -- verify_repository_token (G7-W14: the control-repository write's own provenance check,
# never an installation-token assumption that does not hold for an ambient Actions job token) ----


def test_a_token_that_reads_exactly_the_control_repository_is_accepted() -> None:
    seen: list[str] = []
    decision = verify_repository_token(
        CONTROL_REPOSITORY,
        ACTIONS_TOKEN,
        fetch=_fetch(200, {"full_name": CONTROL_REPOSITORY}, seen),
    )
    assert decision.ok is True
    assert seen and seen[0].endswith(f"/repos/{CONTROL_REPOSITORY}")


def test_the_full_name_comparison_ignores_case() -> None:
    decision = verify_repository_token(
        CONTROL_REPOSITORY,
        ACTIONS_TOKEN,
        fetch=_fetch(200, {"full_name": CONTROL_REPOSITORY.upper()}),
    )
    assert decision.ok is True


def test_an_empty_token_is_refused_without_any_request() -> None:
    seen: list[str] = []
    decision = verify_repository_token(CONTROL_REPOSITORY, "", fetch=_fetch(200, {}, seen))
    assert decision.ok is False
    assert decision.code is Refusal.TOKEN_UNVERIFIABLE
    assert seen == []


def test_a_token_that_resolves_to_a_different_repository_is_refused() -> None:
    decision = verify_repository_token(
        CONTROL_REPOSITORY, ACTIONS_TOKEN, fetch=_fetch(200, {"full_name": "someone-else/other"})
    )
    assert decision.ok is False
    assert decision.code is Refusal.TOKEN_WRONG_SCOPE


def test_a_refused_or_unreachable_lookup_never_assumes_ok() -> None:
    for fetch in (
        _fetch(-1, "ConnectError"),
        _fetch(401, {"message": "bad credentials"}),
        _fetch(403, {"message": "forbidden"}),
        _fetch(500, None),
        _fetch(200, ["not", "a", "dict"]),
    ):
        decision = verify_repository_token(CONTROL_REPOSITORY, ACTIONS_TOKEN, fetch=fetch)
        assert decision.ok is False
        assert decision.code is Refusal.TOKEN_UNVERIFIABLE
