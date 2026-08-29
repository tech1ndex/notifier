from __future__ import annotations

import json
from http import HTTPStatus
from typing import Any

import httpx
from loguru import logger
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from notifier.api.errors import EpicApiError, EpicNotFoundError
from notifier.api.models import EpicGameData, FormattedGame
from notifier.settings import EpicSettings

CONTENT_TYPES = ("products", "bundles")

CMS_ROUTE_TO_STORE_PATH = {
    "productv2": "p",
    "product": "p",
    "p": "p",
    "bundles": "bundles",
}

SPURIOUS_ERROR_CODE = 1004


def parse_service_response(error: dict) -> Any:
    raw = error.get("serviceResponse")
    if not raw:
        return None
    if isinstance(raw, dict | list):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def is_spurious_error(error: dict) -> bool:
    service_response = parse_service_response(error)
    return (
        isinstance(service_response, dict)
        and service_response.get("numericErrorCode") == SPURIOUS_ERROR_CODE
    )


def clean_spurious_errors(payload: Any) -> Any:
    if not isinstance(payload, dict) or not payload.get("errors"):
        return payload

    kept = [error for error in payload["errors"] if not is_spurious_error(error)]
    if kept:
        payload["errors"] = kept
    else:
        payload.pop("errors")
    return payload


def raise_for_response_errors(payload: Any) -> None:
    if not isinstance(payload, dict) or not payload.get("errors"):
        return

    error = payload["errors"][0]
    service_response = parse_service_response(error)

    if not service_response:
        message = error.get("message", "Unknown Epic Games Store error")
        raise EpicApiError(message, service_response=error)

    if isinstance(service_response, dict):
        if str(service_response.get("errorCode", "")).endswith("not_found"):
            raise EpicNotFoundError(
                service_response.get("errorMessage", "Resource not found"),
                service_response.get("numericErrorCode"),
                service_response,
            )
    elif service_response == "not found":
        msg = "The resource was not found, no more data provided by Epic Games Store."
        raise EpicNotFoundError(msg)

    logger.warning(f"Unhandled Epic Games Store response error: {error}")


def store_path_from_url_pattern(url_pattern: str | None) -> str | None:
    if not url_pattern:
        return None
    route = url_pattern.strip("/").split("/")[0]
    return CMS_ROUTE_TO_STORE_PATH.get(route)


class EpicFreeGames:
    def __init__(
        self,
        settings: EpicSettings,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self._transport = transport

    def client(self) -> httpx.Client:
        return httpx.Client(
            transport=self._transport,
            timeout=self.settings.request_timeout_seconds,
            follow_redirects=True,
        )

    def retrying(self, exception_types: type[Exception]) -> Retrying:
        return Retrying(
            stop=stop_after_attempt(self.settings.retry_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=self.settings.retry_wait_min_seconds,
                max=self.settings.retry_wait_max_seconds,
            ),
            retry=retry_if_exception_type(exception_types),
            reraise=True,
        )

    @staticmethod
    def fetch_json(
        client: httpx.Client,
        url: str,
        params: dict | None = None,
    ) -> Any:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_json(
        self,
        client: httpx.Client,
        url: str,
        params: dict | None = None,
    ) -> Any:
        return self.retrying(httpx.HTTPError)(self.fetch_json, client, url, params)

    def get_response(self, client: httpx.Client, url: str) -> httpx.Response:
        return self.retrying(httpx.TransportError)(client.get, url)

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

    def free_games_params(self) -> dict:
        return {
            "locale": self.settings.locale,
            "country": self.settings.country,
            "allowCountries": self.settings.country,
        }

    def fetch_free_games_payload(self) -> Any:
        with self.client() as client:
            payload = self.get_json(
                client,
                self.settings.free_games_url,
                params=self.free_games_params(),
            )

        payload = clean_spurious_errors(payload)
        raise_for_response_errors(payload)
        return payload

    def get_free_games(self) -> list[EpicGameData]:
        payload = self.fetch_free_games_payload()

        try:
            free_games_data = payload["data"]["Catalog"]["searchStore"]["elements"]
        except (KeyError, TypeError) as exc:
            msg = "Unexpected freeGamesPromotions payload shape"
            raise EpicApiError(msg) from exc

        validated_games = [
            EpicGameData(**self._normalize_game_dict(game))
            for game in free_games_data
            if game.get("promotions")
        ]

        return sorted(validated_games, key=lambda g: g.title)

    @staticmethod
    def get_game_slug(game: EpicGameData) -> str:
        if game.product_slug:
            slug = game.product_slug
        elif (
            game.catalog_ns
            and game.catalog_ns.mappings
            and len(game.catalog_ns.mappings) > 0
        ):
            slug = game.catalog_ns.mappings[0].page_slug
        else:
            slug = game.url_slug

        return slug.strip("/").split("/")[0] if slug else slug

    def content_url(self, content_type: str, slug: str) -> str:
        return (
            f"{self.settings.store_content_url}/{self.settings.locale}"
            f"/content/{content_type}/{slug}"
        )

    def fetch_url_pattern(
        self,
        client: httpx.Client,
        content_type: str,
        slug: str,
    ) -> str | None:
        response = self.get_response(client, self.content_url(content_type, slug))

        if response.status_code >= HTTPStatus.BAD_REQUEST:
            if response.status_code != HTTPStatus.NOT_FOUND:
                logger.warning(
                    f"CMS lookup for {slug!r} returned {response.status_code}",
                )
            return None

        try:
            return response.json().get("_urlPattern")
        except (ValueError, AttributeError):
            logger.warning(f"CMS returned an unreadable body for {slug!r}")
            return None

    def resolve_store_path(self, client: httpx.Client, slug: str) -> str | None:
        for content_type in CONTENT_TYPES:
            try:
                url_pattern = self.fetch_url_pattern(client, content_type, slug)
            except httpx.HTTPError as exc:
                logger.warning(f"CMS lookup failed for {slug!r}: {exc}")
                return None

            if url_pattern is None:
                continue

            store_path = store_path_from_url_pattern(url_pattern)
            if store_path is None:
                logger.warning(f"Unrecognised _urlPattern {url_pattern!r} for {slug!r}")
            return store_path

        logger.debug(f"No CMS page for {slug!r}; using the offerType fallback")
        return None

    @staticmethod
    def fallback_store_path(game: EpicGameData) -> str:
        return "bundles" if game.offer_type == "BUNDLE" else "p"

    def store_path(self, client: httpx.Client, game: EpicGameData, slug: str) -> str:
        return self.resolve_store_path(client, slug) or self.fallback_store_path(game)

    def game_url(self, client: httpx.Client, game: EpicGameData) -> str:
        slug = self.get_game_slug(game)
        return f"{self.settings.base_url}/{self.store_path(client, game, slug)}/{slug}"

    @staticmethod
    def is_free_now(game: EpicGameData) -> bool:
        return bool(
            game.promotions.promotional_offers
            and game.price.total_price.discount_price == 0,
        )

    def format_free_games(self) -> list[FormattedGame]:
        free_games = self.get_free_games()
        games_info = []

        with self.client() as client:
            for game in free_games:
                if not self.is_free_now(game):
                    continue

                promotion = game.promotions.promotional_offers[0].promotional_offers[0]
                games_info.append(
                    FormattedGame(
                        game_title=game.title,
                        game_price=game.price.total_price.fmt_price.original_price,
                        end_date=promotion.end_date,
                        game_url=self.game_url(client, game),
                    ),
                )

        return games_info
