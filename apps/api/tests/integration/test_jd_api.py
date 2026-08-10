from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest
from app.auth.models import AuditEvent, Role
from app.auth.sessions import create_session
from app.jds.models import JobDescription
from app.main import create_app
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.fixtures.jd_documents import SAMPLE_TEXT, VALID_TXT


class _Database:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        yield self.session


@pytest.mark.asyncio
async def test_manager_creates_manual_and_uploaded_jds_and_lists_only_owned_records(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    manager = factories.user(organization=organization, role=Role.MANAGER.value)
    other = factories.user(organization=organization, role=Role.MANAGER.value)
    other_jd = factories.job_description(organization=organization, creator=other)
    db_session.add_all([organization, manager, other])
    await db_session.flush()
    db_session.add(other_jd)
    await db_session.flush()
    session = await create_session(db_session, manager, now=clock.now())
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now
    headers = {"Origin": "http://localhost:5173", "X-CSRF-Token": session.csrf_token}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set("mi_session_test", session.token)
        client.cookies.set("mi_csrf", session.csrf_token)
        manual = await client.post(
            "/api/v1/manager/job-descriptions",
            headers=headers,
            json={"title": "Backend Engineer", "content": "Build reliable APIs."},
        )
        uploaded = await client.post(
            "/api/v1/manager/job-descriptions/upload",
            headers=headers,
            data={"title": "Platform Engineer"},
            files={"document": ("role.txt", VALID_TXT, "text/plain")},
        )
        listed = await client.get("/api/v1/manager/job-descriptions?page=1&pageSize=25")
        empty_page = await client.get("/api/v1/manager/job-descriptions?page=2&pageSize=25")

    assert manual.status_code == 201, manual.text
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["sourceFormat"] == "TXT"
    assert {item["title"] for item in listed.json()["items"]} == {
        "Backend Engineer",
        "Platform Engineer",
    }
    assert empty_page.json()["items"] == []
    assert SAMPLE_TEXT == await db_session.scalar(
        select(JobDescription.content_text).where(JobDescription.id == uploaded.json()["id"])
    )
    assert (
        await db_session.scalar(
            select(func.count(AuditEvent.id)).where(AuditEvent.event_type == "JD_CREATED")
        )
        == 2
    )


@pytest.mark.asyncio
async def test_manager_jd_mutations_require_csrf_and_reject_invalid_content_without_rows(
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
        denied = await client.post(
            "/api/v1/manager/job-descriptions",
            json={"title": "Denied", "content": "Must not persist"},
        )
        client.cookies.set("mi_csrf", session.csrf_token)
        invalid = await client.post(
            "/api/v1/manager/job-descriptions/upload",
            headers={
                "Origin": "http://localhost:5173",
                "X-CSRF-Token": session.csrf_token,
            },
            data={"title": "Invalid"},
            files={"document": ("role.txt", b"\x00binary", "text/plain")},
        )
        too_large = await client.post(
            "/api/v1/manager/job-descriptions/upload",
            headers={
                "Origin": "http://localhost:5173",
                "X-CSRF-Token": session.csrf_token,
            },
            data={"title": "Large"},
            files={"document": ("role.txt", b"x" * (5 * 1024 * 1024 + 1), "text/plain")},
        )
        blank_title = await client.post(
            "/api/v1/manager/job-descriptions/upload",
            headers={
                "Origin": "http://localhost:5173",
                "X-CSRF-Token": session.csrf_token,
            },
            data={"title": "   "},
            files={"document": ("role.txt", VALID_TXT, "text/plain")},
        )
    assert denied.status_code == 403
    assert invalid.status_code == 415
    assert too_large.status_code == 413
    assert blank_title.status_code == 400
    assert await db_session.scalar(select(func.count(JobDescription.id))) == 0


@pytest.mark.asyncio
async def test_admin_can_create_a_job_description_through_the_shared_flow(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    admin = factories.user(organization=organization, role=Role.ADMIN.value)
    db_session.add_all([organization, admin])
    await db_session.flush()
    session = await create_session(db_session, admin, now=clock.now())
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now
    headers = {"Origin": "http://localhost:5173", "X-CSRF-Token": session.csrf_token}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        client.cookies.set("mi_session_test", session.token)
        client.cookies.set("mi_csrf", session.csrf_token)
        created = await client.post(
            "/api/v1/manager/job-descriptions",
            headers=headers,
            json={"title": "Admin-created role", "content": "Shared hiring requirements."},
        )

    assert created.status_code == 201, created.text
    assert await db_session.scalar(
        select(JobDescription.created_by_user_id).where(
            JobDescription.id == created.json()["id"]
        )
    ) == admin.id
