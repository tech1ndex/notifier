from pydantic_settings import BaseSettings


class EpicSettings(BaseSettings):
    country: str = "CA"
    locale: str = "en-US"
    sent_games_file_path: str = "sent_games.json"
    base_url: str = "https://store.epicgames.com/en-US"
    free_games_url: str = (
        "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    )
    store_content_url: str = "https://store-content.ak.epicgames.com/api"
    request_timeout_seconds: float = 15.0
    retry_attempts: int = 5
    retry_wait_min_seconds: float = 1.0
    retry_wait_max_seconds: float = 15.0


class SignalBotSettings(BaseSettings):
    signal_api_url: str = "http://localhost:8080"
    signal_phone: str = ""
    signal_group_id: str = ""
    update_interval: float = 3600.0
    one_time_run: bool = False
    send_timeout_seconds: int = 15
