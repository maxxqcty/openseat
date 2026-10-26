"""Integration tests for guest cancellation and automatic promotion."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.db import get_session_factory
from app.models.bookings import Booking
from app.services import bookings as booking_service
from tests.conftest import requires_postgres
from tests.integration.helpers import (
    CSRF_HEADERS,
    book,
    create_session,
    login,
    logout,
    register,
)

pytestmark = requires_postgres


def _setup(
    client: TestClient,
    *,
    capacity: int = 1,
    waiters: int = 2,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Create a session with one confirmed guest and optional waiters."""
    register(client, email="host@example.com", display_name="Host")
    created = create_session(client, capacity=capacity)
    session_id = str(created["id"])

    register(client, email="confirmed@example.com", display_name="Confirmed Guest")
    confirmed = book(client, session_id).json()
    assert confirmed["status"] == "confirmed"

    waitlist: list[dict[str, Any]] = []
    for index in range(1, waiters + 1):
        register(client, email=f"waiter-{index}@example.com", display_name=f"Waiter {index}")
        body = book(client, session_id).json()
        assert body["status"] == "waitlisted"
        assert body["waitlist_position"] == index
        waitlist.append(body)

    return created, confirmed, waitlist


def _cancel(client: TestClient, booking_id: object) -> object:
    return client.delete(f"/api/bookings/{booking_id}", headers=CSRF_HEADERS)


def test_cancelling_confirmed_booking_promotes_oldest_waiter(
    client: TestClient,
    db_url: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="app.services.bookings")
    created, confirmed, waiters = _setup(client, waiters=2)
    session_id = str(created["id"])

    login(client, email="confirmed@example.com")
    response = _cancel(client, confirmed["id"])

    assert response.status_code == 204
    assert response.content == b""

    with get_session_factory(db_url)() as db:
        cancelled = db.get(Booking, uuid.UUID(str(confirmed["id"])))
        promoted = db.get(Booking, uuid.UUID(str(waiters[0]["id"])))
        remaining = db.get(Booking, uuid.UUID(str(waiters[1]["id"])))
        assert cancelled is not None and cancelled.status == "cancelled"
        assert cancelled.cancelled_at is not None
        assert promoted is not None and promoted.status == "confirmed"
        assert promoted.promoted_at is not None
        assert remaining is not None and remaining.status == "waitlisted"
        assert remaining.promoted_at is None

    detail = client.get(f"/api/sessions/{session_id}").json()
    assert detail["confirmed_count"] == 1
    assert detail["checked_in_count"] == 0
    assert detail["waitlist_count"] == 1

    login(client, email="waiter-1@example.com")
    promoted_booking = client.get(f"/api/sessions/{session_id}").json()["my_booking"]
    assert promoted_booking["status"] == "confirmed"
    assert promoted_booking["waitlist_position"] is None

    login(client, email="waiter-2@example.com")
    assert client.get(f"/api/sessions/{session_id}").json()["my_booking"][
        "waitlist_position"
    ] == 1

    assert any(record.getMessage() == "waitlist_promoted" for record in caplog.records)


def test_cancelling_waitlisted_booking_does_not_promote(
    client: TestClient,
    db_url: str,
) -> None:
    created, confirmed, waiters = _setup(client, waiters=2)
    session_id = str(created["id"])

    login(client, email="waiter-1@example.com")
    assert _cancel(client, waiters[0]["id"]).status_code == 204

    with get_session_factory(db_url)() as db:
        cancelled = db.get(Booking, uuid.UUID(str(waiters[0]["id"])))
        remaining = db.get(Booking, uuid.UUID(str(waiters[1]["id"])))
        seat_holder = db.get(Booking, uuid.UUID(str(confirmed["id"])))
        assert cancelled is not None and cancelled.status == "cancelled"
        assert cancelled.cancelled_at is not None
        assert remaining is not None and remaining.status == "waitlisted"
        assert remaining.promoted_at is None
        assert seat_holder is not None and seat_holder.status == "confirmed"

    detail = client.get(f"/api/sessions/{session_id}").json()
    assert detail["confirmed_count"] == 1
    assert detail["waitlist_count"] == 1

    login(client, email="waiter-2@example.com")
    assert client.get(f"/api/sessions/{session_id}").json()["my_booking"][
        "waitlist_position"
    ] == 1


