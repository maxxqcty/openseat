"""Integration tests for race-safe booking against PostgreSQL."""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import get_engine, get_session_factory
from app.models.bookings import Booking
from app.models.sessions import Session
from app.services.bookings import book_session
from tests.conftest import requires_postgres
from tests.integration.helpers import (
    CSRF_HEADERS,
    book,
    create_session,
    logout,
    register,
)

pytestmark = requires_postgres

OVERBOOKED_QUERY = text(
    """
    SELECT s.id
    FROM sessions s
    JOIN bookings b ON b.session_id = s.id
    WHERE b.status IN ('confirmed', 'checked_in')
    GROUP BY s.id, s.capacity
    HAVING count(*) > s.capacity
    """,
)


def _overbooked(db_url: str) -> list[str]:
    engine = get_engine(db_url)
    with engine.connect() as connection:
        return [str(row[0]) for row in connection.execute(OVERBOOKED_QUERY)]


def _start_session(client: TestClient, *, capacity: int) -> dict[str, Any]:
    host = register(client, email="booking-host@example.com")
    created = create_session(client, capacity=capacity)
    assert created["host_id"] == host["id"]
    return created


def test_first_booking_is_confirmed(client: TestClient) -> None:
    created = _start_session(client, capacity=1)

    register(client, email="guest-one@example.com", display_name="Guest One")
    response = book(client, str(created["id"]))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["waitlist_position"] is None
    assert body["session_id"] == created["id"]


def test_full_session_returns_waitlisted_position(client: TestClient) -> None:
    created = _start_session(client, capacity=1)

    register(client, email="guest-one@example.com")
    assert book(client, str(created["id"])).json()["status"] == "confirmed"

    register(client, email="guest-two@example.com")
    response = book(client, str(created["id"]))

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "waitlisted"
    assert body["waitlist_position"] == 1


def test_capacity_boundary_last_seat_confirmed_next_waitlisted(
    client: TestClient,
    db_url: str,
) -> None:
    created = _start_session(client, capacity=2)
    session_id = str(created["id"])

    for email in ("one@example.com", "two@example.com"):
        register(client, email=email)
        assert book(client, session_id).json()["status"] == "confirmed"

    register(client, email="three@example.com")
    third = book(client, session_id)

    assert third.status_code == 201
    assert third.json()["status"] == "waitlisted"
    assert third.json()["waitlist_position"] == 1
    assert _overbooked(db_url) == []


def test_duplicate_active_booking_returns_booking_conflict(client: TestClient) -> None:
    created = _start_session(client, capacity=2)

    register(client, email="duplicate@example.com")
    assert book(client, str(created["id"])).status_code == 201
    second = book(client, str(created["id"]))

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "booking_conflict"


def test_booking_unknown_session_returns_404(client: TestClient) -> None:
    register(client, email="nobody@example.com")

    response = book(client, str(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_booking_ended_session_returns_409(client: TestClient, db_url: str) -> None:
    created = _start_session(client, capacity=1)

    with get_session_factory(db_url)() as db:
        target = db.get(Session, uuid.UUID(str(created["id"])))
        assert target is not None
        target.starts_at = datetime.now(UTC) - timedelta(hours=2)
        db.commit()

    register(client, email="late@example.com")
    response = book(client, str(created["id"]))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_checked_in_booking_still_occupies_a_seat(client: TestClient, db_url: str) -> None:
    created = _start_session(client, capacity=1)
    guest = register(client, email="checked-in@example.com")

    with get_session_factory(db_url)() as db:
        db.add(
            Booking(
                session_id=uuid.UUID(str(created["id"])),
                user_id=uuid.UUID(str(guest["id"])),
                status="checked_in",
                created_at=datetime.now(UTC),
                checked_in_at=datetime.now(UTC),
            ),
        )
        db.commit()

    register(client, email="hopeful@example.com")
    response = book(client, str(created["id"]))

    assert response.status_code == 201
    assert response.json()["status"] == "waitlisted"


def test_concurrent_last_seat_serialises_to_one_confirmed_and_one_waitlisted(
    client: TestClient,
    db_url: str,
) -> None:
    created = _start_session(client, capacity=1)
    session_id = uuid.UUID(str(created["id"]))

    first = register(client, email="racer-one@example.com")
    logout(client)
    second = register(client, email="racer-two@example.com")
    logout(client)

    barrier = threading.Barrier(2)
    results: list[tuple[str, int | None]] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker(user_id: str) -> None:
        factory = get_session_factory(db_url)
        db = factory()
        try:
            barrier.wait(timeout=10)
            booking, position = book_session(
                db,
                session_id=session_id,
                user_id=uuid.UUID(user_id),
            )
            with lock:
                results.append((booking.status, position))
        except BaseException as exc:  # noqa: BLE001 - surfaced in the assertion below
            with lock:
                errors.append(exc)
        finally:
            db.close()

    threads = [
        threading.Thread(target=worker, args=(str(first["id"]),)),
        threading.Thread(target=worker, args=(str(second["id"]),)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert not errors
    assert len(results) == 2
    assert sorted(status for status, _ in results) == ["confirmed", "waitlisted"]
    waitlisted_positions = [position for status, position in results if status == "waitlisted"]
    assert waitlisted_positions == [1]
    assert _overbooked(db_url) == []


def test_invariant_query_detects_no_overbooking_after_bookings(
    client: TestClient,
    db_url: str,
) -> None:
    created = _start_session(client, capacity=3)
    session_id = str(created["id"])

    for index in range(5):
        register(client, email=f"invariant-{index}@example.com")
        book(client, session_id)

    assert _overbooked(db_url) == []

    with get_session_factory(db_url)() as db:
        confirmed = db.execute(
            text(
                "SELECT count(*) FROM bookings WHERE session_id = :session_id "
                "AND status IN ('confirmed', 'checked_in')",
            ),
            {"session_id": uuid.UUID(session_id)},
        ).scalar_one()
    assert confirmed == 3


def test_booking_requires_authentication(client: TestClient) -> None:
    register(client, email="auth-host@example.com")
    created = create_session(client, capacity=1)
    logout(client)

    response = client.post(
        f"/api/sessions/{created['id']}/bookings",
        headers=CSRF_HEADERS,
    )

    assert response.status_code == 401


def test_duplicate_waitlisted_booking_is_rejected(client: TestClient) -> None:
    created = _start_session(client, capacity=1)
    session_id = str(created["id"])

    register(client, email="seat@example.com")
    assert book(client, session_id).json()["status"] == "confirmed"

    register(client, email="waiter@example.com")
    assert book(client, session_id).json()["status"] == "waitlisted"
    duplicate = book(client, session_id)

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "booking_conflict"
