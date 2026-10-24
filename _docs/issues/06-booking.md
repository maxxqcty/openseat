---
title: "Race-safe booking with capacity enforcement"
labels: ["backend", "booking", "database"]
depends_on: ["05"]
---

## Goal

A guest can book a seat, and the system never confirms more guests than the
session's capacity, even when requests arrive at the same time.

## Acceptance criteria

- [ ] A `bookings` model and migration store session, user, status, and
      timestamps, with a partial unique index on active bookings per user and
      session.
- [ ] `POST /api/sessions/{id}/bookings` returns 201 with `confirmed` when a
      seat is free, or 201 with `waitlisted` when the session is full.
- [ ] A second active booking by the same user returns 409
      (`booking_conflict`).
- [ ] Booking a cancelled, ended, or unknown session returns 409 or 404 as
      appropriate.
- [ ] The booking transaction locks the session row, counts `confirmed` plus
      `checked_in`, and commits the booking before releasing the lock.
- [ ] The invariant `confirmed + checked_in <= capacity` holds after every
      commit.
- [ ] A PostgreSQL integration test opens two connections with a barrier,
      books the last seat concurrently, and asserts exactly one `confirmed` and
      one `waitlisted` booking.
- [ ] A test asserts the invariant query returns no rows after the race.
- [ ] Unit tests cover the capacity boundary: the last seat is confirmed, the
      next request is waitlisted.

## Out of scope

- Promotion when a seat frees up. Issue #08.
- Payments, seat selection, and notifications.
- Optimistic UI.

## Constraints

- Domain logic in `backend/app/services/bookings.py`; route in
  `backend/app/api/bookings.py`.
- Use `SELECT ... FOR UPDATE` on the session row inside one transaction.
- Never count seats outside the locked transaction.
- Include `checked_in` in the occupied count from the start.
- Return the documented error shape; no bare exception strings.
