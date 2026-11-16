"""Integration test for correlated spans and metrics on the booking journey."""

from __future__ import annotations

from fastapi.testclient import TestClient
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.config import Settings
from app.main import create_app
from app.telemetry import shutdown_telemetry
from tests.conftest import requires_postgres
from tests.integration.helpers import (
    CSRF_HEADERS,
    book,
    create_session,
    login,
    register,
)

pytestmark = requires_postgres


def _metric_names(reader: InMemoryMetricReader) -> set[str]:
    names: set[str] = set()
    data = reader.get_metrics_data()
    if data is None:
        return names
    for resource_metrics in data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            names.update(metric.name for metric in scope_metrics.metrics)
    return names


def test_booking_journey_emits_spans_metrics_and_trace_header(settings: Settings) -> None:
    exporter = InMemorySpanExporter()
    reader = InMemoryMetricReader()
    app = create_app(settings, span_exporter=exporter, metric_reader=reader)

    try:
        with TestClient(app) as client:
            register(client, email="telemetry-host@example.com", display_name="Host")
            session = create_session(client, capacity=1, starts_in_hours=1)
            session_id = str(session["id"])

            register(client, email="telemetry-guest-a@example.com", display_name="Guest A")
            first = book(client, session_id)
            assert first.status_code == 201, first.text
            first_booking = first.json()

            register(client, email="telemetry-guest-b@example.com", display_name="Guest B")
            second = book(client, session_id)
            assert second.status_code == 201, second.text
            second_booking = second.json()
            assert second_booking["status"] == "waitlisted"

            assert login(client, email="telemetry-guest-a@example.com").status_code == 204
            cancelled = client.delete(
                f"/api/bookings/{first_booking['id']}",
                headers=CSRF_HEADERS,
            )
            assert cancelled.status_code == 204, cancelled.text

            assert login(client, email="telemetry-host@example.com").status_code == 204
            checked_in = client.post(
                f"/api/bookings/{second_booking['id']}/check-in",
                headers=CSRF_HEADERS,
            )
            assert checked_in.status_code == 200, checked_in.text
            assert checked_in.json()["status"] == "checked_in"

            missing = client.get("/api/does-not-exist")
            assert missing.status_code == 404
            trace_id = missing.headers["X-Trace-Id"]
            assert len(trace_id) == 32
            assert all(character in "0123456789abcdef" for character in trace_id)

        spans = exporter.get_finished_spans()
        names = {span.name for span in spans}
        assert {"book_seat", "cancel_booking", "promote_waitlist", "check_in"} <= names

        book_span = next(span for span in spans if span.name == "book_seat")
        assert book_span.attributes is not None
        assert "session.id" in book_span.attributes
        assert "booking.id" in book_span.attributes
        assert book_span.attributes["result"] in {"confirmed", "waitlisted"}

        # SQLAlchemy instrumentation puts the statement in the same trace.
        database_spans = [
            span
            for span in spans
            if span.name.upper().startswith(("SELECT", "INSERT", "UPDATE"))
        ]
        assert database_spans, f"no database spans in {sorted(names)}"
        assert any(span.context.trace_id == book_span.context.trace_id for span in database_spans)

        assert any(
            f"{span.context.trace_id:032x}" == trace_id for span in spans
        ), "the error header does not match a recorded span"

        metric_names = _metric_names(reader)
        assert {
            "openseat_http_requests_total",
            "openseat_http_request_duration_seconds",
            "openseat_bookings_total",
            "openseat_promotions_total",
            "openseat_open_seat_with_waitlist",
            "openseat_overbooked_sessions",
        } <= metric_names
    finally:
        shutdown_telemetry()
