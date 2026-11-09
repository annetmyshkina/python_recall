from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit
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
    ai_enabled: bool = False
    ai_provider: Literal["ollama"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    ai_timeout_seconds: float = Field(default=120.0, ge=1.0, le=300.0)
    ai_keep_alive: str = Field(default="5m", min_length=1, max_length=20)
    ai_max_output_tokens: int = Field(default=1024, ge=64, le=8192)
    ai_max_response_bytes: int = Field(
        default=1024 * 1024,
        ge=1024,
        le=10 * 1024 * 1024,
    )
    ai_temperature: float = Field(default=0.0, ge=0.0, le=2.0)

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

    @field_validator("ollama_base_url")
    @classmethod
    def validate_ollama_base_url(cls, value: str) -> str:
        """Accept an HTTP origin and normalize its trailing slash."""
        normalized = value.strip().rstrip("/")
        parsed = urlsplit(normalized)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("ollama_base_url must be an HTTP(S) origin")
        return normalized

    @field_validator("ollama_model")
    @classmethod
    def validate_ollama_model(cls, value: str) -> str:
        """Reject an empty model name before the application starts."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("ollama_model must not be empty")
        if len(normalized) > 200:
            raise ValueError("ollama_model must contain at most 200 characters")
        return normalized


@lru_cache
def get_settings() -> Settings:
    """Return one immutable-by-convention settings instance per process."""
    return Settings()
