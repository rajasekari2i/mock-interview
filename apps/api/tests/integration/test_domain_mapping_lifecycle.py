from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest
from app.admin.service import reassign_domain_mapping, remove_domain_mapping
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import AuthenticationSession, EntityStatus, RevocationReason
from app.tenancy.coordinator import CandidateTenantMigrationCoordinator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class _FailingParticipant:
    name = "failure"

    async def validate_and_lock(
        self,
        session: AsyncSession,
        candidate_user_ids: tuple[UUID, ...],
        source_org_id: UUID,
        target_org_id: UUID,
    ) -> None:
        del session, candidate_user_ids, source_org_id, target_org_id

    async def migrate(
        self,
        session: AsyncSession,
        candidate_user_ids: tuple[UUID, ...],
        source_org_id: UUID,
        target_org_id: UUID,
        now: datetime,
    ) -> int:
        del session, candidate_user_ids, source_org_id, target_org_id, now
        raise RuntimeError("injected participant failure")


@pytest.mark.asyncio
async def test_removal_disables_only_provenance_users_and_revokes_sessions(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    mapping = factories.domain_mapping(organization=organization)
    mapped = factories.user(
        organization=organization,
        role="CANDIDATE",
        registration_domain_mapping_id=mapping.id,
    )
    independent = factories.user(organization=organization, role="CANDIDATE")
    db_session.add_all([organization, mapping, mapped, independent])
    await db_session.flush()
    db_session.add_all(
        [
            factories.candidate_profile(organization=organization, user=mapped),
            factories.candidate_profile(organization=organization, user=independent),
            factories.session(organization=organization, user=mapped),
            factories.session(organization=organization, user=independent),
        ]
    )
    await db_session.flush()
    await remove_domain_mapping(
        db_session,
        mapping_id=mapping.id,
        actor_user_id=None,
        correlation_id="remove",
        now=clock.now(),
    )
    await db_session.flush()
    assert mapping.removed_at == clock.now()
    assert mapped.status == EntityStatus.DISABLED.value
    assert mapped.auth_generation == 2
    assert independent.status == EntityStatus.ACTIVE.value
    sessions = list((await db_session.scalars(select(AuthenticationSession))).all())
    mapped_session = next(item for item in sessions if item.user_id == mapped.id)
    independent_session = next(item for item in sessions if item.user_id == independent.id)
    assert mapped_session.revocation_reason == RevocationReason.DOMAIN_MAPPING_REMOVED.value
    assert independent_session.revoked_at is None


@pytest.mark.asyncio
async def test_reassignment_cascades_auth_rows_revokes_and_same_org_is_noop(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    source = factories.organization()
    target = factories.organization()
    mapping = factories.domain_mapping(organization=source)
    mapped = factories.user(
        organization=source,
        role="CANDIDATE",
        registration_domain_mapping_id=mapping.id,
    )
    db_session.add_all([source, target, mapping, mapped])
    await db_session.flush()
    profile = factories.candidate_profile(organization=source, user=mapped)
    session = factories.session(organization=source, user=mapped)
    db_session.add_all([profile, session])
    await db_session.flush()

    await reassign_domain_mapping(
        db_session,
        mapping_id=mapping.id,
        target_organization_id=target.id,
        coordinator=CandidateTenantMigrationCoordinator(),
        actor_user_id=None,
        correlation_id="reassign",
        now=clock.now(),
    )
    await db_session.flush()
    await db_session.refresh(profile)
    await db_session.refresh(session)
    await db_session.refresh(mapping)
    await db_session.refresh(mapped)
    assert mapping.org_id == target.id
    assert mapped.org_id == target.id
    assert profile.org_id == target.id
    assert session.org_id == target.id
    assert session.revocation_reason == RevocationReason.DOMAIN_MAPPING_REASSIGNED.value
    generation = mapped.auth_generation
    updated_at = mapping.updated_at
    await reassign_domain_mapping(
        db_session,
        mapping_id=mapping.id,
        target_organization_id=target.id,
        coordinator=CandidateTenantMigrationCoordinator(),
        actor_user_id=None,
        correlation_id="noop",
        now=clock.now(),
    )
    assert mapped.auth_generation == generation
    assert mapping.updated_at == updated_at


@pytest.mark.asyncio
async def test_reassignment_preflight_or_participant_failure_leaves_core_unchanged(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    source = factories.organization()
    target = factories.organization()
    mapping = factories.domain_mapping(organization=source)
    mapped = factories.user(
        organization=source,
        role="CANDIDATE",
        registration_domain_mapping_id=mapping.id,
    )
    db_session.add_all([source, target, mapping, mapped])
    await db_session.flush()
    with pytest.raises(RuntimeError, match="injected participant failure"):
        await reassign_domain_mapping(
            db_session,
            mapping_id=mapping.id,
            target_organization_id=target.id,
            coordinator=CandidateTenantMigrationCoordinator((_FailingParticipant(),)),
            actor_user_id=None,
            correlation_id="failed",
            now=clock.now(),
        )
    assert mapping.org_id == source.id
    assert mapped.org_id == source.id
    assert mapped.auth_generation == 1


@pytest.mark.asyncio
async def test_target_email_collision_rolls_back_reassignment_preflight(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    source = factories.organization()
    target = factories.organization()
    mapping = factories.domain_mapping(organization=source)
    mapped = factories.user(
        organization=source,
        role="CANDIDATE",
        normalized_email="collision@example.test",
        registration_domain_mapping_id=mapping.id,
    )
    collision = factories.user(
        organization=target,
        normalized_email="collision@example.test",
    )
    db_session.add_all([source, target, mapping, mapped, collision])
    await db_session.flush()
    with pytest.raises(AuthError) as denied:
        await reassign_domain_mapping(
            db_session,
            mapping_id=mapping.id,
            target_organization_id=target.id,
            coordinator=CandidateTenantMigrationCoordinator(),
            actor_user_id=None,
            correlation_id="collision",
            now=clock.now(),
        )
    assert denied.value.code is ErrorCode.IDENTITY_CONFLICT
    assert mapping.org_id == source.id
    assert mapped.org_id == source.id
