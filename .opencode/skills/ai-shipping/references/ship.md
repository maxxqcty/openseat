# Stage 2: Ship

Goal: turn the local application into a tested, containerised, publicly
reachable service with an automated pipeline.

Exit gate: the public URL passes the acceptance scenario, and the pipeline is
green from a clean clone.

## 1. Collapse the development topology into one image

In development, a frontend watcher and a backend process run separately. In
production, the frontend is static files that do not change while the app runs,
so the backend can serve them. One image, one process.

```text
Create a Dockerfile that builds the frontend with Node in a builder stage,
then builds the backend image and copies only the built frontend assets into it.

The backend should serve the frontend.
```

Apply:

- multi-stage build, so the runtime image has no Node toolchain or
  `node_modules`;
- `.dockerignore` for `.git`, tests, local databases, and secrets;
- non-root user in the runtime image;
- a health endpoint and a `HEALTHCHECK` (or platform equivalent);
- configuration by environment variable, never baked into the image;
- `docker build -t <app>:<tag> .` and a documented `docker run`.

Verify inside the container, not just on the host: run the acceptance scenario
against the mapped port.

## 2. Move to a production-grade database

SQLite was right for local development. Production usually needs Postgres or a
managed equivalent for concurrency, durability, and backups.

```text
Add Postgres support to the backend.
Keep the same store interface and configuration by DATABASE_URL.
Add migrations and a seed command for local development.
```

Run Postgres locally, point the app at it, and repeat the scenario. Watch for:

- connection strings and credentials in committed files;
- schema creation at startup masking missing migrations;
- timezone and timestamp handling differences;
- transaction boundaries that were implicit in a single-file database.

## 3. Define the whole local stack

```text
Create docker-compose.yaml with two services: database and app.

Add a database health check so the app waits for readiness.
Add a named volume for data.
Expose the app on one port.
```

`docker compose up --build` should be the only command needed. Test from a
clean volume, not from a state you have been mutating for an hour.

## 4. Test the seams, not just the units

Two levels matter:

- **Integration tests** — the backend against a real database, run against the
  Compose stack. They catch schema, query, transaction, and connection issues
  that unit tests with fakes cannot.
- **End-to-end tests** — the browser through the frontend, the API, and the
  database. They catch the user-visible flow.

```text
Create integration tests that run against docker-compose.yaml.
What scenarios should we test?
```

```text
Add an end-to-end test that runs against docker-compose.yaml.

Use Playwright to:
1. <step>
2. <step>
...

Put the tests in e2e/.
```

E2E scenario requirements:

- use two browser contexts when the product is multi-user, not two tabs;
- cover one happy path end to end;
- add at least one failure path (bad credentials, duplicate join, expired link);
- capture a trace or screenshot on failure;
- run against the same image and Compose file that ship.

If the E2E suite is flaky, fix the source of flakiness (waits, shared state,
ordering) rather than adding retries that hide it.

## 5. Choose a deployment target

```text
Propose 2-3 ways to deploy this application.
Compare cost, operational complexity, portability, and managed services.
Recommend one and wait for approval before creating infrastructure.
```

If you want infrastructure as code, ask which options fit the chosen target.
Not every platform supports it; if it does not, say so and move on rather than
hand-building an unrepeatable stack.

Constraints to state up front:

- budget per month;
- region/data residency;
- who operates it;
- expected traffic;
- acceptable downtime;
- whether a managed database is required.

Use a temporary, least-privileged identity for the first manual deploy, and
watch every action. Do not let an agent create account-wide admin users and
walk away.

## 6. Build the pipeline

Desired order on every push to the main branch:

1. backend and frontend unit tests, in parallel;
2. build the image once, tag it immutably, push it to a registry;
3. start the Compose stack from that image;
4. run integration tests;
5. run E2E tests;
6. deploy to the dev environment;
7. verify the health endpoint.

Production is a separate, manual promotion of the tested image.

```text
Create a CI/CD pipeline that:

- runs backend and frontend tests in parallel
- builds the image once and pushes it to <registry>
- runs integration and end-to-end tests against docker-compose.yaml
- deploys to <dev environment>
- verifies the health endpoint after deploy
```

Rules:

- tag with `YYYYMMDD-HHMMSS-<shortsha>`, never `latest` alone;
- authenticate to the cloud with short-lived OIDC credentials, not stored keys;
- fail the pipeline on a failed health check, and keep the logs;
- make deploys idempotent;
- keep production promotion manual until the process has earned trust.

A deploy that "succeeded" because the command exited zero is not verified.
Hit the health endpoint and, where possible, the acceptance scenario.

## 7. Plan rollback and cleanup before you need them

- Know the previous image tag and how to deploy it.
- Know how to roll back a database migration, or state that it is
  forward-only and why.
- `delete-stack` (or equivalent) for everything the exercise created.
- Remove DNS records, deployment variables, and registry images the stack does
  not own.

## Gate checklist

- [ ] One image serves both frontend and backend.
- [ ] Image runs as non-root and has a health check.
- [ ] Production database with migrations; no startup schema hacks.
- [ ] `docker compose up` works from a clean state.
- [ ] Integration tests run against the Compose stack.
- [ ] E2E test covers the acceptance scenario in two browser contexts.
- [ ] At least one error path is tested end to end.
- [ ] Pipeline builds once, tags immutably, and runs all tests.
- [ ] Deploy authenticates with OIDC or equivalent short-lived credentials.
- [ ] Deploy is verified via health endpoint.
- [ ] Rollback and teardown are documented.

## Common failure modes

- **Two containers for no reason.** The frontend is static; a separate web
  server adds a network hop and a second thing to deploy.
- **Rebuild on promote.** The production image differs from the tested one.
- **`latest` everywhere.** You cannot tell what is running or roll back.
- **Tests against a dev server.** The test passes while the shipping topology
  is broken.
- **Single host, single database, no backups.** Fine for a demo; label it.
- **Admin credentials in CI.** Replace with an assumed role as soon as the
  first deploy works.
- **E2E retries instead of fixes.** Flakiness is a signal, not a nuisance.
