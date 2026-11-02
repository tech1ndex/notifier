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


@pytest.mark.parametrize(
    ("product_state", "bundle_state", "expected"),
    [
        ("failed", "sent", "sent"),
        ("pending", "failed", "pending"),
        ("pending", "sent", "sent"),
    ],
)
def test_migration_preserves_non_retryable_state_across_aliases(
    tmp_path,
    product_state,
    bundle_state,
    expected,
):
    storage_file = tmp_path / "sent_games.json"
    aliases = ("https://store.example/p/game", "https://store.example/bundles/game")
    storage_file.write_text(
        json.dumps(dict(zip(aliases, (product_state, bundle_state), strict=True))),
    )
    storage = SentGamesStorage(str(storage_file))

    assert storage.get_or_migrate_game_state("namespace:offer", aliases) == expected
    assert json.loads(storage_file.read_text()) == {"namespace:offer": expected}
    assert (
        SentGamesStorage(str(storage_file)).get_game_state("namespace:offer")
        == expected
    )


def test_existing_offer_state_takes_precedence_over_legacy_url(tmp_path):
    storage_file = tmp_path / "sent_games.json"
    legacy_url = "https://store.example/p/game"
    storage_file.write_text(
        json.dumps({"namespace:offer": "sent", legacy_url: "failed"}),
    )
    storage = SentGamesStorage(str(storage_file))

    assert storage.get_or_migrate_game_state("namespace:offer", (legacy_url,)) == "sent"
