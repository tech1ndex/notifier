import pytest
from notifier.external.epic import EpicFreeGames


class TestIsGameBundle:
    def test_bundle_keyword_collection(self):
        assert EpicFreeGames.is_game_bundle("trine-classic-collection") is True
        assert EpicFreeGames.is_game_bundle("mega-collection-pack") is True

    def test_bundle_keyword_bundle(self):
        assert EpicFreeGames.is_game_bundle("indie-game-bundle") is True
        assert EpicFreeGames.is_game_bundle("ultimate-bundle") is True

    def test_bundle_keyword_pack(self):
        assert EpicFreeGames.is_game_bundle("starter-pack") is True
        assert EpicFreeGames.is_game_bundle("dlc-pack") is True

    def test_bundle_keyword_anthology(self):
        assert EpicFreeGames.is_game_bundle("horror-anthology") is True

    def test_bundle_keyword_complete_edition(self):
        assert EpicFreeGames.is_game_bundle("game-complete-edition") is True

    def test_case_insensitive_matching(self):
        assert EpicFreeGames.is_game_bundle("TRINE-COLLECTION") is True
        assert EpicFreeGames.is_game_bundle("Mega-Bundle") is True
        assert EpicFreeGames.is_game_bundle("Complete-EDITION") is True

    def test_non_bundle_games(self):
        assert EpicFreeGames.is_game_bundle("cyberpunk-2077") is False
        assert EpicFreeGames.is_game_bundle("the-witcher-3") is False
        assert EpicFreeGames.is_game_bundle("fortnite") is False

    def test_partial_keyword_match(self):
        assert EpicFreeGames.is_game_bundle("supercollection") is False
        assert EpicFreeGames.is_game_bundle("megabundle") is False

        assert EpicFreeGames.is_game_bundle("mega-bundle") is True
        assert EpicFreeGames.is_game_bundle("super-collection") is True

    def test_empty_slug(self):
        assert EpicFreeGames.is_game_bundle("") is False

    def test_game_data_with_bundle_offer_type(self):
        class MockGameData:
            offer_type = "BUNDLE"

        mock_game = MockGameData()
        assert EpicFreeGames.is_game_bundle("some-game", mock_game) is True

    def test_game_data_with_non_bundle_offer_type(self):
        class MockGameData:
            offer_type = "GAME"

        mock_game = MockGameData()

        assert EpicFreeGames.is_game_bundle("some-collection", mock_game) is True
        assert EpicFreeGames.is_game_bundle("regular-game", mock_game) is False

    def test_game_data_without_offer_type(self):
        class MockGameData:
            pass

        mock_game = MockGameData()
        assert EpicFreeGames.is_game_bundle("game-bundle", mock_game) is True
        assert EpicFreeGames.is_game_bundle("regular-game", mock_game) is False

    def test_none_game_data(self):
        assert EpicFreeGames.is_game_bundle("game-collection", None) is True
        assert EpicFreeGames.is_game_bundle("regular-game", None) is False

    def test_slug_with_path_prefix(self):
        assert EpicFreeGames.is_game_bundle("p/trine-collection") is True
        assert EpicFreeGames.is_game_bundle("bundles/mega-pack") is True

    def test_edge_cases(self):
        assert EpicFreeGames.is_game_bundle("collection") is True
        assert EpicFreeGames.is_game_bundle("bundle") is True

        assert EpicFreeGames.is_game_bundle("collector-edition") is False
        assert EpicFreeGames.is_game_bundle("unpacked") is False


class TestFormatFreeGamesIntegration:
    @pytest.fixture
    def mock_game_data(self):
        class MockPromotion:
            end_date = "2024-01-15T00:00:00.000Z"

        class MockPromotionalOffers:
            promotional_offers = [MockPromotion()]

        class MockPromotions:
            promotional_offers = [MockPromotionalOffers()]

        class MockPrice:
            class TotalPrice:
                discount_price = 0

                class FmtPrice:
                    original_price = "$29.99"

                fmt_price = FmtPrice()

            total_price = TotalPrice()

        class MockGame:
            def __init__(self, title, slug, is_bundle=False):
                self.title = title
                self.product_slug = slug
                self.url_slug = slug
                self.catalog_ns = None
                self.promotions = MockPromotions()
                self.price = MockPrice()
                if is_bundle:
                    self.offer_type = "BUNDLE"

        return MockGame
