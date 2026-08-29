from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
from conftest import make_raw_game

from notifier.api.epic import EpicFreeGames, store_path_from_url_pattern
from notifier.settings import EpicSettings

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest_mock



class CatalogMappingStub:
    def __init__(self, page_slug: str) -> None:
        self.page_slug = page_slug


class CatalogNsStub:
    def __init__(self, slug: str | None) -> None:
        self.mappings = [CatalogMappingStub(slug)] if slug else []


class EpicGameDataStub:
    def __init__(
        self,
        product_slug: str | None,
        catalog_slug: str | None,
        url_slug: str,
    ) -> None:
        self.product_slug = product_slug
        self.catalog_ns = CatalogNsStub(catalog_slug)
        self.url_slug = url_slug


@pytest.mark.parametrize(
    ("product_slug", "catalog_slug", "url_slug", "expected"),
    [
        ("cardpocalypse/home", None, "", "cardpocalypse"),
        ("lisa-the-definitive-edition", None, "", "lisa-the-definitive-edition"),
        (None, "beacon-pines-629fc3", "", "beacon-pines-629fc3"),
        (None, None, "ghostrunner-2", "ghostrunner-2"),
    ],
)
def test_get_game_slug(
    product_slug: str | None,
    catalog_slug: str | None,
    url_slug: str,
    expected: str,
) -> None:
    game = EpicGameDataStub(product_slug, catalog_slug, url_slug)

    assert expected == EpicFreeGames.get_game_slug(game)


@pytest.mark.parametrize(
    ("url_pattern", "expected"),
    [
        ("/productv2/breathedge", "p"),
        ("/product/breathedge", "p"),
        ("/p/breathedge", "p"),
        ("/bundles/lisa-the-definitive-edition", "bundles"),
        ("/something-new/breathedge", None),
        ("", None),
        (None, None),
    ],
)
def test_store_path_from_url_pattern(
    url_pattern: str | None,
    expected: str | None,
) -> None:
    assert expected == store_path_from_url_pattern(url_pattern)


def test_product_uses_p_route(epic_client: Callable[..., EpicFreeGames]) -> None:
    epic = epic_client(
        elements=[make_raw_game(title="Breathedge", productSlug="breathedge")],
        cms={"breathedge": {"products": "/productv2/breathedge"}},
    )

    games = epic.format_free_games()

    assert f"{epic.settings.base_url}/p/breathedge" == games[0].game_url


def test_bundle_uses_bundles_route(epic_client: Callable[..., EpicFreeGames]) -> None:
    epic = epic_client(
        elements=[
            make_raw_game(
                title="LISA: The Definitive Edition",
                productSlug="lisa-the-definitive-edition",
                offerType="BASE_GAME",
            ),
        ],
        cms={
            "lisa-the-definitive-edition": {
                "bundles": "/bundles/lisa-the-definitive-edition",
            },
        },
    )

    games = epic.format_free_games()

    expected = f"{epic.settings.base_url}/bundles/lisa-the-definitive-edition"
    assert expected == games[0].game_url


def test_home_suffix_stripped_from_url(
    epic_client: Callable[..., EpicFreeGames],
) -> None:
    epic = epic_client(
        elements=[make_raw_game(productSlug="cardpocalypse/home")],
        cms={"cardpocalypse": {"products": "/productv2/cardpocalypse"}},
    )

    games = epic.format_free_games()

    assert f"{epic.settings.base_url}/p/cardpocalypse" == games[0].game_url


def test_missing_cms_page_falls_back_to_offer_type(
    epic_client: Callable[..., EpicFreeGames],
) -> None:
    epic = epic_client(
        elements=[
            make_raw_game(
                title="Rival Stars Horse Racing",
                productSlug=None,
                urlSlug="c27af3c6ec3a47afb720e580138de63e",
                catalogNs={
                    "mappings": [
                        {
                            "pageSlug": "rival-stars-horse-racing-dd09de",
                            "pageType": "productHome",
                        },
                    ],
                },
            ),
        ],
        cms={},
    )

    games = epic.format_free_games()

    expected = f"{epic.settings.base_url}/p/rival-stars-horse-racing-dd09de"
    assert expected == games[0].game_url


def test_cms_host_error_falls_back_to_offer_type(
    epic_client: Callable[..., EpicFreeGames],
) -> None:
    epic = epic_client(
        elements=[
            make_raw_game(
                title="Some Bundle",
                productSlug="some-bundle",
                offerType="BUNDLE",
            ),
        ],
        cms_status=500,
    )

    games = epic.format_free_games()

    assert f"{epic.settings.base_url}/bundles/some-bundle" == games[0].game_url


