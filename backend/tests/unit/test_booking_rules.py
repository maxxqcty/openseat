"""Unit tests for booking seat allocation rules."""

from __future__ import annotations

import pytest

from app.models.bookings import STATUS_CONFIRMED, STATUS_WAITLISTED
from app.services.bookings import status_for_occupancy


@pytest.mark.parametrize(
    ("occupied", "capacity", "expected"),
    [
        (0, 1, STATUS_CONFIRMED),
        (1, 1, STATUS_WAITLISTED),
        (1, 2, STATUS_CONFIRMED),
        (2, 2, STATUS_WAITLISTED),
        (99, 100, STATUS_CONFIRMED),
        (100, 100, STATUS_WAITLISTED),
    ],
)
def test_last_free_seat_is_confirmed_and_the_next_is_waitlisted(
    occupied: int,
    capacity: int,
    expected: str,
) -> None:
    assert status_for_occupancy(occupied=occupied, capacity=capacity) == expected
