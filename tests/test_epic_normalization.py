import copy

import pytest
from pydantic import ValidationError

from notifier.external.epic import EpicFreeGames
from notifier.settings import EpicSettings

RAW_GAME = {
    "title": "Cardpocalypse",
    "id": "abc123",
    "namespace": "cardpocalypse-ns",
    "description": "A card game.",
    "effectiveDate": "2026-08-20T15:00:00.000Z",
    "offerType": "BASE_GAME",
    "expiryDate": None,
    "viewableDate": "2026-08-20T15:00:00.000Z",
    "status": "ACTIVE",
    "isCodeRedemptionOnly": True,
    "keyImages": [{"type": "OfferImageWide", "url": "https://example.com/img.jpg"}],
    "seller": {"id": "s1", "name": "Gambrinous"},
    "productSlug": "cardpocalypse/home",
    "urlSlug": "cardpocalypse",
    "url": None,
    "items": [{"id": "i1", "namespace": "cardpocalypse-ns"}],
    "customAttributes": [
        {"key": "com.epicgames.app.blacklist", "value": ""},
        # Epic began returning null values here, which used to crash validation.
        {"key": "publisherName", "value": None},
    ],
    "categories": [{"path": "freegames"}],
    "tags": [{"id": "1370"}],
    "catalogNs": {
        "mappings": [{"pageSlug": "cardpocalypse", "pageType": "productHome"}],
    },
    "offerMappings": [{"pageSlug": "cardpocalypse", "pageType": "productHome"}],
    "price": {
        "totalPrice": {
            "discountPrice": 0,
            "originalPrice": 2999,
            "voucherDiscount": 0,
            "discount": 2999,
            "currencyCode": "CAD",
            "currencyInfo": {"decimals": 2},
            "fmtPrice": {
                "originalPrice": "CA$29.99",
                "discountPrice": "0",
                "intermediatePrice": "0",
            },
        },
        "lineOffers": [{"appliedRules": []}],
    },
    "promotions": {
        "promotionalOffers": [
            {
                "promotionalOffers": [
                    {
                        "startDate": "2026-08-20T15:00:00.000Z",
                        "endDate": "2026-08-27T15:00:00.000Z",
                        "discountSetting": {
                            "discountType": "PERCENTAGE",
                            "discountPercentage": 0,
                        },
                    },
                ],
            },
        ],
        "upcomingPromotionalOffers": [],
    },
}


@pytest.fixture
def raw_game():
    return copy.deepcopy(RAW_GAME)


@pytest.fixture
def epic(monkeypatch):
    """Build an EpicFreeGames whose API returns whatever elements you pass in."""

    def _epic(elements):
        instance = EpicFreeGames(EpicSettings())

        class FakeApi:
            @staticmethod
            def get_free_games():
                return {"data": {"Catalog": {"searchStore": {"elements": elements}}}}

        monkeypatch.setattr(instance, "client", lambda: FakeApi())
        return instance

    return _epic


class TestCustomAttributes:
    def test_null_custom_attribute_value_is_accepted(self, epic, raw_game):
        games = epic([raw_game]).get_free_games()

        assert [a.value for a in games[0].custom_attributes] == ["", None]

    def test_missing_custom_attributes_key_defaults_to_empty(self, epic, raw_game):
        del raw_game["customAttributes"]

        games = epic([raw_game]).get_free_games()

        assert games[0].custom_attributes == []

    def test_null_custom_attributes_list_defaults_to_empty(self, epic, raw_game):
        raw_game["customAttributes"] = None

        games = epic([raw_game]).get_free_games()

        assert games[0].custom_attributes == []

    def test_custom_attribute_key_is_still_required(self, epic, raw_game):
        raw_game["customAttributes"] = [{"value": "something"}]

        with pytest.raises(ValidationError):
            epic([raw_game]).get_free_games()


class TestFormatFreeGamesWithNullAttributes:
    def test_game_with_null_attribute_value_is_still_formatted(self, epic, raw_game):
        instance = epic([raw_game])

        games = instance.format_free_games()

        assert len(games) == 1
        assert games[0].game_title == "Cardpocalypse"
        assert games[0].game_price == "CA$29.99"
        assert games[0].game_url == f"{instance.settings.base_url}/p/cardpocalypse"
