"""migrations env.py"""

import os
import sys
from pathlib import Path

# Ensure the backend app is importable
_backend_app = Path(__file__).parent.parent / "app"
if str(_backend_app) not in sys.path:
    sys.path.insert(0, str(_backend_app))

# Import the Base from the application models so autogenerate can detect metadata
from models.base import Base  # type: ignore

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL (no Engine is created).
    By skipping the Engine creation we don't even need a DB to be configured.
    Calls to context.execute() emit the given string to the script output.

    URL objects are supported too, provided they are compatible with
    `sqlalchemy.engine.URL`.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable is required for offline migrations")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this mode we need to create an Engine and associate a connection with
    the migration context.
    """
    configuration = context.get_configuration()
    # Override the sqlalchemy.url from the env variable
    configuration["sqlalchemy"].pop("sqlalchemy.url", None)
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable is required for online migrations")

    connectable = engine_from_config(
        {"sqlalchemy": {}},
        prefix="sqlalchemy.",
        url=url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            # Enable citext extension on the database
            from sqlalchemy import text as sa_text
            connection.execute(sa_text("CREATE EXTENSION IF NOT EXISTS citext"))
            context.run_migrations()