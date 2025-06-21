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
    logging.info("Bot initialized for %s", signal_settings.signal_phone)

    group_id = signal_settings.signal_group_id
    epic_settings = EpicSettings()
    epic = EpicFreeGames(epic_settings)

    try:
        while True:
            for game in epic.format_free_games():
                """
                if not storage.is_game_sent(game['game_url']):
                    message = (f"* {game.game_title} {game.game_price} is FREE now, "
                           f"--> {game.game_url}")
                    if bot.send_group_message(group_id=group_id, message=message):
                        storage.mark_game_sent(game['game_url'])
                """
                message = (f"* {game.game_title} {game.game_price} is FREE now, "
                           f"--> {game.game_url}")
                logging.info(message)

            if signal_settings.one_time_run:
                logging.info("One-time run completed. Exiting.")
                sys.exit(0)

            time.sleep(signal_settings.update_interval)
    except KeyboardInterrupt:
        logging.info("\nBot stopped by user")

if __name__ == "__main__":
    main()
