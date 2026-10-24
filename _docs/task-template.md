# Task Template

Every issue uses these four sections. An issue is groomed only when all four
are filled in and every criterion is checkable.

```markdown
## Goal

One or two sentences on what should be true when this is done.

## Acceptance criteria

- [ ] A statement you can check by looking at the result
- [ ] One line per case, including the awkward ones
- [ ] At least one failure path

## Out of scope

- Something that does not belong in this task, moved to #<follow-up>

## Constraints

- Files this should stay inside
- Libraries to use or avoid
- Guidelines to follow
```

## Rules for acceptance criteria

- A reviewer must be able to say yes or no without interpreting intent.
- Prefer observable behaviour: "returns 409 when ..." over "handles conflicts".
- One line per case. Do not bundle three cases into one checkbox.
- Include authorization and validation cases, not only the happy path.
- Include the command or test that proves it when useful.

## Rules for out of scope

- Never delete an item silently. File a follow-up issue and link it.
- "Out of scope" is a contract, not a suggestion. If it is not listed, the
  implementer may not add it.

## Rules for constraints

- Name the files or modules the change should stay inside.
- Name libraries to use or avoid.
- Reference the relevant decision in `_docs/spec.md` or
  `_docs/architecture.md`.
- State performance or compatibility limits when they matter.

## Example

```markdown
## Goal

A guest can cancel a confirmed booking, and the oldest waitlisted guest is
promoted in the same transaction.

## Acceptance criteria

- [ ] `DELETE /api/bookings/{id}` returns 204 for the owner.
- [ ] Cancelling a confirmed booking promotes the oldest waitlisted booking.
- [ ] The promoted booking has `status=confirmed` and `promoted_at` set.
- [ ] Cancelling a waitlisted booking promotes nobody.
- [ ] Cancelling twice returns 204 and does not promote twice.
- [ ] Cancelling another user's booking returns 404.
- [ ] Integration test covers cancellation followed by promotion against
      Postgres.

## Out of scope

- Notifying the promoted guest by email. Follow-up: #<issue>.
- Refunds or payments.

## Constraints

- Domain logic in `backend/app/services/bookings.py`.
- Route in `backend/app/api/bookings.py`.
- Use the existing session transaction and row lock from issue #6.
- Follow `_docs/spec.md` rules 5, 6, and 10.
```
