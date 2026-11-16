"""Unit tests for structured logs, redaction, and telemetry configuration."""

from __future__ import annotations

import json
import logging

from app.config import Settings
from app.telemetry import (
    JsonFormatter,
    RedactionFilter,
    TraceContextFilter,
    configure_telemetry,
    redact_text,
    redact_value,
    shutdown_telemetry,
)


def _record(message: str, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_redaction_removes_emails_cookies_and_authorization_headers() -> None:
    text = (
        "login alice@example.com "
        "Cookie: openseat_session=super-secret "
        "Authorization: Bearer abc.def.ghi "
        "password=hunter2"
    )

    redacted = redact_text(text)

    assert "alice@example.com" not in redacted
    assert "super-secret" not in redacted
    assert "abc.def.ghi" not in redacted
    assert "hunter2" not in redacted
    assert "[redacted-email]" in redacted
    assert "[redacted]" in redacted


def test_redaction_drops_sensitive_structured_fields() -> None:
    payload = {
        "email": "alice@example.com",
        "display_name": "Alice",
        "password": "hunter2",
        "cookie": "openseat_session=secret",
        "authorization": "Bearer token",
        "request_body": '{"email": "alice@example.com"}',
        "safe": "confirmed",
    }

    redacted = redact_value(payload)

    assert redacted["email"] == "[redacted-email]"
    assert redacted["display_name"] == "[redacted-pii]"
    assert redacted["password"] == "[redacted]"
    assert redacted["cookie"] == "[redacted]"
    assert redacted["authorization"] == "[redacted]"
    assert redacted["request_body"] == "[redacted-body]"
    assert redacted["safe"] == "confirmed"


def test_json_formatter_has_the_documented_fields_and_no_pii() -> None:
    record = _record(
        "booking failed for alice@example.com",
        event="booking_failed",
        email="alice@example.com",
        cookie="openseat_session=secret",
        authorization="Bearer abc.def.ghi",
    )
    TraceContextFilter().filter(record)
    RedactionFilter().filter(record)

    payload = json.loads(
        JsonFormatter(service="openseat", environment="test", version="abc123").format(record),
    )

    assert set(payload) >= {
        "timestamp",
        "level",
        "event",
        "service",
        "environment",
        "version",
        "trace_id",
        "span_id",
    }
    assert payload["event"] == "booking_failed"
    assert payload["service"] == "openseat"
    assert payload["environment"] == "test"
    assert payload["version"] == "abc123"
    encoded = json.dumps(payload)
    assert "alice@example.com" not in encoded
    assert "secret" not in encoded
    assert "abc.def.ghi" not in encoded


def test_export_is_disabled_cleanly_without_an_endpoint() -> None:
    settings = Settings(
        app_env="test",
        session_secret="x" * 40,
        otel_exporter_otlp_endpoint="",
    )

    state = configure_telemetry(settings)

    assert state.enabled is False
    assert settings.telemetry_enabled is False
    shutdown_telemetry()


def test_export_is_enabled_when_an_endpoint_is_configured() -> None:
    settings = Settings(
        app_env="test",
        session_secret="x" * 40,
        otel_exporter_otlp_endpoint="https://otlp.example.com",
    )

    state = configure_telemetry(settings)

    assert state.enabled is True
    assert settings.telemetry_enabled is True
    shutdown_telemetry()


def test_sampler_ratio_is_validated() -> None:
    settings = Settings(
        app_env="test",
        session_secret="x" * 40,
        otel_traces_sampler_arg=0.25,
    )
    assert settings.otel_traces_sampler_arg == 0.25
