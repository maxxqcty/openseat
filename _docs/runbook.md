# OpenSeat Runbook

Operational guide for OpenSeat dev and prod. Every alert links to an anchor here.

## On-call at a glance

1. Acknowledge the alert in Grafana.
2. Open the dashboard and identify the affected environment and version.
3. Follow the alert section below. Prefer rollback over live debugging.
4. If the on-call agent opened a branch, review it; never deploy it automatically.
5. Write a short incident note and link it from the issue or PR.

Severity: **page** means user-visible impact. **ticket** means investigate the
next working day.

## Alerts

| Alert | Condition | Severity | Owner |
| --- | --- | --- | --- |
| `OpenSeatDown` | `up{job="openseat"} == 0` for 2m | page | Platform |
| `OpenSeatHighErrorRate` | 5xx ratio > 5% for 10m | page | Backend |
| `OpenSeatBookingErrors` | booking `result="error"` rate > 0.05/s for 10m | page | Backend |
| `OpenSeatWaitlistStalled` | `openseat_open_seat_with_waitlist > 0` for 10m | page | Backend |
| `OpenSeatOverbooked` | `openseat_overbooked_sessions > 0` for 1m | page | Backend |

Every alert must carry `owner`, `dashboard_url`, and `runbook_url` annotations.
The source of truth is `observability/alerts.yaml`.

## OpenSeatDown

**Meaning:** the health endpoint is unreachable or failing.

1. Check the Fly app status and recent releases.
2. Open the app logs; look for migration failures or a crash loop.
3. Check the database status in the Fly dashboard.
4. If the last release is the cause, roll back to the previous tag.
5. If the database is down, restore service before rolling back the app.

```bash
fly status -a openseat-prod
fly logs -a openseat-prod
fly releases -a openseat-prod
```

## OpenSeatHighErrorRate

**Meaning:** more than 5% of HTTP responses are 5xx.

1. Group by route and status in Grafana.
2. Pick one failing trace and follow it to the error log.
3. Check whether the failures started with the last deploy.
4. Roll back if the error rate is above 10% or the cause is unclear after 10 minutes.

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
4. If the error is a code defect, use the on-call agent or fix forward on a branch.
5. If the database is saturated, scale the database before changing code.

## OpenSeatWaitlistStalled

**Meaning:** a session has a free seat while someone is waiting. This is a domain
bug: promotion failed or capacity accounting is wrong.

1. Find the session ID from the metric label or the dashboard table.
2. Query the roster and compare confirmed + checked-in with capacity.
3. Check the latest `promote_waitlist` span and its logs.
4. Reproduce in a test: cancel a confirmed booking with a non-empty waitlist.
5. Fix the promotion transaction; do not patch the count manually.

This is the alert used in the on-call demonstration. The injected bug makes the
last seat unsellable, so the gauge stays positive while a waitlist exists.

## OpenSeatOverbooked

**Meaning:** the invariant `confirmed + checked_in <= capacity` is broken.

1. Treat this as a data-integrity incident. Stop writes if the count is still growing.
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

## Rollback

Rollback deploys a previous image tag. It does not revert migrations.

```bash
gh workflow run rollback.yml -f environment=prod -f tag=20261024-120000-abc1234
```

Rules:

- Migrations must be backward compatible for one release (expand, then contract).
- Never roll back by rebuilding an old commit; promote the stored image.
- After rollback, confirm `/healthz` and the booking smoke test.

## On-call agent handoff

The worker posts an evidence packet to the agent: alert name, environment,
version, dashboard link, runbook link, relevant metric queries, recent deploy,
and sanitised log excerpts. The agent may:

- read the repository and telemetry;
- reproduce the bug in a test;
- commit a fix to a new branch and open a draft PR;
- report that it cannot reproduce the issue.

It may not deploy, merge, access production secrets, or write to the production
database. A human reviews every branch.

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