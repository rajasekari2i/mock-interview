from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

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
async def test_candidate_interview_projection_is_self_scoped_and_paginated(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    manager = factories.user(organization=organization, role=Role.MANAGER.value)
    first = factories.user(organization=organization, role=Role.CANDIDATE.value)
    second = factories.user(organization=organization, role=Role.CANDIDATE.value)
    jd = factories.job_description(organization=organization, creator=manager)
    db_session.add_all([organization, manager, first, second])
    await db_session.flush()
    db_session.add_all(
        [
            factories.candidate_profile(organization=organization, user=first),
            factories.candidate_profile(organization=organization, user=second),
            jd,
        ]
    )
    await db_session.flush()
    first_interview = factories.scheduled_interview(
        organization=organization,
        candidate=first,
        manager=manager,
        job_description=jd,
        scheduled_at=clock.now() + timedelta(days=1),
    )
    second_interview = factories.scheduled_interview(
        organization=organization,
        candidate=second,
        manager=manager,
        job_description=jd,
        scheduled_at=clock.now() + timedelta(days=2),
    )
    db_session.add_all([first_interview, second_interview])
    await db_session.flush()
    session = await create_session(db_session, first, now=clock.now())
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set("mi_session_test", session.token)
        response = await client.get("/api/v1/candidate/interviews?page=1&pageSize=1")
        empty_page = await client.get("/api/v1/candidate/interviews?page=2&pageSize=1")

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": str(first_interview.id),
                "jobDescription": {"id": str(jd.id), "title": jd.title},
                "scheduledAt": first_interview.scheduled_at.isoformat().replace("+00:00", "Z"),
                "status": "SCHEDULED",
            }
        ],
        "page": 1,
        "pageSize": 1,
        "totalItems": 1,
        "totalPages": 1,
    }
    assert empty_page.json()["items"] == []


@pytest.mark.asyncio
async def test_candidate_interview_endpoint_rejects_wrong_role_and_validates_page(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    manager = factories.user(organization=organization, role=Role.MANAGER.value)
    db_session.add_all([organization, manager])
    await db_session.flush()
    session = await create_session(db_session, manager, now=clock.now())
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set("mi_session_test", session.token)
        forbidden = await client.get("/api/v1/candidate/interviews")
        invalid = await client.get("/api/v1/candidate/interviews?page=0&pageSize=101")
    assert forbidden.status_code == 403
    assert invalid.status_code in {403, 422}
