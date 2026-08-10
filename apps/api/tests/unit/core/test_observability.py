from __future__ import annotations

import re
from typing import cast

import httpx
import pytest
from app.core.observability import (
    AUTH_METRICS,
    CorrelationMiddleware,
    MetricsRegistry,
    get_correlation_id,
    structured_event,
)
from fastapi import FastAPI, Request
from starlette.types import Message, Receive, Scope, Send


def make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)

    @app.get("/correlation")
    async def correlation(request: Request) -> dict[str, str]:
        return {
            "context": get_correlation_id(),
            "state": request.state.correlation_id,
        }

    return app


@pytest.mark.asyncio
async def test_correlation_id_is_generated_propagated_and_returned() -> None:
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/correlation")

    correlation_id = response.headers["X-Correlation-ID"]
    assert re.fullmatch(r"[0-9a-f]{32}", correlation_id)
    assert response.json() == {"context": correlation_id, "state": correlation_id}


@pytest.mark.asyncio
async def test_valid_incoming_correlation_is_retained_and_invalid_input_is_replaced() -> None:
    transport = httpx.ASGITransport(app=make_app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        retained = await client.get("/correlation", headers={"X-Correlation-ID": "request-123_ABC"})
        replaced = await client.get(
            "/correlation", headers={"X-Correlation-ID": "unsafe value\nlog"}
        )

    assert retained.headers["X-Correlation-ID"] == "request-123_ABC"
    assert replaced.headers["X-Correlation-ID"] != "unsafe value\nlog"


def test_structured_event_has_required_fields_and_recursively_redacts_secrets() -> None:
    event = structured_event(
        severity="WARNING",
        event_name="auth.login.denied",
        correlation_id="request-123",
        reason_code="PROVIDER_FAILURE",
        details={
            "session_token": "raw-session",
            "nested": {"authorization": "Bearer raw", "safe_count": 2},
            "items": [{"nonce": "raw-nonce"}, "safe"],
        },
    )

    assert event["severity"] == "WARNING"
    assert event["event_name"] == "auth.login.denied"
    assert event["correlation_id"] == "request-123"
    assert event["reason_code"] == "PROVIDER_FAILURE"
    assert event["timestamp"].endswith("Z")
    assert event["details"] == {
        "session_token": "[REDACTED]",
        "nested": {"authorization": "[REDACTED]", "safe_count": 2},
        "items": [{"nonce": "[REDACTED]"}, "safe"],
    }


def test_metrics_registry_exposes_required_counters_and_latency_observations() -> None:
    assert {
        "jd_creation_total",
        "interview_scheduling_total",
        "role_list_request_total",
    } <= set(AUTH_METRICS.counter_names)
    registry = MetricsRegistry()
    for metric_name in AUTH_METRICS.counter_names:
        registry.increment(metric_name, reason="test")
    registry.observe(AUTH_METRICS.latency_name, 0.125, operation="auth.me")

    snapshot = registry.snapshot()
    assert {item["name"] for item in snapshot["counters"]} == set(AUTH_METRICS.counter_names)
    assert all(item["value"] == 1 for item in snapshot["counters"])
    assert snapshot["observations"] == [
        {
            "name": AUTH_METRICS.latency_name,
            "value": 0.125,
            "labels": {"operation": "auth.me"},
        }
    ]

    registry.reset()
    assert registry.snapshot() == {"counters": [], "observations": []}


def test_metrics_reject_unknown_names_negative_values_and_secret_labels() -> None:
    registry = MetricsRegistry()
    secret_label = {"token": "secret"}

    with pytest.raises(ValueError):
        registry.increment("unknown")
    with pytest.raises(ValueError):
        registry.increment(AUTH_METRICS.counter_names[0], amount=-1)
    with pytest.raises(ValueError):
        registry.observe(AUTH_METRICS.latency_name, -0.1)
    with pytest.raises(ValueError):
        registry.observe("unknown", 0.1)
    with pytest.raises(ValueError):
        registry.increment(AUTH_METRICS.counter_names[0], **secret_label)


@pytest.mark.asyncio
async def test_non_http_scopes_pass_through_without_correlation_mutation() -> None:
    called = False

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal called
        called = scope["type"] == "lifespan"

    async def receive() -> Message:
        return {"type": "lifespan.startup"}

    async def send(message: Message) -> None:
        del message

    middleware = CorrelationMiddleware(app)
    await middleware(cast(Scope, {"type": "lifespan"}), receive, send)

    assert called is True
