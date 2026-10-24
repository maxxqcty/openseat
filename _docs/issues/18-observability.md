---
title: "Grafana dashboard, alert rules, and runbook verification"
labels: ["observability", "docs"]
depends_on: ["17"]
---

## Goal

A human or an on-call agent can see the system's health in one dashboard and
receive an actionable alert with an owner, a runbook, and a link to the failing
signal.

## Acceptance criteria

- [ ] `observability/dashboard.json` contains panels for traffic, 5xx rate, p95
      latency, bookings by result, promotions, open seats with a waitlist, and
      overbooked sessions.
- [ ] The dashboard has `environment` and `version` variables and filters every
      panel by them.
- [ ] `observability/alerts.yaml` defines `OpenSeatDown`,
      `OpenSeatHighErrorRate`, `OpenSeatBookingErrors`,
      `OpenSeatWaitlistStalled`, and `OpenSeatOverbooked`.
- [ ] Every alert has `owner`, `dashboard_url`, and `runbook_url` annotations
      and a documented threshold.
- [ ] The open-seat-with-waitlist rule fires after 10 minutes in prod; a
      dev-only copy may use 2 minutes for the demo, and the difference is
      documented.
- [ ] `observability/README.md` explains how to import the dashboard, create the
      contact point, and verify an alert.
- [ ] The dashboard and alert rules are stored in Grafana Cloud and the files
      in the repository match what is deployed.
- [ ] A test alert in dev reaches the configured contact point; the notification
      and screenshot are linked from `_docs/runbook.md` or the README.
- [ ] `_docs/runbook.md` links resolve, and each alert section names the first
      three diagnostic steps and the rollback action.
- [ ] No panel query or alert annotation contains email addresses, names,
      tokens, or other customer data.
- [ ] Screenshots of the dashboard and a firing alert are saved under
      `_docs/evidence/`.

## Out of scope

- SLO burn-rate alerting.
- PagerDuty or a paid on-call rotation.
- Alert routing by team.

## Constraints

- Use Grafana Cloud and the OTLP metrics from issue #17.
- Keep dashboard JSON and alert YAML valid and reviewable; do not store a
  screenshot as the only definition.
- Do not embed credentials in the dashboard or alert files.
- The alert contact point for the demo may be email or a webhook; document it.
