from __future__ import annotations

import operator
from datetime import datetime
from typing import Any

from epicstore_api import EpicGamesStoreAPI
from src.notifier.settings import EpicSettings


class EpicFreeGames:
    def __init__(self, settings: EpicSettings) -> None:
        self.settings = settings

    def client(self) -> EpicGamesStoreAPI:
        return EpicGamesStoreAPI(country=self.settings.country)

    def get_free_games(self) -> list[dict[str, datetime | str | Any]]:
        api = self.client()
        free_games = api.get_free_games()['data']['Catalog']['searchStore']['elements']

        free_games_sorted = sorted(
            filter(lambda g: g.get('promotions'), free_games),
            key=operator.itemgetter('title'),
        )
        games_info = []

        for game in free_games_sorted:
            game_title = game['title']
            url_type = "bundles" if game['offerType'] == "BUNDLE" else "p"
            final_slug = game["catalogNs"]["mappings"][0]["pageSlug"] if game["catalogNs"]["mappings"] else game[
                "urlSlug"]
            game_url = f"https://store.epicgames.com/en/{url_type}/{final_slug}"

            game_price = game['price']['totalPrice']['fmtPrice']['originalPrice']

            game_promotions = game['promotions']['promotionalOffers']

            if game_promotions and game['price']['totalPrice']['discountPrice'] == 0:
                promotion_data = game_promotions[0]['promotionalOffers'][0]
                end_date_iso = promotion_data['endDate'][:-1]

                end_date = datetime.fromisoformat(end_date_iso)
                games_info.append({
                    'name': game_title,
                    'original_price': game_price,
                    'end_date': end_date,
                    'game_url': game_url,
                })
            return games_info