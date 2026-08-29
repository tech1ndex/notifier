from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from notifier.api.epic import EpicFreeGames

if TYPE_CHECKING:
    from collections.abc import Callable



def test_null_custom_attribute_value_is_accepted(
    epic_client: Callable[..., EpicFreeGames],
    raw_game: dict,
) -> None:
    games = epic_client(elements=[raw_game]).get_free_games()

    assert [a.value for a in games[0].custom_attributes] == ["", None]


def test_missing_custom_attributes_key_defaults_to_empty(
    epic_client: Callable[..., EpicFreeGames],
    raw_game: dict,
) -> None:
    del raw_game["customAttributes"]

    games = epic_client(elements=[raw_game]).get_free_games()

    assert games[0].custom_attributes == []


def test_null_custom_attributes_list_defaults_to_empty(
    epic_client: Callable[..., EpicFreeGames],
    raw_game: dict,
) -> None:
    raw_game["customAttributes"] = None

    games = epic_client(elements=[raw_game]).get_free_games()

    assert games[0].custom_attributes == []


def test_custom_attribute_key_is_still_required(
    epic_client: Callable[..., EpicFreeGames],
    raw_game: dict,
) -> None:
    raw_game["customAttributes"] = [{"value": "something"}]

    with pytest.raises(ValidationError):
        epic_client(elements=[raw_game]).get_free_games()


def test_game_with_null_attribute_value_is_still_formatted(
    epic_client: Callable[..., EpicFreeGames],
    raw_game: dict,
) -> None:
    epic = epic_client(
        elements=[raw_game],
        cms={"cardpocalypse": {"products": "/productv2/cardpocalypse"}},
    )

    games = epic.format_free_games()

    assert len(games) == 1
    assert games[0].game_title == "Cardpocalypse"
    assert games[0].game_price == "CA$29.99"
    assert f"{epic.settings.base_url}/p/cardpocalypse" == games[0].game_url
