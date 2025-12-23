import json
import pytest
from notifier.storage import SentGamesStorage


def test_sent_games_storage_states(tmp_path):
    storage_file = tmp_path / "sent_games.json"
    storage = SentGamesStorage(str(storage_file))
    url = "http://game.url/1"
    assert storage.get_game_state(url) is None
    storage.mark_game_pending(url)
    assert storage.get_game_state(url) == "pending"
    storage.mark_game_failed(url)
    assert storage.get_game_state(url) == "failed"
    storage.mark_game_sent(url)
    assert storage.get_game_state(url) == "sent"


def test_storage_missing_file(tmp_path):
    storage_file = tmp_path / "missing.json"
    storage = SentGamesStorage(str(storage_file))
    assert storage.get_game_state("http://any.url") is None


def test_storage_corrupted_json(tmp_path):
    storage_file = tmp_path / "corrupted.json"
    storage_file.write_text("{invalid json")
    
    with pytest.raises(json.JSONDecodeError):
        SentGamesStorage(str(storage_file))


def test_storage_legacy_list_format(tmp_path):
    storage_file = tmp_path / "legacy.json"
    legacy_data = ["http://game.url/1", "http://game.url/2"]
    storage_file.write_text(json.dumps(legacy_data))
    
    storage = SentGamesStorage(str(storage_file))
    assert storage.get_game_state("http://game.url/1") == "sent"
    assert storage.get_game_state("http://game.url/2") == "sent"
    assert storage.get_game_state("http://game.url/3") is None


def test_save_states(tmp_path):
    storage_file = tmp_path / "save.json"
    storage = SentGamesStorage(str(storage_file))
    storage.mark_game_sent("http://game.url/1")
    
    # Reload to verify persistence
    storage2 = SentGamesStorage(str(storage_file))
    assert storage2.get_game_state("http://game.url/1") == "sent"
