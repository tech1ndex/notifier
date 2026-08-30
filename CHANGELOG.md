_______________________________________________________________________________

## [0.24.x Major Changes]

### Added

- `notifier.api` package holding our own Epic client (`epic.py`), error types
  (`errors.py`) and the response models moved from `notifier.external`.
- `httpx` dependency, used for all Epic calls.
- Canonical URL resolution against Epic's CMS
  (`store-content.ak.epicgames.com/api/{locale}/content/{products,bundles}/<slug>`).
  Each CMS page publishes its own `_urlPattern`, which is the source of truth for
  a game's route. Note that the pattern is the CMS's *internal* route
  (`/productv2/<slug>`), not the public one, so the leading segment is mapped onto
  the storefront path via `CMS_ROUTE_TO_STORE_PATH`; real multi-title bundles are
  served under `/bundles/<slug>`. An unrecognised pattern is treated as "unknown"
  and falls back rather than being used verbatim.
- `EpicSettings` entries for everything the client talks to or tunes, so no
  endpoint or retry value is hard coded: `free_games_url`, `store_content_url`,
  `locale`, `request_timeout_seconds`, `retry_attempts`,
  `retry_wait_min_seconds` and `retry_wait_max_seconds`.

### Changed

- Free games are fetched with a direct `GET` to
  `store-site-backend-static.ak.epicgames.com/freeGamesPromotions` (with `locale`,
  `country` and `allowCountries`). This endpoint is plain JSON, not GraphQL, and
  needs no anti-bot handling — only `store.epicgames.com` is bot-protected, and we
  never call it. That made the library's `cloudscraper` session dead weight.
- Store URLs are resolved from the CMS first, falling back to the previous
  `offerType == "BUNDLE"` heuristic when a lookup fails, 404s on both content
  types, or returns a route we do not recognise. The feed's `pageType` is
  unreliable (LISA: The Definitive Edition reports `productHome` but really lives
  at `/bundles/lisa-the-definitive-edition`), and `offerType` is only a heuristic,
  so the fallback exists purely so a content-host hiccup never drops a
  notification.
- Outbound Epic calls retry with the same `tenacity` policy used elsewhere,
  defaulting to five attempts with exponential backoff but now driven by
  `EpicSettings`. The free-games fetch retries transport errors and 5xx; CMS
  lookups retry transport errors only, so the caller can act on a 404.

### Fixed

- Bundle URLs no longer 404 (follow-up to the `offerType`-only fix).
- The published end date is taken from the promotional offer that is actually
  live and free, instead of `promotionalOffers[0].promotionalOffers[0]`. Epic
  models these as a list of lists and does not guarantee ordering, so the first
  entry could be an expired or upcoming window, or a concurrent partial discount
  - any of which would put a wrong "free until" date in the notification. A group
  with an empty inner list also raised `IndexError` and killed the whole run;
  such a game is now skipped with a warning.
- A missing CMS page logs at DEBUG rather than WARNING. Most live games (5 of 8
  at time of writing - every one whose slug carries Epic's `-<hex>` suffix) have
  no page in the legacy CMS, so taking the `offerType` fallback is the normal
  path, not an anomaly. WARNING is now reserved for cases that need attention: a
  non-404 CMS status, an unreadable body, a transport failure, or an
  `_urlPattern` whose route we do not recognise.

### Removed

- `epicstore_api` and `cloudscraper` dependencies. Two behaviours were ported out
  of the library before dropping it: `_clean_1004_errors`, because
  `freeGamesPromotions` intermittently returns error code 1004 alongside a
  perfectly valid payload and Epic's own launcher ignores it, and `_get_errors`,
  the response-level error check for errors served with an HTTP 200. As in the
  library, only recognised errors (missing `serviceResponse`, or an `errorCode`
  ending in `not_found`) are fatal; anything else is logged and tolerated so a
  stray error never costs us a notification.

_______________________________________________________________________________

## [0.1.0] - YYYY-MM-DD

This is the initial version of the project.

### Added

- The base project

[CHANGELOG.md]: https://keepachangelog.com/en/1.1.0/
[Semantic Versioning]: http://semver.org/

<!-- markdownlint-configure-file {
    "MD022": false,
    "MD024": false,
    "MD030": false,
    "MD032": false
} -->
<!--
    MD022: Blanks around headings
    MD024: No duplicate headings
    MD030: Spaces after list markers
    MD032: Blanks around lists
-->
