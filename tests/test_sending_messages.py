import pytest
import pytest_mock

from notifier.main import send_with_retry
from notifier.bot.signal import SignalBot


def test_retry_mechanism(mocker: pytest_mock.MockerFixture) -> None:
    mocker.patch("time.sleep", return_value=None)
    bot = SignalBot("http://fake-url", "+123456789")
    group_id = "test-group"
    message = "Test message"
    mock_send = mocker.patch(
        "notifier.bot.signal.SignalBot.send_group_message", new=mocker.MagicMock()
    )
    mock_send.side_effect = [None, None, None, {"status": "success"}]
    result = send_with_retry(bot, group_id, message)
    assert 4 == mock_send.call_count
    assert {"status": "success"} == result


def test_retry_exceeds_max_attempts(mocker: pytest_mock.MockerFixture) -> None:
    mocker.patch("time.sleep", return_value=None)
    bot = SignalBot("http://fake-url", "+123456789")
    group_id = "test-group"
    message = "Test message"
    mock_send = mocker.patch(
        "notifier.bot.signal.SignalBot.send_group_message", new=mocker.MagicMock()
    )
    mock_send.side_effect = [None] * 5
    with pytest.raises(Exception):
        send_with_retry(bot, group_id, message)
    assert 5 == mock_send.call_count
