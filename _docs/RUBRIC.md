# Release rubric and submission checklist

This is the 12-criterion, 24-point release rubric for OpenSeat. Each criterion
is worth 2 points. Points are claimed only when the evidence is reproducible
from the public repository or a public link. External evidence that needs an
account, a live deploy, a recording, or a human reviewer stays pending until it
exists.

## Score summary

| # | Criterion | Possible | Claimed | Evidence | Gap |
| --- | --- | --- | --- | --- | --- |
| 1 | Problem, users, and core flow are clear | 2 | 2 | `README.md`, `_docs/spec.md` | None |
| 2 | Public demo is reachable and matches the release | 2 | 1 | <https://open-seat.onrender.com/healthz> | Live commit was `330e577` while `main` was `ca65aa5`; re-verify after the release deploy |
| 3 | Fresh clone runs with documented commands | 2 | 2 | `README.md`, `_docs/evidence/README.md#fresh-clone-verification` | None |
| 4 | Domain rules are implemented and tested | 2 | 2 | `backend/app/services/`, `backend/tests/unit/`, `backend/tests/integration/` | None |
| 5 | Capacity is race-safe under concurrency | 2 | 2 | `backend/tests/integration/test_bookings.py` race test | None |
| 6 | Authentication, authorization, and input validation | 2 | 2 | `backend/app/api/auth.py`, `backend/tests/integration/test_auth.py` | None |
| 7 | Automated tests cover unit, integration, and E2E | 2 | 2 | `make test`, `make e2e`, `.github/workflows/ci.yml` | None |
| 8 | CI builds once, gates deploy, and supports rollback | 2 | 1 | `.github/workflows/ci.yml`, `promote.yml`, `rollback.yml` | `RENDER_DEPLOY_HOOK_URL` secret is operator-supplied; live gate not yet observed |
| 9 | Traces, metrics, and structured logs correlate | 2 | 2 | `backend/app/telemetry.py`, `backend/tests/integration/test_telemetry_spans.py` | None |
| 10 | Dashboard and actionable alerts | 2 | 1 | `observability/dashboard.json`, `observability/alerts.yaml`, `backend/tests/unit/test_observability_assets.py` | Live Grafana stack, contact point, and screenshots pending |
| 11 | On-call agent produces a reviewed branch/PR | 2 | 1 | `on-call/worker.py`, `on-call/chaos.py`, `backend/tests/unit/test_oncall_worker.py` | Live chaos deploy, transcript, branch, and draft PR pending |
| 12 | Documentation, security audit, video, and peer reviews | 2 | 1 | `README.md`, `_docs/`, `_docs/security.md` | Demo video and three peer reviews pending |
| **Total** |  | **24** | **19** |  |  |

Claimed 19/24. The five unclaimed points are external evidence or a live
deployment observation, not missing implementation. Update this table after the
release deploy, the Grafana capture, the on-call run, the video, and the peer
reviews.

## Criterion details

### 1. Problem, users, and core flow

- The README states the problem, the host and guest roles, and the
  booking/waitlist/promotion/check-in flow.
- The spec defines the acceptance scenarios and domain rules.

### 2. Public demo

- The free Render service is public and `/healthz` returns `status: ok` and
  `database: available`.
- The deployed commit must match the release commit. Re-run:

```bash
make render-verify URL=https://open-seat.onrender.com
EXPECTED_VERSION=<release-sha> make render-verify URL=https://open-seat.onrender.com
```

### 3. Fresh clone

- The exact commands and results are recorded in
  `_docs/evidence/README.md#fresh-clone-verification`.
- No filled `.env`, database dump, or secret is required.

### 4. Domain rules

- Last seat confirmed, next booking waitlisted.
- Checked-in bookings still occupy seats.
- Oldest waitlisted promoted first.
- Cancelling a waitlisted booking does not promote.
- Duplicate active booking, cancelled session, past session, and invalid
  check-in are rejected.

### 5. Race safety

