from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest
from app.auth.models import AuthenticationSession, RevocationReason
from app.auth.sessions import create_session
from app.main import create_app
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class _Database:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        yield self.session


@pytest.mark.asyncio
async def test_global_logout_revokes_two_sessions_and_clears_both_cookies(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    user = factories.user(organization=organization)
    db_session.add_all([organization, user])
    await db_session.flush()
    first = await create_session(db_session, user, now=clock.now())
    second = await create_session(db_session, user, now=clock.now())
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("mi_session_test", first.token)
        client.cookies.set("mi_csrf", first.csrf_token)
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "http://localhost:5173", "X-CSRF-Token": first.csrf_token},
        )

    assert response.status_code == 204
    assert response.headers["cache-control"] == "no-store"
    assert response.headers.get_list("set-cookie")[0].startswith("mi_session_test=")
    assert any(cookie.startswith("mi_csrf=") for cookie in response.headers.get_list("set-cookie"))
    assert await db_session.scalar(
        select(func.count())
        .select_from(AuthenticationSession)
        .where(
            AuthenticationSession.user_id == user.id,
            AuthenticationSession.revocation_reason == RevocationReason.LOGOUT_ALL.value,
        )
    ) == 2
    assert second.record.revoked_at == clock.now()


@pytest.mark.asyncio
async def test_logout_is_idempotent_for_unknown_session_but_still_requires_csrf(
    db_session: AsyncSession, clock: object
) -> None:
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("mi_session_test", "unknown")
        client.cookies.set("mi_csrf", "csrf-value")
        denied = await client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "https://attacker.test", "X-CSRF-Token": "csrf-value"},
        )
        allowed = await client.post(
            "/api/v1/auth/logout",
            headers={"Origin": "http://localhost:5173", "X-CSRF-Token": "csrf-value"},
        )

    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "CSRF_DENIED"
    assert allowed.status_code == 204
