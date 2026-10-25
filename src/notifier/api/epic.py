from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any

import httpx
from loguru import logger
from tenacity import (
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from notifier.api.errors import EpicApiError, EpicNotFoundError
from notifier.api.models import EpicGameData, FormattedGame, PromotionalOffer
from notifier.settings import EpicSettings

CONTENT_TYPES = ("products", "bundles")

CMS_ROUTE_TO_STORE_PATH = {
    "productv2": "p",
    "product": "p",
    "p": "p",
    "bundles": "bundles",
}

SPURIOUS_ERROR_CODE = 1004

FREE_DISCOUNT_PERCENTAGE = 0


def is_transport_error(exc: BaseException) -> bool:
    return isinstance(exc, httpx.TransportError)


def is_retryable_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return (
            status == HTTPStatus.TOO_MANY_REQUESTS
            or status >= HTTPStatus.INTERNAL_SERVER_ERROR
        )
    return isinstance(exc, httpx.TransportError)


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
        self._store_path_cache: dict[str, str | None] = {}
        self.had_cms_errors = False

    def client(self) -> httpx.Client:
        return httpx.Client(
            transport=self._transport,
            timeout=self.settings.request_timeout_seconds,
            follow_redirects=True,
        )

    def retrying(self, should_retry: Callable[[BaseException], bool]) -> Retrying:
        return Retrying(
            stop=stop_after_attempt(self.settings.retry_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=self.settings.retry_wait_min_seconds,
                max=self.settings.retry_wait_max_seconds,
            ),
            retry=retry_if_exception(should_retry),
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
        try:
            return response.json()
        except ValueError as exc:
            msg = "freeGamesPromotions returned an unreadable body"
            raise EpicApiError(msg) from exc

    def get_json(
        self,
        client: httpx.Client,
        url: str,
        params: dict | None = None,
    ) -> Any:
        return self.retrying(is_retryable_error)(
            self.fetch_json,
            client,
            url,
            params,
        )

    def get_response(self, client: httpx.Client, url: str) -> httpx.Response:
        return self.retrying(is_transport_error)(client.get, url)

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

        if response.status_code == HTTPStatus.NOT_FOUND:
            return None
        response.raise_for_status()

        try:
            payload = response.json()
        except ValueError as exc:
            msg = f"CMS returned an unreadable body for {slug!r}"
            raise EpicApiError(msg) from exc

        url_pattern = payload.get("_urlPattern") if isinstance(payload, dict) else None
        if not isinstance(url_pattern, str) or not url_pattern.strip():
            msg = f"CMS returned an invalid _urlPattern for {slug!r}"
            raise EpicApiError(msg)
        return url_pattern

    def resolve_store_path(self, client: httpx.Client, slug: str) -> str | None:
        if slug not in self._store_path_cache:
            self._store_path_cache[slug] = self.lookup_store_path(client, slug)
        return self._store_path_cache[slug]

    def lookup_store_path(self, client: httpx.Client, slug: str) -> str | None:
        for content_type in CONTENT_TYPES:
            url_pattern = self.fetch_url_pattern(client, content_type, slug)

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

    @staticmethod
    def all_promotional_offers(game: EpicGameData) -> list[PromotionalOffer]:
        return [
            offer
            for group in game.promotions.promotional_offers
            for offer in group.promotional_offers
        ]

    @staticmethod
    def is_giveaway(offer: PromotionalOffer) -> bool:
        return offer.discount_setting.discount_percentage == FREE_DISCOUNT_PERCENTAGE

    def current_promotion(self, game: EpicGameData) -> PromotionalOffer | None:
        offers = self.all_promotional_offers(game)
        if not offers:
            return None

        now = datetime.now(tz=UTC)
        active = [o for o in offers if o.start_date <= now <= o.end_date]
        giveaways = [o for o in active if self.is_giveaway(o)]
        upcoming_end = [o for o in offers if o.end_date >= now]

        for candidates in (giveaways, active, upcoming_end):
            if candidates:
                return min(candidates, key=lambda o: o.end_date)

        return None

    def format_free_games(self) -> list[FormattedGame]:
        # Report partial failures to callers while returning successfully resolved games.
        self.had_cms_errors = False
        free_games = self.get_free_games()
        games_info = []

        with self.client() as client:
            for game in free_games:
                if not self.is_free_now(game):
                    continue

                promotion = self.current_promotion(game)
                if promotion is None:
                    logger.warning(
                        f"{game.title!r} is free but has no promotional offer; skipping",
                    )
                    continue

                if not self.get_game_slug(game):
                    logger.warning(f"{game.title!r} has no store slug; skipping")
                    continue

                try:
                    game_url = self.game_url(client, game)
                except (httpx.HTTPError, EpicApiError) as exc:
                    self.had_cms_errors = True
                    logger.warning(
                        f"CMS lookup failed for {game.title!r}; "
                        f"skipping until next run: {exc}",
                    )
                    continue

                games_info.append(
                    FormattedGame(
                        game_id=game.id,
                        game_namespace=game.namespace,
                        game_title=game.title,
                        game_price=game.price.total_price.fmt_price.original_price,
                        end_date=promotion.end_date,
                        game_url=game_url,
                    ),
                )

        return games_info
