from notifier.main import send_with_timeout
from notifier.storage import SentGamesStorage


class DummyBot:
    def send_group_message(self, group_id: str, message: str):
        return True


def test_sent_games_storage_states(tmp_path):
    storage = SentGamesStorage()
    url = "http://game.url/1"
    assert storage.get_game_state(url) is None
    storage.mark_game_pending(url)
    assert storage.get_game_state(url) == "pending"
    storage.mark_game_failed(url)
    assert storage.get_game_state(url) == "failed"
    storage.mark_game_sent(url)
    assert storage.get_game_state(url) == "sent"


def test_send_with_timeout_success(mocker):
    bot = DummyBot()
    group_id = "gid"
    message = "msg"
    mocker.patch.object(bot, "send_group_message", return_value=True)
    result = send_with_timeout(bot, group_id, message, 2)
    assert result is True


def test_send_with_timeout_timeout(mocker):
    class SlowBot:
        def send_group_message(self, group_id: str, message: str):
            import time

            time.sleep(3)
            return True

    bot = SlowBot()
    group_id = "gid"
    message = "msg"
    result = send_with_timeout(bot, group_id, message, 1)
    assert result is False
