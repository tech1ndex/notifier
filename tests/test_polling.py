from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx
import pytest
from conftest import free_games_payload, make_raw_game
from requests.exceptions import RequestException

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
    elements = [make_raw_game(id="failed-id", title="A Failed", productSlug="failed-game")]
    if include_healthy_game:
        elements.append(
            make_raw_game(id="healthy-id", title="B Healthy", productSlug="healthy-game"),
        )

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
    assert storage.get_game_state("cardpocalypse-ns:failed-id") is None
    if include_healthy_game:
        assert storage.get_game_state("cardpocalypse-ns:healthy-id") == "sent"

    healthy = True
    isolated_main.reset_mock()
    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    assert exc_info.value.code == 0
    isolated_main.assert_called_once()
    assert failed_url in isolated_main.call_args.args[2]
    assert SentGamesStorage(storage.file_path).get_game_state("cardpocalypse-ns:failed-id") == "sent"


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


@pytest.mark.parametrize("state", ["sent", "pending"])
@pytest.mark.parametrize("url_change", ["route", "slug", "locale"])
def test_offer_not_resent_after_restart_with_changed_url(
    *,
    state: str,
    url_change: str,
    isolated_main: MagicMock,
    tmp_path: Path,
    epic_client: Callable[..., EpicFreeGames],
    mocker: pytest_mock.MockerFixture,
) -> None:
    first_epic = epic_client(elements=[make_raw_game()])
    slug = "renamed-game" if url_change == "slug" else "cardpocalypse"
    restarted_epic = epic_client(
        elements=[make_raw_game(productSlug=slug)],
        cms={slug: {"bundles": f"/bundles/{slug}"}} if url_change == "route" else {},
        locale="fr-FR" if url_change == "locale" else "en-US",
    )
    mocker.patch.object(
        main_module,
        "EpicFreeGames",
        side_effect=[first_epic, restarted_epic],
    )
    if state == "pending":
        # Stop during delivery, after pending has been persisted.
        isolated_main.side_effect = KeyboardInterrupt
        main_module.main()
    else:
        with pytest.raises(SystemExit) as exc_info:
            main_module.main()
        assert exc_info.value.code == 0

    storage_path = str(tmp_path / "sent_games.json")
    game_key = "cardpocalypse-ns:abc123"
    assert SentGamesStorage(storage_path).get_game_state(game_key) == state
    assert isolated_main.call_args.args[2].endswith("/p/cardpocalypse")
    assert restarted_epic.format_free_games()[0].game_url != first_epic.format_free_games()[0].game_url

    isolated_main.reset_mock(side_effect=True)
    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    assert exc_info.value.code == 0
    isolated_main.assert_not_called()
    assert SentGamesStorage(storage_path).get_game_state(game_key) == state


@pytest.mark.parametrize("old_route", ["p", "bundles"])
@pytest.mark.parametrize(
    ("file_format", "state"),
    [("dict", "sent"), ("dict", "pending"), ("dict", "failed"), ("list", "sent")],
)
def test_legacy_url_state_migrates_before_sending(
    *,
    old_route: str,
    file_format: str,
    state: str,
    isolated_main: MagicMock,
    tmp_path: Path,
    epic_client: Callable[..., EpicFreeGames],
    mocker: pytest_mock.MockerFixture,
) -> None:
    storage_file = tmp_path / "sent_games.json"
    old_url = f"https://store.epicgames.com/en-US/{old_route}/cardpocalypse"
    unrelated_url = "https://store.epicgames.com/en-US/p/another-game"
    old_data = [old_url, unrelated_url] if file_format == "list" else {old_url: state, unrelated_url: "sent"}
    storage_file.write_text(json.dumps(old_data))

    # Resolve the opposite route on the first run after upgrading.
    cms = {"cardpocalypse": {"bundles": "/bundles/cardpocalypse"}} if old_route == "p" else {}
    epic = epic_client(elements=[make_raw_game()], cms=cms)
    mocker.patch.object(main_module, "EpicFreeGames", return_value=epic)

    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    assert exc_info.value.code == 0
    assert isolated_main.call_count == int(state == "failed")
    stored = json.loads(storage_file.read_text())
    expected_state = "sent" if state == "failed" else state
    assert stored == {"cardpocalypse-ns:abc123": expected_state, unrelated_url: "sent"}

    # Reload the migrated file with a new client and another changed URL.
    restarted_epic = epic_client(elements=[make_raw_game(productSlug="renamed-game")])
    mocker.patch.object(main_module, "EpicFreeGames", return_value=restarted_epic)
    isolated_main.reset_mock()
    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    assert exc_info.value.code == 0
    isolated_main.assert_not_called()


@pytest.mark.parametrize(
    ("new_id", "new_namespace"),
    [("another-offer", "cardpocalypse-ns"), ("abc123", "another-namespace")],
)
def test_different_offer_using_same_url_is_sent(
    *,
    new_id: str,
    new_namespace: str,
    isolated_main: MagicMock,
    tmp_path: Path,
    epic_client: Callable[..., EpicFreeGames],
    mocker: pytest_mock.MockerFixture,
) -> None:
    storage_file = tmp_path / "sent_games.json"
    old_url = "https://store.epicgames.com/en-US/p/cardpocalypse"
    storage_file.write_text(json.dumps({old_url: "sent"}))
    first_epic = epic_client(elements=[make_raw_game()])
    restarted_epic = epic_client(elements=[make_raw_game(id=new_id, namespace=new_namespace)])
    mocker.patch.object(main_module, "EpicFreeGames", side_effect=[first_epic, restarted_epic])

    with pytest.raises(SystemExit):
        main_module.main()
    isolated_main.assert_not_called()

    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    assert exc_info.value.code == 0
    isolated_main.assert_called_once()
    stored = json.loads(storage_file.read_text())
    assert stored == {"cardpocalypse-ns:abc123": "sent", f"{new_namespace}:{new_id}": "sent"}


def test_failed_send_is_retried_after_restart_with_changed_route(
    isolated_main: MagicMock,
    tmp_path: Path,
    epic_client: Callable[..., EpicFreeGames],
    mocker: pytest_mock.MockerFixture,
) -> None:
    first_epic = epic_client(elements=[make_raw_game()])
    restarted_epic = epic_client(
        elements=[make_raw_game()],
        cms={"cardpocalypse": {"bundles": "/bundles/cardpocalypse"}},
    )
    mocker.patch.object(main_module, "EpicFreeGames", side_effect=[first_epic, restarted_epic])
    isolated_main.side_effect = RequestException("Signal unavailable")

    with pytest.raises(SystemExit):
        main_module.main()
    game_key = "cardpocalypse-ns:abc123"
    storage_path = str(tmp_path / "sent_games.json")
    assert SentGamesStorage(storage_path).get_game_state(game_key) == "failed"

    isolated_main.reset_mock(side_effect=True)
    with pytest.raises(SystemExit) as exc_info:
        main_module.main()

    assert exc_info.value.code == 0
    isolated_main.assert_called_once()
    assert isolated_main.call_args.args[2].endswith("/bundles/cardpocalypse")
    assert SentGamesStorage(storage_path).get_game_state(game_key) == "sent"
