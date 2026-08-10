from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest
from app.auth.models import Role
from app.auth.sessions import create_session
from app.main import create_app
from sqlalchemy.ext.asyncio import AsyncSession


class _Database:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        yield self.session


@pytest.mark.asyncio
@pytest.mark.parametrize("role", list(Role))
async def test_current_user_is_the_only_profile_exposed(
    db_session: AsyncSession, factories: object, clock: object, role: Role
) -> None:
    organization = factories.organization()
    authenticated = factories.user(
        organization=organization,
        role=role.value,
        email=f"{role.value.lower()}@example.test",
        normalized_email=f"{role.value.lower()}@example.test",
    )
    another = factories.user(
        organization=organization,
        email="another@example.test",
        normalized_email="another@example.test",
    )
    db_session.add_all([organization, authenticated, another])
    await db_session.flush()
    if role is Role.CANDIDATE:
        db_session.add(factories.candidate_profile(organization=organization, user=authenticated))
        await db_session.flush()
    created = await create_session(db_session, authenticated, now=clock.now())
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set("mi_session_test", created.token)
        response = await client.get("/api/v1/auth/me")
        guessed_profile = await client.get(f"/api/v1/auth/users/{another.id}/profile")

    assert response.status_code == 200
    assert response.json()["user"]["id"] == str(authenticated.id)
    assert response.json()["user"]["email"] == authenticated.email
    assert guessed_profile.status_code == 404
