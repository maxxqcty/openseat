# OpenSeat — Product Specification

**Version:** 1.0 (scaffold)
**Status:** Approved for implementation
**Last updated:** 2026-10-24

---

## 1. Overview

OpenSeat is a booking and waitlist app for small workshops.

A host publishes a one-off workshop with a fixed number of seats. Guests
reserve a seat; when the workshop is full, they join a waitlist and see their
position. When a confirmed guest cancels, the oldest waitlisted guest is
promoted automatically. At the door, the host checks guests in from the roster.

> Fill every seat, without overbooking.

### Problem

Small workshop hosts run sign-ups through group chats, forms, and spreadsheets.
When someone cancels, the host manually messages the next person, and seats sit
empty while people wait. Attendance is tracked on paper or not at all.

### Users

| User | Needs |
| --- | --- |
| Host | Publish a session, see who is coming, fill cancellations quickly, check people in |
| Guest | Find a session, reserve a seat, know whether they are confirmed or waiting, cancel without emailing anyone |

Any authenticated user can host. "Host" is a relationship to a session, not a
global role.

### Goals

- A guest can go from browsing to a confirmed seat in under a minute.
- A cancellation fills the freed seat automatically, in the same transaction.
- The host can see the truth of who is confirmed, waiting, and checked in.
- Every important action is observable and testable.
- The system never overbooks, including under concurrent requests.

### Non-goals

- Payments, deposits, refunds.
- Email, SMS, or push notifications.
- Recurring sessions or calendar integrations.
- Seat maps, tables, or floor plans.
- File or image uploads.
- Teams, organisations, or admin roles.
- Native mobile apps.
- Internationalisation. The UI is English; times are stored in UTC and
  displayed in the browser's local timezone.

---

## 2. Domain rules

These rules are normative. Tests must cover each one.

1. A session has a `capacity` between 1 and 100.
2. A booking is `confirmed` while the number of confirmed plus checked-in
   bookings is below capacity; otherwise it is `waitlisted`.
3. A checked-in booking still occupies a seat.
4. A user may hold at most one **active** booking per session. Active means
   `confirmed`, `waitlisted`, or `checked_in`.
5. Cancelling a confirmed booking promotes the **oldest** active waitlisted
   booking in the same transaction, and sets `promoted_at`.
6. Cancelling a waitlisted booking removes it and does not promote anyone.
7. A host may cancel a session; all active bookings become `cancelled`.
8. Check-in is allowed only for a confirmed booking, from 2 hours before the
   start until the session ends.
9. Authorization is ownership-based. Any authenticated user may create a
   session. Only that session's host may read its roster, cancel it, or check
   guests in. Guests may cancel only their own bookings.
10. Seat allocation must be race-safe. The invariant
    `confirmed + checked_in <= capacity` must hold at every commit. Use a row
    lock on the session (or an equivalent serialised check) inside the
    transaction.

### Waitlist ordering

Order active waitlisted bookings by `created_at`, then `id` as a deterministic
tie-breaker. Position is 1-based: the oldest waitlisted guest has position 1.

### Session lifecycle

```text
scheduled ──(host cancels)──► cancelled
    │
    └──(start + duration passes)──► past (derived, not stored)
```

`past` is computed from `starts_at + duration_minutes`; it is not a database
status. Past sessions remain viewable but cannot be booked.

---

## 3. User stories

### Guest

1. As a visitor, I can browse upcoming sessions without an account.
2. As a visitor, I can open a session and see its details, seat count, and
   whether I am signed in.
3. As a guest, I can sign up, log in, and log out.
4. As a guest, I can book a seat in a session with space and see a confirmation.
5. As a guest, I can join the waitlist when the session is full and see my
   position.
6. As a guest, I can cancel my booking.
7. As a guest, I can see all my bookings and their current statuses.
8. As a guest, I am promoted automatically when a seat frees up.

### Host

9. As a host, I can create a session with a title, description, start time,
   duration, capacity, and location.
10. As a host, I can see upcoming and past sessions I created.
11. As a host, I can open a roster grouped into confirmed, waitlisted, and
    checked in.
12. As a host, I can check in a confirmed guest during the check-in window.
13. As a host, I can cancel a session after confirming the action.
14. As a host, I cannot see or modify another host's roster.

---

## 4. Acceptance scenarios

These scenarios are the source of the E2E tests and the demo script.

### A. Happy path

1. Host signs up and creates a session with capacity 1.
2. Guest A signs up in a second browser context and opens the session.
3. Guest A books the seat and sees **Confirmed**.
4. The host roster shows Guest A as confirmed.
5. The public session page shows 0 seats left.

### B. Waitlist and promotion

1. Guest B opens the full session and books; B sees **Waitlisted, position 1**.
2. The host roster lists B under waitlisted.
3. Guest A cancels.
4. Guest B's session page updates to **Confirmed** within one polling interval
   (10 seconds) or on refresh.
5. The host roster shows A cancelled and B confirmed.

### C. Check-in

