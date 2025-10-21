import concurrent.futures
import sys
import time

import requests
import tenacity

from notifier.bot.signal import SignalBot
from notifier.external.epic import EpicFreeGames
from notifier.logger.setup import setup_logger
from notifier.settings import EpicSettings, SignalBotSettings
from notifier.storage import SentGamesStorage


def send_with_retry(bot, group_id, message, timeout: float | None = None, max_attempts: int = 5):
    attempt = 0
    wait = 2.0
    deadline = time.time() + timeout if timeout is not None else None
    while True:
        try:
            result = bot.send_group_message(group_id=group_id, message=message)
            if result is None:
                attempt += 1
                if attempt >= max_attempts:
                    raise tenacity.RetryError(f"Exceeded {max_attempts} attempts")
                if deadline is not None:
                    time_left = deadline - time.time()
                    if time_left <= 0:
                        raise TimeoutError("send_with_retry timed out")
                    sleep = min(wait, time_left)
                else:
                    sleep = wait
                time.sleep(sleep)
                wait = min(wait * 2, 30)
                continue
            return result
        except requests.exceptions.RequestException:
            attempt += 1
            if attempt >= max_attempts:
                raise tenacity.RetryError(f"Exceeded {max_attempts} attempts")
            if deadline is not None:
                time_left = deadline - time.time()
                if time_left <= 0:
                    raise TimeoutError("send_with_retry timed out")
                sleep = min(wait, time_left)
            else:
                sleep = wait
            time.sleep(sleep)
            wait = min(wait * 2, 30)


def send_with_timeout(bot, group_id, message, timeout: int) -> bool:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(send_with_retry, bot, group_id, message, timeout)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return False


def main():
    logger = setup_logger()
    signal_settings = SignalBotSettings()
    bot = SignalBot(signal_settings.signal_api_url, signal_settings.signal_phone)
    storage = SentGamesStorage()
    logger.info(f"Bot initialized for {signal_settings.signal_phone}")

    group_id = signal_settings.signal_group_id
    epic_settings = EpicSettings()
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
                    sent = send_with_timeout(
                        bot,
                        group_id,
                        message,
                        signal_settings.send_timeout_seconds,
                    )
                    if sent:
                        storage.mark_game_sent(game.game_url)
                    else:
                        storage.mark_game_failed(game.game_url)
                        logger.error(f"Timeout sending message for {game.game_url}")
                except (requests.exceptions.RequestException, ConnectionError, TimeoutError) as e:
                    storage.mark_game_failed(game.game_url)
                    logger.error(f"Failed to send message after retries: {e}")

            if signal_settings.one_time_run:
                logger.info("One-time run completed. Exiting.")
                sys.exit(0)

            time.sleep(signal_settings.update_interval)
    except KeyboardInterrupt:
        logger.info("\nBot stopped by user")


if __name__ == "__main__":
    main()
