---
title: "Frontend service layer with an in-memory mock"
labels: ["frontend"]
depends_on: ["02"]
---

## Goal

Every future API call goes through one typed service layer, and the UI can be
built and tested against a realistic in-memory implementation before the backend
is ready.

## Acceptance criteria

- [ ] `frontend/src/services/types.ts` defines the domain types and an `Api`
      interface for auth, sessions, bookings, and the roster.
- [ ] `mock.ts` implements the full flow: register, login, logout, `me`; list,
      create, get, and cancel sessions; book and cancel; roster and check-in.
- [ ] The mock enforces capacity, one active booking per user, the waitlist
      position, automatic promotion of the oldest waiter, and the check-in
      window.
- [ ] `index.ts` selects the mock or HTTP implementation. In development the
      default is `mock`; in a production build the default is `http`.
      `VITE_API_MODE` overrides both.
- [ ] `resetMock()` restores deterministic seed data for tests.
- [ ] No component or page calls `fetch`; only `services/http.ts` may do so.
- [ ] At least six tests cover the mock: capacity boundary, waitlist position,
      promotion, duplicate booking, cancelled session, and check-in window.
- [ ] The mock exposes the same error codes as the API contract
      (`booking_conflict`, `forbidden`, `not_found`, `validation_error`).

## Out of scope

- Real HTTP calls. Issue #12.
- Server state, caching, or a state-management library.
- Persisting the mock across a page reload.

## Constraints

- Keep the interface small enough to implement in one file.
- Do not add a global store; the mock owns its own module-level data.
- No artificial delays in tests; optional short latency in development only.
- The mock must remain a development tool and must not be bundled as the
  production default.
