"""Secret-safe correlation, structured event, and in-process metrics primitives."""

from __future__ import annotations

import re
from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_CORRELATION_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,100}$")
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")
_SECRET_KEY_PARTS = frozenset(
    {"authorization", "code", "cookie", "nonce", "password", "secret", "state", "token"}
)


@dataclass(frozen=True)
class AuthMetricNames:
    counter_names: tuple[str, ...] = (
        "auth_login_success_total",
        "auth_login_denied_total",
        "auth_provider_failure_total",
        "auth_session_created_total",
        "auth_session_expired_total",
        "auth_session_revoked_total",
        "auth_authorization_denied_total",
    )
    latency_name: str = "auth_request_latency_seconds"


AUTH_METRICS = AuthMetricNames()


def _is_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(part in lowered for part in _SECRET_KEY_PARTS)


def _redact(value: object, key: str = "") -> object:
    if key and _is_secret_key(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {
            str(item_key): _redact(item_value, str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def structured_event(
    *,
    severity: str,
    event_name: str,
    correlation_id: str,
    reason_code: str,
    details: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build one serializable, secret-redacted structured log event."""

    timestamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    return {
        "timestamp": timestamp,
        "severity": severity,
        "event_name": event_name,
        "correlation_id": correlation_id,
        "reason_code": reason_code,
        "details": _redact(details or {}),
    }


class MetricsRegistry:
    """Small deterministic registry; a production exporter can consume its snapshot."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}
        self._observations: list[dict[str, object]] = []

    @staticmethod
    def _validate_labels(labels: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
        if any(_is_secret_key(key) for key in labels):
            raise ValueError("Secret-bearing metric labels are prohibited")
        return tuple(sorted(labels.items()))

    def increment(self, name: str, amount: int = 1, **labels: str) -> None:
        if name not in AUTH_METRICS.counter_names:
            raise ValueError(f"Unknown authentication counter: {name}")
        if amount < 0:
            raise ValueError("Counter increments cannot be negative")
        label_key = self._validate_labels(labels)
        key = (name, label_key)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + amount

    def observe(self, name: str, value: float, **labels: str) -> None:
        if name != AUTH_METRICS.latency_name:
            raise ValueError(f"Unknown authentication observation: {name}")
        if value < 0:
            raise ValueError("Latency observations cannot be negative")
        label_key = self._validate_labels(labels)
        observation: dict[str, object] = {
            "name": name,
            "value": value,
            "labels": dict(label_key),
        }
        with self._lock:
            self._observations.append(observation)

    def snapshot(self) -> dict[str, list[dict[str, object]]]:
        with self._lock:
            counters = [
                {"name": name, "value": value, "labels": dict(labels)}
                for (name, labels), value in sorted(self._counters.items())
            ]
            observations = [dict(item) for item in self._observations]
        return {"counters": counters, "observations": observations}

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._observations.clear()


metrics = MetricsRegistry()


def record_login_success(*, role: str) -> None:
    metrics.increment("auth_login_success_total", role=role)


def record_login_denial(*, reason: str, provider_failure: bool = False) -> None:
    metrics.increment("auth_login_denied_total", reason=reason)
    if provider_failure:
        metrics.increment("auth_provider_failure_total")


def get_correlation_id() -> str:
    return _correlation_id.get()


class CorrelationMiddleware:
    """Validate or create one correlation ID and propagate it through the request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get("X-Correlation-ID", "")
        correlation_id = incoming if _CORRELATION_PATTERN.fullmatch(incoming) else uuid4().hex
        token = _correlation_id.set(correlation_id)
        scope.setdefault("state", {})["correlation_id"] = correlation_id

        async def send_with_correlation(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)["X-Correlation-ID"] = correlation_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation)
        finally:
            _correlation_id.reset(token)


class AuthMetricsMiddleware:
    """Observe request latency for authentication and Admin security operations."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = str(scope.get("path", ""))
        if scope["type"] != "http" or not path.startswith(("/api/v1/auth", "/api/v1/admin")):
            await self.app(scope, receive, send)
            return
        started = perf_counter()
        try:
            await self.app(scope, receive, send)
        finally:
            metrics.observe(
                AUTH_METRICS.latency_name,
                perf_counter() - started,
                operation=path,
            )
