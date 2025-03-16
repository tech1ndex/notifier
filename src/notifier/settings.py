from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    country: str = "CA"
