from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx
import pytest
from conftest import free_games_payload, make_raw_game

from notifier.api.epic import EpicFreeGames, clean_spurious_errors
from notifier.api.errors import EpicApiError, EpicNotFoundError
from notifier.settings import EpicSettings

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest_mock


SPURIOUS_CODE = 1004
REAL_CODE = 1001
NOT_FOUND_CODE = 1009
ATTEMPTS_BEFORE_SUCCESS = 3


def make_error(
    numeric_code: int | None = None,
    error_code: str = "errors.com.epicgames.unknown",
    message: str = "boom",
) -> dict:
    return {
        "message": message,
        "serviceResponse": json.dumps(
            {
                "errorCode": error_code,
                "errorMessage": message,
                "numericErrorCode": numeric_code,
            },
        ),
    }


def test_spurious_errors_are_dropped() -> None:
    payload = {"data": {}, "errors": [make_error(SPURIOUS_CODE)]}

    assert "errors" not in clean_spurious_errors(payload)


def test_real_errors_are_kept() -> None:
    payload = {
        "data": {},
        "errors": [make_error(SPURIOUS_CODE), make_error(REAL_CODE)],
    }

    cleaned = clean_spurious_errors(payload)

    assert len(cleaned["errors"]) == 1
    service_response = json.loads(cleaned["errors"][0]["serviceResponse"])
    assert service_response["numericErrorCode"] == REAL_CODE


@pytest.mark.parametrize(
    "errors",
    [
        [{"message": "boom"}],
        [{"serviceResponse": "not json at all"}],
    ],
)
def test_unreadable_service_response_is_tolerated(errors: list[dict]) -> None:
    payload = {"data": {}, "errors": errors}

    assert len(clean_spurious_errors(payload)["errors"]) == 1


def test_payload_without_errors_is_untouched() -> None:
    payload = {"data": {"x": 1}}

    assert payload == clean_spurious_errors(payload)


@pytest.mark.parametrize("numeric_code", [SPURIOUS_CODE, REAL_CODE])
def test_games_still_parse_alongside_errors(
    numeric_code: int,
    epic_client: Callable[..., EpicFreeGames],
) -> None:
    payload = free_games_payload([make_raw_game()])
    payload["errors"] = [make_error(numeric_code)]

    games = epic_client(payload=payload).get_free_games()

    assert [g.title for g in games] == ["Cardpocalypse"]


def test_not_found_error_raises(epic_client: Callable[..., EpicFreeGames]) -> None:
    payload = free_games_payload([])
    payload["errors"] = [
        make_error(
            NOT_FOUND_CODE,
            error_code="errors.com.epicgames.catalog.offer_not_found",
            message="offer not found",
        ),
    ]

    with pytest.raises(EpicNotFoundError):
        epic_client(payload=payload).get_free_games()


def test_error_without_service_response_raises(
    epic_client: Callable[..., EpicFreeGames],
) -> None:
    payload = free_games_payload([])
    payload["errors"] = [{"message": "boom", "serviceResponse": ""}]

    with pytest.raises(EpicApiError):
        epic_client(payload=payload).get_free_games()


def test_bare_not_found_string_raises(
    epic_client: Callable[..., EpicFreeGames],
) -> None:
    payload = free_games_payload([])
    payload["errors"] = [{"serviceResponse": json.dumps("not found")}]

    with pytest.raises(EpicNotFoundError):
        epic_client(payload=payload).get_free_games()


def test_unexpected_payload_shape_raises(
    epic_client: Callable[..., EpicFreeGames],
) -> None:
    with pytest.raises(EpicApiError, match="payload shape"):
        epic_client(payload={"data": {"Catalog": None}}).get_free_games()


def test_games_without_promotions_are_skipped(
    epic_client: Callable[..., EpicFreeGames],
) -> None:
    games = epic_client(
        elements=[make_raw_game(promotions=None), make_raw_game(title="Kept")],
    ).get_free_games()

    assert [g.title for g in games] == ["Kept"]


def test_server_error_is_retried_then_succeeds(
    mocker: pytest_mock.MockerFixture,
) -> None:
    mock_sleep = mocker.patch("tenacity.nap.time.sleep", return_value=None)
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(request.url.path)
        if len(attempts) < ATTEMPTS_BEFORE_SUCCESS:
            return httpx.Response(503, json={})
        return httpx.Response(200, json=free_games_payload([]))

    epic = EpicFreeGames(EpicSettings(), transport=httpx.MockTransport(handler))

    assert epic.get_free_games() == []
    assert len(attempts) == ATTEMPTS_BEFORE_SUCCESS
    assert mock_sleep.call_count == ATTEMPTS_BEFORE_SUCCESS - 1


def test_persistent_server_error_reraises(mocker: pytest_mock.MockerFixture) -> None:
    mocker.patch("tenacity.nap.time.sleep", return_value=None)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={})

    epic = EpicFreeGames(EpicSettings(), transport=httpx.MockTransport(handler))

    with pytest.raises(httpx.HTTPStatusError):
        epic.get_free_games()


@pytest.mark.parametrize("retry_attempts", [1, 2, 7])
def test_retry_attempts_setting_is_honoured(
    retry_attempts: int,
    mocker: pytest_mock.MockerFixture,
) -> None:
    mocker.patch("tenacity.nap.time.sleep", return_value=None)
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(request.url.path)
        return httpx.Response(503, json={})

    epic = EpicFreeGames(
        EpicSettings(retry_attempts=retry_attempts),
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(httpx.HTTPStatusError):
        epic.get_free_games()

    assert len(attempts) == retry_attempts


def test_free_games_url_setting_is_used() -> None:
    requested = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, json=free_games_payload([]))

    epic = EpicFreeGames(
        EpicSettings(free_games_url="https://mirror.example.com/promos"),
        transport=httpx.MockTransport(handler),
    )
    epic.get_free_games()

    assert requested[0].startswith("https://mirror.example.com/promos?")
