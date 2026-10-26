"""Unit tests for the check-in window rule."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.models.sessions import Session
from app.services.roster import check_in_window, is_check_in_open


def _session(starts_at: datetime, duration_minutes: int = 60) -> Session:
    return Session(
        id=uuid.uuid4(),
        host_id=uuid.uuid4(),
        title="Check-in window",
        description="",
        starts_at=starts_at,
        duration_minutes=duration_minutes,
        capacity=1,
        location="Studio",
        status="scheduled",
    )


def test_window_opens_exactly_two_hours_before_start() -> None:
    now = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)

    assert is_check_in_open(_session(now + timedelta(hours=2)), now=now)
    assert is_check_in_open(_session(now + timedelta(hours=2, seconds=-1)), now=now)
    assert not is_check_in_open(_session(now + timedelta(hours=2, seconds=1)), now=now)


def test_window_stays_open_until_the_session_ends() -> None:
    now = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
    open_session = _session(now - timedelta(minutes=60))

    assert is_check_in_open(open_session, now=now)
    assert not is_check_in_open(_session(now - timedelta(minutes=61)), now=now)
    assert check_in_window(open_session) == (now - timedelta(hours=3), now)
