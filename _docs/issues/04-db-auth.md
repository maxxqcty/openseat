---
title: "Database foundation and authentication"
labels: ["backend", "auth", "database"]
depends_on: ["01"]
---

## Goal

Users can register, sign in, sign out, and fetch their profile, with accounts
persisted in PostgreSQL and a secure cookie session.

## Acceptance criteria

- [ ] SQLAlchemy 2 models and an Alembic baseline create `users` and enable the
      `citext` extension.
- [ ] `DATABASE_URL` configures the connection; a missing or unreachable
      database fails fast at startup.
- [ ] `POST /api/auth/register` returns 201 with the public user; duplicate email
      returns 409; invalid email or a short password returns 422.
- [ ] Email uniqueness is case-insensitive; passwords are hashed with Argon2id
      and never returned or logged.
- [ ] `POST /api/auth/login` returns 204 and sets an `HttpOnly`,
      `SameSite=Lax` cookie; `Secure` is set when `APP_ENV=production`.
- [ ] Bad credentials return 401 with the standard error shape; more than 10
      attempts per minute per email plus IP returns 429.
- [ ] `POST /api/auth/logout` returns 204 and clears the cookie.
- [ ] `GET /api/auth/me` returns 200 with the user or 401 when signed out.
- [ ] Every mutating request requires `X-Requested-With: openseat`; a missing
      header returns 403.
- [ ] Integration tests run against PostgreSQL and cover duplicate email, wrong
      password, cookie flags, CSRF rejection, and rate limiting.
- [ ] `GET /healthz` now reports the real database status.

## Out of scope

- Password reset, email verification, OAuth, roles, and admin accounts.
- Refresh tokens and "remember me".
- Seeding demo users. Issue #11.

## Constraints

- Models in `backend/app/models/`, auth logic in
  `backend/app/services/auth.py`, routes in `backend/app/api/auth.py`.
- Use `argon2-cffi` for hashing and `pyjwt` for the signed cookie.
- `SESSION_SECRET` is required outside tests and must be at least 32 characters.
- Tests may not use SQLite; use PostgreSQL with migrations applied.
- Never store the session token in `localStorage`.