def test_cms_unreachable_falls_back_to_offer_type(
    epic_client: Callable[..., EpicFreeGames],
    mocker: pytest_mock.MockerFixture,
) -> None:
    epic = epic_client(
        elements=[make_raw_game(productSlug="cardpocalypse")],
        cms={"cardpocalypse": {"products": "/productv2/cardpocalypse"}},
    )
    mock_get = mocker.patch(
        "notifier.api.epic.EpicFreeGames.get_response",
        side_effect=httpx.ConnectError("content host down"),
    )

    games = epic.format_free_games()

    mock_get.assert_called_once()
    assert f"{epic.settings.base_url}/p/cardpocalypse" == games[0].game_url


def test_unrecognised_url_pattern_falls_back_to_offer_type(
    epic_client: Callable[..., EpicFreeGames],
) -> None:
    epic = epic_client(
        elements=[make_raw_game(productSlug="cardpocalypse", offerType="BUNDLE")],
        cms={"cardpocalypse": {"products": "/store-page-v9/cardpocalypse"}},
    )

    games = epic.format_free_games()

    assert f"{epic.settings.base_url}/bundles/cardpocalypse" == games[0].game_url


def test_missing_cms_page_does_not_warn(
    epic_client: Callable[..., EpicFreeGames],
    captured_logs: list[dict],
) -> None:
    # The majority of live games have no CMS page, so the fallback is routine
    # and must not warn - otherwise every normal run looks broken.
    epic = epic_client(
        elements=[make_raw_game(productSlug="monument-valley-1d99d3")],
        cms={},
    )

    epic.format_free_games()

    levels = {record["level"] for record in captured_logs}
    assert "WARNING" not in levels
    assert any("offerType fallback" in r["message"] for r in captured_logs)


@pytest.mark.parametrize(
    ("kwargs", "expected_fragment"),
    [
        ({"cms_status": 500}, "returned 500"),
        (
            {"cms": {"cardpocalypse": {"products": "/store-page-v9/cardpocalypse"}}},
            "Unrecognised _urlPattern",
        ),
    ],
)
def test_unexpected_cms_conditions_warn(
    kwargs: dict,
    expected_fragment: str,
    epic_client: Callable[..., EpicFreeGames],
    captured_logs: list[dict],
) -> None:
    epic = epic_client(
        elements=[make_raw_game(productSlug="cardpocalypse")],
        **kwargs,
    )

    epic.format_free_games()

    warnings = [r["message"] for r in captured_logs if r["level"] == "WARNING"]
    assert any(expected_fragment in message for message in warnings)


def test_store_content_url_setting_is_used() -> None:
    requested = []

    def handler(request: httpx.Request) -> httpx.Response:
        if "promos" in request.url.path:
            elements = [make_raw_game(productSlug="cardpocalypse")]
            return httpx.Response(
                200,
                json={"data": {"Catalog": {"searchStore": {"elements": elements}}}},
            )
        requested.append(str(request.url))
        return httpx.Response(200, json={"_urlPattern": "/productv2/cardpocalypse"})

    epic = EpicFreeGames(
        EpicSettings(
            free_games_url="https://mirror.example.com/promos",
            store_content_url="https://cms.example.com/api",
        ),
        transport=httpx.MockTransport(handler),
    )
    games = epic.format_free_games()

    expected = "https://cms.example.com/api/en-US/content/products/cardpocalypse"
    assert requested[0] == expected
    assert f"{epic.settings.base_url}/p/cardpocalypse" == games[0].game_url


def test_requests_use_configured_locale_and_country() -> None:
    seen: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/freeGamesPromotions"):
            seen.append(dict(request.url.params))
            elements = [make_raw_game(productSlug="cardpocalypse")]
            return httpx.Response(
                200,
                json={"data": {"Catalog": {"searchStore": {"elements": elements}}}},
            )
        seen.append(request.url.path)
        return httpx.Response(200, json={"_urlPattern": "/productv2/cardpocalypse"})

    epic = EpicFreeGames(
        EpicSettings(locale="fr-FR", country="FR"),
        transport=httpx.MockTransport(handler),
    )
    epic.format_free_games()

    assert seen[0] == {"locale": "fr-FR", "country": "FR", "allowCountries": "FR"}
    assert seen[1] == "/api/fr-FR/content/products/cardpocalypse"
