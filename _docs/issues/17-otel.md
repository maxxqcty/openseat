---
title: "OpenTelemetry traces, metrics, and structured logs"
labels: ["observability", "backend"]
depends_on: ["15"]
---

## Goal

A booking can be followed from the HTTP request through the database and the
promotion step in Grafana, using correlated traces, metrics, and logs that
contain no customer data.

## Acceptance criteria

- [ ] OpenTelemetry initialises before the app and sets `service.name=openseat`,
      `deployment.environment`, and `service.version` from configuration.
- [ ] Traces use OTLP export to Grafana Cloud and include FastAPI, SQLAlchemy,
      and outbound HTTP spans.
- [ ] Manual spans exist for `book_seat`, `cancel_booking`, `promote_waitlist`,
      and `check_in`, with session, booking, and result attributes but no email,
      display name, cookie, or token.
- [ ] Metrics are exported: HTTP request count and duration, bookings by result,
      promotions by result, `openseat_open_seat_with_waitlist`, and
      `openseat_overbooked_sessions`.
- [ ] The gauges are refreshed periodically from the database; they are not
      incremented in memory.
- [ ] Logs are JSON on stdout with timestamp, level, event, service,
      environment, version, `trace_id`, and `span_id`.
- [ ] The logging filter redacts emails, cookies, authorization headers, and
      request bodies; a unit test proves it.
- [ ] Error responses include an `X-Trace-Id` header matching the current span.
- [ ] Export is disabled cleanly when no OTLP endpoint is configured, so local
      tests do not need Grafana.
- [ ] Sampling is configurable; dev uses 100% and prod can use a lower ratio.
- [ ] A Grafana trace shows a booking with its database statement and the
      promotion span in the same trace.
- [ ] Tests use an in-memory exporter to assert span names and redaction, and do
      not require network access.

## Out of scope

- Frontend real-user monitoring.
- A custom collector or self-hosted Grafana.
- Log retention policy beyond the Grafana Cloud free tier.

## Constraints

- Instrumentation in `backend/app/telemetry.py`; call it from the app factory.
- Use the OTel SDK and OTLP HTTP exporter, not a vendor-specific agent.
- Do not log request bodies, passwords, cookies, or personal data.
- Keep the exporter off by default when `OTEL_EXPORTER_OTLP_ENDPOINT` is empty.
- Pin instrumentation versions and document the Grafana Cloud setup in
  `observability/README.md`.
