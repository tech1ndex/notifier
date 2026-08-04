from types import SimpleNamespace

import pytest
import pytest_mock
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import HTTPError, Timeout

import notifier.main as main_module
from notifier.bot.signal import SignalBot
from notifier.main import send_message
from notifier.storage import SentGamesStorage


def test_retry_mechanism(mocker: pytest_mock.MockerFixture) -> None:
    mocker.patch("time.sleep", return_value=None)
    bot = SignalBot("http://fake-url", "+123456789")
    group_id = "test-group"
    message = "Test message"
    mock_send_call_count = 4
    mock_send = mocker.patch(
        "notifier.bot.signal.SignalBot.send_group_message",
        new=mocker.MagicMock(),
    )
    # Raise HTTPError for the first 3 calls, then succeed
    mock_send.side_effect = [
        HTTPError("Fail"),
        HTTPError("Fail"),
        HTTPError("Fail"),
        {"status": "success"},
    ]

    result = send_message(bot, group_id, message)

    assert mock_send.call_count == mock_send_call_count
    assert result == {"status": "success"}


def test_retry_on_connection_error(mocker: pytest_mock.MockerFixture) -> None:
    mocker.patch("time.sleep", return_value=None)
    bot = SignalBot("http://fake-url", "+123456789")
    group_id = "test-group"
    message = "Test message"
    mock_send_call_count = 3
    mock_send = mocker.patch(
        "notifier.bot.signal.SignalBot.send_group_message",
        new=mocker.MagicMock(),
    )
    # Raise ConnectionError, then Timeout, then succeed
    mock_send.side_effect = [
        RequestsConnectionError("Fail"),
        Timeout("Fail"),
        {"status": "success"},
    ]

    result = send_message(bot, group_id, message)

    assert mock_send.call_count == mock_send_call_count
    assert result == {"status": "success"}


def test_retry_exceeds_max_attempts(mocker: pytest_mock.MockerFixture) -> None:
    mocker.patch("time.sleep", return_value=None)
    bot = SignalBot("http://fake-url", "+123456789")
    group_id = "test-group"
    message = "Test message"
    mock_send_call_count = 5
    mock_send = mocker.patch(
        "notifier.bot.signal.SignalBot.send_group_message",
        new=mocker.MagicMock(),
    )
    # Always raise HTTPError
    mock_send.side_effect = [HTTPError("Fail")] * 5

    with pytest.raises(HTTPError):
        send_message(bot, group_id, message)

    assert mock_send.call_count == mock_send_call_count


def test_pending_game_not_resent_after_restart(
    tmp_path,
    mocker: pytest_mock.MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage_file = tmp_path / "sent_games.json"
    pending_url = "http://game.url/pending"
    new_url = "http://game.url/new"

    SentGamesStorage(str(storage_file)).mark_game_pending(pending_url)

    mocker.patch.object(
        main_module,
        "get_storage_path",
        return_value=str(storage_file),
    )
    monkeypatch.setenv("ONE_TIME_RUN", "true")

    mocker.patch.object(main_module, "SignalBot", autospec=True)
    fake_epic = mocker.patch.object(main_module, "EpicFreeGames", autospec=True)
    fake_epic.return_value.format_free_games.return_value = [
        SimpleNamespace(
            game_url=pending_url,
            game_title="Pending Game",
            game_price="$0",
        ),
        SimpleNamespace(game_url=new_url, game_title="New Game", game_price="$0"),
    ]

    mock_send = mocker.patch.object(main_module, "send_message")

    with pytest.raises(SystemExit):
        main_module.main()

    assert mock_send.call_count == 1
    sent_message = mock_send.call_args.args[2]
    assert new_url in sent_message
    assert pending_url not in sent_message
    reloaded = SentGamesStorage(str(storage_file))
    assert reloaded.get_game_state(new_url) == "sent"
    assert reloaded.get_game_state(pending_url) == "pending"
