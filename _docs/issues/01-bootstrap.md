---
title: "Bootstrap repository, tooling, CI skeleton, and health endpoint"
labels: ["setup", "backend", "ci"]
depends_on: []
---

## Goal

A fresh clone can install dependencies, run the app, run tests, and pass CI with
a minimal backend and frontend.

## Acceptance criteria

- [ ] `backend/` is a uv project on Python 3.12 with FastAPI, Pydantic v2,
      pytest, ruff, and mypy.
- [ ] `GET /healthz` returns 200 and JSON with `status`, `version`, and
      `database` fields; the database field is `"not_configured"` until issue
      #04.
- [ ] `frontend/` is a Vite React TypeScript app with Tailwind, Vitest, ESLint,
      and a smoke test.
- [ ] The landing route renders an OpenSeat placeholder with the product name
      and a link to the sign-in placeholder.
- [ ] Root `Makefile` exposes `install`, `dev`, `test`, `lint`, and `fmt`.
- [ ] `make dev` starts the API on port 8091 and Vite on port 5173 through
      `scripts/dev.py`; Ctrl+C stops both.
- [ ] `make test` runs backend and frontend tests; `make lint` runs ruff, mypy,
      eslint, and `tsc --noEmit`.
- [ ] `.github/workflows/ci.yml` runs backend and frontend jobs on push and pull
      request; the jobs are independent and green.
- [ ] `.env.example`, `.gitignore`, and a quickstart in `README.md` are present;
      no secrets are committed.
- [ ] A short "Prerequisites" section lists Python 3.12, uv, Node 22+, npm,
      make, and Docker.

## Out of scope

- Database models or migrations. Issue #04.
- Authentication and product behaviour.
- Dockerfile and Compose. Issue #13.
- Deployment. Issue #15.

## Constraints

- Backend entry point: `backend/app/main.py`; use an app factory.
- Frontend source: `frontend/src/`; do not add a component library.
- Use Tailwind, not a hand-written CSS framework.
- Node 22 in CI even if the local Node is newer.
- No `create_all` in application code.
- Do not add a state-management or data-fetching library.
