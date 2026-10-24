---
title: "Waitlist position in session detail and my bookings"
labels: ["backend", "api"]
depends_on: ["06"]
---

## Goal

A waitlisted guest can see their place in line, and the position is always
consistent with the current roster.

## Acceptance criteria

- [ ] A waitlisted booking response includes `waitlist_position`, 1-based.
- [ ] Position is ordered by `created_at` ascending, then `id` as a
      deterministic tie-breaker.
- [ ] `GET /api/sessions/{id}` includes `waitlist_position` inside `my_booking`
      when the caller is waitlisted, and `null` otherwise.
- [ ] `GET /api/me/bookings` includes the position for each waitlisted booking.
- [ ] Position is computed from active waitlisted rows; no position column is
      stored.
- [ ] After a promotion, the remaining waitlisted positions shift down by one.
- [ ] A test with three waitlisted users asserts positions 1, 2, and 3 and the
      order after the first is promoted.
- [ ] The queries avoid N+1 and remain correct with ten waitlisted bookings.

## Out of scope

- Notifying a guest about their position.
- Waitlist expiry or a "claim your seat" flow.
- Displaying the position in the UI. Issue #12.

## Constraints

- Compute the position in `backend/app/services/bookings.py` or a shared
  waitlist helper; do not duplicate the ordering in routers.
- Reuse the same ordering in cancellation and promotion.
- Use a window function or a single ordered query; do not issue one query per
  booking.
- Keep the response backward compatible: `waitlist_position` is optional.
