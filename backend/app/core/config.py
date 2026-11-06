from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Python Recall API"
    app_service: str = "python-recall-backend"
    app_version: str = "0.1.0"
    app_env: Literal["development", "test", "production"] = "development"
    app_debug: bool = False
    app_timezone: str = "UTC"
    app_new_cards_per_day: int = Field(default=20, ge=1, le=100)
    api_v1_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+psycopg://python_recall:python_recall@localhost:5433/python_recall"
    )

    @field_validator("app_timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        """Require a valid IANA timezone name."""
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("app_timezone must be a valid IANA timezone") from error
        return value

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        """Keep route composition predictable."""
        if not value.startswith("/") or value.endswith("/"):
            raise ValueError(
                "api_v1_prefix must start with '/' and have no trailing '/'"
            )
        return value


@lru_cache
def get_settings() -> Settings:
    """Return one immutable-by-convention settings instance per process."""
    return Settings()