- Two concurrent requests for the last seat produce exactly one confirmed and
  one waitlisted booking.
- The invariant query after the race is
  `confirmed + checked_in <= capacity`.

### 6. Auth and authorization

- Argon2id hashes, HttpOnly cookie, CSRF header, rate limits.
- Non-host roster and non-owner booking checks are covered by tests.
- Validation errors use the JSON error envelope.

### 7. Tests

- Backend unit and integration suites run against PostgreSQL.
- Frontend unit tests cover loading, confirmed, waitlisted, full, error, 401,
  403, and 409 states.
- Playwright covers the full host/guest/waitlist/check-in journey.
- CI runs the contract check and the E2E gate.

### 8. CI/CD

- The build job builds the Dockerfile once and saves the image.
- E2E loads that exact image.
- The deploy job runs only after E2E on `main` and calls the Render deploy hook
  when the secret is configured.
- The paid promotion workflow reuses the GHCR digest and requires a typed
  confirmation.
- The rollback workflow requires a typed confirmation.
- `autoDeployTrigger: checksPass` is the fallback when Render can read checks.

### 9. Observability

- FastAPI, SQLAlchemy, and domain spans share a trace.
- Metrics cover traffic, latency, bookings by result, promotions, open seats
  with a waitlist, and overbooked sessions.
- JSON logs include `timestamp`, `level`, `event`, `service`, `environment`,
  `version`, `trace_id`, and `span_id`.
- Redaction tests prove emails, display names, cookies, authorization headers,
  and tokens do not reach logs or packets.

### 10. Dashboard and alerts

- Seven required panels and `environment`/`version` variables.
- Five required alert names, each with `owner`, `dashboard_url`, and
  `runbook_url`.
- The production waitlist rule waits 10 minutes; the development copy waits
  2 minutes.
- The runbook headings match the alert links.
- The live Grafana stack and screenshots are pending.

### 11. On-call agent

- Polls every 60 seconds, filters to page severity and the configured
  environment.
- Deduplicates by fingerprint, ignores resolved alerts, and stores state
  outside the repository.
- Builds a redacted packet with metrics, commits, and log excerpts.
- Creates an isolated worktree and enforces a 20-minute timeout.
- Rejects protected-path changes and records the transcript, branch, and draft
  PR URL.
- The live chaos run and draft PR are pending.

### 12. Documentation, security, video, and reviews

- README, architecture, testing, runbook, observability, on-call, evidence, and
  security docs are present.
- `pip-audit`, `npm audit --omit=dev`, and gitleaks report no high or critical
  findings.
- The demo video and three peer reviews are pending external action.

## Submission checklist

- [x] Public repository.
- [x] README opens with the problem, users, and core flow, then features,
      architecture, local run, tests, deploy, observability, and evidence.
- [x] README lists the public demo URL, local dev URL, and evidence links.
- [x] `_docs/RUBRIC.md` lists 12 criteria and 24 points with claimed points and
      evidence.
- [x] Architecture matches the code and records deviations.
- [x] Dashboard and alert assets are in `observability/`.
- [x] On-call worker and chaos helper are in `on-call/`.
- [x] Security scans were run and recorded.
- [x] Fresh-clone commands are recorded.
- [x] Tag `v1.0.0` is created.
- [ ] The release deploy is verified with `EXPECTED_VERSION`.
- [ ] The Render deploy hook secret is configured and the guarded deploy is
      observed.
- [ ] Grafana dashboard screenshot.
- [ ] Firing alert screenshot and delivered notification.
- [ ] Live on-call chaos run, transcript, branch, and draft PR.
- [ ] 5-8 minute demo video.
- [ ] Three peer reviews.
- [ ] Public dev URL. Not available on Render's free tier; the local dev URL
      and the paid two-environment path are documented instead.

## Deadline note

The target deadline is recorded by the operator. If a criterion is not fully
met, this table says so and records the reason. Do not replace pending
external evidence with a mock or a screenshot from a different environment.
