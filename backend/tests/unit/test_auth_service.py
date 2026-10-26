"""Unit tests for password hashing, tokens, and settings validation."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.errors import ApiError
from app.services.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash != "correct horse battery staple"
    assert password_hash.startswith("$argon2")
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_token_roundtrip_returns_user_id() -> None:
    user_id = uuid.uuid4()

    token = create_access_token(user_id)

    assert decode_access_token(token) == user_id


def test_invalid_token_raises_unauthorized() -> None:
    with pytest.raises(ApiError) as excinfo:
        decode_access_token("not-a-token")

    assert excinfo.value.status_code == 401
    assert excinfo.value.code == "unauthorized"


def test_session_secret_is_required_outside_tests() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="production", session_secret="too-short")

    settings = Settings(app_env="production", session_secret="y" * 32)
    assert settings.cookie_secure is True
