# Architecture

> This document describes the code that exists in v1.0.0. The backlog in
> `_docs/backlog.md` records how it was built. Deviations from the original
> issue constraints are listed in the decisions table at the end.

## Context

OpenSeat is a single web application with a React frontend, a FastAPI backend,
and PostgreSQL. One container serves the built frontend and the API in
production.

```text
Client
  |
  | HTTPS, HttpOnly cookie
  v
FastAPI (one process)
  +-- /api/*          JSON API
  +-- /*              static React build
  +-- SQLAlchemy --> PostgreSQL
  +-- OTLP --------> Grafana Cloud

On-call worker (separate process)
  +-- polls Grafana Alerting
  +-- builds a redacted packet
  +-- creates an isolated worktree
  +-- starts a headless coding agent -> draft PR
```

The on-call worker never deploys, merges, or writes to production.

## Components

| Component | Responsibility | Location |
| --- | --- | --- |
| API routers | HTTP validation, auth, status codes | `backend/app/api/` |
| Domain services | Booking, waitlist, promotion, check-in rules | `backend/app/services/` |
| Models | SQLAlchemy mappings | `backend/app/models/` |
| Schemas | Pydantic request/response models | `backend/app/schemas/` |
| Telemetry | OTel providers, metrics, JSON logs, redaction | `backend/app/telemetry.py` |
| Frontend services | One place for every API call | `frontend/src/services/` |
| Pages/components | Rendering and interaction | `frontend/src/pages/`, `frontend/src/components/` |
| On-call worker | Alert polling, evidence packet, agent launch | `on-call/` |
| Observability assets | Dashboard, alerts, setup guide | `observability/` |
| CI/CD | Build once, E2E gate, guarded deploy, promote, rollback | `.github/workflows/` |

## Request flows

### Book a seat

```text
POST /api/sessions/{id}/bookings
  + authenticate cookie
  + validate session is scheduled and not past
  + BEGIN
  + SELECT session FOR UPDATE
  + count active confirmed + checked_in
  + if count < capacity: insert confirmed
    else: insert waitlisted, compute position
  + COMMIT
  + 201 booking
```

The row lock serialises concurrent bookings for the same session. Different
sessions proceed in parallel. The count is never taken outside the locked
transaction.

### Cancel and promote

```text
DELETE /api/bookings/{id}
  + authenticate, load booking, check owner
  + BEGIN
  + SELECT session FOR UPDATE
  + if booking confirmed: set cancelled
      + select oldest waitlisted FOR UPDATE
      + if exists: set confirmed, promoted_at
  + if booking waitlisted: set cancelled
  + COMMIT
  + 204
```

Promotion is part of the cancellation transaction. If promotion fails, the
cancellation rolls back; a freed seat is not lost.

### Check in

