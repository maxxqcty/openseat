"""Authentication API routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.exceptions import HTTPException

from app.config import get_settings
from app.services.auth import (
    AuthCredentials,
    PublicUser,
    ErrorShape,
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    get_current_user,
    authenticate_user,
    signout_response,
)

# Rate limiting tracking: {email+ip: {"count": int, "reset_at": float}}
login_attempts: dict[str, dict] = {}

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _check_rate_limit(email: str, ip: str | None) -> None:
    """Rate limit: 10 attempts per minute per email plus IP.

    Raises 429 if limit exceeded.
    """
    from time import monotonic

    key = f"{email}|{ip or ''}"
    now = monotonic()
    window = 60  # seconds

    attempt = login_attempts.get(key)
    if attempt:
        if now - attempt["reset_at"] > window:
            # Window expired, reset
            login_attempts[key] = {"count": 1, "reset_at": now + window}
            return
        if attempt["count"] >= 10:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again later.",
            )
        attempt["count"] += 1
    else:
        login_attempts[key] = {"count": 1, "reset_at": now + window}


def _check_csrf_header(request: Request) -> None:
    """Mutating requests require X-Requested-With: openseat header.

    A missing or incorrect header returns 403.
    """
    requested_with = request.headers.get("X-Requested-With")
    if requested_with != "openseat":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing or invalid",
        )


@router.post("/register", status_code=201, response_model=PublicUser)
async def register(
    credentials: AuthCredentials,
    response: Response,
    request: Request,
) -> PublicUser:
    """Register a new user account.

    Returns 201 with the public user on success.
    Returns 409 if duplicate email.
    Returns 422 for invalid email or short password.
    """
    # Check CSRF header for mutating request
    _check_csrf_header(request)

    # Check for duplicate email
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.config import get_db_session

    session = get_db_session()
    try:
        stmt = select(User).where(User.email == credentials.email)
        existing = session.scalar(stmt)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
    finally:
        session.close()

    # Create the user
    from app.models.users import User  # type: ignore
    from app.config import get_db_session

    hashed_pw = hash_password(credentials.password)
    user_dict = {
        "email": credentials.email,
        "hashed_password": hashed_pw,
        "is_active": True,
        "is_superuser": False,
        "is_verified": False,
    }

    session = get_db_session()
    try:
        user = User(**user_dict)
        session.add(user)
        session.commit()
        session.refresh(user)
    finally:
        session.close()

    # Return public user representation
    public = PublicUser.model_validate(user)

    # Set the access token cookie
    token = create_access_token(sub=user.id)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=get_settings().app_env == "production",
        path="/",
    )

    return public


@router.post("/login", status_code=204, response_model=None)
async def login(
    credentials: AuthCredentials,
    response: Response,
    request: Request,
) -> None:
    """Log in a user.

    Returns 204 on success with HttpOnly, SameSite=Lax cookie.
    Returns 401 for bad credentials.
    Rate limits: 10 attempts per minute per email plus IP returns 429.
    """
    _check_rate_limit(credentials.email, request.client.host if request.client else None)

    user = authenticate_user(credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Set the access token cookie
    response.set_cookie(
        key="access_token",
        value=create_access_token(sub=user.id),
        httponly=True,
        samesite="lax",
        secure=get_settings().app_env == "production",
        path="/",
    )

    return None


@router.post("/logout", status_code=204, response_model=None)
async def logout(response: Response) -> None:
    """Log out a user.

    Returns 204 and clears the access_token cookie.
    """
    signout_response(response)
    return None


@router.get("/me", response_model=PublicUser)
async def me(request: Request) -> PublicUser:
    """Get the current user's profile.

    Returns 200 with user data or 401 when signed out.
    """
    return get_current_user(request)


@router.get("/csrf-token")
async def csrf_token(request: Request) -> dict:
    """Return a CSRF token for mutating requests.

    Mutating requests require X-Requested-With: openseat header.
    A missing or incorrect header returns 403.
    """
    _check_csrf_header(request)
    import os
    return {"csrf_token": os.urandom(32).hex()}