1. Host opens the roster and checks in Guest B.
2. Guest B sees **Checked in**.
3. The seat count remains at capacity; B still occupies a seat.
4. Guest A, signed in but not the host, receives 403 when attempting to check
   anyone in.

### D. Negative rules

1. A second active booking for the same session returns 409.
2. Booking a cancelled or past session returns 409.
3. A non-host requesting the roster returns 403.
4. A non-owner deleting someone else's booking returns 404.
5. Check-in before the window or for a waitlisted booking returns 409.
6. Missing CSRF header on a mutation returns 403.

### E. Concurrency

1. A session has one seat left.
2. Two clients submit a booking at the same time.
3. Exactly one booking is confirmed and one is waitlisted.
4. The confirmed plus checked-in count never exceeds capacity.

### F. Incident loop

1. An injected off-by-one makes the last seat unsellable.
2. `openseat_open_seat_with_waitlist` becomes greater than 0 and the alert
   fires after 10 minutes.
3. The on-call worker starts a headless agent with the evidence packet.
4. The agent reproduces, fixes, tests, and commits to an isolated branch.
5. A human reviews the branch; the transcript and branch are linked in the
   README.

---

## 5. Functional requirements

### 5.1 Authentication

- Email and password registration; display name required.
- Email is unique and case-insensitive.
- Passwords are hashed with Argon2id.
- Login sets an `HttpOnly`, `SameSite=Lax` cookie containing a signed session
  token. `Secure` is set in production.
- Session lifetime is 8 hours; logout clears the cookie.
- Every mutating request must include `X-Requested-With: openseat`; otherwise
  return 403. This is the CSRF defence in addition to `SameSite=Lax`.
- Login attempts are limited to 10 per minute per email plus IP; return 429
  when exceeded.
- No password reset, email verification, or social login in v1.

### 5.2 Sessions

- Fields: title (3–120 chars), description (0–2000 chars), `starts_at` (future,
  UTC), duration (15–480 minutes), capacity (1–100), location (3–200 chars).
- A host may create unlimited sessions.
- Public list shows scheduled sessions that have not ended, ordered by
  `starts_at`.
- Session detail returns seat counts and the caller's booking state if signed
  in.
- Only the host may cancel. Cancelling sets status to `cancelled` and cancels
  all active bookings. It is idempotent.
- Editing a published session is out of scope; cancel and recreate instead.

### 5.3 Bookings

- A booking transitions:

```text
(none) ──book──► confirmed ──cancel──► cancelled
                    │
                    └──check-in──► checked_in

(none) ──book full──► waitlisted ──cancel──► cancelled
                         │
                         └──promotion──► confirmed ──check-in──► checked_in
```

- Booking a full session returns 201 with status `waitlisted` and a position.
- Booking a session with space returns 201 with status `confirmed`.
- Cancelling is idempotent: deleting an already cancelled booking returns 204.
- Cancelling a confirmed booking promotes the oldest waitlisted booking in the
  same transaction. If none exists, the seat simply becomes free.
- A checked-in booking cannot be cancelled by the guest; the host can correct
  attendance only through a future admin feature (out of scope). Guest cancel
  after check-in returns 409.

### 5.4 Roster and check-in

- Roster is host-only and returns three groups: confirmed, waitlisted,
  checked in. Each entry shows display name, booking status, and relevant
  timestamps. Email addresses are not exposed in the roster.
- Check-in is host-only and allowed from 2 hours before `starts_at` until the
  session ends.
- Check-in is idempotent: checking in an already checked-in guest returns 200.
- Check-in of a waitlisted or cancelled booking returns 409.

### 5.5 Time

- All timestamps are stored and returned in UTC, ISO 8601 with offset.
- The frontend displays them in the browser's local timezone and labels the
  timezone in the UI.

---

## 6. API contract

Base path: `/api`. All responses are JSON. Errors use:

```json
{
  "error": {
    "code": "booking_conflict",
    "message": "You already have an active booking for this session.",
    "details": {}
  }
}
```

| Method | Path | Auth | Success | Notes |
| --- | --- | --- | --- | --- |
| POST | `/api/auth/register` | public | 201 user | 409 duplicate email |
| POST | `/api/auth/login` | public | 204 + cookie | 401 bad credentials, 429 rate limit |
| POST | `/api/auth/logout` | user | 204 | Clears cookie |
| GET | `/api/auth/me` | user | 200 user | 401 when signed out |
| GET | `/api/sessions` | public | 200 list | Upcoming, scheduled |
| POST | `/api/sessions` | user | 201 session | Caller becomes host |
| GET | `/api/sessions/{id}` | public | 200 detail | Includes counts and `my_booking` |
| POST | `/api/sessions/{id}/cancel` | host | 200 session | Idempotent |
| GET | `/api/sessions/{id}/bookings` | host | 200 roster | Confirmed/waitlisted/checked-in |
| POST | `/api/sessions/{id}/bookings` | user | 201 booking | Confirmed or waitlisted |
| DELETE | `/api/bookings/{id}` | owner | 204 | May promote |
| POST | `/api/bookings/{id}/check-in` | host | 200 booking | Window enforced |
| GET | `/api/me/bookings` | user | 200 list | Ordered by session start |
| GET | `/healthz` | public | 200 health | Includes DB status and version |

