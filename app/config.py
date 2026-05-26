from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_base_url: str = "http://127.0.0.1:8000"
    database_url: str = "sqlite+aiosqlite:///./data/echo.db"

    encryption_key: str = Field(default="", alias="ECHO_ENCRYPTION_KEY")

    telegram_bot_token: str = ""
    telegram_channel_id: str = ""

    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = "http://127.0.0.1:8000/oauth/linkedin/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
