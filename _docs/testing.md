# Testing Strategy

## Principle

Test the rules that can hurt users: capacity, ordering, promotion, permissions,
and the check-in window. Test the operational surface that can hide a failure:
telemetry correlation, alert assets, deploy tooling, and the on-call worker.
Do not chase coverage on glue code.

## Pyramid

| Level | Tool | What it covers | Speed |
| --- | --- | --- | --- |
| Backend unit | pytest | Pure domain rules, validation, ordering, telemetry redaction, alert assets, deploy and on-call tooling | Fast |
| Frontend unit | Vitest + React Testing Library | Component states, error rendering, service mock | Fast |
| Integration | pytest + httpx + Postgres | API, transactions, constraints, concurrency, correlated spans | Medium |
| E2E | Playwright | The full host/guest/waitlist/check-in journey | Slow |

## Commands

```bash
make test    # backend unit + frontend unit + integration
make e2e     # Playwright against docker-compose.yaml
make lint    # ruff (app, on-call, scripts), mypy, eslint, tsc
make audit   # pip-audit and npm audit --omit=dev
```

Focused runs:

```bash
cd backend
uv run pytest tests/unit/test_booking_rules.py -q
uv run pytest tests/integration/test_bookings.py -q
uv run pytest tests/unit/test_telemetry.py -q
uv run pytest tests/integration/test_telemetry_spans.py -q
uv run pytest tests/unit/test_observability_assets.py -q
uv run pytest tests/unit/test_oncall_worker.py -q

cd frontend
npm run test -- BookingButton
```

`make e2e` accepts `E2E_BASE_URL` to run against an existing environment and
`E2E_IMAGE` to run against a prebuilt image. CI builds the image once, saves
it, and passes it to the E2E job through `E2E_IMAGE`, so the tested bytes are
the deployed bytes.

## Required coverage

### Domain rules (unit)

- capacity boundary: last seat confirmed, next booking waitlisted;
- checked-in bookings still occupy seats;
- oldest waitlisted promoted first, ties broken deterministically;
- cancelling a waitlisted booking does not promote;
- duplicate active booking rejected;
- booking a cancelled or past session rejected;
- check-in outside the window rejected;
- check-in of a waitlisted booking rejected.

### API and database (integration)

- registration, login, logout, `me`;
- cookie flags and CSRF rejection;
- authorization: non-host roster 403, non-owner delete 404;
- booking and promotion against Postgres;
- partial unique index prevents two active bookings;
- **race test:** two concurrent requests for the last seat produce exactly one
  confirmed and one waitlisted booking;
- invariant query after the race:
  `confirmed + checked_in <= capacity`;
- health endpoint reflects database availability;
- a booking journey produces a manual span and SQL spans in one trace, exports
  metrics, and returns an `X-Trace-Id` header on errors.

### Telemetry (unit and integration)

- export is disabled when `OTEL_EXPORTER_OTLP_ENDPOINT` is empty;
- resource attributes include service name, environment, and version;
- JSON logs carry `timestamp`, `level`, `event`, `service`, `environment`,
  `version`, `trace_id`, and `span_id`;
- redaction removes emails, display names, cookies, authorization headers,
  bearer tokens, passwords, tokens, API keys, and request bodies;
- DB-backed gauges report the real invariant rather than an in-memory counter;
- the in-memory span exporter and metric reader are used in tests, so no
  Grafana account is required.

### Observability assets (unit)

- `observability/dashboard.json` has the required panels and the
  `environment`/`version` variables;
- `observability/alerts.yaml` defines the five page alerts plus the
  development waitlist copy;
- every alert has `owner`, `dashboard_url`, and `runbook_url`;
- every runbook link resolves to a heading in `_docs/runbook.md`;
- the production waitlist rule uses 10 minutes and the development copy uses
  2 minutes.

### Deploy and on-call tooling (unit)

- `scripts/render.py validate` accepts the Blueprint and rejects drift;
- `deploy-hook` refuses to run without the URL and redacts the hook in output;
- `promote` and `rollback` require a typed confirmation;
- the on-call worker deduplicates by fingerprint and ignores resolved alerts;
- the evidence packet redacts emails, display names, cookies, and tokens;
- the agent environment is an allowlist and never receives Render, database,
  session, Grafana, or OTLP secrets;
- state must live outside the repository;
- a run that changes `.github/`, `render.yaml`, `deploy/`, `on-call/`, or
  `observability/` is rejected;
- the agent timeout terminates the process tree;
- the chaos helper injects and reverts the off-by-one in a disposable
  worktree.

### Frontend (unit)

- booking button states: loading, confirmed, waitlisted, full, error;
- waitlist position rendering;
- 401 redirects to login;
- 403 and 409 show actionable messages;
- empty and error states on the session list.

### End-to-end (Playwright)

Three browser contexts: host, guest A, guest B.

1. Host creates a capacity-1 session.
2. A books; sees confirmed.
3. B books; sees waitlisted, position 1.
4. A cancels.
5. B sees confirmed after polling or refresh.
6. Host checks B in; B sees checked in.
7. A (non-host) cannot check in.

Also cover: duplicate booking, booking a cancelled session, and a missing CSRF
header. Capture a trace, screenshot, and video on failure.

## Fixtures and isolation

- Each integration test runs in a transaction that is rolled back, or against a
  fresh schema created by migrations.
- Do not share mutable fixtures between tests.
- Seed only what the test needs; no global demo data in tests.
- Use unique emails per test (`uuid4` suffix) to avoid cross-run collisions.
- Freeze time for check-in-window tests; do not depend on the wall clock.
- The concurrency test uses two real connections and a barrier; do not simulate
  it with sequential calls.
- Telemetry tests inject an in-memory span exporter and metric reader; they
  never contact Grafana.

## What is intentionally not tested

- Tailwind classes and visual appearance. Use screenshots for the demo.
- Third-party libraries (Render, Grafana, Playwright).
- Load and soak testing in v1.
- A live Grafana account, a delivered notification, and a real coding-agent
  model call. Those need external accounts and are tracked as pending evidence
  in `_docs/evidence/README.md`.
- Email, payments, and other out-of-scope features.

## CI

`.github/workflows/ci.yml` runs five jobs on every push and pull request:

1. **Backend** - ruff, mypy, migrations, drift check, pytest against a
   PostgreSQL 16 service container.
2. **Contract** - `scripts/check_contract.py`.
3. **Frontend** - eslint, tsc, vitest, production build.
4. **Build image** - builds the root Dockerfile once, saves it as an artifact,
   and pushes it to GHCR only on `main`.
5. **E2E** - loads that exact artifact and runs Playwright against it.

On `main`, a **deploy** job runs only after E2E. It calls the Render deploy hook
when `RENDER_DEPLOY_HOOK_URL` is configured and then verifies `/healthz` with
`EXPECTED_VERSION` set to the commit SHA. Without the secret it warns and skips
the hook; `autoDeployTrigger: checksPass` remains the fallback.

Failures keep the Playwright report, trace, screenshot, and video as artifacts.

## Evidence for the rubric

- `make test`, `make e2e`, and `make lint` results are recorded in
  `_docs/evidence/README.md`.
- CI shows the backend, contract, frontend, build, and E2E jobs.
- The concurrency test is named in criterion 5 of `_docs/RUBRIC.md`.
- Telemetry, dashboard, and on-call evidence is listed in
  `_docs/evidence/README.md`, separated from pending external captures.
