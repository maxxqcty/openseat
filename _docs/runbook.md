# OpenSeat Runbook

Operational guide for the OpenSeat demo and local development. Every alert in
`observability/alerts.yaml` links to an anchor here.

## On-call at a glance

1. Acknowledge the alert in Grafana.
2. Open the dashboard and identify the affected environment and version.
3. Follow the alert section below. Prefer rollback over live debugging.
4. If the on-call worker opened a branch, review it; never deploy it
   automatically.
5. Write a short incident note and link it from the issue or PR.

Severity: **page** means user-visible impact. **ticket** means investigate the
next working day.

The source of truth for thresholds and annotations is
`observability/alerts.yaml`. The dashboard is `observability/dashboard.json`.
Setup instructions are in `observability/README.md`.

## Alerts

| Alert | Condition | For | Severity | Owner |
| --- | --- | --- | --- | --- |
| `OpenSeatDown` | `up{job="openseat"} == 0` | 2m | page | Platform |
| `OpenSeatHighErrorRate` | 5xx ratio > 5% | 5m | page | Backend |
| `OpenSeatBookingErrors` | booking `result="error"` (unexpected failure; expected 4xx rejections are `rejected`) rate > 0.05/s | 10m | page | Backend |
| `OpenSeatWaitlistStalled` | `openseat_open_seat_with_waitlist > 0` | 10m | page | Backend |
| `OpenSeatWaitlistStalledDev` | same gauge, `environment="development"` | 2m | page | Backend |
| `OpenSeatOverbooked` | `openseat_overbooked_sessions > 0` | 1m | page | Backend |

Every alert carries `owner`, `dashboard_url`, and `runbook_url` annotations.
The development copy of the waitlist rule exists only so a demo can show the
alert quickly; production keeps the ten-minute window.

## OpenSeatDown

**Meaning:** the health endpoint is unreachable or failing.

1. Check the Render service status and recent deploys.
2. Open the service logs; look for migration failures or a crash loop.
3. Check the database status in the Render dashboard.
4. If the last deploy is the cause, roll back to the previous deploy.
5. If the database is down, restore service before rolling back the app.

```bash
curl -fsS https://openseat-9b15.onrender.com/healthz
make render-verify URL=https://openseat-9b15.onrender.com
```

The Render dashboard shows the same data under **Logs**, **Events**, and
**Deploys**; there is no platform CLI in the default workflow.

## OpenSeatHighErrorRate

**Meaning:** more than 5% of HTTP responses are 5xx.

1. Group by route and status in Grafana.
2. Pick one failing trace and follow it to the error log.
3. Check whether the failures started with the last deploy.
4. Roll back if the error rate is above 10% or the cause is unclear after
   10 minutes.

```promql
sum by (route, status) (rate(openseat_http_requests_total{status=~"5.."}[5m]))
```

```logql
{service_name="openseat"} | json | level="error" | line_format "{{.trace_id}} {{.message}}"
```

## OpenSeatBookingErrors

**Meaning:** bookings are failing for a reason other than a handled conflict.

1. Filter logs by `event="booking_failed"`.
2. Check database connectivity and lock wait time.
3. Reproduce with the failing session ID from the log.
4. If the error is a code defect, use the on-call worker or fix forward on a
   branch.
5. If the database is saturated, scale the database before changing code.

## OpenSeatWaitlistStalled

**Meaning:** a session has a free seat while someone is waiting. This is a
domain bug: promotion failed or capacity accounting is wrong.

1. Find the session ID from the metric label or the dashboard table.
2. Query the roster and compare confirmed + checked-in with capacity.
3. Check the latest `promote_waitlist` span and its logs.
4. Reproduce in a test: cancel a confirmed booking with a non-empty waitlist.
5. Fix the promotion transaction; do not patch the count manually.

This is the alert used in the on-call demonstration. The injected bug makes the
last seat look occupied, so the gauge stays positive while a waitlist exists.
The development rule fires after two minutes; the production rule after ten.

## OpenSeatOverbooked

**Meaning:** the invariant `confirmed + checked_in <= capacity` is broken.

1. Treat this as a data-integrity incident. Stop writes if the count is still
   growing.
2. Identify the session and the bookings that exceed capacity.
3. Preserve evidence: export the rows and the relevant traces.
4. Roll back the release that introduced the race.
5. Correct data only with a reviewed migration or script; record every change.

```sql
select s.id, s.capacity,
       count(*) filter (where b.status in ('confirmed', 'checked_in')) as taken
from sessions s
join bookings b on b.session_id = s.id
where s.status = 'scheduled'
group by s.id, s.capacity
having count(*) filter (where b.status in ('confirmed', 'checked_in')) > s.capacity;
```

## Deploy and rollback

The normal deploy is a merge to `main`. CI builds the image once, runs E2E
against that image, and only then calls the Render deploy hook. If the hook
secret is not configured, `autoDeployTrigger: checksPass` is the fallback and
the workflow prints a warning.

Verify a deploy:

```bash
make render-verify URL=https://openseat-9b15.onrender.com
EXPECTED_VERSION=<sha> make render-verify URL=https://openseat-9b15.onrender.com
```

On the free plan, roll back from **Render Dashboard > Deploys > Rollback**.
On the paid image-backed path, use the workflow:

```bash
gh workflow run rollback.yml \
  -f deploy_id=dep-xxxxxxxxxxxx \
  -f confirm=rollback
```

Rules:

- Migrations must be backward compatible for one release (expand, then
  contract).
- Never roll back by rebuilding an old commit on the paid path; promote the
  stored image.
- After rollback, confirm `/healthz` and the booking smoke test.

## On-call agent handoff

`make on-call` starts the worker. It polls Grafana every 60 seconds for active
page-severity alerts in `ON_CALL_ENVIRONMENT`, deduplicates by fingerprint, and
stores state outside the repository (`~/.openseat/on-call` by default).

For each new alert the worker:

1. builds a redacted packet with the alert, labels, annotations, environment,
   deployed version, dashboard and runbook URLs, current metric values, recent
   commits, and sanitised log excerpts;
2. creates an isolated git worktree on a new branch;
3. starts the configured headless agent with a 20-minute timeout;
4. records the transcript, branch, and draft PR URL;
5. rejects the run if the agent changed `.github/`, `render.yaml`, `deploy/`,
   `on-call/`, or `observability/`.

The agent may read the repository, reproduce the bug in a test, commit a fix to
the branch, and open a draft PR. It may not merge, deploy, access production
secrets, or write to the production database. A human reviews every branch.

Dry run without a Grafana account:

```bash
make on-call ARGS="--dry-run --alert-file /tmp/alert.json"
```

## Incident note template

```markdown
## Incident: <title>

- Detected: <timestamp and alert>
- Impact: <who could not do what>
- Environment/version: <dev|prod, tag>
- Cause: <one paragraph>
- Detection: <how the alert found it>
- Response: <what we did, including rollback>
- Fix: <PR/branch and test>
- Follow-up: <issue links>
```

## Routine checks

- Weekly: dependency audit, failed deploy review, dashboard link check.
- Before submission: fire each alert in dev, confirm the runbook link resolves,
  and run the demo script end to end.
- The live Grafana notification, screenshots, demo video, and peer reviews are
  tracked as external evidence in `_docs/evidence/README.md`.
