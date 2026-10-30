---
title: "Production Dockerfile and one-command Compose stack"
labels: ["infra", "docker"]
depends_on: ["11", "12"]
---

## Goal

One command starts the full product locally, and one image can be deployed to
any environment.

## Acceptance criteria

- [ ] A multi-stage `Dockerfile` builds the frontend, installs backend
      production dependencies, and runs FastAPI as a non-root user.
- [ ] One container serves the built React app and `/api` on the same origin;
      client-side routes fall back to `index.html` without shadowing `/api`.
- [ ] The image exposes port 8080 and has a healthcheck against `/healthz`.
- [ ] The final image contains no dev dependencies, source maps, `.env`, or
      secrets, and is under 400 MB.
- [ ] `docker-compose.yaml` starts PostgreSQL 16 and the app, waits for the
      database healthcheck, and applies migrations before the app starts.
- [ ] `SESSION_SECRET` comes from the environment or `.env`; no default secret
      is baked into the image.
- [ ] PostgreSQL data persists in a named volume; `docker compose down -v`
      removes it.
- [ ] `make docker-up`, `make docker-down`, and `make seed` work on Windows,
      macOS, and Linux.
- [ ] `docker compose up --build` serves the UI, `/healthz` returns 200, and a
      booking flow works with cookies.
- [ ] The image carries OCI labels for source, revision, version, and title.
- [ ] README documents the Compose workflow and the seed command.

## Out of scope

- Deployment to Render. Issue #15.
- Multi-architecture builds, Kubernetes, and a separate frontend container.
- Seeding automatically in production.

## Constraints

- Base images: `python:3.12-slim` and `node:22-alpine`; pin to a minor version.
- Use `uv sync --frozen --no-dev` and `npm ci` in the build.
- Do not run the Vite dev server in production.
- Add `.dockerignore` for `node_modules`, `.venv`, `.git`, tests, and caches.
- Keep the release command separate from the image entrypoint so migrations can
  be controlled during deployment.