```text
POST /api/bookings/{id}/check-in
  + authenticate, load booking + session, check host
  + check window: starts_at - 2h <= now <= starts_at + duration
  + check status == confirmed
  + set checked_in, checked_in_at
  + 200
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
    existence is already public.

## Contract policy

`openapi.yaml` at the repository root is canonical. It documents every
endpoint, the error shape, the session cookie, and the CSRF header. The types
in `frontend/src/services/api-types.ts` mirror its schemas, and FastAPI also
generates a schema at `/openapi.json`.

CI runs `scripts/check_contract.py`, which asserts that every path and method
in `openapi.yaml` exists in the generated schema and vice versa. Path or method
mismatches are blocking; schema-level differences are warnings in v1.

## Data

The schema is defined in `_docs/spec.md`. The important constraints:

- partial unique index on active bookings per user and session;
- check constraints on capacity and duration;
- `citext` for case-insensitive email;
- timestamps stored as `timestamptz` in UTC.

Migrations are the only way the schema changes. `create_all` is forbidden in
application code. The container entrypoint runs `alembic upgrade head` before
uvicorn.

## Deployment topology

| Environment | App | Database | Trigger |
| --- | --- | --- | --- |
| prod/demo | `openseat` on Render | `openseat-db` (free, expires after 30 days) | merge to `main` after CI and E2E |
| local dev | Docker Compose | `db` container | manual |

- Render builds the root Dockerfile from `render.yaml`. The free tier has no
  prebuilt-image promotion and no separate hosted dev environment.
- The container entrypoint runs `alembic upgrade head` before uvicorn; a failed
  migration stops the service start.
- `/healthz` checks the database and returns the deployed commit
  (`RENDER_GIT_COMMIT`).
- Rollback redeploys a previous Render deploy; migrations must be backward
  compatible for one release.

## CI/CD

Every pull request and push runs four jobs:

1. **backend** - ruff, mypy, migrations, drift check, pytest against Postgres.
2. **contract** - `scripts/check_contract.py`.
3. **frontend** - eslint, tsc, vitest, production build.
4. **build** - builds the root Dockerfile once, saves the image, and on `main`
   pushes it to GHCR as `YYYYMMDD-HHMMSS-<shortsha>`.

The **e2e** job downloads the saved image, loads it, and runs Playwright against
that exact artifact. The **deploy** job runs only on `main`, only after E2E,
and calls the Render deploy hook when `RENDER_DEPLOY_HOOK_URL` is configured.
It then verifies `/healthz` with `EXPECTED_VERSION` set to the commit SHA.

`autoDeployTrigger: checksPass` is the fallback when Render can detect GitHub
checks. The deploy hook is the documented fallback when it cannot. Neither path
deploys before E2E.

The paid promotion workflow (`.github/workflows/promote.yml`) uses the same
GHCR digest, never rebuilds, requires the `production` GitHub Environment, and
requires the operator to type `promote`. The rollback workflow
(`.github/workflows/rollback.yml`) redeploys a previous Render deploy and
requires the operator to type `rollback`.

## Observability

- OTel resource: `service.name=openseat`,
  `deployment.environment=<APP_ENV>`, `service.version=<APP_VERSION or commit>`.
- Spans: HTTP request, `book_seat`, `cancel_booking`, `promote_waitlist`,
  `check_in`, SQL statements (auto).
- Metrics: HTTP traffic and latency, bookings by result, promotions,
  open-seat-with-waitlist, overbooked sessions.
- Logs: JSON, with `trace_id` and `span_id`; no PII.
- Alerts: symptom-based; see `_docs/runbook.md`.
- Dashboard and alert assets: `observability/`.

Export is disabled when `OTEL_EXPORTER_OTLP_ENDPOINT` is empty. Tests pass an
in-memory span exporter and metric reader instead of contacting Grafana.

## On-call worker

`on-call/worker.py` polls Grafana every 60 seconds, filters to page-severity
alerts in the configured environment, and deduplicates by fingerprint. It
writes state, packets, transcripts, and worktrees outside the repository. The
agent environment is an allowlist; it never receives production secrets. The
worker rejects changes to `.github/`, `render.yaml`, `deploy/`, `on-call/`, and
`observability/`. A 20-minute timeout bounds every run. The agent opens a draft
PR; a human reviews and merges it.

## Decisions and trade-offs

| Decision | Why | Cost |
| --- | --- | --- |
| One container | Simpler deploy, same origin, no CORS in prod | Frontend rebuild required for UI changes |
| Cookie session | No token in JS, simpler logout | CSRF handling, no native client in v1 |
| Polling every 10s | No WebSocket infrastructure | Up to 10s staleness |
| Row lock per session | Correct capacity under concurrency | Serialises bookings per session |
| No notifications | Keeps scope small | Guests must check the page |
| Render free tier | Free Docker hosting and Postgres, Blueprint in git | Database expires after 30 days; one hosted environment; cold starts |
| Grafana Cloud | Fast path to correlated telemetry | Vendor dependency, free-tier limits |
| Build once in CI | E2E and deploy use the same bytes | Slightly longer CI; image artifact retention |
| Deploy hook after E2E | Guarantees the gate even if Render cannot read checks | Requires a repository secret |
| DB-backed observable gauges | Survive process restarts and report the real invariant | A database query per metric collection |
| Exact OTel pins | Instrumentation packages have tight version coupling | Manual upgrade cadence |
| SQLAlchemy `<2.1` | OTel SQLAlchemy instrumentation rejects 2.1 | Cannot use SQLAlchemy 2.1 yet |
| Alpine base image | Smaller image and faster cold starts | **Deviation from issue #13's `python:3.12-slim` constraint** |
| Telemetry off without endpoint | Local tests and Compose need no Grafana account | No telemetry until the operator configures OTLP |
| On-call state outside repo | Packets and transcripts may contain sensitive context | Operator must back up `~/.openseat/on-call` if needed |
| Free plan uses Git deploy | Render free tier cannot promote an image | Paid promotion path is documented but not active |

## Known deviations

1. **Alpine instead of Debian slim.** Issue #13 specified
   `python:3.12-slim`. The root `Dockerfile` uses Alpine to keep the image
   small and reduce cold-start cost on Render. The runtime still uses Python
   3.12, a non-root user, and a healthcheck.
2. **No separate public dev environment.** Issue #15 and #16 describe dev and
   prod. Render's free tier allows one web service and one free Postgres
   database, so the hosted demo is the only public environment. Development is
   local Compose. The paid two-environment path is documented in
   `deploy/render/README.md` and the promotion workflow.
3. **Deploy hook secret is operator-supplied.** The workflow is implemented,
   but `RENDER_DEPLOY_HOOK_URL` must be added to the GitHub repository secrets
   before the guarded hook can run. Until then, `checksPass` is the fallback.
4. **External evidence is pending.** Grafana screenshots, a live alert
   notification, the demo video, the live chaos run, and peer reviews require
   accounts or humans. They are listed in `_docs/evidence/README.md` and are
   not simulated.
