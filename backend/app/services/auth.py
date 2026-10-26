"""Authentication domain logic: hashing, tokens, and account operations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import argon2
import jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import ApiError
from app.models.users import User

_ALGORITHM = "HS256"
_hasher = argon2.PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plain-text password with Argon2id."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plain-text password against an Argon2 hash."""
    try:
        return _hasher.verify(password_hash, password)
    except (
        argon2.exceptions.VerifyMismatchError,
        argon2.exceptions.VerificationError,
        argon2.exceptions.InvalidHashError,
    ):
        return False


def create_access_token(user_id: uuid.UUID) -> str:
    """Create a signed session token for the user."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=settings.session_ttl_hours),
    }
    return jwt.encode(payload, settings.session_secret, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    """Validate a session token and return the user id."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.session_secret, algorithms=[_ALGORITHM])
        return uuid.UUID(str(payload["sub"]))
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise ApiError(401, "unauthorized", "Authentication required") from exc


def register_user(
    db: Session,
    *,
    display_name: str,
    email: str,
    password: str,
) -> User:
    """Create an account, rejecting blank names and duplicate emails."""
    name = display_name.strip()
    if not name:
        raise ApiError(422, "validation_error", "Display name is required")

    if db.scalar(select(User).where(User.email == email)) is not None:
        raise ApiError(409, "conflict", "Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApiError(409, "conflict", "Email already registered") from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User | None:
    """Return the matching user for valid credentials, otherwise None."""
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
