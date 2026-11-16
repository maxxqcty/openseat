# OpenSeat

> Fill every seat, without overbooking.

[![CI](https://github.com/maxxqcty/openseat/actions/workflows/ci.yml/badge.svg)](https://github.com/maxxqcty/openseat/actions/workflows/ci.yml)

OpenSeat is a booking and waitlist app for small workshops. A host publishes a
session with a fixed capacity. Guests reserve a seat, join a waitlist when the
session is full, and are promoted automatically when someone cancels. At the
door, the host checks guests in from the roster.

**Status:** v1.0.0. All 20 backlog issues are implemented. The public demo,
CI, Docker stack, tests, telemetry, dashboard assets, alerts, runbook, and
on-call worker are in the repository. External evidence that needs accounts or
a human (Grafana screenshots, a firing alert, the demo video, peer reviews) is
tracked honestly in [`_docs/evidence/README.md`](_docs/evidence/README.md).

- Public demo: <https://open-seat.onrender.com>
- Repository: <https://github.com/maxxqcty/openseat>
- Issue tracker: <https://github.com/maxxqcty/openseat/issues>
- Demo video: **pending external recording** (see
  [`_docs/evidence/README.md#demo-video`](_docs/evidence/README.md#demo-video))
- On-call evidence: **pending live chaos run** (see
  [`_docs/evidence/README.md#on-call`](_docs/evidence/README.md#on-call))

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
        |
Guest A books ---------------------> Confirmed
        |
Guest B books ---------------------> Waitlisted (position 1)
        |
Guest A cancels -------------------> Guest B promoted automatically
        |
Host checks B in ------------------> Checked in (still occupies the seat)
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
- OpenAPI contract checked in CI.
- OpenTelemetry traces, metrics, and structured JSON logs.
- Grafana dashboard, five page alerts, runbook, and an on-call worker that
  opens a draft pull request for human review.

Out of scope: payments, email, recurring sessions, uploads, teams, seat maps.
See [`_docs/spec.md`](_docs/spec.md).

## Architecture

```text
Browser (React + Vite)
   |
   |  same-origin /api
   v
FastAPI -> SQLAlchemy -> PostgreSQL
   |
   +-> OTLP -> Grafana Cloud (metrics, logs, traces, alerts)
                    |
                    v
            on-call worker -> headless coding agent
                    |
                    +-> isolated worktree -> draft PR (human review)
```

In production one container serves the built frontend and the API. In
development, Vite proxies `/api` to FastAPI so cookies and paths behave the same
way. The on-call worker is a separate process and never deploys.

| Layer | Choice |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL 16 |
| Frontend | React, TypeScript, Vite, React Router, Tailwind |
| Tests | pytest, httpx, React Testing Library, Playwright |
| Deploy | Render Blueprint: one free web service and one free Postgres |
| Telemetry | OpenTelemetry -> Grafana Cloud |
| CI/CD | GitHub Actions, GHCR image, guarded Render deploy hook |

## Prerequisites

- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node.js 22+ and npm
- GNU Make (Git Bash or WSL on Windows)
- Docker with Compose v2
- `gh` for the issue workflow
- A [Render](https://render.com) account to deploy (no CLI required)

## Local development

```bash
cp .env.example .env         # macOS / Linux
Copy-Item .env.example .env  # Windows PowerShell

make install
make dev
```

`make install` runs `uv sync` in `backend/` and `npm ci` in `frontend/`.
`make dev` starts both processes through `scripts/dev.py`; Ctrl+C stops both.

- Frontend: <http://localhost:5173>
- API: <http://localhost:8091>
- Health: <http://localhost:8091/healthz>
- API docs: <http://localhost:8091/docs>

Full stack with Postgres:

```bash
docker compose up --build
```

- App: <http://localhost:8080>
- Health: <http://localhost:8080/healthz>

The development environment is local Compose, not a second public Render
environment. Render's free tier allows one web service and one free Postgres
database, so a separate public dev deployment would require a paid plan. The
public demo is the only hosted environment; the dev URL is the local one above.

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

Seeding is safe to run twice and is development-only. It refuses to run when
`APP_ENV=production`.

## Tests

```bash
make test   # backend unit + integration + frontend unit
make e2e    # Playwright journey against the Compose stack
make lint   # ruff, mypy, eslint, tsc --noEmit
make fmt    # ruff and Prettier
```

The test strategy is in [`_docs/testing.md`](_docs/testing.md). The end-to-end
suite in `e2e/` drives three browser contexts (host, guest A, guest B) through
sign-up, a capacity-1 booking, the waitlist, promotion after a cancellation,
and host check-in. `make e2e` drops the database volume, builds the image,
waits for `/healthz`, runs the suite, and tears the stack down again even when a
test fails. Set `E2E_BASE_URL` to run the same suite against an existing
environment, or `E2E_IMAGE` to run against a prebuilt image.

Failures keep a trace, screenshot, and video in `e2e/test-results/`, and CI
uploads them as the `playwright-artifacts` artifact.

## API contract

`openapi.yaml` at the repository root is the canonical API contract. The
FastAPI app must expose every path and method it documents, and
`frontend/src/services/api-types.ts` mirrors its request and response schemas.
CI fails when either side adds or removes an endpoint without updating the
contract.

```bash
cd backend && uv run python ../scripts/check_contract.py
```

## Deployment

| Environment | URL | Trigger |
| --- | --- | --- |
| prod/demo | <https://open-seat.onrender.com> | merge to `main` after CI and E2E |
| local dev | <http://localhost:8080> | `docker compose up --build` |

The public demo runs on [Render](https://render.com) from the root
`render.yaml` Blueprint: one free web service (`openseat`) builds the root
`Dockerfile` in Frankfurt and serves HTTPS, and one free Postgres database
(`openseat-db`) backs it. Render generates `SESSION_SECRET` and injects
`DATABASE_URL`; no secret is committed or baked into the image.

### CI/CD

Every pull request and push runs backend lint, type check, migrations, tests,
the contract check, frontend lint, type check, tests, and build. On `main`:

1. The build job builds the root Dockerfile once and saves that exact image.
2. The E2E job loads the saved image and runs Playwright against it.
3. Only after E2E passes, the deploy job calls the Render deploy hook.
4. The workflow polls `/healthz` with `EXPECTED_VERSION` set to the commit SHA.
5. The same image is pushed to GHCR as `YYYYMMDD-HHMMSS-<shortsha>`.

`autoDeployTrigger: checksPass` remains the fallback when Render can detect the
GitHub checks. The deploy hook is the documented fallback when it cannot. Set
the `RENDER_DEPLOY_HOOK_URL` repository secret to enable it; without the
secret, the workflow warns and skips the hook rather than deploying unguarded.

The free plan deploys from Git and cannot promote a prebuilt image. The paid
path in `.github/workflows/promote.yml` promotes the exact GHCR digest to an
image-backed service without rebuilding; it requires the `production` GitHub
Environment, a required reviewer, and a typed `promote` confirmation. Rollback
is `.github/workflows/rollback.yml` (typed `rollback` confirmation) on the paid
path, or **Deploys > Rollback** in the Render dashboard on the free path.

### Free-tier limits

- The web service spins down after 15 minutes without traffic and takes about a
  minute to wake, so the first request after idle is slow.
- One free Postgres database is allowed per workspace. It has 1 GB of storage
  and **expires 30 days after creation**, so treat it as disposable.
- Pre-deploy commands are paid-only. The container entrypoint runs
  `alembic upgrade head` before uvicorn, so a failed migration stops the
  service instead of shipping a broken release.

### First deploy and verification

1. Push the repository to GitHub.
2. In the Render Dashboard choose **New > Blueprint**, connect the repository,
   and apply `render.yaml` on `main`.
3. Render creates the database, generates the secret, builds the image, and
   waits for `/healthz`.
4. Verify the deploy:

```bash
make render-validate
make render-verify URL=https://open-seat.onrender.com
```

`scripts/render.py validate` checks the Blueprint offline;
`scripts/render.py verify` polls the public URL for up to three minutes to
cover a cold start. Set `EXPECTED_VERSION=<sha>` to assert a specific deploy.

## Observability

OpenTelemetry resource attributes include `service.name`,
`deployment.environment`, and `service.version`. The booking journey emits
traces, metrics, and structured logs that share a trace ID. Export is disabled
when `OTEL_EXPORTER_OTLP_ENDPOINT` is empty, so local tests need no Grafana
account.

- Dashboard: [`observability/dashboard.json`](observability/dashboard.json)
- Alerts: [`observability/alerts.yaml`](observability/alerts.yaml)
- Setup and thresholds: [`observability/README.md`](observability/README.md)
- Runbook: [`_docs/runbook.md`](_docs/runbook.md)
- On-call worker: [`on-call/README.md`](on-call/README.md)

The dashboard filters every panel by `environment` and `version`. The five
page alerts are `OpenSeatDown`, `OpenSeatHighErrorRate`,
`OpenSeatBookingErrors`, `OpenSeatWaitlistStalled`, and `OpenSeatOverbooked`.
Every alert carries `owner`, `dashboard_url`, and `runbook_url` annotations.
The production waitlist alert waits 10 minutes; a development-only copy waits
2 minutes for the demo.

The on-call worker polls Grafana every 60 seconds, deduplicates by alert
fingerprint, builds a redacted evidence packet, creates an isolated worktree,
and runs a headless coding agent with a 20-minute timeout. It records the
transcript, branch, and draft PR URL. It cannot merge, deploy, or change
workflows, and a human reviews every change.

## Security

- Secrets live in Render or GitHub Environment secrets, never in the
  repository or the image.
- The agent environment is an allowlist; it never receives `RENDER_API_KEY`,
  `DATABASE_URL`, `SESSION_SECRET`, the Grafana token, or OTLP headers.
- Telemetry and the on-call packet redact emails, display names, cookies,
  authorization headers, passwords, tokens, and request bodies.
- Dependencies were scanned with `uv run pip-audit`, `npm audit --omit=dev`,
  and `gitleaks detect`. Results are in
  [`_docs/security.md`](_docs/security.md).

## Evidence

The evidence index is [`_docs/evidence/README.md`](_docs/evidence/README.md).
It distinguishes repository evidence (tests, CI, Docker, dashboard files) from
external evidence that requires a Grafana account, a live chaos deploy, a
recording, or peer reviewers. The rubric claim table is
[`_docs/RUBRIC.md`](_docs/RUBRIC.md).

## Repository map

```text
backend/            FastAPI app, domain services, tests
frontend/           React app, services layer, tests
e2e/                Playwright tests
on-call/            alert worker, chaos helper, agent brief
observability/      dashboard, alert rules, setup guide
deploy/             Render deployment notes
_docs/              spec, process, architecture, testing, runbook, evidence
_docs/issues/       the 20 issue sources
scripts/            issue creation, contract, Render, E2E, dev helpers
```

## Documentation

- Product scope and acceptance scenarios: [`_docs/spec.md`](_docs/spec.md)
- Architecture and decisions: [`_docs/architecture.md`](_docs/architecture.md)
- Testing strategy: [`_docs/testing.md`](_docs/testing.md)
- Operational runbook: [`_docs/runbook.md`](_docs/runbook.md)
- Rubric and submission checklist: [`_docs/RUBRIC.md`](_docs/RUBRIC.md)
- Security audit: [`_docs/security.md`](_docs/security.md)
- Working agreement: [`_docs/process.md`](_docs/process.md)
- Backlog: [`_docs/backlog.md`](_docs/backlog.md)
