# Testing Strategy

## Principle

Test the rules that can hurt users: capacity, ordering, promotion, permissions,
and the check-in window. Do not chase coverage on glue code.

## Pyramid

| Level | Tool | What it covers | Speed |
| --- | --- | --- | --- |
| Backend unit | pytest | Pure domain rules, validation, ordering | Fast |
| Frontend unit | Vitest + React Testing Library | Component states, error rendering, service mock | Fast |
| Integration | pytest + httpx + Postgres | API, transactions, constraints, concurrency | Medium |
| E2E | Playwright | The full host/guest/waitlist/check-in journey | Slow |

## Commands

```bash
make test    # backend unit + frontend unit + integration
make e2e     # Playwright against docker-compose.yaml
make lint    # ruff, mypy, eslint, tsc
```

Focused runs:

```bash
cd backend
uv run pytest tests/unit/test_booking_rules.py -q
uv run pytest tests/integration/test_booking_race.py -q

cd frontend
npm run test -- BookingButton
```

## Required coverage

### Domain rules (unit)

- capacity boundary: last seat confirmed, next booking waitlisted;
- checked-in bookings still occupy seats;
- oldest waitlisted promoted first, ties broken deterministically;
- cancelling a waitlisted booking does not promote;
- duplicate active booking rejected;
- booking a cancelled or past session rejected;
- check-in outside the window rejected;
- check-in of a waitlisted booking rejected.

### API and database (integration)

- registration, login, logout, `me`;
- cookie flags and CSRF rejection;
- authorization: non-host roster 403, non-owner delete 404;
- booking and promotion against Postgres;
- partial unique index prevents two active bookings;
- **race test:** two concurrent requests for the last seat produce exactly one
  confirmed and one waitlisted booking;
- invariant query after the race:
  `confirmed + checked_in <= capacity`;
- health endpoint reflects database availability.

### Frontend (unit)

- booking button states: loading, confirmed, waitlisted, full, error;
- waitlist position rendering;
- 401 redirects to login;
- 403 and 409 show actionable messages;
- empty and error states on the session list.

### End-to-end (Playwright)

Three browser contexts: host, guest A, guest B.

1. Host creates a capacity-1 session.
2. A books; sees confirmed.
3. B books; sees waitlisted, position 1.
4. A cancels.
5. B sees confirmed after polling or refresh.
6. Host checks B in; B sees checked in.
7. A (non-host) cannot check in.

Also cover: duplicate booking, booking a cancelled session, and a missing CSRF
header. Capture a trace and screenshot on failure.

## Fixtures and isolation

- Each integration test runs in a transaction that is rolled back, or against a
  fresh schema created by migrations.
- Do not share mutable fixtures between tests.
- Seed only what the test needs; no global demo data in tests.
- Use unique emails per test (`uuid4` suffix) to avoid cross-run collisions.
- Freeze time for check-in-window tests; do not depend on the wall clock.
- The concurrency test uses two real connections and a barrier; do not simulate
  it with sequential calls.

## What is intentionally not tested

- Tailwind classes and visual appearance. Use screenshots for the demo.
- Third-party libraries (Render, Grafana, Playwright).
- Load and soak testing in v1. Add a k6 smoke test only if time remains.
- Email, payments, and other out-of-scope features.

## CI

- Pull request: lint, unit, frontend, integration (Postgres service container),
  image build.
- Main: the same, then build and push the image, run E2E against Compose, deploy
  dev, smoke `/healthz`.
- Failures keep logs and the Playwright trace as artifacts.

## Evidence for the rubric

The README links:

- the `make test` command and a successful run;
- a CI run showing parallel backend/frontend jobs;
- a Playwright report or trace;
- the concurrency test by name.
