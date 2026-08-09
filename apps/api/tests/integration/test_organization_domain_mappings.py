from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

import httpx
import pytest
from app.admin.service import (
    create_domain_mapping,
    list_domain_mappings,
    reassign_domain_mapping,
    remove_domain_mapping,
)
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import EntityStatus, Role
from app.auth.sessions import create_session
from app.main import create_app
from app.tenancy.coordinator import CandidateTenantMigrationCoordinator
from sqlalchemy.ext.asyncio import AsyncSession


class _Database:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        yield self.session


@pytest.mark.asyncio
async def test_mapping_create_normalizes_lists_and_rejects_duplicate_active_domain(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    db_session.add(organization)
    await db_session.flush()
    mapping = await create_domain_mapping(
        db_session,
        domain=" Example.TEST ",
        organization_id=organization.id,
        actor_user_id=None,
        correlation_id="mapping-create",
        now=clock.now(),
    )
    assert mapping.normalized_domain == "example.test"
    assert await list_domain_mappings(db_session) == [mapping]
    with pytest.raises(AuthError) as duplicate:
        await create_domain_mapping(
            db_session,
            domain="example.test",
            organization_id=organization.id,
            actor_user_id=None,
            correlation_id="duplicate",
            now=clock.now(),
        )
    assert duplicate.value.code is ErrorCode.IDENTITY_CONFLICT
    with pytest.raises(AuthError) as missing:
        await create_domain_mapping(
            db_session,
            domain="missing.example",
            organization_id=UUID(int=999),
            actor_user_id=None,
            correlation_id="missing",
            now=clock.now(),
        )
    assert missing.value.code is ErrorCode.RESOURCE_NOT_FOUND
    organization.status = EntityStatus.DISABLED.value
    with pytest.raises(AuthError) as inactive:
        await create_domain_mapping(
            db_session,
            domain="inactive.example",
            organization_id=organization.id,
            actor_user_id=None,
            correlation_id="inactive",
            now=clock.now(),
        )
    assert inactive.value.code is ErrorCode.IDENTITY_CONFLICT


@pytest.mark.asyncio
async def test_admin_mapping_http_contract_and_non_admin_denial(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    target = factories.organization()
    admin = factories.user(organization=organization, role=Role.ADMIN.value)
    candidate = factories.user(organization=organization, role=Role.CANDIDATE.value)
    db_session.add_all([organization, target, admin, candidate])
    await db_session.flush()
    db_session.add(factories.candidate_profile(organization=organization, user=candidate))
    await db_session.flush()
    admin_session = await create_session(db_session, admin, now=clock.now())
    candidate_session = await create_session(db_session, candidate, now=clock.now())
    app = create_app(testing=True)
    app.state.database = _Database(db_session)
    app.state.clock = clock.now
    transport = httpx.ASGITransport(app=app)
    headers = {
        "Origin": "http://localhost:5173",
        "X-CSRF-Token": admin_session.csrf_token,
    }
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        anonymous = await client.get("/api/v1/admin/organization-domain-mappings")
        client.cookies.set("mi_session_test", admin_session.token)
        client.cookies.set("mi_csrf", admin_session.csrf_token)
        created = await client.post(
            "/api/v1/admin/organization-domain-mappings",
            headers=headers,
            json={"domain": "Example.TEST", "organizationId": str(organization.id)},
        )
        listed = await client.get("/api/v1/admin/organization-domain-mappings")
        client.cookies.set("mi_session_test", candidate_session.token)
        forbidden = await client.delete(
            f"/api/v1/admin/organization-domain-mappings/{created.json()['id']}",
            headers={
                "Origin": "http://localhost:5173",
                "X-CSRF-Token": candidate_session.csrf_token,
            },
        )
        client.cookies.set("mi_session_test", admin_session.token)
        client.cookies.set("mi_csrf", admin_session.csrf_token)
        reassigned = await client.patch(
            f"/api/v1/admin/organization-domain-mappings/{created.json()['id']}",
            headers=headers,
            json={"organizationId": str(target.id)},
        )
        removed = await client.delete(
            f"/api/v1/admin/organization-domain-mappings/{created.json()['id']}",
            headers=headers,
        )
        active_only = await client.get("/api/v1/admin/organization-domain-mappings")
        with_removed = await client.get(
            "/api/v1/admin/organization-domain-mappings?include_removed=true"
        )
    assert anonymous.status_code == 401
    assert created.status_code == 201, created.text
    assert created.json()["domain"] == "example.test"
    assert listed.json()["items"][0]["id"] == created.json()["id"]
    assert forbidden.status_code == 403
    assert reassigned.status_code == 200
    assert reassigned.json()["organizationId"] == str(target.id)
    assert removed.status_code == 204
    assert active_only.json()["items"] == []
    assert with_removed.json()["items"][0]["status"] == "REMOVED"


@pytest.mark.asyncio
async def test_mapping_mutations_fail_closed_for_invalid_or_inactive_resources(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    source = factories.organization()
    inactive = factories.organization(status=EntityStatus.DISABLED.value)
    mapping = factories.domain_mapping(organization=source)
    removed = factories.domain_mapping(
        organization=source,
        normalized_domain="removed.example",
        removed_at=clock.now(),
    )
    db_session.add_all([source, inactive, mapping, removed])
    await db_session.flush()

    with pytest.raises(AuthError) as invalid_domain:
        await create_domain_mapping(
            db_session,
            domain="not a domain",
            organization_id=source.id,
            actor_user_id=None,
            correlation_id="invalid",
            now=clock.now(),
        )
    assert invalid_domain.value.code is ErrorCode.VALIDATION_ERROR

    for missing_id in (UUID(int=998), removed.id):
        with pytest.raises(AuthError) as unavailable:
            await remove_domain_mapping(
                db_session,
                mapping_id=missing_id,
                actor_user_id=None,
                correlation_id="unavailable",
                now=clock.now(),
            )
        assert unavailable.value.code is ErrorCode.RESOURCE_NOT_FOUND

    for target_id, expected in (
        (UUID(int=997), ErrorCode.RESOURCE_NOT_FOUND),
        (inactive.id, ErrorCode.IDENTITY_CONFLICT),
    ):
        with pytest.raises(AuthError) as target_error:
            await reassign_domain_mapping(
                db_session,
                mapping_id=mapping.id,
                target_organization_id=target_id,
                coordinator=CandidateTenantMigrationCoordinator(),
                actor_user_id=None,
                correlation_id="target-error",
                now=clock.now(),
            )
        assert target_error.value.code is expected
