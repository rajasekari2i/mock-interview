from __future__ import annotations

import pytest
from app.admin.service import change_user_role, change_user_status
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import AuditEvent, AuthenticationSession, EntityStatus, Role
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_role_change_revokes_every_session_and_audits_same_transaction(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    user = factories.user(organization=organization)
    db_session.add_all([organization, user])
    await db_session.flush()
    db_session.add_all(
        [
            factories.session(organization=organization, user=user),
            factories.session(organization=organization, user=user),
        ]
    )
    await db_session.flush()

    await change_user_role(
        db_session,
        user_id=user.id,
        role=Role.ADMIN,
        actor_user_id=user.id,
        correlation_id="request-1",
        now=clock.now(),
    )

    assert user.role == Role.ADMIN.value and user.auth_generation == 2
    assert await db_session.scalar(
        select(func.count())
        .select_from(AuthenticationSession)
        .where(AuthenticationSession.revoked_at.is_not(None))
    ) == 2
    assert await db_session.scalar(select(func.count()).select_from(AuditEvent)) == 1


@pytest.mark.asyncio
async def test_candidate_transition_conflict_rolls_back_without_revocation(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    user = factories.user(organization=organization, role=Role.CANDIDATE.value)
    db_session.add_all([organization, user])
    await db_session.flush()
    db_session.add(factories.candidate_profile(organization=organization, user=user))
    await db_session.flush()

    with pytest.raises(AuthError) as error:
        await change_user_role(
            db_session,
            user_id=user.id,
            role=Role.MANAGER,
            actor_user_id=user.id,
            correlation_id="request-2",
            now=clock.now(),
        )
    assert error.value.code is ErrorCode.CANDIDATE_PROFILE_CONFLICT
    assert user.role == Role.CANDIDATE.value and user.auth_generation == 1


@pytest.mark.asyncio
async def test_disablement_revokes_all_and_reenable_restores_no_session(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    user = factories.user(organization=organization)
    db_session.add_all([organization, user])
    await db_session.flush()
    session = factories.session(organization=organization, user=user)
    db_session.add(session)
    await db_session.flush()

    await change_user_status(
        db_session,
        user_id=user.id,
        status=EntityStatus.DISABLED,
        actor_user_id=user.id,
        correlation_id="request-3",
        now=clock.now(),
    )
    await change_user_status(
        db_session,
        user_id=user.id,
        status=EntityStatus.ACTIVE,
        actor_user_id=user.id,
        correlation_id="request-4",
        now=clock.now(),
    )
    assert user.status == EntityStatus.ACTIVE.value
    assert session.revoked_at is not None


@pytest.mark.asyncio
async def test_mutation_not_found_idempotence_and_transition_to_candidate(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    admin = factories.user(organization=organization, role=Role.ADMIN.value)
    manager = factories.user(organization=organization)
    db_session.add_all([organization, admin, manager])
    await db_session.flush()

    with pytest.raises(AuthError) as no_role_user:
        await change_user_role(
            db_session,
            user_id=factories.uuid(),
            role=Role.ADMIN,
            actor_user_id=admin.id,
            correlation_id="missing-role",
            now=clock.now(),
        )
    assert no_role_user.value.code is ErrorCode.RESOURCE_NOT_FOUND
    with pytest.raises(AuthError) as no_status_user:
        await change_user_status(
            db_session,
            user_id=factories.uuid(),
            status=EntityStatus.DISABLED,
            actor_user_id=admin.id,
            correlation_id="missing-status",
            now=clock.now(),
        )
    assert no_status_user.value.code is ErrorCode.RESOURCE_NOT_FOUND

    assert await change_user_role(
        db_session,
        user_id=manager.id,
        role=Role.MANAGER,
        actor_user_id=admin.id,
        correlation_id="same-role",
        now=clock.now(),
    ) is manager
    assert await change_user_status(
        db_session,
        user_id=manager.id,
        status=EntityStatus.ACTIVE,
        actor_user_id=admin.id,
        correlation_id="same-status",
        now=clock.now(),
    ) is manager
    await change_user_role(
        db_session,
        user_id=manager.id,
        role=Role.CANDIDATE,
        actor_user_id=admin.id,
        correlation_id="to-candidate",
        now=clock.now(),
    )
    assert manager.role == Role.CANDIDATE.value
