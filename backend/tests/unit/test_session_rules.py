"""Unit tests for derived session rules."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.models.sessions import Session
from app.services.sessions import as_utc, is_past


def _session(starts_at: datetime, duration_minutes: int = 60) -> Session:
    return Session(
        id=uuid.uuid4(),
        host_id=uuid.uuid4(),
        title="Test session",
        description="",
        starts_at=starts_at,
        duration_minutes=duration_minutes,
        capacity=1,
        location="Studio",
        status="scheduled",
    )


def test_is_past_compares_start_plus_duration() -> None:
    now = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)

    assert is_past(_session(now - timedelta(minutes=61)), now=now)
    assert not is_past(_session(now - timedelta(minutes=59)), now=now)
    assert not is_past(_session(now + timedelta(hours=1)), now=now)


def test_as_utc_treats_naive_timestamps_as_utc() -> None:
    naive = datetime(2026, 10, 26, 12, 0)
    aware = as_utc(naive)

    assert aware.tzinfo is UTC
    assert aware.hour == 12
