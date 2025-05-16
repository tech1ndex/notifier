from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    external_store: str = "epic"

class EpicSettings(BaseSettings):
    country: str = "CA"
    sent_games_file_path: str = "sent_games.json"

class UnifiStoreSettings(BaseSettings):
    base_url: str = "https://ca.store.ui.com/ca/en"
    model: str = "ucg-max-ns"


class SignalBotSettings(BaseSettings):
    signal_api_url: str = "http://localhost:8080"
    signal_phone: str = ""
    signal_group_id: str = ""
    update_interval: float = 3600.0
    one_time_run: bool = False
