from __future__ import annotations

import httpx
import pytest
from app.auth.authorization import scoped_authorization_dependency
from app.auth.errors import AuthError
from app.auth.models import RevocationReason, Role
from app.auth.policies import AuthContext, Capability, ResourceScope
from app.auth.sessions import create_session, resolve_session, revoke_all_sessions
from app.core.observability import (
    AUTH_METRICS,
    metrics,
    record_login_denial,
    record_login_success,
)
from app.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_authentication_metrics_cover_session_denial_and_latency_signals(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    metrics.reset()
    organization = factories.organization()
    user = factories.user(organization=organization)
    db_session.add_all([organization, user])
    await db_session.flush()
    created = await create_session(db_session, user, now=clock.now())
    await revoke_all_sessions(
        db_session,
        user_id=user.id,
        reason=RevocationReason.SECURITY_REVOKED,
        now=clock.now(),
    )
    with pytest.raises(AuthError):
        await resolve_session(db_session, created.token, now=clock.now())
    expiring = await create_session(db_session, user, now=clock.now())
    clock.advance(hours=2)
    with pytest.raises(AuthError):
        await resolve_session(db_session, expiring.token, now=clock.now())
    with pytest.raises(AuthError):
        await scoped_authorization_dependency(
            AuthContext(user.id, organization.id, Role.MANAGER, None),
            ResourceScope(organization.id, Capability.ADMIN_MANAGE_USERS),
        )

    app = create_app(testing=True)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/api/v1/auth/me")).status_code == 401

    snapshot = metrics.snapshot()
    names = {entry["name"] for entry in snapshot["counters"]}
    assert {
        "auth_session_created_total",
        "auth_session_revoked_total",
        "auth_session_expired_total",
        "auth_authorization_denied_total",
    } <= names
    assert any(
        entry["name"] == AUTH_METRICS.latency_name for entry in snapshot["observations"]
    )


def test_login_and_provider_counters_are_declared_and_secret_safe() -> None:
    metrics.reset()
    record_login_success(role="MANAGER")
    record_login_denial(reason="ACCESS_NOT_PROVISIONED")
    record_login_denial(reason="OAUTH_PROVIDER_UNAVAILABLE", provider_failure=True)
    values: dict[object, object] = {}
    for entry in metrics.snapshot()["counters"]:
        name = entry["name"]
        values[name] = int(values.get(name, 0)) + int(entry["value"])
    assert values == {
        "auth_login_denied_total": 2,
        "auth_login_success_total": 1,
        "auth_provider_failure_total": 1,
    }
