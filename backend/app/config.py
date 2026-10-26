"""Application settings loaded from the environment."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration.

    Values come from process environment variables first, then from a local
    `.env` file. Defaults keep the skeleton runnable without configuration.
    """

    model_config = {"env_file": (".env", "../.env"), "env_file_encoding": "utf-8", "extra": "ignore"}

    app_env: str = "development"
    app_version: str = "dev"
    database_url: str | None = None

    # Argon2 settings
    argon2_time_cost: int = 15
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 2

    # Session settings
    session_secret: str = ""
    session_cookie_secure: bool = False


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()


def get_db_session():
    """Dependency-injected database session generator.

    Yields a SQLAlchemy Session object that is automatically closed
    after the requesting context ends.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(
        get_settings().database_url or "sqlite:///./test.db",
        pool_pre_ping=True,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()