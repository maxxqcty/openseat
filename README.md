# OpenSeat

> Fill every seat, without overbooking.

[![CI](https://github.com/maxxqcty/openseat/actions/workflows/ci.yml/badge.svg)](https://github.com/maxxqcty/openseat/actions/workflows/ci.yml)

OpenSeat is a booking and waitlist app for small workshops. A host publishes a
session with a fixed number of seats. Guests book a seat, or join the waitlist
when it is full, and the oldest waiter is promoted automatically when someone
cancels. At the door, the host checks guests in from the roster.

**Live demo:** <https://openseat-9b15.onrender.com>
(free tier: the first request after idle takes about a minute to wake)

## The problem

Workshop hosts run sign-ups through group chats and spreadsheets. When someone
cancels, the host messages the next person by hand and a seat sits empty.
OpenSeat keeps the roster, waitlist, and check-in list in one place and fills a
cancelled seat on its own.

## How it works

```text
Host creates a session (capacity 1)
Guest A books      -> Confirmed
Guest B books      -> Waitlisted (position 1)
Guest A cancels    -> Guest B is promoted automatically
Host checks B in   -> Checked in (still holds the seat)
```

| Role | What they can do |
| --- | --- |
| Host | Create and cancel sessions, view the roster, check guests in |
| Guest | Browse, book, join the waitlist, cancel, see their status |

**Features:** email/password accounts (HttpOnly cookies), race-safe booking that
never exceeds capacity, waitlist positions, check-in from two hours before the
start, an OpenAPI contract checked in CI, and OpenTelemetry traces, metrics and
logs with a Grafana dashboard, alerts and an on-call worker.

**Out of scope:** payments, email, recurring sessions, uploads, teams, seat maps.

## Quick start

You need Python 3.12 with [uv](https://docs.astral.sh/uv/), Node.js 22+, GNU
Make (Git Bash or WSL on Windows), and Docker for the full stack.

```bash
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
make install
make dev
```

| What | URL |
| --- | --- |
| Frontend | <http://localhost:5173> |
| API | <http://localhost:8091> (docs at `/docs`, health at `/healthz`) |

`make dev` needs `DATABASE_URL` in `.env` (see `.env.example`) and a running
PostgreSQL. To run everything, including Postgres, in one command:

```bash
docker compose up --build     # app at http://localhost:8080
```

### Demo data

```bash
make seed          # demo users, sessions and bookings (development only)
make seed-reset    # remove the seeded rows, then recreate them
```

Seeded accounts share the password `openseat-dev-password`:
`host@example.com`, `guest-a@example.com`, `guest-b@example.com`.

## Tests

```bash
make test    # backend unit + integration, frontend unit
make e2e     # Playwright: host and two guests against the Compose stack
make lint    # ruff, mypy, eslint, tsc
```

See [`_docs/testing.md`](_docs/testing.md) for the strategy. The API contract is
`openapi.yaml`; CI fails if the app and the contract drift apart.

## Deploying

The demo runs on [Render](https://render.com) (free web service and free
Postgres) from `render.yaml`, in one Docker container that serves the frontend
and the API. Every push to `main` runs CI, then the E2E suite, then deploys.

```bash
make render-validate                                 # check render.yaml offline
make render-verify URL=https://openseat-9b15.onrender.com
```

Free-tier caveats: the service sleeps after 15 minutes idle, and the free
database **expires 30 days after creation**. Setup, deploy hook, promotion and
rollback are in [`deploy/render/README.md`](deploy/render/README.md).

## Tech stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16 |
| Frontend | React, TypeScript, Vite, Tailwind |
| Tests | pytest, React Testing Library, Playwright |
| Delivery | Docker, GitHub Actions, Render |
| Telemetry | OpenTelemetry to Grafana Cloud |

## Documentation

| Topic | Where |
| --- | --- |
| Product scope and rules | [`_docs/spec.md`](_docs/spec.md) |
| Architecture and decisions | [`_docs/architecture.md`](_docs/architecture.md) |
| Observability setup | [`observability/README.md`](observability/README.md) |
| Runbook for the alerts | [`_docs/runbook.md`](_docs/runbook.md) |
| On-call worker | [`on-call/README.md`](on-call/README.md) |
| Security audit | [`_docs/security.md`](_docs/security.md) |
| Evidence and rubric | [`_docs/evidence/README.md`](_docs/evidence/README.md), [`_docs/RUBRIC.md`](_docs/RUBRIC.md) |
| Backlog and process | [`_docs/backlog.md`](_docs/backlog.md), [`_docs/process.md`](_docs/process.md) |

## Status

v1.0.0 is implemented. Evidence that needs a Grafana account, a live chaos run,
a recording or reviewers (dashboard screenshots, the on-call draft PR, the demo
video, peer reviews) is still **pending** and tracked in
[`_docs/evidence/README.md`](_docs/evidence/README.md).
