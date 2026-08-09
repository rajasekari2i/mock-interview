from __future__ import annotations

import httpx
import pytest
from app.main import create_app


@pytest.mark.asyncio
async def test_login_redirect_and_unauthenticated_me_contract() -> None:
    app = create_app(testing=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=False
    ) as client:
        login = await client.get("/api/v1/auth/google/login")
        current = await client.get("/api/v1/auth/me")
        cancelled = await client.get(
            "/api/v1/auth/google/callback", params={"state": "state", "error": "cancelled"}
        )
        incomplete = await client.get(
            "/api/v1/auth/google/callback", params={"state": "state"}
        )

    assert login.status_code == 302
    assert login.headers["cache-control"] == "no-store"
    assert "state=" in login.headers["location"]
    assert current.status_code == 401
    assert current.headers["cache-control"] == "no-store"
    assert current.json()["error"]["recovery"] == "SIGN_IN_AGAIN"
    assert "OAUTH_CANCELLED" in cancelled.headers["location"]
    assert "OAUTH_RESPONSE_INVALID" in incomplete.headers["location"]


def test_application_has_no_public_registration_route() -> None:
    paths = create_app(testing=True).openapi()["paths"]
    assert not any("register" in path or "signup" in path for path in paths)
