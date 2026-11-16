# Evidence index

This page separates what the repository proves from what still needs a live
account, a recording, or a human reviewer. A criterion is not marked complete
just because a file exists.

Status legend:

- **Verified** - reproducible from the repository and checked in this release.
- **Pending external** - requires an account, a live deploy, a recording, or a
  reviewer. The steps are documented; no result is fabricated.
- **Not claimed** - out of scope for v1.

## Repository evidence

| Evidence | Status | Where |
| --- | --- | --- |
| Problem, users, core flow, features | Verified | `README.md`, `_docs/spec.md` |
| Architecture and decisions | Verified | `_docs/architecture.md` |
| Backend unit and integration tests | Verified | `backend/tests/`, `make test` |
| Frontend unit tests | Verified | `frontend/src/**/*.test.tsx`, `make test` |
| End-to-end journey | Verified | `e2e/tests/`, `make e2e` |
| Race-safety test | Verified | `backend/tests/integration/test_bookings.py` |
| OpenAPI contract check | Verified | `openapi.yaml`, `scripts/check_contract.py` |
| Docker image and Compose stack | Verified | `Dockerfile`, `docker-compose.yaml` |
| CI build-once and E2E gate | Verified | `.github/workflows/ci.yml` |
| Guarded Render deploy hook | Implemented; secret pending | `.github/workflows/ci.yml`, `scripts/render.py` |
| Paid promotion and rollback | Implemented; paid path not active | `.github/workflows/promote.yml`, `.github/workflows/rollback.yml` |
| Traces, metrics, JSON logs, redaction | Verified | `backend/app/telemetry.py`, `backend/tests/unit/test_telemetry.py` |
| Dashboard and alert assets | Verified | `observability/dashboard.json`, `observability/alerts.yaml` |
| Alert annotation and runbook-link tests | Verified | `backend/tests/unit/test_observability_assets.py` |
| On-call worker, timeout, dedupe, redaction | Verified | `on-call/worker.py`, `backend/tests/unit/test_oncall_worker.py` |
| Chaos helper | Verified | `on-call/chaos.py`, `backend/tests/unit/test_oncall_worker.py` |
| Security audit | Verified | `_docs/security.md` |
| Tag `v1.0.0` | Verified after release | GitHub releases |

## Live demo

- URL: <https://open-seat.onrender.com>
- Health: <https://open-seat.onrender.com/healthz>
- Status: **verified reachable**; the deployed commit is checked with
  `make render-verify`.
- Note: the free web service sleeps after 15 minutes without traffic. The first
  request after idle can take about a minute.

## Grafana dashboard

- Status: **pending external**.
- Files: `observability/dashboard.json`, `observability/README.md`.
- Capture:
  1. Import the dashboard into a Grafana Cloud stack.
  2. Set the `environment` and `version` filters to the demo.
  3. Run the booking journey so all panels have data.
  4. Save a full-page screenshot to
     `_docs/evidence/screenshots/dashboard.png`.
- Acceptance: traffic, 5xx rate, p95 latency, bookings by result, promotions,
  open seats with a waitlist, and overbooked sessions are all visible, and the
  environment/version variables filter them.

## Firing alert and notification

- Status: **pending external**.
- Files: `observability/alerts.yaml`, `_docs/runbook.md`.
- Capture:
  1. Configure a contact point (email or webhook).
  2. Trigger the development waitlist rule with the chaos helper.
  3. Save the firing alert and the delivered notification to
     `_docs/evidence/screenshots/alert-firing.png` and
     `_docs/evidence/screenshots/alert-notification.png`.
- Acceptance: the alert shows `OpenSeatWaitlistStalledDev`, the owner, the
  dashboard link, and the runbook link.

## On-call

- Status: **pending external**.
- Files: `on-call/README.md`, `on-call/worker.py`, `on-call/chaos.py`.
- Capture:
  1. Create a disposable worktree and inject the off-by-one bug:
     `python on-call/chaos.py --worktree <worktree> --apply`.
  2. Deploy that worktree to the development service.
  3. Create a capacity-1 session, book it, and join the waitlist.
  4. Start `make on-call` and let the alert fire.
  5. Save the worker transcript path, branch name, and draft PR URL in the
     table below.
  6. Review the draft PR and record the post-fix verification command.
  7. Revert the bug with `python on-call/chaos.py --worktree <worktree> --revert`
     before submission.

| Item | Value |
| --- | --- |
| Transcript | pending |
| Branch | pending |
| Draft PR | pending |
| Post-fix verification | pending |
| Reviewer | pending |

## Demo video

- Status: **pending external recording**.
- Target length: 5-8 minutes.
- Script: [`demo-script.md`](demo-script.md).
- Save the public link here when recorded. The recording must show:
  browse, sign up, host creates a session, guest books, second guest joins the
  waitlist, cancellation promotes the waiter, host checks in, Grafana
  trace/log correlation, the alert, the agent branch/PR, and the fix
  verification.
- The video must contain no secrets, tokens, emails, or real personal data.
  Use the seeded example.com accounts and a local or demo environment.

## Peer reviews

- Status: **pending external**.
- Required: three reviews of the public repository.
- Record the reviewer name or handle, the date, the link, and whether the
  review was on the code, the demo, or the operations story.

| Reviewer | Date | Link | Scope |
| --- | --- | --- | --- |
| pending | pending | pending | pending |
| pending | pending | pending | pending |
| pending | pending | pending | pending |

## Fresh-clone verification

- Status: **verified in this release** (commands and results below).
- Commands:

```bash
git clone https://github.com/maxxqcty/openseat.git
cd openseat
cp .env.example .env
docker compose up --build
make test
make e2e
```

- Record the date, commit, and any environment-specific notes. Do not commit a
  filled `.env`.

## Hygiene rules

- Use the seeded example.com accounts; never a real email address.
- Crop or blur browser chrome, terminals, and Grafana headers that could show
  an account, token, or private URL.
- Do not paste a token, cookie, `Authorization` header, database URL, or
  request body into a screenshot or transcript.
- Run `gitleaks detect --source . --redact` before publishing a recording or a
  screenshot set.
- If a criterion is only partially met, keep the status as pending and explain
  what is missing. Do not overstate it.
