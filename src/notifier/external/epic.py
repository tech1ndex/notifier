from __future__ import annotations

from epicstore_api import EpicGamesStoreAPI

from notifier.external.models import EpicGameData, FormattedGame
from notifier.settings import EpicSettings


class EpicFreeGames:
    def __init__(self, settings: EpicSettings) -> None:
        self.settings = settings

    def client(self) -> EpicGamesStoreAPI:
        return EpicGamesStoreAPI(country=self.settings.country)

    @staticmethod
    def _normalize_game_dict(game: dict) -> dict:
        g = dict(game)

        list_keys = [
            "keyImages",
            "items",
            "customAttributes",
            "categories",
            "tags",
            "offerMappings",
        ]
        for k in list_keys:
            if g.get(k) is None:
                g[k] = []

        if g.get("catalogNs") is None:
            g["catalogNs"] = {"mappings": []}
        elif g["catalogNs"].get("mappings") is None:
            g["catalogNs"]["mappings"] = []

        if g.get("price") is not None and g["price"].get("lineOffers") is None:
            g["price"]["lineOffers"] = []

        if g.get("promotions") is not None:
            if g["promotions"].get("promotionalOffers") is None:
                g["promotions"]["promotionalOffers"] = []
            if g["promotions"].get("upcomingPromotionalOffers") is None:
                g["promotions"]["upcomingPromotionalOffers"] = []

            for group in g["promotions"].get("promotionalOffers", []):
                if group.get("promotionalOffers") is None:
                    group["promotionalOffers"] = []

        return g

    def get_free_games(self) -> list[EpicGameData]:
        api = self.client()
        free_games_data = api.get_free_games()["data"]["Catalog"]["searchStore"][
            "elements"
        ]

        validated_games = [
            EpicGameData(**self._normalize_game_dict(game))
            for game in free_games_data
            if game.get("promotions")
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

    @staticmethod
    def is_game_bundle(slug: str, game_data=None) -> bool:
        slug_lower = slug.lower()
        slug_parts = set(slug_lower.replace("-", " ").replace("_", " ").split())

        bundle_keywords = {
            "collection",
            "bundle",
            "pack",
            "anthology",
        }

        if bundle_keywords & slug_parts:
            return True

        if "complete-edition" in slug_lower:
            return True

        return bool(
            game_data
            and hasattr(game_data, "offer_type")
            and game_data.offer_type == "BUNDLE"
        )

    def format_free_games(self) -> list[FormattedGame]:
        free_games = self.get_free_games()
        games_info = []

        for game in free_games:
            if (
                game.promotions.promotional_offers
                and game.price.total_price.discount_price == 0
            ):
                promotion = game.promotions.promotional_offers[0].promotional_offers[0]
                game_slug = self.get_game_slug(game)

                path_prefix = (
                    "bundles" if self.is_game_bundle(game_slug, game) else None
                )
                game_url = (
                    f"{self.settings.base_url}/{path_prefix}/{game_slug}"
                    if path_prefix
                    else f"{self.settings.base_url}/{game_slug}"
                )

                games_info.append(
                    FormattedGame(
                        game_title=game.title,
                        game_price=game.price.total_price.fmt_price.original_price,
                        end_date=promotion.end_date,
                        game_url=game_url,
                    ),
                )

        return games_info
