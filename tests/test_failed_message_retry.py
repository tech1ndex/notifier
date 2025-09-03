from notifier.storage import SentGamesStorage

def test_failed_message_is_retried() -> None:
    storage = SentGamesStorage()
    url = "http://game.url/failed"
    storage.mark_game_failed(url)
    state = storage.get_game_state(url)
    assert state == "failed"
    storage.mark_game_pending(url)
    assert storage.get_game_state(url) == "pending"
    state = storage.get_game_state(url)
    assert state == "pending"

def test_sent_and_pending_are_not_retried() -> None:
    storage = SentGamesStorage()
    sent_url = "http://game.url/sent"
    pending_url = "http://game.url/pending"
    storage.mark_game_sent(sent_url)
    storage.mark_game_pending(pending_url)
    assert storage.get_game_state(sent_url) == "sent"
    assert storage.get_game_state(pending_url) == "pending"
    assert storage.get_game_state(sent_url) == "sent"
    assert storage.get_game_state(pending_url) == "pending"

