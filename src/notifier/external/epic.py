from typing import Any

from epicstore_api import EpicGamesStoreAPI
from src.notifier.settings import Settings

class EpicFreeGames:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def client(self) -> EpicGamesStoreAPI:
        return EpicGamesStoreAPI(country=self.settings.country)

    def format_games_info(self) -> list[dict[str, str | Any]]:
        free_games = self.client().get_free_games()

        games_info = []
        for game in free_games['data']['Catalog']['searchStore']['elements']:
            name = game['title']
            original_price = game['price']['totalPrice']['fmtPrice']['originalPrice']
            discount_price = game['price']['totalPrice']['fmtPrice']['discountPrice']
            url_slug = game['catalogNs']['mappings'][0]['pageSlug'] if game['catalogNs']['mappings'] else game['urlSlug']
            store_url = f"https://store.epicgames.com/en-US/p/{url_slug}"

            games_info.append({
                'name': name,
                'original_price': original_price,
                'discount_price': discount_price,
                'store_url': store_url
            })
        return games_info

"""
    for game in games_info:
        print(f"Name: {game['name']}, Original Price: {game['original_price']}, "
                f"Discount Price: {game['discount_price']}, URL: {game['store_url']}")
"""

