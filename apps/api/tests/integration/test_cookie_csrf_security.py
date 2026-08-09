from __future__ import annotations

import hashlib
import secrets

import httpx
import pytest
from app.auth.errors import AuthError, ErrorCode
from app.auth.security import CsrfPolicy, SessionCookiePolicy
from app.main import create_app


def test_csrf_requires_exact_origin_cookie_header_and_bound_digest() -> None:
    token = secrets.token_urlsafe(32)
    policy = CsrfPolicy(("https://app.example.test",))

    policy.validate(
        origin="https://app.example.test",
        cookie_token=token,
        header_token=token,
        expected_digest=hashlib.sha256(token.encode()).digest(),
    )
    for unsafe in (
        {"origin": "https://attacker.example", "header_token": token},
        {"origin": "https://app.example.test", "header_token": "wrong"},
    ):
        with pytest.raises(AuthError) as error:
            policy.validate(
                origin=unsafe["origin"],
                cookie_token=token,
                header_token=unsafe["header_token"],
                expected_digest=hashlib.sha256(token.encode()).digest(),
            )
        assert error.value.code is ErrorCode.CSRF_DENIED


def test_production_cookie_policy_is_host_only_secure_and_http_only() -> None:
    policy = SessionCookiePolicy.production()
    assert policy.name == "__Host-mi_session"
    assert policy.options == {
        "secure": True,
        "httponly": True,
        "samesite": "lax",
        "path": "/",
    }
    with pytest.raises(ValueError):
        SessionCookiePolicy.development("__Host-unsafe")


@pytest.mark.asyncio
async def test_credentialed_cors_uses_an_exact_origin_allowlist() -> None:
    transport = httpx.ASGITransport(app=create_app(testing=True))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        allowed = await client.options(
            "/api/v1/auth/me",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        denied = await client.options(
            "/api/v1/auth/me",
            headers={
                "Origin": "https://attacker.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert allowed.headers["access-control-allow-credentials"] == "true"
    assert "access-control-allow-origin" not in denied.headers
