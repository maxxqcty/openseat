# Observability

OpenSeat exports OpenTelemetry traces, metrics, and JSON logs to Grafana Cloud
through OTLP/HTTP. The exporter is disabled when `OTEL_EXPORTER_OTLP_ENDPOINT`
is empty, so local tests and `docker compose up` never need a Grafana account.

## What is emitted

| Signal | Name | Notes |
| --- | --- | --- |
| Trace | FastAPI server span | Method, route, status; `/healthz` is excluded |
| Trace | SQLAlchemy statement span | Same trace as the booking request |
| Trace | `book_seat`, `cancel_booking`, `promote_waitlist`, `check_in` | Session, booking, and result attributes only |
| Metric | `openseat_http_requests_total` | `method`, `route`, `status` |
| Metric | `openseat_http_request_duration_seconds` | Histogram for p95 |
| Metric | `openseat_bookings_total` | `result=confirmed|waitlisted|cancelled|checked_in|already_checked_in|rejected|error` |
| Metric | `openseat_promotions_total` | `result=promoted|none` |
| Metric | `openseat_open_seat_with_waitlist` | Gauge refreshed from PostgreSQL |
| Metric | `openseat_overbooked_sessions` | Gauge refreshed from PostgreSQL |
| Log | JSON on stdout | `timestamp`, `level`, `event`, `service`, `environment`, `version`, `trace_id`, `span_id` |

The gauges are observable callbacks. The metric reader queries the database on
each collection; nothing increments them in memory. That is why the alert still
fires after a process restart.

No span, metric attribute, or log field contains an email, display name,
cookie, authorization header, password, token, or request body. The redaction
filter and its unit test live in `backend/app/telemetry.py` and
`backend/tests/unit/test_telemetry.py`.

## Grafana Cloud setup

1. Create a free Grafana Cloud stack.
2. Open **Connections > OpenTelemetry > Configure**. Copy the OTLP endpoint and
   the generated authorization header.
3. In Render, open the `openseat` service and set:
   - `OTEL_EXPORTER_OTLP_ENDPOINT` to the endpoint, for example
     `https://otlp-gateway-prod-eu-west-0.grafana.net/otlp`.
   - `OTEL_EXPORTER_OTLP_HEADERS` to `Authorization=Basic <base64>`.
   - `OTEL_TRACES_SAMPLER_ARG=0.1` (production samples 10%; local Compose
     defaults to 1.0).
4. Redeploy or restart the service. `/healthz` still works if telemetry is
   misconfigured; check the service logs for `metric_gauge_failed` or exporter
   warnings.
5. Confirm metrics arrived in **Explore**:
   `openseat_http_requests_total` and `openseat_open_seat_with_waitlist`.

The endpoint and header are secrets. They live in Render's environment, never
in `render.yaml`, the dashboard, or this repository.

## Import the dashboard

1. In Grafana choose **Dashboards > New > Import**.
2. Upload `observability/dashboard.json` and select the Prometheus data source
   that receives the OTLP metrics.
3. Save it with UID `openseat-main`.
4. The `environment` and `version` variables filter every panel. Use them to
   compare the demo and a local environment.

The dashboard panels cover traffic, 5xx rate, p95 latency, bookings by result,
promotions, open seats with a waitlist, and overbooked sessions.

## Import the alert rules

1. Replace `grafanacloud-prometheus` in `observability/alerts.yaml` with the
   Prometheus data source UID of your stack.
2. Replace the `dashboard_url` host with your Grafana stack URL.
3. In Grafana choose **Alerting > Alert rules > Import**, or provision the file
   from a Git-synced folder.
4. Create a contact point (email or webhook) under **Alerting > Contact points**
   and attach it to the `OpenSeat` notification policy.
5. Add a mute timing only for planned maintenance; do not silence the demo.

### Alert thresholds

| Alert | Expression | For | Severity |
| --- | --- | --- | --- |
| `OpenSeatDown` | `up{job="openseat",environment="production"} == 0` | 2m | page |
| `OpenSeatHighErrorRate` | 5xx ratio > 5% | 5m | page |
| `OpenSeatBookingErrors` | booking error rate > 0.05/s | 10m | page |
| `OpenSeatWaitlistStalled` | open seats with a waitlist > 0 | 10m | page |
| `OpenSeatWaitlistStalledDev` | same, `environment="development"` | 2m | page |
| `OpenSeatOverbooked` | overbooked sessions > 0 | 1m | page |

The dev copy exists only so a demo can show the alert quickly. Production keeps
the ten-minute window to avoid paging on a transient race that resolves itself.
Both rules carry `owner`, `dashboard_url`, and `runbook_url` annotations.

## Verify an alert

1. Start the local stack with telemetry pointed at a development Grafana Cloud
   stack, or use the demo.
2. Create a capacity-1 session, book it, and join the waitlist.
3. In a development database, simulate the bug by confirming a waitlisted
   booking while the seat is still occupied, or run the chaos script from
   issue #19. The gauge becomes `1`.
4. Wait for the dev rule (2 minutes) and confirm the notification reaches the
   contact point.
5. Open the alert, follow the dashboard link, then follow the runbook link.
6. Save the notification screenshot and the firing-alert screenshot under
   `_docs/evidence/` with no email addresses or personal data.

## Evidence status

The repository contains the dashboard, alert rules, and runbook. The live
Grafana stack, a real notification, and screenshots require a Grafana Cloud
account and a configured contact point, so they are recorded in
`_docs/evidence/README.md` as external evidence to capture before submission.
The files are the source of truth; a screenshot is never the only definition.

## Local verification without Grafana

```bash
cd backend
uv run pytest tests/unit/test_observability_assets.py tests/unit/test_telemetry.py
```

The tests parse the dashboard JSON and alert YAML, assert every panel filters by
`environment` and `version`, check the alert names and annotations, and prove
the logging redaction filter removes PII. They never contact Grafana.
