import pytest
import pytest_mock
import os
from pathlib import Path
from notifier.external.epic import EpicFreeGames
from notifier.settings import EpicSettings


def _fake_api_response():
    return {
        "data": {
            "Catalog": {
                "searchStore": {
                    "elements": [
                        {
                            "title": "Free Game",
                            "id": "game1",
                            "namespace": "ns",
                            "description": "A free game",
                            "effectiveDate": "2025-10-19T00:00:00Z",
                            "offerType": "BASE",
                            "expiryDate": None,
                            "viewableDate": None,
                            "status": "ACTIVE",
                            "isCodeRedemptionOnly": False,
                            "keyImages": [{"type": "thumbnail", "url": "http://example.com/img"}],
                            "seller": {"id": "seller1", "name": "Seller"},
                            "productSlug": None,
                            "urlSlug": "game-slug",
                            "url": None,
                            "items": [{"id": "item1", "namespace": "ns"}],
                            "customAttributes": [{"key": "k", "value": "v"}],
                            "categories": [{"path": "games"}],
                            "tags": [{"id": "t1"}],
                            "catalogNs": {"mappings": None},
                            "offerMappings": None,
                            "price": {
                                "totalPrice": {
                                    "discountPrice": 0,
                                    "originalPrice": 1000,
                                    "voucherDiscount": 0,
                                    "discount": 0,
                                    "currencyCode": "USD",
                                    "currencyInfo": {"decimals": 2},
                                    "fmtPrice": {
                                        "originalPrice": "$10.00",
                                        "discountPrice": "$0.00",
                                        "intermediatePrice": "$10.00",
                                    },
                                },
                                "lineOffers": [
                                    {"appliedRules": [{"id": None, "endDate": None, "discountSetting": None}]}
                                ],
                            },
                            "promotions": {
                                "promotionalOffers": [
                                    {
                                        "promotionalOffers": [
                                            {
                                                "startDate": "2025-10-19T00:00:00Z",
                                                "endDate": "2025-10-26T00:00:00Z",
                                                "discountSetting": {"discountType": "PERCENTAGE", "discountPercentage": 100},
                                            }
                                        ]
                                    }
                                ],
                                "upcomingPromotionalOffers": [],
                            },
                        }
                    ]
                }
            }
        }
    }


def test_normalize_and_validate_none_mappings(mocker: pytest_mock.MockerFixture, tmp_path: Path) -> None:
    fake_api = mocker.MagicMock()
    fake_api.get_free_games.return_value = _fake_api_response()

    # Patch EpicFreeGames.client to return our fake API object
    mocker.patch("notifier.external.epic.EpicFreeGames.client", return_value=fake_api)

    # Ensure SentGamesStorage uses an ephemeral file so tests are deterministic
    os.environ["SENT_GAMES_FILE_PATH"] = str(tmp_path / "sent_games.json")

    epic = EpicFreeGames(EpicSettings())

    games = epic.get_free_games()

    assert len(games) == 1
    game = games[0]

    # After normalization & validation, these should be lists (possibly empty)
    assert isinstance(game.catalog_ns.mappings, list)
    assert isinstance(game.offer_mappings, list)
    assert game.catalog_ns.mappings == []
    assert game.offer_mappings == []
