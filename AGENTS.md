# AGENTS.md

OpenSeat is a booking and waitlist app for small workshops. Read
`_docs/spec.md` before changing behaviour, and `_docs/architecture.md` before
changing a flow or a deployment path.

## Commands

Run `make install` once, then use these targets from the repository root.

```bash
make install     # backend + frontend dependencies
make dev         # run backend and frontend locally
make test        # backend unit + frontend unit + integration
make e2e         # Playwright against docker-compose.yaml
make lint        # ruff (app, on-call, scripts), mypy, eslint, tsc
make fmt         # format backend and frontend
make audit       # pip-audit and npm audit --omit=dev
docker compose up --build   # full stack with Postgres
```

Backend-only:

```bash
cd backend
uv run pytest
uv run pytest tests/unit/test_booking_rules.py
uv run pytest tests/unit/test_oncall_worker.py
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

Deploy and operations:

```bash
make render-validate                     # offline Blueprint check
make render-verify URL=https://openseat-9b15.onrender.com
make render-deploy-hook ARGS="--dry-run" # guarded hook, dry run locally
make render-promote ARGS="--dry-run"     # paid same-digest promotion
make render-rollback ARGS="--dry-run"    # paid rollback
make on-call ARGS="--dry-run --alert-file <path>"
```

## Documents

Read only what the task needs.

- `_docs/spec.md` — product scope, domain rules, acceptance scenarios, API.
- `_docs/process.md` — roles, lifecycle, closure rules, commit conventions.
- `_docs/task-template.md` — the four-section issue template.
- `_docs/team/pm.md` — grooming role.
- `_docs/team/swe.md` — implementation role.
- `_docs/team/qa.md` — verification role.
- `_docs/architecture.md` — components, data model, contract policy, CI/CD,
  on-call, decisions, and known deviations.
- `_docs/testing.md` — test pyramid, commands, fixtures, required coverage.
- `_docs/runbook.md` — alerts and incident response.
- `_docs/security.md` — audit results, controls, residual risks.
- `_docs/RUBRIC.md` — 12 criteria, 24 points, claimed evidence, submission
  checklist.
- `_docs/evidence/README.md` — repository evidence versus pending external
  captures.
- `observability/README.md` — Grafana import, thresholds, alert wiring.
- `on-call/README.md` — worker configuration, token scope, chaos demo.
- `deploy/render/README.md` — Render Blueprint, deploy hook, promotion,
  rollback, free-tier limits.
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
- Never deploy to production by hand. The deploy job runs only after E2E on
  `main`; the paid path uses the promotion workflow with a typed confirmation.
- Do not weaken or delete a test to make a suite pass.
- Do not add external evidence that does not exist. Pending captures stay
  pending in `_docs/evidence/README.md`.
- New dependencies need a reason in the issue or PR. Prefer the standard
  library and the existing stack.
- If corrected twice on the same point, update the relevant document before
  continuing.

## Stack

| Layer | Choice |
| --- | --- |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL 16 |
| Frontend | Node 22, React, TypeScript, Vite, React Router, Tailwind |
| Tests | pytest, httpx, React Testing Library, Playwright |
| Container | Multi-stage Dockerfile, non-root, healthcheck |
| Deploy | Render Blueprint: one free web service and one free Postgres |
| Telemetry | OpenTelemetry to Grafana Cloud |
| CI/CD | GitHub Actions, build once, GHCR image, E2E gate, guarded deploy hook |
| On-call | Grafana Alerting -> worker -> isolated worktree -> draft PR |

## Definition of done

- Every acceptance criterion in the issue is implemented.
- Tests cover the new behaviour and the whole suite passes.
- `make lint` passes.
- The change is committed and pushed to a branch.
- The issue has a comment describing what changed and how it was verified.
- The issue remains open for QA.

## Current stage

v1.0.0 is implemented. The backend, frontend, local dev runner, Docker stack,
tests, lint, CI/CD, telemetry, dashboard, alerts, runbook, on-call worker, and
release docs are in place. The backlog is `_docs/backlog.md`; the release claim
table is `_docs/RUBRIC.md`. Remaining work is external evidence: a live Grafana
capture, a chaos run and draft PR, the demo video, and peer reviews.
