import logging
import sys
import time

from bot.signal import SignalBot
from external.epic import EpicFreeGames
from logger.setup import setup_logger
from settings import EpicSettings, SignalBotSettings
from storage import SentGamesStorage


def main():
    setup_logger()
    signal_settings = SignalBotSettings()
    bot = SignalBot(signal_settings.signal_api_url, signal_settings.signal_phone)
    storage = SentGamesStorage()
    logging.info(f"Bot initialized with phone number {signal_settings.signal_phone}")

    group_id = signal_settings.signal_group_id
    epic_settings = EpicSettings()
    epic = EpicFreeGames(epic_settings)

    try:
        while True:
            games = epic.format_games_info()
            for game in games:
                if not storage.is_game_sent(game["store_url"]):
                    message = f"New free game - {game['name']} - {game['store_url']}"
                    if bot.send_group_message(group_id=group_id, message=message):
                        storage.mark_game_sent(game["store_url"])

            if signal_settings.one_time_run:
                logging.info("One-time run completed. Exiting.")
                sys.exit(0)

            time.sleep(signal_settings.update_interval)
    except KeyboardInterrupt:
        logging.info("\nBot stopped by user")

if __name__ == "__main__":
    main()
