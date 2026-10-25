from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
from conftest import free_games_payload, make_raw_game

import notifier.main as main_module
from notifier.api.epic import EpicFreeGames
from notifier.settings import EpicSettings, SignalBotSettings
from notifier.storage import SentGamesStorage

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from unittest.mock import MagicMock

    import pytest_mock


@pytest.fixture
def isolated_main(tmp_path: Path, mocker: pytest_mock.MockerFixture) -> MagicMock:
    mocker.patch.object(
        main_module,
        "get_storage_path",
        return_value=str(tmp_path / "sent_games.json"),
    )
    mocker.patch.object(main_module, "SignalBot", autospec=True)
    mocker.patch.object(
        main_module,
        "SignalBotSettings",
        return_value=SignalBotSettings(one_time_run=True),
    )
    return mocker.patch.object(main_module, "send_message")


def test_malformed_feed_exits_unsuccessfully(
    isolated_main: MagicMock,
    mocker: pytest_mock.MockerFixture,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>temporarily unavailable</html>")

    epic = EpicFreeGames(EpicSettings(), transport=httpx.MockTransport(handler))
    mocker.patch.object(main_module, "EpicFreeGames", return_value=epic)

    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    assert exc_info.value.code == 1
    isolated_main.assert_not_called()


def test_malformed_feed_recovers_next_poll(
    isolated_main: MagicMock,
    mocker: pytest_mock.MockerFixture,
) -> None:
    expected_polls = 2
    feed_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal feed_requests
        if request.url.path.startswith("/freeGamesPromotions"):
            feed_requests += 1
            if feed_requests == 1:
                return httpx.Response(200, text="<html>temporarily unavailable</html>")
            return httpx.Response(200, json=free_games_payload([make_raw_game()]))
        return httpx.Response(404)

    epic = EpicFreeGames(EpicSettings(), transport=httpx.MockTransport(handler))
    mocker.patch.object(main_module, "EpicFreeGames", return_value=epic)
    mocker.patch.object(
        main_module,
        "SignalBotSettings",
        return_value=SignalBotSettings(one_time_run=False),
    )
    mocker.patch.object(main_module.time, "sleep", side_effect=[None, KeyboardInterrupt])

    main_module.main()

    assert feed_requests == expected_polls
    isolated_main.assert_called_once()
    assert f"{epic.settings.base_url}/p/cardpocalypse" in isolated_main.call_args.args[2]


@pytest.mark.parametrize("failure", ["http", "transport", "malformed"])
@pytest.mark.parametrize("include_healthy_game", [False, True])
def test_one_time_cms_failure_reports_failure_and_recovers(
    failure: str,
    include_healthy_game: bool,
    isolated_main: MagicMock,
    tmp_path: Path,
    mocker: pytest_mock.MockerFixture,
) -> None:
    healthy = False
    elements = [make_raw_game(title="A Failed", productSlug="failed-game")]
    if include_healthy_game:
        elements.append(make_raw_game(title="B Healthy", productSlug="healthy-game"))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/freeGamesPromotions"):
            return httpx.Response(200, json=free_games_payload(elements))
        if not healthy and request.url.path.endswith("/failed-game"):
            if failure == "transport":
                msg = "CMS unavailable"
                raise httpx.ConnectError(msg, request=request)
            if failure == "malformed":
                return httpx.Response(200, json={})
            return httpx.Response(503)
        return httpx.Response(200, json={"_urlPattern": "/productv2/game"})

    epic = EpicFreeGames(
        EpicSettings(retry_attempts=1),
        transport=httpx.MockTransport(handler),
    )
    mocker.patch.object(main_module, "EpicFreeGames", return_value=epic)

    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    assert exc_info.value.code == 1
    assert isolated_main.call_count == int(include_healthy_game)
    storage = SentGamesStorage(str(tmp_path / "sent_games.json"))
    failed_url = f"{epic.settings.base_url}/p/failed-game"
    assert storage.get_game_state(failed_url) is None
    if include_healthy_game:
        assert storage.get_game_state(f"{epic.settings.base_url}/p/healthy-game") == "sent"

    healthy = True
    isolated_main.reset_mock()
    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    assert exc_info.value.code == 0
    isolated_main.assert_called_once()
    assert failed_url in isolated_main.call_args.args[2]
    assert SentGamesStorage(storage.file_path).get_game_state(failed_url) == "sent"


@pytest.mark.parametrize("include_game", [False, True])
def test_one_time_run_without_cms_errors_succeeds(
    include_game: bool,
    isolated_main: MagicMock,
    epic_client: Callable[..., EpicFreeGames],
    mocker: pytest_mock.MockerFixture,
) -> None:
    # Missing CMS pages are legitimate and still allow the offerType fallback.
    epic = epic_client(elements=[make_raw_game()] if include_game else [])
    mocker.patch.object(main_module, "EpicFreeGames", return_value=epic)

    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    assert exc_info.value.code == 0
    assert isolated_main.call_count == int(include_game)
