---
title: "Cancellation and automatic promotion of the oldest waiter"
labels: ["backend", "booking", "database"]
depends_on: ["06", "07"]
---

## Goal

When a confirmed guest cancels, the oldest waitlisted guest takes the seat in
the same transaction, with no manual host action.

## Acceptance criteria

- [ ] `DELETE /api/bookings/{id}` returns 204 for the owner and is idempotent.
- [ ] Another user's booking returns 404, not 403, to avoid leaking existence.
- [ ] Cancelling a confirmed booking promotes the oldest active waitlisted
      booking in the same transaction and sets `promoted_at`.
- [ ] If the waitlist is empty, the cancellation leaves the seat free.
- [ ] Cancelling a waitlisted booking does not promote anyone.
- [ ] A checked-in booking cannot be cancelled by the guest; return 409.
- [ ] Double cancellation returns 204 and never promotes twice.
- [ ] A test forces an error during promotion and asserts the original
      cancellation rolled back.
- [ ] Integration tests cover promotion order, waitlist cancellation,
      idempotency, and the 404 case.

## Out of scope

- Email or SMS notification to the promoted guest.
- Refunds.
- A host removing an individual guest. Follow-up issue if needed.

## Constraints

- Use the same session row lock and transaction boundary as booking.
- Do not start a second transaction for promotion.
- Reuse the waitlist ordering from issue #07.
- Emit a domain event or structured log for a successful promotion; metrics
  wiring lands in issue #17.
- No capacity counter column that can drift from the bookings table.
