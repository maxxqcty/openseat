---
title: "Deploy the demo to Render with PostgreSQL"
labels: ["infra", "deploy"]
depends_on: ["13"]
---

## Goal

A public HTTPS demo runs the root Docker image with a managed PostgreSQL
database and generated secrets, deployed from `render.yaml` on Render's free
tier.

## Acceptance criteria

- [ ] `render.yaml` at the repository root defines one free Docker web service
      (`openseat`) and one free PostgreSQL database (`openseat-db`) in
      Frankfurt.
- [ ] The web service listens on Render's injected `PORT`, serves HTTPS, and
      passes `/healthz`.
- [ ] `SESSION_SECRET` uses `generateValue`; `DATABASE_URL` comes from the
      Render database. No secret appears in git or the image.
- [ ] The container entrypoint runs `alembic upgrade head` and fails the start
      if migrations fail (free plans cannot run pre-deploy commands).
- [ ] `/healthz` returns 200 with `status: "ok"`, `database: "available"`, and
      the deployed commit (from `RENDER_GIT_COMMIT`) as `version`.
- [ ] The UI loads, registration works, a session can be created and booked,
      and the cookie has `Secure` and `HttpOnly`.
- [ ] Seed data runs only against the local Compose stack, never Render.
- [ ] Rollback from the Render dashboard is documented and tested once.
- [ ] README lists the URL, deploy trigger, free-tier limits, and cost
      expectation.
- [ ] `make render-validate` and `make render-verify URL=...` work without a
      Render account.

## Out of scope

- CI/CD automation. Issue #16.
- A separate dev/staging environment, custom domains, and multi-region. A
  second environment needs a paid PostgreSQL plan; see
  `deploy/render/README.md`.
- Blue/green or canary deploys.

## Constraints

- Use the image built in issue #13; do not add a second deployment path.
- Region Frankfurt by default; document how to change it.
- One web service for the demo.
- Do not run PostgreSQL inside the application container.
- Do not commit secrets to `render.yaml`; use `generateValue` and
  `fromDatabase`.
- Free Postgres expires 30 days after creation, so the demo database is
  disposable.
