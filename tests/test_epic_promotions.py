from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest
from conftest import make_raw_game

from notifier.api.epic import EpicFreeGames
from notifier.api.models import PromotionalOffer

if TYPE_CHECKING:
    from collections.abc import Callable

NOW = datetime.now(tz=timezone.utc)
CMS = {"cardpocalypse": {"products": "/productv2/cardpocalypse"}}


def offer(start_days: int, end_days: int, percentage: int | None = 0) -> dict:
    return {
        "startDate": (NOW + timedelta(days=start_days)).isoformat(),
        "endDate": (NOW + timedelta(days=end_days)).isoformat(),
        "discountSetting": {
            "discountType": "PERCENTAGE",
            "discountPercentage": percentage,
        },
    }


def promotions(*groups: list[dict]) -> dict:
    return {
        "promotionalOffers": [{"promotionalOffers": list(g)} for g in groups],
        "upcomingPromotionalOffers": [],
    }


def game_with(*groups: list[dict]) -> dict:
    return make_raw_game(productSlug="cardpocalypse", promotions=promotions(*groups))


def test_single_offer_is_used(epic_client: Callable[..., EpicFreeGames]) -> None:
    live = offer(-1, 6)
    epic = epic_client(elements=[game_with([live])], cms=CMS)

    games = epic.format_free_games()

    assert games[0].end_date.isoformat() == live["endDate"]


def test_expired_offer_is_not_chosen_over_the_live_one(
    epic_client: Callable[..., EpicFreeGames],
) -> None:
    # Epic lists offers in its own order; an expired one must not set end_date.
    expired = offer(-30, -20)
    live = offer(-1, 6)
    epic = epic_client(elements=[game_with([expired, live])], cms=CMS)

    games = epic.format_free_games()

    assert games[0].end_date.isoformat() == live["endDate"]


def test_future_offer_is_not_chosen_over_the_live_one(
    epic_client: Callable[..., EpicFreeGames],
) -> None:
    upcoming = offer(10, 20)
    live = offer(-1, 6)
    epic = epic_client(elements=[game_with([upcoming, live])], cms=CMS)

    games = epic.format_free_games()

    assert games[0].end_date.isoformat() == live["endDate"]


def test_giveaway_is_preferred_over_a_concurrent_discount(
    epic_client: Callable[..., EpicFreeGames],
) -> None:
    # A half-price sale can overlap the giveaway; the free window governs.
    sale = offer(-5, 20, percentage=50)
    giveaway = offer(-1, 6, percentage=0)
    epic = epic_client(elements=[game_with([sale, giveaway])], cms=CMS)

    games = epic.format_free_games()

    assert games[0].end_date.isoformat() == giveaway["endDate"]


def test_offers_are_flattened_across_groups(
    epic_client: Callable[..., EpicFreeGames],
) -> None:
    expired = offer(-30, -20)
    live = offer(-1, 6)
    epic = epic_client(elements=[game_with([expired], [live])], cms=CMS)

    games = epic.format_free_games()

    assert games[0].end_date.isoformat() == live["endDate"]


def test_empty_offer_group_does_not_crash(
    epic_client: Callable[..., EpicFreeGames],
    captured_logs: list[dict],
) -> None:
    # Normalisation turns a null inner list into [], so indexing it would raise.
    epic = epic_client(elements=[game_with([])], cms=CMS)

    games = epic.format_free_games()

    assert games == []
    warnings = [r["message"] for r in captured_logs if r["level"] == "WARNING"]
    assert any("no promotional offer" in message for message in warnings)


def test_null_offer_group_does_not_crash(
    epic_client: Callable[..., EpicFreeGames],
) -> None:
    element = make_raw_game(productSlug="cardpocalypse")
    element["promotions"]["promotionalOffers"] = [{"promotionalOffers": None}]
    epic = epic_client(elements=[element], cms=CMS)

    assert epic.format_free_games() == []


@pytest.mark.parametrize(
    ("percentage", "expected_giveaway"),
    [(0, True), (50, False), (100, False), (None, False)],
)
def test_is_giveaway(percentage: int | None, expected_giveaway: bool) -> None:
    parsed = PromotionalOffer(**offer(-1, 6, percentage=percentage))

    assert EpicFreeGames.is_giveaway(parsed) is expected_giveaway
