import pytest
import pytest_mock
from requests.exceptions import HTTPError, Timeout

from notifier.bot.signal import SignalBot


def test_send_group_message_success(mocker: pytest_mock.MockerFixture) -> None:
    base_url = "http://signal-api"
    phone = "+123456789"
    group_id = "group1"
    message = "hello"
    
    bot = SignalBot(base_url, phone)
    
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 201
    mock_post.return_value.json.return_value = {"timestamp": 12345}
    
    result = bot.send_group_message(group_id, message)
    
    assert result == {"timestamp": 12345}
    mock_post.assert_called_once()
    import json
    assert json.loads(mock_post.call_args.kwargs["data"]) == {
        "message": message,
        "number": phone,
        "recipients": [group_id],
    }


def test_send_group_message_http_error(mocker: pytest_mock.MockerFixture) -> None:
    base_url = "http://signal-api"
    phone = "+123456789"
    bot = SignalBot(base_url, phone)
    
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.raise_for_status.side_effect = HTTPError("Bad Request")
    
    with pytest.raises(HTTPError):
        bot.send_group_message("group1", "hello")


def test_send_group_message_timeout(mocker: pytest_mock.MockerFixture) -> None:
    base_url = "http://signal-api"
    phone = "+123456789"
    bot = SignalBot(base_url, phone)
    
    mock_post = mocker.patch("requests.post")
    mock_post.side_effect = Timeout("Timeout")
    
    with pytest.raises(Timeout):
        bot.send_group_message("group1", "hello")
