"""OpenTelemetry traces, metrics, and structured JSON logs.

The exporter is off unless ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set, so local
tests and development never need Grafana. Instrumentation is created once per
application process; tests can pass an in-memory span exporter and metric
reader to assert span names and redaction without touching the network.
"""

from __future__ import annotations

import json
import logging
import re
import secrets
import sys
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.metrics import Counter, Histogram, Meter, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SimpleSpanProcessor,
    SpanExporter,
)
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_OFF,
    ALWAYS_ON,
    ParentBased,
    Sampler,
    TraceIdRatioBased,
)
from opentelemetry.trace import Span, Status, StatusCode, Tracer

from app.config import Settings

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_AUTH_RE = re.compile(
    r"(?i)\b(proxy-authorization|authorization)\b\s*[:=]\s*[^\r\n,;]+",
)
_COOKIE_RE = re.compile(r"(?i)\b(set-cookie|cookie)\b\s*[:=]\s*[^\r\n]+")
_BEARER_RE = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_SECRET_RE = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key|display_name|full_name)\b\s*[:=]\s*"
    r"(\"[^\"]*\"|'[^']*'|[^\s,;]+)",
)

_SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "body",
        "cookie",
        "display_name",
        "email",
        "name",
        "password",
        "payload",
        "request_body",
        "secret",
        "session",
        "set-cookie",
        "token",
    }
)

_REDACTED_BODY = "[redacted-body]"
_REDACTED_EMAIL = "[redacted-email]"
_REDACTED_PII = "[redacted-pii]"
_REDACTED = "[redacted]"

_RESERVED_LOG_KEYS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
        "taskName",
    }
)


def redact_text(value: str) -> str:
    """Remove emails, cookies, authorization headers, and secret values."""
    redacted = _EMAIL_RE.sub(_REDACTED_EMAIL, value)
    redacted = _AUTH_RE.sub(r"\1: [redacted]", redacted)
    redacted = _COOKIE_RE.sub(r"\1: [redacted]", redacted)
    redacted = _BEARER_RE.sub("Bearer [redacted]", redacted)
    return _SECRET_RE.sub(r"\1=[redacted]", redacted)


