import sys
import time
import concurrent.futures
import tenacity

from src.notifier.bot.signal import SignalBot
from src.notifier.external.epic import EpicFreeGames
from src.notifier.logger.setup import setup_logger
from src.notifier.settings import EpicSettings, SignalBotSettings
from src.notifier.storage import SentGamesStorage

@tenacity.retry(
    stop=tenacity.stop_after_attempt(5),
    wait=tenacity.wait_exponential(multiplier=2, min=2, max=30),
    retry=tenacity.retry_if_result(lambda result: result is None),
    reraise=True
)
def send_with_retry(bot, group_id, message):
    return bot.send_group_message(group_id=group_id, message=message)

def send_with_timeout(bot, group_id, message, timeout: int) -> bool:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(send_with_retry, bot, group_id, message)
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
                if state == "sent" or state == "pending":
                    continue
                message = f"* {game.game_title} {game.game_price} is FREE now --> {game.game_url}"
                storage.mark_game_pending(game.game_url)
                try:
                    sent = send_with_timeout(bot, group_id, message, signal_settings.send_timeout_seconds)
                    if sent:
                        storage.mark_game_sent(game.game_url)
                    else:
                        storage.mark_game_failed(game.game_url)
                        logger.error(f"Timeout sending message for {game.game_url}")
                except Exception as e:
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