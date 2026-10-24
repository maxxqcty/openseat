# Architecture

> Target architecture. The code and the paths below land through the backlog in
> `_docs/backlog.md`; this document is the contract they implement.

## Context

OpenSeat is a single web application with a React frontend, a FastAPI backend,
and PostgreSQL. One container serves the built frontend and the API in
production.

```text
Client
  │ HTTPS, HttpOnly cookie
  ▼
FastAPI (one process)
  ├── /api/*          JSON API
  ├── /*              static React build
  ├── SQLAlchemy ──► PostgreSQL
  └── OTLP ─────────► Grafana Cloud
```

The on-call worker is a separate process. It polls Grafana and starts a headless
coding agent in an isolated git worktree. It never deploys.

## Components

| Component | Responsibility | Location |
| --- | --- | --- |
| API routers | HTTP validation, auth, status codes | `backend/app/api/` |
| Domain services | Booking, waitlist, promotion, check-in rules | `backend/app/services/` |
| Models | SQLAlchemy mappings | `backend/app/models/` |
| Schemas | Pydantic request/response models | `backend/app/schemas/` |
| Frontend services | One place for every API call | `frontend/src/services/` |
| Pages/components | Rendering and interaction | `frontend/src/pages/`, `components/` |
| On-call worker | Alert polling, evidence packet, agent launch | `on-call/` |
| Observability assets | Dashboard, alerts, collector config | `observability/` |

## Request flows

### Book a seat

```text
POST /api/sessions/{id}/bookings
  → authenticate cookie
  → validate session is scheduled and not past
  → BEGIN
  → SELECT session FOR UPDATE
  → count active confirmed + checked_in
  → if count < capacity: insert confirmed
    else: insert waitlisted, compute position
  → COMMIT
  → 201 booking
```

The row lock serialises concurrent bookings for the same session. Different
sessions proceed in parallel. Never count outside the locked transaction.

### Cancel and promote

```text
DELETE /api/bookings/{id}
  → authenticate, load booking, check owner
  → BEGIN
  → SELECT session FOR UPDATE
  → if booking confirmed: set cancelled
      → select oldest waitlisted FOR UPDATE
      → if exists: set confirmed, promoted_at
  → if booking waitlisted: set cancelled
  → COMMIT
  → 204
```

Promotion is part of the cancellation transaction. If promotion fails, the
cancellation must roll back; a freed seat must not be lost. Emit counters only
after commit.

### Check in

```text
POST /api/bookings/{id}/check-in
  → authenticate, load booking + session, check host
  → check window: starts_at - 2h <= now <= starts_at + duration
  → check status == confirmed
  → set checked_in, checked_in_at
  → 200
```

`checked_in` still counts against capacity. The capacity query includes both
`confirmed` and `checked_in`.

## Authentication and authorization

- Argon2id password hashes.
- Signed JWT in an `HttpOnly`, `SameSite=Lax`, `Secure` (prod) cookie.
- 8-hour lifetime, no refresh token in v1.
- Mutations require `X-Requested-With: openseat` to block simple CSRF.
- Ownership checks:
  - host actions compare `session.host_id` with the current user;
  - guest actions compare `booking.user_id` with the current user;
  - non-owner requests return 404 for objects they cannot see, 403 only when
    existence is already public (for example, a signed-in non-host requesting a
    roster for a public session).

## Contract policy

`openapi.yaml` at the repository root is generated from the frontend service
layer and is the target the backend implements. FastAPI also generates a schema
at `/openapi.json`.

CI runs `scripts/check_contract.py`, which asserts that every path and method in
`openapi.yaml` exists in the generated schema and vice versa. Schema-level
differences are reported as warnings in v1; the path/method mismatch is
blocking. This catches the common failure where the frontend calls an endpoint
the backend never implemented, without pretending to be a full contract test.

If the team decides to drop `openapi.yaml`, delete the check and document the
decision. Do not keep a contract that nobody verifies.

## Data

The schema is defined in `_docs/spec.md`. The important constraints:

- partial unique index on active bookings per user and session;
- check constraints on capacity and duration;
- `citext` for case-insensitive email;
- timestamps stored as `timestamptz` in UTC.

Migrations are the only way the schema changes. `create_all` is forbidden in
application code. The release step runs `alembic upgrade head`.

## Deployment topology

| Environment | App | Database | Trigger |
| --- | --- | --- | --- |
| dev | `openseat-dev` | `openseat-dev-db` | push to `main` |
| prod | `openseat-prod` | `openseat-prod-db` | manual promotion |

- One image tag `YYYYMMDD-HHMMSS-shortsha`, pushed to GHCR.
- The same digest is deployed to dev and promoted to prod.
- Fly release command runs migrations before the new version starts.
- `/healthz` checks the database and returns the deployed version.
- Rollback deploys a previous tag; migrations must be backward compatible for
  one release.

## Observability

- OTel resource: `service.name=openseat`,
  `deployment.environment=dev|prod`, `service.version=<tag>`.
- Spans: HTTP request, `book_seat`, `cancel_booking`, `promote_waitlist`,
  `check_in`, SQL statements (auto).
- Metrics: see `_docs/spec.md` and `observability/README.md`.
- Logs: JSON, with `trace_id` and `span_id`; no PII.
- Alerts: symptom-based; see `_docs/runbook.md`.

## Decisions and trade-offs

| Decision | Why | Cost |
| --- | --- | --- |
| One container | Simpler deploy, same origin, no CORS in prod | Frontend rebuild required for UI changes |
| Cookie session | No token in JS, simpler logout | CSRF handling, no native client in v1 |
| Polling every 10s | No WebSocket infrastructure | Up to 10s staleness |
| Row lock per session | Correct capacity under concurrency | Serialises bookings per session |
| No notifications | Keeps scope small | Guests must check the page |
| Fly.io | Image-based deploy, two environments, low cost | Vendor-specific config, less course parity than AWS |
| Grafana Cloud | Fast path to correlated telemetry | Vendor dependency, free-tier limits |