Status codes: 400 malformed, 401 unauthenticated, 403 forbidden/CSRF, 404 not
found or not visible, 409 conflict, 422 schema validation, 429 rate limit.

The canonical contract lives in `openapi.yaml` at the repository root. See
`_docs/architecture.md` for the drift policy.

---

## 7. Data model

```text
users
  id uuid primary key
  email citext unique not null
  password_hash text not null
  display_name text not null
  created_at timestamptz not null

sessions
  id uuid primary key
  host_id uuid not null references users(id)
  title text not null
  description text not null default ''
  starts_at timestamptz not null
  duration_minutes int not null check (duration_minutes between 15 and 480)
  capacity int not null check (capacity between 1 and 100)
  location text not null
  status text not null check (status in ('scheduled', 'cancelled'))
  created_at timestamptz not null

bookings
  id uuid primary key
  session_id uuid not null references sessions(id)
  user_id uuid not null references users(id)
  status text not null check (status in
    ('confirmed', 'waitlisted', 'cancelled', 'checked_in'))
  created_at timestamptz not null
  promoted_at timestamptz null
  checked_in_at timestamptz null
  cancelled_at timestamptz null
```

Constraints and indexes:

- Partial unique index on `(session_id, user_id)` where status is
  `confirmed`, `waitlisted`, or `checked_in`.
- Index on `(session_id, status, created_at)` for roster and waitlist order.
- Index on `(host_id, starts_at)` for the host dashboard.
- Index on `(user_id, created_at)` for "my bookings".
- `citext` extension enabled by the first migration.

---

## 8. Non-functional requirements

### Run and test

- `make dev` starts backend and frontend with one command.
- `make test` runs backend unit, frontend unit, and integration tests.
- `make e2e` runs Playwright against the Compose stack.
- `docker compose up --build` starts app plus database with one command.

### Performance

- p95 API latency under 300 ms locally and under 1.5 s in the deployed
  environment for the booking flow.
- Session list supports at least 500 upcoming sessions without a noticeable
  slowdown; pagination is out of scope but the query must be indexed.

### Reliability

- Health endpoint reflects database connectivity.
- Deploys are health-checked and roll back by image tag.
- Migrations are versioned and run as a release step.

### Security

- Argon2id password hashing.
- HttpOnly, SameSite=Lax session cookie; Secure in production.
- Ownership checks on every host action and booking mutation.
- No secrets in git; `.env.example` only.
- No customer data, credentials, or tokens in telemetry.
- Dependency audit run before submission.

### Accessibility

- Every input has a label.
- Interactive elements are keyboard reachable and show a visible focus state.
- Status changes are announced via an ARIA live region.
- Colour contrast meets WCAG AA for text.

### Observability

- OTel resource attributes: `service.name=openseat`,
  `deployment.environment`, `service.version`.
- Traces cover the booking journey, including the promotion step.
- Metrics include bookings by result, promotions, failures, latency, open seat
  with waitlist, and overbooked sessions.
- Logs are structured JSON and include `trace_id` and `span_id`.
- A Grafana dashboard filters by environment and version.
- At least three alerts include owner, dashboard, and runbook links.

---

## 9. Out of scope (v1)

- Payments and refunds.
- Email or SMS notifications.
- Recurring sessions and calendar sync.
- Waitlist expiry, automatic re-confirmation, or "claim your seat" emails.
- Seat maps.
- Image uploads.
- Organisation accounts, teams, and roles.
- Capacity changes after publication.
- Editing a published session.
- Guest cancellation after check-in.
- Native apps.
- Internationalisation.
- Real-time WebSocket updates. The session page polls every 10 seconds while
  visible and refreshes on window focus.

---

## 10. Open decisions

| Decision | Default for v1 | Revisit when |
| --- | --- | --- |
| Polling vs WebSockets | Poll every 10s | Real-time demand or >100 concurrent users |
| Session cookie vs bearer token | HttpOnly cookie | A mobile client is added |
| Self-hosted vs managed telemetry | Grafana Cloud | Cost or data residency changes |
| Fly.io vs another platform | Fly.io | The day-1 deployment spike fails |
| Waitlist ordering | `created_at`, `id` | Fairness policy changes |
| Check-in window | 2h before to end | Hosts report a different need |

---

## 11. Definition of done

- All acceptance scenarios A–E pass, manually and in Playwright (A–D).
- Domain rules 1–10 have automated tests.
- The app runs with one command locally and via Compose.
- Dev and prod URLs are public; prod is promoted by the manual workflow.
- The dashboard shows a real booking journey with correlated logs and traces.
- An injected bug triggers an alert and produces a reviewed agent branch.
- The README links evidence for every rubric criterion.
