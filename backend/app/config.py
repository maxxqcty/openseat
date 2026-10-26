"""Application settings loaded from the environment."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Values come from process environment variables first, then from a local
    `.env` file. `SESSION_SECRET` is mandatory outside tests and must be at
    least 32 characters long.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    app_version: str = "dev"
    database_url: str | None = None

    session_secret: str = ""
    session_cookie_name: str = "openseat_session"
    session_ttl_hours: int = 8
    session_cookie_secure: bool = False

    @model_validator(mode="after")
    def validate_session_secret(self) -> Settings:
        if self.app_env != "test" and len(self.session_secret) < 32:
            msg = "SESSION_SECRET is required and must be at least 32 characters long"
            raise ValueError(msg)
        return self

    @property
    def cookie_secure(self) -> bool:
        """Send the session cookie over HTTPS in production."""
        return self.session_cookie_secure or self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
