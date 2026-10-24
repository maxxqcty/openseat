---
title: "Host roster and check-in API"
labels: ["backend", "api"]
depends_on: ["05", "08"]
---

## Goal

A host can see who is confirmed, waiting, and checked in, and can check a
confirmed guest in during the allowed window.

## Acceptance criteria

- [ ] `GET /api/sessions/{id}/bookings` is host-only and returns three ordered
      groups: confirmed, waitlisted, checked in.
- [ ] Each roster entry includes booking ID, display name, status, booking time,
      check-in time, and waitlist position when relevant.
- [ ] The roster never exposes email addresses or password data.
- [ ] A signed-in non-host receives 403; an unknown session returns 404.
- [ ] `POST /api/bookings/{id}/check-in` is host-only and sets
      `checked_in_at` on a confirmed booking.
- [ ] Check-in is allowed from exactly 2 hours before `starts_at` through the
      end of the session; outside that window returns 409.
- [ ] Checking in a waitlisted, cancelled, or already checked-in booking
      returns 409, except an already checked-in booking is idempotent and
      returns 200.
- [ ] A non-host receives 403.
- [ ] Session detail still counts checked-in bookings against capacity.
- [ ] Tests freeze time and cover both window boundaries, 403, 404, and the
      idempotent case.

## Out of scope

- QR codes, offline check-in, and attendance export.
- Guest-initiated check-in.
- The roster page UI. Issue #12.

## Constraints

- Authorization helper shared by roster, check-in, and session cancellation.
- Domain logic in `backend/app/services/roster.py` or `bookings.py`.
- Use UTC for all comparisons; the browser handles display.
- Roster ordering: confirmed by booking time, waitlisted by position, checked
  in by check-in time.
