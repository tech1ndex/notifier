from pydantic_settings import BaseSettings


class EpicSettings(BaseSettings):
    country: str = "CA"

class SignalBotSettings(BaseSettings):
    signal_api_url: str = "http://localhost:8080"
    signal_phone: str = ""
    signal_group_id: str = ""
    update_interval: float = "3600"
    one_time_run: bool = False