def redact_value(value: Any, *, key: str | None = None) -> Any:
    """Recursively redact a structured value before it reaches a log."""
    if key is not None and key.lower() in _SENSITIVE_KEYS:
        if key.lower() in {"body", "payload", "request_body"}:
            return _REDACTED_BODY
        if key.lower() == "email":
            return _REDACTED_EMAIL
        if key.lower() in {"display_name", "full_name", "name"}:
            return _REDACTED_PII
        return _REDACTED
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {
            str(item_key): redact_value(item, key=str(item_key)) for item_key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [redact_value(item) for item in value]
    return value


class RedactionFilter(logging.Filter):
    """Scrub PII and credentials from every record before formatting."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(str(record.msg))
        if record.args:
            if isinstance(record.args, Mapping):
                record.args = {
                    key: redact_value(value, key=str(key)) for key, value in record.args.items()
                }
            else:
                record.args = tuple(redact_value(value) for value in record.args)
        for key, value in list(record.__dict__.items()):
            if key in _RESERVED_LOG_KEYS or key.startswith("_"):
                continue
            record.__dict__[key] = redact_value(value, key=key)
        return True


class TraceContextFilter(logging.Filter):
    """Add the active trace and span IDs to each record."""

    def filter(self, record: logging.LogRecord) -> bool:
        span_context = trace.get_current_span().get_span_context()
        record.trace_id = f"{span_context.trace_id:032x}" if span_context.is_valid else ""
        record.span_id = f"{span_context.span_id:016x}" if span_context.is_valid else ""
        return True


class JsonFormatter(logging.Formatter):
    """Render one JSON object per line on stdout."""

    def __init__(self, *, service: str, environment: str, version: str) -> None:
        super().__init__()
        self.service = service
        self.environment = environment
        self.version = version

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", record.getMessage()),
            "service": self.service,
            "environment": self.environment,
            "version": self.version,
            "logger": record.name,
            "trace_id": getattr(record, "trace_id", ""),
            "span_id": getattr(record, "span_id", ""),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOG_KEYS or key.startswith("_"):
                continue
            if key in {"timestamp", "level", "event", "service", "environment", "version"}:
                continue
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(redact_value(payload), default=str, separators=(",", ":"))


def configure_logging(settings: Settings) -> None:
    """Install the JSON handler on the root logger and uvicorn loggers."""
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(TraceContextFilter())
    handler.addFilter(RedactionFilter())
    handler.setFormatter(
        JsonFormatter(
            service=settings.otel_service_name,
            environment=settings.app_env,
            version=settings.app_version or "dev",
        ),
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True


# ---------------------------------------------------------------------------
# Tracing and metrics
# ---------------------------------------------------------------------------

_INSTRUMENTS: Instruments | None = None
_STATE: TelemetryState | None = None


@dataclass
class Instruments:
    """Metric instruments shared by the request and domain layers."""

    http_requests: Counter
    http_duration: Histogram
    bookings: Counter
    promotions: Counter
    open_seat_with_waitlist: Any
    overbooked_sessions: Any


@dataclass
class TelemetryState:
    """Providers and instruments owned by one application process."""

    enabled: bool
    tracer_provider: TracerProvider | None
    meter_provider: MeterProvider | None
    tracer: Tracer
    meter: Meter


def _sampler(settings: Settings) -> Sampler:
    name = settings.otel_traces_sampler.lower()
    if name in {"always_on", "alwayson"}:
        return ALWAYS_ON
    if name in {"always_off", "alwaysoff"}:
        return ALWAYS_OFF
    return ParentBased(TraceIdRatioBased(settings.otel_traces_sampler_arg))


def _headers(settings: Settings) -> dict[str, str]:
    headers: dict[str, str] = {}
    for pair in settings.otel_exporter_otlp_headers.split(","):
        key, separator, value = pair.partition("=")
        if separator and key.strip():
            headers[key.strip()] = value.strip()
    return headers


def _observable_gauges(settings: Settings, meter: Meter) -> tuple[Any, Any]:
    """Create DB-backed gauges refreshed by the metric reader, never in memory."""
    if not settings.database_url:
        return (
            meter.create_observable_gauge(
                "openseat_open_seat_with_waitlist",
                callbacks=[lambda options: [Observation(0)]],
                description="Scheduled sessions with a free seat and a non-empty waitlist.",
            ),
            meter.create_observable_gauge(
                "openseat_overbooked_sessions",
                callbacks=[lambda options: [Observation(0)]],
                description="Sessions where occupied seats exceed capacity.",
            ),
        )

    from sqlalchemy import text

    from app.db import get_engine

    engine = get_engine(settings.database_url)
    attributes = {"environment": settings.app_env, "version": settings.app_version or "dev"}

    def _scalar(query: str) -> int:
        try:
            with engine.connect() as connection:
                return int(connection.execute(text(query)).scalar() or 0)
        except Exception:  # pragma: no cover - defensive: metrics must not break the app
            LOGGER.warning("metric_gauge_failed", exc_info=True)
            return 0

    open_seat_query = """
        SELECT count(*)
        FROM sessions s
        WHERE s.status = 'scheduled'
          AND s.capacity > (
              SELECT count(*) FROM bookings b
              WHERE b.session_id = s.id AND b.status IN ('confirmed', 'checked_in')
          )
          AND EXISTS (
              SELECT 1 FROM bookings b
              WHERE b.session_id = s.id AND b.status = 'waitlisted'
          )
    """
    overbooked_query = """
        SELECT count(*)
        FROM sessions s
        WHERE s.capacity < (
            SELECT count(*) FROM bookings b
            WHERE b.session_id = s.id AND b.status IN ('confirmed', 'checked_in')
        )
    """

    def _open_seat_callback(options: Any) -> Iterable[Observation]:
        yield Observation(_scalar(open_seat_query), attributes)

    def _overbooked_callback(options: Any) -> Iterable[Observation]:
        yield Observation(_scalar(overbooked_query), attributes)

    return (
        meter.create_observable_gauge(
            "openseat_open_seat_with_waitlist",
            callbacks=[_open_seat_callback],
            description="Scheduled sessions with a free seat and a non-empty waitlist.",
        ),
        meter.create_observable_gauge(
            "openseat_overbooked_sessions",
            callbacks=[_overbooked_callback],
            description="Sessions where occupied seats exceed capacity.",
        ),
    )


def configure_telemetry(
    settings: Settings,
    *,
    span_exporter: SpanExporter | None = None,
    metric_reader: MetricReader | None = None,
) -> TelemetryState:
    """Create providers and instruments. Export is skipped without an endpoint."""
    global _INSTRUMENTS, _STATE

    enabled = span_exporter is not None or metric_reader is not None or settings.telemetry_enabled
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.app_env,
            "service.version": settings.app_version or "dev",
        },
    )

    if not enabled:
        state = TelemetryState(
            enabled=False,
            tracer_provider=None,
            meter_provider=None,
            tracer=trace.get_tracer("openseat"),
            meter=metrics.get_meter("openseat"),
        )
        _STATE = state
        _INSTRUMENTS = None
        if settings.app_env != "test":
            configure_logging(settings)
        return state

    tracer_provider = TracerProvider(resource=resource, sampler=_sampler(settings))
    headers = _headers(settings)
    if span_exporter is not None:
        tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    elif settings.telemetry_enabled:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=f"{settings.otel_exporter_otlp_endpoint.rstrip('/')}/v1/traces",
                    headers=headers,
                ),
            ),
        )

    if metric_reader is not None:
        readers: list[MetricReader] = [metric_reader]
    elif settings.telemetry_enabled:
        readers = [
            PeriodicExportingMetricReader(
                OTLPMetricExporter(
                    endpoint=f"{settings.otel_exporter_otlp_endpoint.rstrip('/')}/v1/metrics",
                    headers=headers,
                ),
                export_interval_millis=settings.otel_metric_export_interval_ms,
            ),
        ]
    else:
        readers = []

    meter_provider = MeterProvider(resource=resource, metric_readers=readers)
    meter = meter_provider.get_meter("openseat")
    attributes = {"environment": settings.app_env, "version": settings.app_version or "dev"}

    open_seat, overbooked = _observable_gauges(settings, meter)
    instruments = Instruments(
        http_requests=meter.create_counter(
            "openseat_http_requests_total",
            unit="1",
            description="HTTP requests handled by the API.",
        ),
        http_duration=meter.create_histogram(
            "openseat_http_request_duration_seconds",
            unit="s",
            description="HTTP request latency.",
        ),
        bookings=meter.create_counter(
            "openseat_bookings_total",
            unit="1",
            description="Booking attempts by result.",
        ),
        promotions=meter.create_counter(
            "openseat_promotions_total",
            unit="1",
            description="Waitlist promotion attempts by result.",
        ),
        open_seat_with_waitlist=open_seat,
        overbooked_sessions=overbooked,
    )
    instruments.http_requests.add(0, attributes)

    state = TelemetryState(
        enabled=True,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        tracer=tracer_provider.get_tracer("openseat"),
        meter=meter,
    )
    _STATE = state
    _INSTRUMENTS = instruments

    if settings.database_url:
        try:
            from app.db import get_engine

            SQLAlchemyInstrumentor().instrument(
                engine=get_engine(settings.database_url),
                tracer_provider=tracer_provider,
            )
        except Exception:  # pragma: no cover - instrumentation must not block startup
            LOGGER.warning("sqlalchemy_instrumentation_failed", exc_info=True)
    HTTPXClientInstrumentor().instrument(tracer_provider=tracer_provider)

    if settings.app_env != "test":
        configure_logging(settings)
    return state


def instrument_app(app: FastAPI, state: TelemetryState | None = None) -> None:
    """Attach FastAPI server spans to the application."""
    resolved = state or _STATE
    if resolved is None or not resolved.enabled or resolved.tracer_provider is None:
        return
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=resolved.tracer_provider,
        meter_provider=resolved.meter_provider,
        excluded_urls="/healthz",
    )


def get_tracer() -> Tracer:
    """Return the process tracer, falling back to the global no-op tracer."""
    if _STATE is not None:
        return _STATE.tracer
    return trace.get_tracer("openseat")


def _attributes(**extra: Any) -> dict[str, Any]:
    attributes = dict(extra)
    state = _STATE
    if state is not None and state.tracer_provider is not None:
        resource = state.tracer_provider.resource
        attributes["environment"] = resource.attributes.get("deployment.environment", "")
        attributes["version"] = resource.attributes.get("service.version", "")
    return attributes


def record_http_request(
    *,
    method: str,
    route: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """Record one HTTP request for the traffic and latency panels."""
    if _INSTRUMENTS is None:
        return
    attributes = _attributes(method=method, route=route, status=str(status_code))
    _INSTRUMENTS.http_requests.add(1, attributes)
    _INSTRUMENTS.http_duration.record(duration_seconds, attributes)


def record_booking(result: str) -> None:
    """Count a booking attempt by its outcome."""
    if _INSTRUMENTS is None:
        return
    _INSTRUMENTS.bookings.add(1, _attributes(result=result))


def record_promotion(result: str) -> None:
    """Count a waitlist promotion attempt by its outcome."""
    if _INSTRUMENTS is None:
        return
    _INSTRUMENTS.promotions.add(1, _attributes(result=result))


def current_trace_id() -> str:
    """Return the active trace ID, or a random one when no span is recording."""
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        return f"{span_context.trace_id:032x}"
    return secrets.token_hex(16)


def trace_header() -> dict[str, str]:
    """Return the response header that correlates an error with its trace."""
    return {"X-Trace-Id": current_trace_id()}


def set_span_result(span: Span, result: str, **attributes: Any) -> None:
    """Set a stable result attribute and error status on a span."""
    span.set_attribute("result", result)
    for key, value in attributes.items():
        span.set_attribute(key, value)
    if result == "error":
        span.set_status(Status(StatusCode.ERROR))


class Timer:
    """Small context manager that records elapsed seconds."""

    def __init__(self) -> None:
        self.started = time.perf_counter()

    @property
    def elapsed(self) -> float:
        return time.perf_counter() - self.started


def http_metrics_middleware() -> Callable[[Any, Callable[[Any], Any]], Any]:
    """Build the middleware that records metrics and adds ``X-Trace-Id``."""

    async def middleware(request: Any, call_next: Callable[[Any], Any]) -> Any:
        timer = Timer()
        response = await call_next(request)
        route = request.scope.get("route")
        route_path = getattr(route, "path", None) or "unmatched"
        record_http_request(
            method=request.method,
            route=route_path,
            status_code=response.status_code,
            duration_seconds=timer.elapsed,
        )
        response.headers.setdefault("X-Trace-Id", current_trace_id())
        return response

    return middleware


def shutdown_telemetry() -> None:
    """Flush providers and remove global instrumentation.

    Tests call this after inspecting an in-memory exporter so the next test
    starts with a clean provider instead of writing to a shut-down one.
    """
    global _INSTRUMENTS, _STATE
    if _STATE is not None:
        if _STATE.tracer_provider is not None:
            _STATE.tracer_provider.shutdown()
        if _STATE.meter_provider is not None:
            _STATE.meter_provider.shutdown()
    try:
        HTTPXClientInstrumentor().uninstrument()
        SQLAlchemyInstrumentor().uninstrument()
    except Exception:  # pragma: no cover - defensive cleanup
        LOGGER.debug("telemetry_uninstrument_failed", exc_info=True)
    _STATE = None
    _INSTRUMENTS = None
