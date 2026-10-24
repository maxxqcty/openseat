# AGENTS.md

OpenSeat is a booking and waitlist app for small workshops. Read
`_docs/spec.md` before changing behaviour.

## Commands

These targets are created by issue #1. If a target is missing, the bootstrap
task has not landed yet.

```bash
make install     # backend + frontend dependencies
make dev         # run backend and frontend locally
make test        # backend unit + frontend unit + integration
make e2e         # Playwright against docker-compose.yaml
make lint        # ruff, mypy, eslint, tsc
make fmt         # format backend and frontend
docker compose up --build   # full stack with Postgres
```

Backend-only:

```bash
cd backend
uv run pytest
uv run pytest tests/unit/test_booking_rules.py
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8091
```

Frontend-only:

```bash
cd frontend
npm run dev
npm run test
npm run build
```

## Documents

Read only what the task needs.

- `_docs/spec.md` — product scope, domain rules, acceptance scenarios, API.
- `_docs/process.md` — roles, lifecycle, closure rules, commit conventions.
- `_docs/task-template.md` — the four-section issue template.
- `_docs/team/pm.md` — grooming role.
- `_docs/team/swe.md` — implementation role.
- `_docs/team/qa.md` — verification role.
- `_docs/architecture.md` — components, data model, contract policy.
- `_docs/testing.md` — test pyramid, commands, fixtures.
- `_docs/runbook.md` — alerts and incident response.
- `.opencode/skills/ai-shipping/SKILL.md` — the end-to-end build/ship/operate
  method for this project. Load it when starting a new stage.

## Rules

- Work one GitHub issue at a time. Read the acceptance criteria before starting
  and again before declaring done.
- Do not change acceptance criteria. If one is wrong or impossible, comment on
  the issue and stop.
- Do not close issues. The orchestrator closes only after QA outputs PASS.
- Keep all API calls in `frontend/src/services/`. No `fetch` in components.
- Keep domain rules in `backend/app/services/`, not in routers.
- The seat invariant is `confirmed + checked_in <= capacity`. Protect it in a
  transaction with a row lock.
- Store timestamps in UTC; convert only for display.
- Write tests for new behaviour, including at least one failure path.
- Commit after every meaningful step. Use `feat:`, `fix:`, `test:`, `docs:`,
  `refactor:`, `chore:`. Reference the issue number.
- Never commit secrets, `.env`, database dumps, or tokens.
- Never send emails, display names, passwords, cookies, or tokens to telemetry.
- Never deploy to production by hand. Use the promotion workflow.
- New dependencies need a reason in the issue or PR. Prefer the standard
  library and the existing stack.
- If corrected twice on the same point, update the relevant document before
  continuing.

## Stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 |
| Frontend | Node 22, React, TypeScript, Vite, React Router, Tailwind |
| Tests | pytest, httpx, React Testing Library, Playwright |
| Container | Multi-stage Dockerfile, non-root, healthcheck |
| Deploy | Fly.io apps `openseat-dev` and `openseat-prod`, GHCR images |
| Telemetry | OpenTelemetry to Grafana Cloud |

## Definition of done

- Every acceptance criterion in the issue is implemented.
- Tests cover the new behaviour and the whole suite passes.
- `make lint` passes.
- The change is committed and pushed to a branch.
- The issue has a comment describing what changed and how it was verified.
- The issue remains open for QA.

## Current stage

Scaffold. The backlog is `_docs/backlog.md`; issues 1–20 are staged in
`_docs/issues/` and can be created with `python scripts/create_issues.py`.
