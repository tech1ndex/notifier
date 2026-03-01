import json
from unittest.mock import Mock

import pytest
import requests

from notifier.bot.signal import SignalBot

EXPECTED_TIMEOUT = 10
EXPECTED_TIMESTAMP = 1234567890


def test_send_group_message_success(mocker):
    bot = SignalBot("http://test-url", "+1234567890")

    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"timestamp": EXPECTED_TIMESTAMP}

    mock_post = mocker.patch("requests.post", return_value=mock_response)

    result = bot.send_group_message("test-group-id", "Test message")

    assert mock_post.call_count == 1
    call_args = mock_post.call_args

    assert call_args[0][0] == "http://test-url/v2/send"
    assert call_args[1]["headers"]["Content-Type"] == "application/json"

    payload = json.loads(call_args[1]["data"])
    assert payload["message"] == "Test message"
    assert payload["number"] == "+1234567890"
    assert payload["recipients"] == ["test-group-id"]

    assert call_args[1]["timeout"] == EXPECTED_TIMEOUT
    assert result == {"timestamp": EXPECTED_TIMESTAMP}


def test_send_group_message_failure(mocker):
    bot = SignalBot("http://test-url", "+1234567890")

    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.raise_for_status.side_effect = requests.HTTPError(
        response=mock_response,
    )

    mock_post = mocker.patch("requests.post", return_value=mock_response)

    with pytest.raises(requests.HTTPError):
        bot.send_group_message("test-group-id", "Test message")

    assert mock_post.call_count == 1


def test_send_group_message_with_timeout_parameter(mocker):
    bot = SignalBot("http://test-url", "+1234567890")

    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {}

    mock_post = mocker.patch("requests.post", return_value=mock_response)

    bot.send_group_message("test-group-id", "Test message")

    call_args = mock_post.call_args
    assert call_args[1]["timeout"] == EXPECTED_TIMEOUT


def test_send_group_message_connection_error(mocker):
    bot = SignalBot("http://test-url", "+1234567890")

    mocker.patch(
        "requests.post",
        side_effect=requests.ConnectionError("Connection failed"),
    )

    with pytest.raises(requests.ConnectionError):
        bot.send_group_message("test-group-id", "Test message")


def test_send_group_message_timeout_error(mocker):
    bot = SignalBot("http://test-url", "+1234567890")

    mocker.patch("requests.post", side_effect=requests.Timeout("Request timed out"))

    with pytest.raises(requests.Timeout):
        bot.send_group_message("test-group-id", "Test message")


def test_send_group_message_base_url_trailing_slash():
    bot1 = SignalBot("http://test-url/", "+1234567890")
    bot2 = SignalBot("http://test-url", "+1234567890")

    assert bot1.base_url == bot2.base_url == "http://test-url"


def test_send_group_message_response_json_parsing(mocker):
    bot = SignalBot("http://test-url", "+1234567890")

    mock_response = Mock()
    mock_response.status_code = 201
    expected_json = {
        "timestamp": EXPECTED_TIMESTAMP,
        "messageId": "abc123",
        "status": "sent",
    }
    mock_response.json.return_value = expected_json

    mocker.patch("requests.post", return_value=mock_response)

    result = bot.send_group_message("test-group-id", "Test message")

    assert result == expected_json
    assert result["timestamp"] == EXPECTED_TIMESTAMP
    assert result["messageId"] == "abc123"
    assert result["status"] == "sent"
