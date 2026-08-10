from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest
from app.admin.router import _response
from app.auth.dependencies import AuthenticatedRequest
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


def _security_headers(csrf: str) -> dict[str, str]:
    return {"Origin": "http://localhost:5173", "X-CSRF-Token": csrf}


@pytest.mark.asyncio
async def test_authenticated_me_and_all_admin_mutation_routes(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    admin = factories.user(
        organization=organization,
        role=Role.ADMIN.value,
        profile_picture_url="https://images.example.test/admin.png",
    )
    target = factories.user(organization=organization)
    db_session.add_all([organization, admin, target])
    await db_session.flush()
    created = await create_session(db_session, admin, now=clock.now())
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("mi_session_test", created.token)
        client.cookies.set("mi_csrf", created.csrf_token)
        current = await client.get("/api/v1/auth/me")
        provisioned = await client.post(
            "/api/v1/admin/users",
            headers=_security_headers(created.csrf_token),
            json={
                "organizationId": str(organization.id),
                "email": "candidate-api@example.com",
                "displayName": "API Candidate",
                "role": "CANDIDATE",
                "status": "ACTIVE",
            },
        )
        role_changed = await client.patch(
            f"/api/v1/admin/users/{target.id}/role",
            headers=_security_headers(created.csrf_token),
            json={"role": "CANDIDATE"},
        )
        disabled = await client.patch(
            f"/api/v1/admin/users/{target.id}/status",
            headers=_security_headers(created.csrf_token),
            json={"status": "DISABLED"},
        )

    assert current.json()["user"]["role"] == "ADMIN"
    assert current.json()["user"]["email"] == admin.email
    assert current.json()["user"]["profilePictureUrl"] == admin.profile_picture_url
    assert provisioned.status_code == 201, provisioned.text
    assert provisioned.json()["candidateProfileId"] is not None
    assert role_changed.json()["role"] == "CANDIDATE"
    assert role_changed.json()["candidateProfileId"] is not None
    assert disabled.json()["status"] == "DISABLED"


@pytest.mark.asyncio
async def test_candidate_me_includes_profile_and_non_admin_is_forbidden(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    candidate = factories.user(organization=organization, role=Role.CANDIDATE.value)
    db_session.add_all([organization, candidate])
    await db_session.flush()
    profile = factories.candidate_profile(organization=organization, user=candidate)
    db_session.add(profile)
    await db_session.flush()
    created = await create_session(db_session, candidate, now=clock.now())
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("mi_session_test", created.token)
        client.cookies.set("mi_csrf", created.csrf_token)
        current = await client.get("/api/v1/auth/me")
        forbidden = await client.post(
            "/api/v1/admin/users",
            headers=_security_headers(created.csrf_token),
            json={
                "organizationId": str(organization.id),
                "email": "nope@example.com",
                "displayName": "Nope",
                "role": "MANAGER",
                "status": "ACTIVE",
            },
        )

    assert current.json()["user"]["candidateProfileId"] == str(profile.id)
    assert forbidden.status_code == 403
    assert current.json()["user"]["email"] == candidate.email
    assert current.json()["user"]["profilePictureUrl"] is None


@pytest.mark.asyncio
async def test_candidate_session_without_profile_is_rejected(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    candidate = factories.user(organization=organization, role=Role.CANDIDATE.value)
    db_session.add_all([organization, candidate])
    await db_session.flush()
    created = await create_session(db_session, candidate, now=clock.now())
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set("mi_session_test", created.token)
        response = await client.get("/api/v1/auth/me")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CANDIDATE_PROFILE_CONFLICT"


@pytest.mark.asyncio
async def test_admin_response_fails_if_mutated_user_disappears(
    db_session: AsyncSession, factories: object
) -> None:
    organization = factories.organization()
    admin = factories.user(organization=organization, role=Role.ADMIN.value)
    db_session.add_all([organization, admin])
    await db_session.flush()
    record = factories.session(organization=organization, user=admin)
    db_session.add(record)
    await db_session.flush()
    context = AuthenticatedRequest(db_session, admin, record, None)
    with pytest.raises(RuntimeError, match="disappeared"):
        await _response(context, factories.uuid())
