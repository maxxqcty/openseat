"""Integration tests for waitlist positions and the my-bookings endpoint."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import get_session_factory
from app.models.bookings import Booking
from tests.conftest import requires_postgres
from tests.integration.helpers import (
    book,
    counted_selects,
    create_session,
    login,
    register,
)

pytestmark = requires_postgres


def _filled_session(
    client: TestClient,
    *,
    capacity: int = 1,
    title: str = "Waitlist Workshop",
) -> tuple[str, dict[str, object]]:
    """Create a session and fill it with one confirmed guest."""
    register(client, email="wait-host@example.com", display_name="Host")
    created = create_session(client, capacity=capacity, title=title)
    session_id = str(created["id"])

    register(client, email="seat@example.com", display_name="Seat Holder")
    assert book(client, session_id).json()["status"] == "confirmed"
    return session_id, created


def _join_waitlist(
    client: TestClient,
    *,
    session_id: str,
    email: str,
    display_name: str,
) -> dict[str, object]:
    """Register a guest and put them on the waitlist."""
    register(client, email=email, display_name=display_name)
    response = book(client, session_id)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "waitlisted"
    return body


def test_positions_are_one_based_in_booking_order(client: TestClient) -> None:
    session_id, _ = _filled_session(client)

    positions = []
    for index, email in enumerate(
        ("first@example.com", "second@example.com", "third@example.com"),
        start=1,
    ):
        body = _join_waitlist(
            client,
            session_id=session_id,
            email=email,
            display_name=f"Waiter {index}",
        )
        positions.append(body["waitlist_position"])

    assert positions == [1, 2, 3]

    login(client, email="second@example.com")
    detail = client.get(f"/api/sessions/{session_id}").json()
    assert detail["my_booking"]["waitlist_position"] == 2

    login(client, email="seat@example.com")
    confirmed = client.get(f"/api/sessions/{session_id}").json()
    assert confirmed["my_booking"]["status"] == "confirmed"
    assert confirmed["my_booking"]["waitlist_position"] is None


def test_my_bookings_returns_position_and_session_summary(client: TestClient) -> None:
    session_id, created = _filled_session(client)
    _join_waitlist(
        client,
        session_id=session_id,
        email="first@example.com",
        display_name="First",
    )
    _join_waitlist(
        client,
        session_id=session_id,
        email="second@example.com",
        display_name="Second",
    )

    login(client, email="second@example.com")
    response = client.get("/api/me/bookings")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["status"] == "waitlisted"
    assert body[0]["waitlist_position"] == 2
    assert body[0]["session"]["id"] == created["id"]
    assert body[0]["session"]["title"] == created["title"]
    assert body[0]["session"]["starts_at"] == created["starts_at"]
    assert body[0]["session"]["past"] is False


def test_my_bookings_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/me/bookings")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_positions_shift_when_the_first_waiter_is_promoted(
    client: TestClient,
    db_url: str,
) -> None:
    session_id, _ = _filled_session(client)
    first = _join_waitlist(
        client,
        session_id=session_id,
        email="first@example.com",
        display_name="First",
    )
    _join_waitlist(
        client,
        session_id=session_id,
        email="second@example.com",
        display_name="Second",
    )
    _join_waitlist(
        client,
        session_id=session_id,
        email="third@example.com",
        display_name="Third",
    )

    with get_session_factory(db_url)() as db:
        promoted = db.get(Booking, uuid.UUID(str(first["id"])))
        assert promoted is not None
        promoted.status = "confirmed"
        promoted.promoted_at = datetime.now(UTC)
        db.commit()

    login(client, email="second@example.com")
    assert client.get(f"/api/sessions/{session_id}").json()["my_booking"]["waitlist_position"] == 1

    login(client, email="third@example.com")
    detail = client.get(f"/api/sessions/{session_id}").json()
    assert detail["my_booking"]["waitlist_position"] == 2
    assert client.get("/api/me/bookings").json()[0]["waitlist_position"] == 2

    login(client, email="first@example.com")
    promoted_detail = client.get(f"/api/sessions/{session_id}").json()
    assert promoted_detail["my_booking"]["waitlist_position"] is None


def test_ten_waiters_hold_positions_one_through_ten(client: TestClient) -> None:
    session_id, _ = _filled_session(client)

    for index in range(1, 11):
        body = _join_waitlist(
            client,
            session_id=session_id,
            email=f"waiter-{index}@example.com",
            display_name=f"Waiter {index}",
        )
        assert body["waitlist_position"] == index

    for index, expected in ((1, 1), (5, 5), (10, 10)):
        login(client, email=f"waiter-{index}@example.com")
        detail = client.get(f"/api/sessions/{session_id}").json()
        assert detail["my_booking"]["waitlist_position"] == expected
        my_bookings = client.get("/api/me/bookings").json()
        assert my_bookings[0]["waitlist_position"] == expected


def test_my_bookings_orders_by_start_without_n_plus_one(
    client: TestClient,
    db_url: str,
) -> None:
    register(client, email="many-host@example.com", display_name="Host")
    sessions = [
        create_session(client, capacity=1, starts_in_hours=hours, title=f"In {hours}h")
        for hours in (7, 2, 9, 1, 5, 10, 3, 8, 4, 6)
    ]

    register(client, email="filler@example.com", display_name="Filler")
    for created in sessions:
        assert book(client, str(created["id"])).json()["status"] == "confirmed"

    register(client, email="target@example.com", display_name="Target")
    for created in sessions:
        assert book(client, str(created["id"])).json()["status"] == "waitlisted"

    with counted_selects(db_url) as statements:
        response = client.get("/api/me/bookings")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 10
    assert all(item["status"] == "waitlisted" for item in body)
    assert all(item["waitlist_position"] == 1 for item in body)
    starts = [item["session"]["starts_at"] for item in body]
    assert starts == sorted(starts)
    # auth lookup, bookings with sessions, and the batched position query.
    assert len(statements) == 3


def test_equal_created_at_is_broken_by_booking_id(
    client: TestClient,
    db_url: str,
) -> None:
    session_id, _ = _filled_session(client)

    users = []
    for index in range(1, 4):
        users.append(
            register(client, email=f"tie-{index}@example.com", display_name=f"Tie {index}"),
        )

    created_at = datetime.now(UTC)
    with get_session_factory(db_url)() as db:
        for user in users:
            db.add(
                Booking(
                    session_id=uuid.UUID(session_id),
                    user_id=uuid.UUID(str(user["id"])),
                    status="waitlisted",
                    created_at=created_at,
                ),
            )
        db.commit()
        rows = db.execute(
            select(Booking.id, Booking.user_id).where(
                Booking.session_id == uuid.UUID(session_id),
            ),
        ).all()
    booking_ids = {str(user_id): booking_id for booking_id, user_id in rows}

    expected_order = sorted(users, key=lambda user: booking_ids[str(user["id"])])
    for position, user in enumerate(expected_order, start=1):
        login(client, email=str(user["email"]))
        detail = client.get(f"/api/sessions/{session_id}").json()
        assert detail["my_booking"]["waitlist_position"] == position
