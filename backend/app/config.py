"""Application settings loaded from the environment."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
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
    app_version: str = ""
    database_url: str | None = None

    session_secret: str = ""
    session_cookie_name: str = "openseat_session"
    session_ttl_hours: int = 8
    session_cookie_secure: bool | None = None

    @field_validator("database_url", mode="after")
    @classmethod
    def normalize_database_url(cls, value: str | None) -> str | None:
        """Accept the libpq form ``postgres://`` used by hosted providers.

        Render and other platforms expose a ``postgres://`` (or
        ``postgresql://``) connection string; SQLAlchemy needs an explicit
        dialect, so add the psycopg driver before the first connect.
        """
        if value is None:
            return None
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix) :]
        return value

    @model_validator(mode="after")
    def validate_session_secret(self) -> Settings:
        if self.app_env != "test" and len(self.session_secret) < 32:
            msg = "SESSION_SECRET is required and must be at least 32 characters long"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def default_app_version(self) -> Settings:
        """Use the deployed commit when the platform does not set APP_VERSION."""
        if not self.app_version:
            self.app_version = os.environ.get("RENDER_GIT_COMMIT", "dev")
        return self

    @property
    def cookie_secure(self) -> bool:
        """Send the session cookie over HTTPS, unless explicitly overridden."""
        if self.session_cookie_secure is not None:
            return self.session_cookie_secure
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
