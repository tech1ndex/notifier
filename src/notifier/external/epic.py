from __future__ import annotations

from epicstore_api import EpicGamesStoreAPI
from notifier.external.models import EpicGameData, FormattedGame
from notifier.settings import EpicSettings


class EpicFreeGames:
    def __init__(self, settings: EpicSettings) -> None:
        self.settings = settings

    def client(self) -> EpicGamesStoreAPI:
        return EpicGamesStoreAPI(country=self.settings.country)

    def get_free_games(self) -> list[EpicGameData]:
        api = self.client()
        free_games_data = api.get_free_games()["data"]["Catalog"]["searchStore"][
            "elements"
        ]
        validated_games = [
            EpicGameData(**game) for game in free_games_data if game.get("promotions")
        ]

        return sorted(validated_games, key=lambda g: g.title)

    @staticmethod
    def get_game_slug(game: EpicGameData) -> str:
        if game.product_slug:
            return game.product_slug
        if (
            game.catalog_ns
            and game.catalog_ns.mappings
            and len(game.catalog_ns.mappings) > 0
        ):
            return game.catalog_ns.mappings[0].page_slug
        return game.url_slug

    def format_free_games(self) -> list[FormattedGame]:
        free_games = self.get_free_games()
        games_info = []

        for game in free_games:
            if (
                game.promotions.promotional_offers
                and game.price.total_price.discount_price == 0
            ):
                promotion = game.promotions.promotional_offers[0].promotional_offers[0]

                games_info.append(
                    FormattedGame(
                        game_title=game.title,
                        game_price=game.price.total_price.fmt_price.original_price,
                        end_date=promotion.end_date,
                        game_url=f"{self.settings.base_url}/{self.get_game_slug(game)}",
                    ),
                )

        return games_info
