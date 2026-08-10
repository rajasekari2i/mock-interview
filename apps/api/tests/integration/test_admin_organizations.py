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


def _headers(csrf: str) -> dict[str, str]:
    return {"Origin": "http://localhost:5173", "X-CSRF-Token": csrf}


@pytest.mark.asyncio
async def test_only_admin_can_create_and_list_organizations(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    existing = factories.organization()
    admin = factories.user(organization=existing, role=Role.ADMIN.value)
    candidate = factories.user(organization=existing, role=Role.CANDIDATE.value)
    db_session.add_all([existing, admin, candidate])
    await db_session.flush()
    db_session.add(factories.candidate_profile(organization=existing, user=candidate))
    await db_session.flush()
    admin_session = await create_session(db_session, admin, now=clock.now())
    candidate_session = await create_session(db_session, candidate, now=clock.now())
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set("mi_session_test", admin_session.token)
        client.cookies.set("mi_csrf", admin_session.csrf_token)
        missing_csrf = await client.post(
            "/api/v1/admin/organizations", json={"name": "No CSRF", "slug": "no-csrf"}
        )
        created = await client.post(
            "/api/v1/admin/organizations",
            headers=_headers(admin_session.csrf_token),
            json={"name": "Acme", "slug": "acme"},
        )
        listed = await client.get("/api/v1/admin/organizations")
        duplicate = await client.post(
            "/api/v1/admin/organizations",
            headers=_headers(admin_session.csrf_token),
            json={"name": "Duplicate", "slug": "ACME"},
        )
        client.cookies.set("mi_session_test", candidate_session.token)
        forbidden = await client.post(
            "/api/v1/admin/organizations",
            headers=_headers(candidate_session.csrf_token),
            json={"name": "Forbidden", "slug": "forbidden"},
        )

    assert missing_csrf.status_code == 403
    assert created.status_code == 201
    assert created.json()["status"] == "ACTIVE"
    assert any(item["slug"] == "acme" for item in listed.json()["items"])
    assert duplicate.status_code == 409
    assert forbidden.status_code == 403
