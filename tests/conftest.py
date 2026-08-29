from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

import httpx
import pytest
from loguru import logger

from notifier.api.epic import EpicFreeGames
from notifier.settings import EpicSettings

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

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


def make_raw_game(**overrides: Any) -> dict:
    game = copy.deepcopy(RAW_GAME)
    game.update(overrides)
    return game


def free_games_payload(elements: list[dict]) -> dict:
    return {"data": {"Catalog": {"searchStore": {"elements": elements}}}}


@pytest.fixture
def raw_game() -> dict:
    return copy.deepcopy(RAW_GAME)


@pytest.fixture
def captured_logs() -> Iterator[list[dict]]:
    records: list[dict] = []
    sink_id = logger.add(
        lambda message: records.append(
            {
                "level": message.record["level"].name,
                "message": message.record["message"],
            },
        ),
        level="DEBUG",
    )
    yield records
    logger.remove(sink_id)


@pytest.fixture
def epic_client() -> Callable[..., EpicFreeGames]:
    def _epic(
        elements: list[dict] | None = None,
        cms: dict[str, dict[str, str]] | None = None,
        cms_status: int | None = None,
        payload: dict | None = None,
        **settings: Any,
    ) -> EpicFreeGames:
        cms_pages = cms or {}
        body = payload if payload is not None else free_games_payload(elements or [])

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path.startswith("/freeGamesPromotions"):
                return httpx.Response(200, json=body)

            if cms_status is not None:
                return httpx.Response(cms_status, json={})

            *_, content_type, slug = request.url.path.strip("/").split("/")
            url_pattern = cms_pages.get(slug, {}).get(content_type)
            if url_pattern is None:
                return httpx.Response(404, json={})
            return httpx.Response(200, json={"_urlPattern": url_pattern})

        return EpicFreeGames(
            EpicSettings(**settings),
            transport=httpx.MockTransport(handler),
        )

    return _epic