def test_double_cancellation_is_idempotent_and_promotes_once(
    client: TestClient,
    db_url: str,
) -> None:
    _, confirmed, waiters = _setup(client, waiters=2)

    login(client, email="confirmed@example.com")
    assert _cancel(client, confirmed["id"]).status_code == 204
    assert _cancel(client, confirmed["id"]).status_code == 204

    with get_session_factory(db_url)() as db:
        promoted = db.get(Booking, uuid.UUID(str(waiters[0]["id"])))
        remaining = db.get(Booking, uuid.UUID(str(waiters[1]["id"])))
        assert promoted is not None and promoted.status == "confirmed"
        assert promoted.promoted_at is not None
        assert remaining is not None and remaining.status == "waitlisted"
        assert remaining.promoted_at is None


def test_cancelling_someone_elses_booking_returns_404(
    client: TestClient,
    db_url: str,
) -> None:
    _, confirmed, _ = _setup(client, waiters=1)

    register(client, email="intruder@example.com", display_name="Intruder")
    response = _cancel(client, confirmed["id"])

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"

    with get_session_factory(db_url)() as db:
        booking = db.get(Booking, uuid.UUID(str(confirmed["id"])))
        assert booking is not None and booking.status == "confirmed"


def test_checked_in_booking_cannot_be_cancelled(
    client: TestClient,
    db_url: str,
) -> None:
    _, confirmed, _ = _setup(client, waiters=0)

    with get_session_factory(db_url)() as db:
        booking = db.get(Booking, uuid.UUID(str(confirmed["id"])))
        assert booking is not None
        booking.status = "checked_in"
        booking.checked_in_at = datetime.now(UTC)
        db.commit()

    login(client, email="confirmed@example.com")
    response = _cancel(client, confirmed["id"])

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"

    with get_session_factory(db_url)() as db:
        booking = db.get(Booking, uuid.UUID(str(confirmed["id"])))
        assert booking is not None and booking.status == "checked_in"


def test_cancelling_with_an_empty_waitlist_frees_the_seat(
    client: TestClient,
) -> None:
    created, confirmed, _ = _setup(client, waiters=0)
    session_id = str(created["id"])

    login(client, email="confirmed@example.com")
    assert _cancel(client, confirmed["id"]).status_code == 204

    detail = client.get(f"/api/sessions/{session_id}").json()
    assert detail["confirmed_count"] == 0
    assert detail["waitlist_count"] == 0

    register(client, email="newcomer@example.com", display_name="Newcomer")
    replacement = book(client, session_id)

    assert replacement.status_code == 201
    assert replacement.json()["status"] == "confirmed"


def test_unknown_booking_returns_404_and_requires_authentication(
    client: TestClient,
) -> None:
    _, confirmed, _ = _setup(client, waiters=0)

    login(client, email="confirmed@example.com")
    unknown = _cancel(client, uuid.uuid4())
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "not_found"

    logout(client)
    unauthenticated = _cancel(client, confirmed["id"])
    assert unauthenticated.status_code == 401


def test_promotion_failure_rolls_back_the_cancellation(
    client: TestClient,
    db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, confirmed, waiters = _setup(client, waiters=1)
    booking_id = uuid.UUID(str(confirmed["id"]))
    user_id = uuid.UUID(str(confirmed["user_id"]))

    def explode(*args: object, **kwargs: object) -> None:
        raise RuntimeError("promotion failed")

    monkeypatch.setattr(booking_service, "_promote_oldest_waiter", explode)

    with get_session_factory(db_url)() as db:
        with pytest.raises(RuntimeError, match="promotion failed"):
            booking_service.cancel_booking(
                db,
                booking_id=booking_id,
                user_id=user_id,
            )
        db.rollback()

    with get_session_factory(db_url)() as db:
        original = db.get(Booking, booking_id)
        waiter = db.get(Booking, uuid.UUID(str(waiters[0]["id"])))
        assert original is not None and original.status == "confirmed"
        assert original.cancelled_at is None
        assert waiter is not None and waiter.status == "waitlisted"
        assert waiter.promoted_at is None
