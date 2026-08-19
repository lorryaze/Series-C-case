"""Application settings, loaded from the environment via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the internal tools platform."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Internal Tools Platform"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = True

    database_url: str = "sqlite:///./internal_tools.db"
    sql_echo: bool = False

    jwt_secret_key: str = Field(
        default="change-me-in-production",
        description="HMAC key used to sign access tokens.",
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 12 * 60

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ]

    reporting_currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="Currency the dashboard aggregates are reported in.",
    )

    demo_user_password: str = "demo123"

    login_rate_limit_attempts: int = Field(
        default=10,
        ge=1,
        description="Failed login attempts allowed per client within the window.",
    )
    login_rate_limit_window_seconds: int = Field(
        default=300,
        ge=1,
        description="Rolling window used to count failed login attempts.",
    )
    refresh_token_expire_minutes: int = 7 * 24 * 60


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
