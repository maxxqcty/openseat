"""Integration tests proving every test starts from an empty database."""

from __future__ import annotations

import uuid

from sqlalchemy import create_engine, text

from tests.conftest import TABLES, requires_postgres, reset_database

pytestmark = requires_postgres


def _counts(database_url: str) -> dict[str, int]:
    engine = create_engine(database_url)
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for table in TABLES:
            counts[table] = connection.execute(
                text(f"SELECT count(*) FROM {table}"),
            ).scalar_one()
    engine.dispose()
    return counts


def _empty_counts() -> dict[str, int]:
    return {table: 0 for table in TABLES}


def test_integration_tests_start_from_clean_tables(db_url: str) -> None:
    assert _counts(db_url) == _empty_counts()


def test_reset_database_clears_rows_written_by_a_test(db_url: str) -> None:
    engine = create_engine(db_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, email, password_hash, display_name) "
                "VALUES (:id, :email, 'unused-hash', 'Temporary Guest')",
            ),
            {"id": uuid.uuid4(), "email": f"{uuid.uuid4().hex}@example.com"},
        )
    engine.dispose()

    assert _counts(db_url)["users"] == 1

    reset_database(db_url)

    assert _counts(db_url) == _empty_counts()
