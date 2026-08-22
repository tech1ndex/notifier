from typing import ClassVar

import pytest

from notifier.external.epic import EpicFreeGames
from notifier.settings import EpicSettings


class TestGetGameSlug:
    def _game(self, *, product_slug=None, catalog_slug=None, url_slug=""):
        class MockMapping:
            def __init__(self, page_slug):
                self.page_slug = page_slug

        class MockCatalogNs:
            def __init__(self, slug):
                self.mappings = [MockMapping(slug)] if slug else []

        class MockGame:
            pass

        game = MockGame()
        game.product_slug = product_slug
        game.catalog_ns = MockCatalogNs(catalog_slug)
        game.url_slug = url_slug
        return game

    def test_strips_home_suffix_from_product_slug(self):
        game = self._game(product_slug="cardpocalypse/home")
        assert EpicFreeGames.get_game_slug(game) == "cardpocalypse"

    def test_clean_product_slug_unchanged(self):
        game = self._game(product_slug="lisa-the-definitive-edition")
        assert EpicFreeGames.get_game_slug(game) == "lisa-the-definitive-edition"

    def test_falls_back_to_catalog_ns_slug(self):
        game = self._game(catalog_slug="beacon-pines-629fc3")
        assert EpicFreeGames.get_game_slug(game) == "beacon-pines-629fc3"

    def test_falls_back_to_url_slug(self):
        game = self._game(url_slug="ghostrunner-2")
        assert EpicFreeGames.get_game_slug(game) == "ghostrunner-2"


class TestFormatFreeGamesIntegration:
    @pytest.fixture
    def mock_game_data(self):
        class MockPromotion:
            end_date = "2024-01-15T00:00:00.000Z"

        class MockPromotionalOffers:
            promotional_offers: ClassVar = [MockPromotion()]

        class MockPromotions:
            promotional_offers: ClassVar = [MockPromotionalOffers()]

        class MockPrice:
            class TotalPrice:
                discount_price = 0

                class FmtPrice:
                    original_price = "$29.99"

                fmt_price = FmtPrice()

            total_price = TotalPrice()

        class MockGame:
            def __init__(self, title, slug, offer_type="BASE_GAME"):
                self.title = title
                self.product_slug = slug
                self.url_slug = slug
                self.catalog_ns = None
                self.offer_type = offer_type
                self.promotions = MockPromotions()
                self.price = MockPrice()

        return MockGame

    def test_regular_game_url(self, mock_game_data):
        settings = EpicSettings()
        epic = EpicFreeGames(settings)
        epic.get_free_games = lambda: [mock_game_data("Ghostrunner 2", "ghostrunner-2")]

        games = epic.format_free_games()

        assert games[0].game_url == f"{settings.base_url}/p/ghostrunner-2"

    def test_bundle_uses_bundles_route(self, mock_game_data):
        settings = EpicSettings()
        epic = EpicFreeGames(settings)
        epic.get_free_games = lambda: [
            mock_game_data(
                "LISA: The Definitive Edition",
                "lisa-the-definitive-edition",
                offer_type="BUNDLE",
            ),
        ]

        games = epic.format_free_games()

        assert (
            games[0].game_url
            == f"{settings.base_url}/bundles/lisa-the-definitive-edition"
        )
        assert "/p/bundles/" not in games[0].game_url

    def test_complete_edition_is_product_not_bundle(self, mock_game_data):
        # "Complete Edition" naming must NOT force the bundle route; offerType wins.
        settings = EpicSettings()
        epic = EpicFreeGames(settings)
        epic.get_free_games = lambda: [
            mock_game_data(
                "RollerCoaster Tycoon 3 Complete Edition",
                "rollercoaster-tycoon-3-complete-edition/home",
                offer_type="BASE_GAME",
            ),
        ]

        games = epic.format_free_games()

        assert (
            games[0].game_url
            == f"{settings.base_url}/p/rollercoaster-tycoon-3-complete-edition"
        )

    def test_home_suffix_stripped_from_url(self, mock_game_data):
        settings = EpicSettings()
        epic = EpicFreeGames(settings)
        epic.get_free_games = lambda: [
            mock_game_data("Cardpocalypse", "cardpocalypse/home"),
        ]

        games = epic.format_free_games()

        assert games[0].game_url == f"{settings.base_url}/p/cardpocalypse"
        assert "/home" not in games[0].game_url
