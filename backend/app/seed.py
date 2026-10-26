"""Seed a realistic demo dataset for local development.

Run it with ``uv run python -m app.seed`` or ``make seed``. The seed is
idempotent: running it twice updates the same rows instead of duplicating them,
and ``--reset`` deletes only the seeded rows before recreating them. Session
start times are recomputed from the current clock on every run, so the demo
never goes stale.

Seeding is development-only. The module refuses to run when ``APP_ENV`` is
``production``, and nothing in the application calls it automatically.

Demo accounts share the development password ``openseat-dev-password``. They
use example.com addresses and placeholder names; no real personal data and no
production credentials appear in this file.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.config import Settings, get_settings
from app.db import get_session_factory
from app.models.bookings import STATUS_CANCELLED as BOOKING_CANCELLED
from app.models.bookings import STATUS_CONFIRMED, STATUS_WAITLISTED, Booking
from app.models.sessions import STATUS_CANCELLED, STATUS_SCHEDULED, Session
from app.models.users import User
from app.services.auth import hash_password

BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Fixed namespace so the seeded identifiers are stable across machines and runs.
SEED_NAMESPACE = uuid.UUID("5f2b1c44-6f3a-5e5b-9a6d-0c1d2e3f4a5b")

# Development-only password shared by every seeded account.
SEED_PASSWORD = "openseat-dev-password"


def seed_id(kind: str, key: str) -> uuid.UUID:
    """Return the deterministic identifier for one seeded row."""
    return uuid.uuid5(SEED_NAMESPACE, f"openseat:seed:{kind}:{key}")


@dataclass(frozen=True)
class SeedUser:
    key: str
    email: str
    display_name: str


@dataclass(frozen=True)
class SeedSession:
    key: str
    title: str
    description: str
    starts_in_days: int
    duration_minutes: int
    capacity: int
    location: str
    status: str


@dataclass(frozen=True)
class SeedBooking:
    key: str
    session_key: str
    user_key: str
    status: str
    created_ago_minutes: int
    cancelled_ago_minutes: int | None = None


SEED_USERS: tuple[SeedUser, ...] = (
    SeedUser("host", "host@example.com", "Demo Host"),
    SeedUser("guest-a", "guest-a@example.com", "Guest A"),
    SeedUser("guest-b", "guest-b@example.com", "Guest B"),
)

SEED_SESSIONS: tuple[SeedSession, ...] = (
    SeedSession(
        key="open",
        title="Intro to Risograph Printing",
        description="A hands-on session covering two-colour separation and "
        "proofing. Bring a flat illustration to print.",
        starts_in_days=7,
        duration_minutes=120,
        capacity=6,
        location="Ink and Press Studio, Room 2",
        status=STATUS_SCHEDULED,
    ),
    SeedSession(
        key="full",
        title="Bookbinding: Coptic Stitch",
        description="Sew a full notebook from start to finish. Materials are "
        "provided and the session is already full.",
        starts_in_days=3,
        duration_minutes=90,
        capacity=1,
        location="Bindery Loft, Bench 4",
        status=STATUS_SCHEDULED,
    ),
    SeedSession(
        key="cancelled",
        title="Screen Printing Clinic",
        description="A clinic that was called off, kept here so the demo shows "
        "a cancelled session in the history.",
        starts_in_days=10,
        duration_minutes=60,
        capacity=4,
        location="Textile Workshop",
        status=STATUS_CANCELLED,
    ),
)

# guest-a holds the only seat of the full session, guest-b waits behind it at
# position 1. The cancelled session keeps a cancelled booking so "my bookings"
# shows history.
SEED_BOOKINGS: tuple[SeedBooking, ...] = (
    SeedBooking(
        key="full-seat",
        session_key="full",
        user_key="guest-a",
        status=STATUS_CONFIRMED,
        created_ago_minutes=600,
    ),
    SeedBooking(
        key="full-waitlist",
        session_key="full",
        user_key="guest-b",
        status=STATUS_WAITLISTED,
        created_ago_minutes=540,
    ),
    SeedBooking(
        key="cancelled-guest-a",
        session_key="cancelled",
        user_key="guest-a",
        status=BOOKING_CANCELLED,
        created_ago_minutes=1440,
        cancelled_ago_minutes=720,
    ),
)


@dataclass(frozen=True)
class SeedResult:
    users: int
    sessions: int
    bookings: int
    removed: int


def _values(primary_key: uuid.UUID, fields: dict[str, Any]) -> dict[str, Any]:
    return {"id": primary_key, **fields}


def _upsert(db: DbSession, table: Any, values: dict[str, Any]) -> None:
    """Insert or refresh one row, keyed on its deterministic id."""
    statement = (
        pg_insert(table)
        .values(**values)
        .on_conflict_do_update(
            index_elements=[table.c.id.name],
            set_={key: value for key, value in values.items() if key != "id"},
        )
    )
    db.execute(statement)


def delete_seeded(db: DbSession) -> int:
    """Remove only the seeded rows, in FK-safe order. Returns rows removed."""
    booking_ids = [seed_id("booking", booking.key) for booking in SEED_BOOKINGS]
    session_ids = [seed_id("session", session.key) for session in SEED_SESSIONS]
    user_ids = [seed_id("user", user.key) for user in SEED_USERS]

    # Bookings reference sessions, sessions reference users: delete in that order.
    grouped = ((Booking, booking_ids), (Session, session_ids), (User, user_ids))
    removed = 0
    for model, identifiers in grouped:
        count = db.scalar(select(func.count(model.id)).where(model.id.in_(identifiers)))
        removed += int(count or 0)
        db.execute(delete(model).where(model.id.in_(identifiers)))
    return removed


def seed_database(db: DbSession, *, now: datetime | None = None) -> SeedResult:
    """Create or refresh the seeded rows. Safe to call repeatedly."""
    current = now or datetime.now(UTC)
    password_hash = hash_password(SEED_PASSWORD)

    for user in SEED_USERS:
        _upsert(
            db,
            User.__table__,
            _values(
                seed_id("user", user.key),
                {
                    "email": user.email,
                    "password_hash": password_hash,
                    "display_name": user.display_name,
                    "created_at": current - timedelta(days=30),
                },
            ),
        )

    for session in SEED_SESSIONS:
        _upsert(
            db,
            Session.__table__,
            _values(
                seed_id("session", session.key),
                {
                    "host_id": seed_id("user", "host"),
                    "title": session.title,
                    "description": session.description,
                    # Recomputed each run so the demo never drifts into the past.
                    "starts_at": current + timedelta(days=session.starts_in_days),
                    "duration_minutes": session.duration_minutes,
                    "capacity": session.capacity,
                    "location": session.location,
                    "status": session.status,
                    "created_at": current - timedelta(days=7),
                },
            ),
        )

    for booking in SEED_BOOKINGS:
        cancelled_at = (
            current - timedelta(minutes=booking.cancelled_ago_minutes)
            if booking.cancelled_ago_minutes is not None
            else None
        )
        _upsert(
            db,
            Booking.__table__,
            _values(
                seed_id("booking", booking.key),
                {
                    "session_id": seed_id("session", booking.session_key),
                    "user_id": seed_id("user", booking.user_key),
                    "status": booking.status,
                    "created_at": current - timedelta(minutes=booking.created_ago_minutes),
                    "promoted_at": None,
                    "checked_in_at": None,
                    "cancelled_at": cancelled_at,
                },
            ),
        )

    db.commit()

    return SeedResult(
        users=len(SEED_USERS),
        sessions=len(SEED_SESSIONS),
        bookings=len(SEED_BOOKINGS),
        removed=0,
    )


def _upgrade_schema(database_url: str) -> None:
    """Bring the schema to head so seeding works on a fresh database."""
    from alembic import command
    from alembic.config import Config

    os.environ.setdefault("DATABASE_URL", database_url)
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    command.upgrade(config, "head")


def _assert_not_seeded_elsewhere(db: DbSession) -> None:
    """Fail clearly when a seeded email belongs to a row we must not touch."""
    seeded_ids = {seed_id("user", user.key) for user in SEED_USERS}
    for user in SEED_USERS:
        owner = db.scalar(
            select(User.id).where(User.email == user.email),
        )
        if owner is not None and owner not in seeded_ids:
            msg = (
                f"{user.email} already exists with a different id and is not "
                "seeded data; refusing to overwrite it. Use another database "
                "for the demo."
            )
            raise RuntimeError(msg)


def run(settings: Settings, *, reset: bool = False) -> SeedResult:
    """Seed the configured database, optionally resetting seeded rows first."""
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required to seed the database")

    _upgrade_schema(settings.database_url)

    factory = get_session_factory(settings.database_url)
    with factory() as db:
        _assert_not_seeded_elsewhere(db)
        removed = delete_seeded(db) if reset else 0
        db.commit()
        result = seed_database(db)
    return SeedResult(
        users=result.users,
        sessions=result.sessions,
        bookings=result.bookings,
        removed=removed,
    )


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point for ``python -m app.seed``."""
    parser = argparse.ArgumentParser(
        prog="python -m app.seed",
        description="Populate the development database with demo data.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete only the seeded rows before recreating them.",
    )
    arguments = parser.parse_args(argv)

    settings = get_settings()
    if settings.app_env == "production":
        print(
            "Refusing to seed: APP_ENV=production. Seeding is a development-only "
            "operation and is never run automatically.",
            file=sys.stderr,
        )
        return 1

    try:
        result = run(settings, reset=arguments.reset)
    except (RuntimeError, IntegrityError) as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1

    removed = f" (after removing {result.removed} seeded rows)" if arguments.reset else ""
    print(
        f"Seeded {result.users} users, {result.sessions} sessions, and "
        f"{result.bookings} bookings{removed}.",
    )
    print(f"Demo password for every seeded account: {SEED_PASSWORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
