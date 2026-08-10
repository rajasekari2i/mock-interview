from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

import httpx
import pytest
from app.auth.models import AuditEvent, EntityStatus, Role
from app.auth.sessions import create_session
from app.interviews.models import ScheduledInterview
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
async def test_manager_schedules_once_replays_and_candidate_sees_allocation(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    manager = factories.user(organization=organization, role=Role.MANAGER.value)
    candidate = factories.user(organization=organization, role=Role.CANDIDATE.value)
    db_session.add_all([organization, manager, candidate])
    await db_session.flush()
    jd = factories.job_description(organization=organization, creator=manager)
    db_session.add_all([factories.candidate_profile(organization=organization, user=candidate), jd])
    await db_session.flush()
    manager_session = await create_session(db_session, manager, now=clock.now())
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now
    headers = {
        "Origin": "http://localhost:5173",
        "X-CSRF-Token": manager_session.csrf_token,
        "Idempotency-Key": "00000000-0000-0000-0000-000000000001",
    }
    payload = {
        "candidateId": str(candidate.id),
        "jobDescriptionId": str(jd.id),
        "scheduledAt": (clock.now() + timedelta(days=1)).isoformat(),
    }
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set("mi_session_test", manager_session.token)
        client.cookies.set("mi_csrf", manager_session.csrf_token)
        created = await client.post("/api/v1/manager/interviews", headers=headers, json=payload)
        replayed = await client.post("/api/v1/manager/interviews", headers=headers, json=payload)
        conflict = await client.post(
            "/api/v1/manager/interviews",
            headers=headers,
            json={**payload, "scheduledAt": (clock.now() + timedelta(days=2)).isoformat()},
        )
        manager_list = await client.get("/api/v1/manager/interviews")
        candidates = await client.get("/api/v1/manager/candidates")

    assert created.status_code == 201, created.text
    assert created.headers["Idempotency-Replayed"] == "false"
    assert replayed.status_code == 200
    assert replayed.headers["Idempotency-Replayed"] == "true"
    assert conflict.status_code == 409
    assert len(manager_list.json()["items"]) == 1
    assert candidates.json()["items"] == [
        {"id": str(candidate.id), "displayName": candidate.display_name, "email": candidate.email}
    ]
    assert await db_session.scalar(select(func.count(ScheduledInterview.id))) == 1
    assert (
        await db_session.scalar(
            select(func.count(AuditEvent.id)).where(AuditEvent.event_type == "INTERVIEW_SCHEDULED")
        )
        == 1
    )

    candidate_session = await create_session(db_session, candidate, now=clock.now())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as candidate_client:
        candidate_client.cookies.set("mi_session_test", candidate_session.token)
        allocation = await candidate_client.get("/api/v1/candidate/interviews")
    assert [item["id"] for item in allocation.json()["items"]] == [created.json()["id"]]


@pytest.mark.asyncio
async def test_scheduling_rejects_invalid_or_unavailable_resources_without_partial_rows(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    other_organization = factories.organization(slug="other")
    manager = factories.user(organization=organization, role=Role.MANAGER.value)
    candidate = factories.user(organization=organization, role=Role.CANDIDATE.value)
    disabled = factories.user(
        organization=organization,
        role=Role.CANDIDATE.value,
        status=EntityStatus.DISABLED.value,
    )
    other_candidate = factories.user(organization=other_organization, role=Role.CANDIDATE.value)
    other_manager = factories.user(organization=organization, role=Role.MANAGER.value)
    db_session.add_all(
        [
            organization,
            other_organization,
            manager,
            candidate,
            disabled,
            other_candidate,
            other_manager,
        ]
    )
    await db_session.flush()
    own_jd = factories.job_description(organization=organization, creator=manager)
    other_jd = factories.job_description(organization=organization, creator=other_manager)
    db_session.add_all([own_jd, other_jd])
    await db_session.flush()
    auth = await create_session(db_session, manager, now=clock.now())
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now
    headers = {
        "Origin": "http://localhost:5173",
        "X-CSRF-Token": auth.csrf_token,
        "Idempotency-Key": "00000000-0000-0000-0000-000000000002",
    }
    base = {
        "candidateId": str(candidate.id),
        "jobDescriptionId": str(own_jd.id),
        "scheduledAt": (clock.now() + timedelta(hours=1)).isoformat(),
    }
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set("mi_session_test", auth.token)
        client.cookies.set("mi_csrf", auth.csrf_token)
        responses = [
            await client.post(
                "/api/v1/manager/interviews",
                headers=headers,
                json={**base, "candidateId": str(disabled.id)},
            ),
            await client.post(
                "/api/v1/manager/interviews",
                headers=headers,
                json={**base, "candidateId": str(other_candidate.id)},
            ),
            await client.post(
                "/api/v1/manager/interviews",
                headers=headers,
                json={**base, "jobDescriptionId": str(other_jd.id)},
            ),
            await client.post(
                "/api/v1/manager/interviews",
                headers=headers,
                json={**base, "scheduledAt": clock.now().isoformat()},
            ),
        ]
    assert [response.status_code for response in responses] == [404, 404, 404, 400]
    assert await db_session.scalar(select(func.count(ScheduledInterview.id))) == 0
