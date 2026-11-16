"""Unit tests for the in-memory login throttle."""

import pytest

from app.api import auth
from app.errors import ApiError


@pytest.fixture(autouse=True)
def _reset() -> None:
    auth.reset_rate_limits()


def test_blocks_only_after_ten_recorded_failures() -> None:
    for _ in range(10):
        auth._enforce_rate_limit("a@example.com", "1.1.1.1")
        auth._record_failed_login("a@example.com", "1.1.1.1")

    with pytest.raises(ApiError) as blocked:
        auth._enforce_rate_limit("A@example.com ", "1.1.1.1")
    assert blocked.value.status_code == 429


def test_successful_logins_do_not_count_and_clear_failures() -> None:
    for _ in range(9):
        auth._record_failed_login("a@example.com", "1.1.1.1")
    auth._clear_failed_logins("a@example.com", "1.1.1.1")

    for _ in range(30):
        auth._enforce_rate_limit("a@example.com", "1.1.1.1")  # never records


def test_expired_keys_are_pruned(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [1000.0]
    monkeypatch.setattr(auth, "monotonic", lambda: clock[0])
    for index in range(auth._PRUNE_THRESHOLD + 5):
        auth._record_failed_login(f"user{index}@example.com", "1.1.1.1")

    clock[0] += auth._RATE_WINDOW_SECONDS + 1
    auth._enforce_rate_limit("fresh@example.com", "1.1.1.1")

    assert len(auth._attempts) == 0
