# OpenSeat

> Fill every seat, without overbooking.

OpenSeat is a booking and waitlist app for small workshops. A host publishes a
session with a fixed capacity. Guests reserve a seat, join a waitlist when the
session is full, and are promoted automatically when someone cancels. At the
door, the host checks guests in from the roster.

**Status:** scaffold. The implementation follows the 20-issue backlog in
`_docs/backlog.md`.

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

## Local development

Prerequisites: Python 3.12, [uv](https://docs.astral.sh/uv/), Node 22+, npm,
make, Docker with Compose v2, and `gh` for the issue workflow.

```bash
cp .env.example .env       # macOS / Linux
Copy-Item .env.example .env  # Windows PowerShell
make install
make dev
```

These targets are created by issue #1; until it lands, the repository contains
the specification and backlog only.

- Frontend: http://localhost:5173
- API: http://localhost:8091
- API docs: http://localhost:8091/docs

Full stack with Postgres:

```bash
docker compose up --build
```

## Tests

```bash
make test   # backend unit, frontend unit, integration
make e2e    # Playwright against docker-compose.yaml
make lint
```

The test strategy is in `_docs/testing.md`.

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
definitions live in `observability/`. The runbook is `_docs/runbook.md`.

## How this project is built

The work follows a PM → SWE → QA lifecycle, with each role in a fresh context.

- Specification and acceptance criteria: `_docs/spec.md`
- Working agreement: `_docs/process.md`
- Roles: `_docs/team/`
- Backlog: `_docs/backlog.md`
- Issue sources: `_docs/issues/`

## Publish the repository and issues

The local repository has one commit. Authenticate the GitHub CLI, create the
public repository, and open the backlog:

```bash
gh auth login
gh repo create openseat --public --source=. --remote=origin --push
python scripts/create_issues.py --dry-run
python scripts/create_issues.py
```

If `openseat` is already taken, choose a unique name such as
`openseat-zoomcamp`. If the remote already exists, push with
`git push -u origin main` and then run the issue script.

The script creates the labels, creates all 20 issues in dependency order, adds
dependency comments, and writes `.issue-map.json` (git-ignored).

## Repository map

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
