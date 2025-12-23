from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

from requests.exceptions import HTTPError, ConnectionError, Timeout
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from notifier.bot.signal import SignalBot
from notifier.external.epic import EpicFreeGames
from notifier.logger.setup import setup_logger
from notifier.settings import EpicSettings, SignalBotSettings
from notifier.storage import SentGamesStorage

logger = setup_logger()


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type((HTTPError, ConnectionError, Timeout)),
    reraise=True,
)
def send_message(bot: SignalBot, group_id: str, message: str) -> dict | None:
    return bot.send_group_message(group_id=group_id, message=message)


def get_storage_path(settings: EpicSettings) -> str:
    default_path = settings.sent_games_file_path

    # When running under pytest, use an isolated temp file to avoid interference
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return str(
            Path(tempfile.gettempdir())
            / f".notifier_sent_games_test_{os.getpid()}.json",
        )
    if default_path == "sent_games.json":
        return str(Path.home() / ".notifier_sent_games.json")
    return default_path


def main():
    signal_settings = SignalBotSettings()
    bot = SignalBot(signal_settings.signal_api_url, signal_settings.signal_phone)
    
    epic_settings = EpicSettings()
    storage_path = get_storage_path(epic_settings)
    storage = SentGamesStorage(storage_path)
    
    logger.info(f"Bot initialized for {signal_settings.signal_phone}")

    group_id = signal_settings.signal_group_id
    epic = EpicFreeGames(epic_settings)

    try:
        while True:
            for game in epic.format_free_games():
                state = storage.get_game_state(game.game_url)
                if state in {"sent", "pending"}:
                    continue
                message = f"* {game.game_title} {game.game_price} is FREE now --> {game.game_url}"
                storage.mark_game_pending(game.game_url)
                try:
                    send_message(bot, group_id, message)
                    storage.mark_game_sent(game.game_url)
                except Exception as e:
                    storage.mark_game_failed(game.game_url)
                    logger.error(f"Failed to send message for {game.game_url}: {e}")

            if signal_settings.one_time_run:
                logger.info("One-time run completed. Exiting.")
                sys.exit(0)

            time.sleep(signal_settings.update_interval)
    except KeyboardInterrupt:
        logger.info("\nBot stopped by user")


if __name__ == "__main__":
    main()
