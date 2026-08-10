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
async def test_admin_lists_application_users_and_jds_with_independent_stable_pages(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    other_organization = factories.organization(slug="other")
    admin = factories.user(organization=organization, role=Role.ADMIN.value, display_name="Admin")
    manager = factories.user(
        organization=other_organization, role=Role.MANAGER.value, display_name="Manager"
    )
    users = [
        factories.user(
            organization=organization if index % 2 == 0 else other_organization,
            role=Role.MANAGER.value,
            display_name=f"User {index:04d}",
        )
        for index in range(998)
    ]
    db_session.add_all([organization, other_organization, admin, manager, *users])
    await db_session.flush()
    jds = [
        factories.job_description(
            organization=other_organization,
            creator=manager,
            title=f"JD {index:04d}",
        )
        for index in range(1000)
    ]
    db_session.add_all(jds)
    await db_session.flush()
    auth = await create_session(db_session, admin, now=clock.now())
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set("mi_session_test", auth.token)
        user_ids: list[str] = []
        jd_ids: list[str] = []
        for page in range(1, 11):
            user_response = await client.get(f"/api/v1/admin/users?page={page}&pageSize=100")
            jd_response = await client.get(
                f"/api/v1/admin/job-descriptions?page={page}&pageSize=100"
            )
            assert user_response.status_code == jd_response.status_code == 200
            user_ids.extend(item["id"] for item in user_response.json()["items"])
            jd_ids.extend(item["id"] for item in jd_response.json()["items"])
        details = await client.get(f"/api/v1/admin/users/{users[0].id}")
    assert len(user_ids) == len(set(user_ids)) == 1000
    assert len(jd_ids) == len(set(jd_ids)) == 1000
    assert details.json()["displayName"] == users[0].display_name
    assert details.json()["profilePictureUrl"] is None

    manager_auth = await create_session(db_session, manager, now=clock.now())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as manager_client:
        manager_client.cookies.set("mi_session_test", manager_auth.token)
        denied_users = await manager_client.get("/api/v1/admin/users")
        denied_jds = await manager_client.get("/api/v1/admin/job-descriptions")
    assert denied_users.status_code == denied_jds.status_code == 403
