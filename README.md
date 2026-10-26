# OpenSeat

> Fill every seat, without overbooking.

[![CI](https://github.com/maxxqcty/openseat/actions/workflows/ci.yml/badge.svg)](https://github.com/maxxqcty/openseat/actions/workflows/ci.yml)

OpenSeat is a booking and waitlist app for small workshops. A host publishes a
session with a fixed capacity. Guests reserve a seat, join a waitlist when the
session is full, and are promoted automatically when someone cancels. At the
door, the host checks guests in from the roster.

**Status:** bootstrap complete. The API and web shell run locally, and CI runs
backend and frontend checks on every push and pull request. The 20-issue
backlog is open in the
[issue tracker](https://github.com/maxxqcty/openseat/issues); feature work
continues with issue #2.

- Repository: <https://github.com/maxxqcty/openseat>
- Tracker: <https://github.com/maxxqcty/openseat/issues>

---

## The problem

Small workshop hosts run sign-ups through group chats, forms, and spreadsheets.
When someone cancels, the host messages the next person by hand, and a seat sits
empty while someone is waiting. Attendance is tracked on paper or not at all.

OpenSeat keeps the roster, the waitlist, and the check-in list in one place, and
fills a cancelled seat automatically.

## Users and core flow

| Role | What they do |
| --- | --- |
| Host | Create a session, watch the roster, check guests in, cancel if needed |
| Guest | Browse, book, join the waitlist, cancel, see status |

```text
Host creates a session (capacity 1)
        │
Guest A books ──────────────► Confirmed
        │
Guest B books ──────────────► Waitlisted (position 1)
        │
Guest A cancels ────────────► Guest B promoted automatically
        │
Host checks B in ───────────► Checked in (still occupies the seat)
```

## Features (v1)

- Public browse of upcoming sessions.
- Email/password accounts with HttpOnly cookie sessions.
- Host-created sessions with capacity, time, duration, and location.
- Race-safe booking that never exceeds capacity.
- Waitlist with position and automatic promotion of the oldest waiter.
- Host roster grouped by confirmed, waitlisted, and checked in.
- Check-in windowed to two hours before the start until the session ends.
- Session cancellation by the host.
- Metrics, traces, and structured logs for the booking journey.
- Alerts on user-visible failures and an AI on-call responder.

Out of scope: payments, email, recurring sessions, uploads, teams, seat maps.
See `_docs/spec.md` for the full list.

## Architecture

```text
Browser (React + Vite)
   │  same-origin /api
   ▼
FastAPI ── SQLAlchemy ── PostgreSQL
   │
   └── OTLP ──► Grafana Cloud (metrics, logs, traces, alerts)
                        │
                        ▼
                on-call worker ──► headless coding agent
                                      └── isolated branch / draft PR
```

In production one container serves the built frontend and the API. In
development, Vite proxies `/api` to FastAPI so cookies and paths behave the same
way.

| Layer | Choice |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 |
| Frontend | React, TypeScript, Vite, React Router, Tailwind |
| Tests | pytest, httpx, React Testing Library, Playwright |
| Deploy | Fly.io (`openseat-dev`, `openseat-prod`), GHCR images |
| Telemetry | OpenTelemetry → Grafana Cloud |

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node.js 22+ and npm
- GNU Make
- Docker with Compose v2 (first used by issue #13)
- `gh` for the issue workflow

## Local development

```bash
cp .env.example .env         # macOS / Linux
Copy-Item .env.example .env  # Windows PowerShell

make install
make dev
```

`make install` runs `uv sync` in `backend/` and `npm ci` in `frontend/`.
`make dev` starts both processes through `scripts/dev.py`; Ctrl+C stops both.

- Frontend: http://localhost:5173
- API: http://localhost:8091
- Health: http://localhost:8091/healthz
- API docs: http://localhost:8091/docs

Full stack with Postgres (arrives with issue #13):

```bash
docker compose up --build
```

## Demo data

```bash
make seed         # create the demo users, sessions, and bookings
make seed-reset   # delete only the seeded rows, then recreate them
```

Seeded accounts use example.com addresses and placeholder names, and share the
development password `openseat-dev-password`:

| Account | Email |
| --- | --- |
| Host | `host@example.com` |
| Guest A | `guest-a@example.com` |
| Guest B | `guest-b@example.com` |

Seeding is safe to run twice: it refreshes the same rows instead of duplicating
them, and session start times are recomputed from the clock so the demo never
goes stale. Seeding is development-only — `uv run python -m app.seed` refuses to
run when `APP_ENV=production`, and nothing in the application calls it
automatically.

## Tests

```bash
make test   # backend unit + frontend unit
make e2e    # Playwright journey against the Compose stack
make lint   # ruff, mypy, eslint, tsc --noEmit
make fmt    # ruff and Prettier
```

The test strategy is in `_docs/testing.md`.

The end-to-end suite in `e2e/` drives three browser contexts — host, guest A,
and guest B — through sign-up, a capacity-1 booking, the waitlist, promotion
after a cancellation, and host check-in. `make e2e` drops the database volume,
rebuilds the image, waits for `/healthz`, runs the suite, and tears the stack
down again even when a test fails.

To run the same suite against an environment that is already running:

```bash
cd e2e && npm ci && npx playwright install chromium   # first time only
E2E_BASE_URL=http://localhost:8080 make e2e
```

Failures keep a trace, a screenshot, and a video in `e2e/test-results/`, and CI
uploads them as the `playwright-artifacts` artifact.

## API contract

`openapi.yaml` at the repository root is the canonical API contract. The
FastAPI app must expose every path and method it documents, and
`frontend/src/services/api-types.ts` mirrors its request and response schemas.
CI fails when either side adds or removes an endpoint without updating the
contract; schema-level differences (success status and request body) are
warnings in v1.

```bash
cd backend && uv run python ../scripts/check_contract.py
```

The check runs offline: it imports the app, never connects to a database, and
supplies its own test settings.

## Deployment

| Environment | Trigger | URL |
| --- | --- | --- |
| dev | push to `main` | _to be added_ |
| prod | manual promotion of a tested image | _to be added_ |

Images are tagged `YYYYMMDD-HHMMSS-shortsha` and promoted, never rebuilt.

## Observability

OpenTelemetry resource attributes include `service.name`,
`deployment.environment`, and `service.version`. The booking journey emits
traces, metrics, and structured logs that share a trace ID. Dashboard and alert
definitions will live in `observability/` (issues #17–#18). The runbook is
`_docs/runbook.md`.

## How this project is built

The work follows a PM → SWE → QA lifecycle, with each role in a fresh context.

- Specification and acceptance criteria: `_docs/spec.md`
- Working agreement: `_docs/process.md`
- Roles: `_docs/team/`
- Backlog: `_docs/backlog.md`
- Issue sources: `_docs/issues/`

## Repository and tracker

- Public repository: <https://github.com/maxxqcty/openseat>
- Issue tracker: <https://github.com/maxxqcty/openseat/issues>

The repository was created with `gh repo create`, and all 20 issues were opened
with `scripts/create_issues.py`. The script remains useful for a fork or for
rebuilding the tracker:

```bash
python scripts/create_issues.py --dry-run
python scripts/create_issues.py
```

It creates the labels, creates the issues in dependency order, adds dependency
comments, and writes `.issue-map.json` (git-ignored).

## Repository map

Target layout; directories appear as their issues land.

```text
backend/            FastAPI app, domain services, tests
frontend/           React app, services layer, tests
e2e/                Playwright tests
on-call/            alert worker and agent prompt
observability/      dashboard, alert rules, collector config
deploy/             Fly configuration and deployment notes
_docs/              spec, process, roles, architecture, testing, runbook
_docs/issues/       the 20 issue sources
scripts/            issue creation and maintenance scripts
```

## Roadmap

| # | Milestone |
| --- | --- |
| 1 | Repository, tooling, CI skeleton |
| 2–3 | Frontend shell and mock service layer |
| 4–9 | Auth, sessions, booking, waitlist, promotion, check-in |
| 10–12 | OpenAPI contract, Postgres, frontend integration |
| 13–16 | Containers, E2E, deployment, CI/CD |
| 17–18 | Telemetry, dashboard, alerts, runbook |
| 19 | On-call worker and chaos test |
| 20 | Documentation, demo, rubric audit |
