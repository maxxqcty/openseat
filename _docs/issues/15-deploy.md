---
title: "Deploy dev and prod to Fly.io with PostgreSQL"
labels: ["infra", "deploy"]
depends_on: ["13"]
---

## Goal

Two public HTTPS environments run the same image, each with its own database
and secrets.

## Acceptance criteria

- [ ] Fly apps `openseat-dev` and `openseat-prod` exist in one region, each with
      a PostgreSQL database.
- [ ] `deploy/fly/` contains the configuration for both apps; internal port is
      8080, HTTPS is enforced, and one machine stays warm for the demo.
- [ ] `DATABASE_URL`, `SESSION_SECRET`, `APP_ENV`, and `APP_VERSION` are set as
      Fly secrets per app; no secret appears in git or the image.
- [ ] The release command runs `alembic upgrade head` and fails the deploy if
      migrations fail.
- [ ] `/healthz` returns 200 with `database: "ok"` and the deployed version on
      both URLs.
- [ ] The UI loads, registration works, a session can be created and booked,
      and the cookie has `Secure` and `HttpOnly` in prod.
- [ ] The dev and prod databases are separate; no prod data is copied to dev.
- [ ] Seed data is loaded in dev only, manually, after the deploy.
- [ ] A rollback with the previous image tag is documented and tested once.
- [ ] README lists both URLs, the deploy commands, and the cost expectation.

## Out of scope

- CI/CD automation. Issue #16.
- Custom domains and multi-region.
- Blue/green or canary deploys.

## Constraints

- Use the image built in issue #13; do not add a second deployment path.
- Region `fra` by default; document how to change it.
- One app machine per environment for the course demo.
- Do not run PostgreSQL inside the application container.
- Do not put secrets in `fly.toml`.
