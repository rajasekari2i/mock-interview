from __future__ import annotations

import pytest
from app.admin.service import create_organization, list_organizations
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import AuditEvent, EntityStatus, Organization
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_admin_creates_and_lists_active_organization(
    db_session: AsyncSession, clock: object
) -> None:
    created = await create_organization(
        db_session,
        name="  Acme Engineering  ",
        slug=" Acme-Engineering ",
        actor_user_id=None,
        correlation_id="organization-create",
        now=clock.now(),
    )

    assert created.name == "Acme Engineering"
    assert created.slug == "acme-engineering"
    assert created.status == EntityStatus.ACTIVE.value
    assert await list_organizations(db_session) == [created]
    assert await db_session.scalar(select(func.count()).select_from(AuditEvent)) == 1


@pytest.mark.asyncio
async def test_organization_creation_rejects_invalid_and_duplicate_values(
    db_session: AsyncSession, clock: object
) -> None:
    await create_organization(
        db_session,
        name="Acme",
        slug="acme",
        actor_user_id=None,
        correlation_id="first",
        now=clock.now(),
    )

    with pytest.raises(AuthError) as duplicate:
        await create_organization(
            db_session,
            name="Other Acme",
            slug="ACME",
            actor_user_id=None,
            correlation_id="duplicate",
            now=clock.now(),
        )
    assert duplicate.value.code is ErrorCode.IDENTITY_CONFLICT

    for name, slug in [("   ", "valid"), ("Valid", "not valid"), ("Valid", "-bad")]:
        with pytest.raises(AuthError) as invalid:
            await create_organization(
                db_session,
                name=name,
                slug=slug,
                actor_user_id=None,
                correlation_id="invalid",
                now=clock.now(),
            )
        assert invalid.value.code is ErrorCode.VALIDATION_ERROR

    assert await db_session.scalar(select(func.count()).select_from(Organization)) == 1
