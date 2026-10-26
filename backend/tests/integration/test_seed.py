"""Integration tests for the development seed."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app import seed
from app.config import Settings
from app.db import get_session_factory
from app.models.bookings import Booking
from app.models.sessions import Session
from app.models.users import User
from app.services.auth import authenticate_user, hash_password
from app.services.bookings import waitlist_position
from tests.conftest import requires_postgres

pytestmark = requires_postgres


def _settings(db_url: str) -> Settings:
    return Settings(
        app_env="test",
        app_version="test-version",
        database_url=db_url,
        session_secret="x" * 40,
    )


def test_seed_creates_the_documented_demo_rows(db_url: str) -> None:
    result = seed.run(_settings(db_url))

    assert (result.users, result.sessions, result.bookings) == (3, 3, 3)

    with get_session_factory(db_url)() as db:
        emails = set(db.scalars(select(User.email)).all())
        assert emails == {
            "host@example.com",
            "guest-a@example.com",
            "guest-b@example.com",
        }

        # Seeded identifiers are stable across machines and runs.
        assert db.get(User, seed.seed_id("user", "host")) is not None
        assert db.get(User, seed.seed_id("user", "guest-a")) is not None
        assert db.get(User, seed.seed_id("user", "guest-b")) is not None

        now = datetime.now(UTC)
        for session in db.scalars(select(Session)).all():
            assert session.starts_at > now, session.title

        open_id = seed.seed_id("session", "open")
        open_session = db.get(Session, open_id)
        assert open_session is not None
        assert open_session.status == "scheduled"
        assert (
            db.scalar(select(func.count(Booking.id)).where(Booking.session_id == open_id)) == 0
        )

        full_id = seed.seed_id("session", "full")
        confirmed = db.scalar(
            select(Booking).where(
                Booking.session_id == full_id,
                Booking.status == "confirmed",
            ),
        )
        assert confirmed is not None
        assert confirmed.user_id == seed.seed_id("user", "guest-a")

        waiter = db.scalar(
            select(Booking).where(
                Booking.session_id == full_id,
                Booking.status == "waitlisted",
            ),
        )
        assert waiter is not None
        assert waiter.user_id == seed.seed_id("user", "guest-b")
        assert waitlist_position(db, waiter) == 1

        cancelled_session = db.get(Session, seed.seed_id("session", "cancelled"))
        assert cancelled_session is not None
        assert cancelled_session.status == "cancelled"

        # The documented development password works, and it is stored hashed.
        host = authenticate_user(
            db,
            email="host@example.com",
            password=seed.SEED_PASSWORD,
        )
        assert host is not None
        assert authenticate_user(db, email="host@example.com", password="wrong") is None


def test_seed_is_idempotent(db_url: str) -> None:
    seed.run(_settings(db_url))

    def snapshot() -> set[tuple[str, uuid.UUID]]:
        with get_session_factory(db_url)() as db:
            rows: set[tuple[str, uuid.UUID]] = set()
            rows.update(("user", user_id) for user_id in db.scalars(select(User.id)))
            rows.update(("session", session_id) for session_id in db.scalars(select(Session.id)))
            rows.update(("booking", booking_id) for booking_id in db.scalars(select(Booking.id)))
        return rows

    first = snapshot()
    seed.run(_settings(db_url))
    second = snapshot()

    assert second == first
    with get_session_factory(db_url)() as db:
        assert db.scalar(select(func.count(User.id))) == 3
        assert db.scalar(select(func.count(Session.id))) == 3
        assert db.scalar(select(func.count(Booking.id))) == 3


def test_seed_reset_removes_only_seeded_rows(db_url: str) -> None:
    seed.run(_settings(db_url))

    outsider_id = uuid.uuid4()
    outsider_session_id = uuid.uuid4()
    with get_session_factory(db_url)() as db:
        db.add(
            User(
                id=outsider_id,
                email="someone@example.com",
                password_hash=hash_password("password123"),
                display_name="Someone",
            ),
        )
        # No relationship() maps these classes, so flush the host first.
        db.flush()
        db.add(
            Session(
                id=outsider_session_id,
                host_id=outsider_id,
                title="Someone else's session",
                description="",
                starts_at=datetime.now(UTC) + timedelta(days=2),
                duration_minutes=60,
                capacity=2,
                location="Studio Z",
                status="scheduled",
            ),
        )
        db.commit()

    result = seed.run(_settings(db_url), reset=True)

    # Three sessions, three users, and three bookings are seeded.
    assert result.removed == 9

    with get_session_factory(db_url)() as db:
        assert db.get(User, outsider_id) is not None
        assert db.get(Session, outsider_session_id) is not None
        assert db.scalar(select(func.count(User.id))) == 4
        assert db.scalar(select(func.count(Session.id))) == 4
        assert db.scalar(select(func.count(Booking.id))) == 3


def test_seed_refuses_to_run_in_production(
    db_url: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    production = Settings(
        app_env="production",
        app_version="test-version",
        database_url=db_url,
        session_secret="z" * 40,
    )
    monkeypatch.setattr(seed, "get_settings", lambda: production)

    assert seed.main([]) == 1

    assert "Refusing to seed" in capsys.readouterr().err
    with get_session_factory(db_url)() as db:
        assert db.scalar(select(func.count(User.id))) == 0


def test_seed_refuses_to_overwrite_a_non_seeded_account(db_url: str) -> None:
    stranger_id = uuid.uuid4()
    with get_session_factory(db_url)() as db:
        db.add(
            User(
                id=stranger_id,
                email="host@example.com",
                password_hash=hash_password("password123"),
                display_name="Real Person",
            ),
        )
        db.commit()

    with pytest.raises(RuntimeError, match="host@example.com"):
        seed.run(_settings(db_url))

    with get_session_factory(db_url)() as db:
        kept = db.scalar(select(User).where(User.email == "host@example.com"))
        assert kept is not None
        assert kept.id == stranger_id
        assert kept.display_name == "Real Person"
        assert db.scalar(select(func.count(User.id))) == 1
