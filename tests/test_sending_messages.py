import pytest
import pytest_mock
from requests.exceptions import HTTPError, ConnectionError, Timeout

from notifier.bot.signal import SignalBot
from notifier.main import send_message


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
        ConnectionError("Fail"),
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
