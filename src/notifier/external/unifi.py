from __future__ import annotations

import json

import requests
from bs4 import BeautifulSoup
from src.notifier.settings import UnifiStoreSettings
from tenacity import retry, stop_after_attempt


class UnifiStockChecker:
    def __init__(self, settings: UnifiStoreSettings) -> None:
        self.settings = settings

    @retry(
        stop=stop_after_attempt(1),
    )
    def get_webpage_data(self) -> BeautifulSoup | None:
        url = (
            f"{self.settings.base_url}/category/cloud-gateways-compact/collections/cloud-gateway-max/products/"
            f"{self.settings.model}?variant={self.settings.model}"
        )

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            return BeautifulSoup(response.content, "html.parser")

        except requests.exceptions.RequestException:
            return None

    def get_availability(self) -> str | None:
        soup = self.get_webpage_data()
        if soup:
            script_tag = soup.find(
                "script",
                {"id": "product-jsonld", "type": "application/ld+json"},
            )

            if script_tag:
                json_data = json.loads(script_tag.text)
                return json_data["offers"]["availability"]
        return None

    def check_availability(self) -> bool:
        availability = self.get_availability()
        return availability != "https://schema.org/OutOfStock"
