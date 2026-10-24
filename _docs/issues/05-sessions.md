---
title: "Session creation, listing, detail, and host cancellation"
labels: ["backend", "sessions"]
depends_on: ["04"]
---

## Goal

A signed-in user can publish a workshop, the public can browse and inspect it,
and the host can cancel it.

## Acceptance criteria

- [ ] A `sessions` model and migration store host, title, description, start,
      duration, capacity, location, status, and creation time.
- [ ] `POST /api/sessions` requires authentication and creates a scheduled
      session with the caller as host; invalid fields return 422.
- [ ] `GET /api/sessions` is public and returns scheduled sessions that have not
      ended, ordered by `starts_at` ascending.
- [ ] `GET /api/sessions/{id}` is public and returns seat counts and the
      caller's `my_booking` (null when signed out); an unknown ID returns 404.
- [ ] `POST /api/sessions/{id}/cancel` is host-only, returns 200, is idempotent,
      and cancels every active booking on the session.
- [ ] A signed-in non-host receives 403 when cancelling.
- [ ] `past` is derived from `starts_at + duration_minutes`; it is never stored
      as a session status.
- [ ] Integration tests cover success, 403, 404, validation, and the booking
      cascade on cancellation.
- [ ] The list and detail queries do not produce N+1 queries.

## Out of scope

- Editing a published session, changing capacity, or recurring sessions.
- Booking. Issue #06.
- Frontend forms. Issue #12.

## Constraints

- Domain logic in `backend/app/services/sessions.py`; routes in
  `backend/app/api/sessions.py`.
- Store and return UTC ISO 8601 timestamps.
- Use a constant or enum for status; no free-text status values.
- Keep the cancellation cascade in the same transaction.
