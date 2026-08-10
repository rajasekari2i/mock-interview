from __future__ import annotations

import pytest
from app.admin.service import reassign_domain_mapping
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import Role
from app.interviews.tenancy import ScheduledInterviewTenantMigrationParticipant
from app.tenancy.coordinator import CandidateTenantMigrationCoordinator
from sqlalchemy.ext.asyncio import AsyncSession


def test_production_registry_contains_scheduled_interviews_once() -> None:
    coordinator = CandidateTenantMigrationCoordinator(
        (ScheduledInterviewTenantMigrationParticipant(),)
    )
    assert [participant.name for participant in coordinator.participants] == [
        "scheduled_interviews"
    ]


@pytest.mark.asyncio
async def test_candidate_domain_reassignment_with_interview_fails_before_any_tenant_change(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    source = factories.organization()
    target = factories.organization(slug="target")
    mapping = factories.domain_mapping(organization=source)
    candidate = factories.user(
        organization=source,
        role=Role.CANDIDATE.value,
        registration_domain_mapping_id=mapping.id,
    )
    manager = factories.user(organization=source, role=Role.MANAGER.value)
    db_session.add_all([source, target, mapping, candidate, manager])
    await db_session.flush()
    jd = factories.job_description(organization=source, creator=manager)
    db_session.add_all(
        [factories.candidate_profile(organization=source, user=candidate), jd]
    )
    await db_session.flush()
    interview = factories.scheduled_interview(
        organization=source, candidate=candidate, manager=manager, job_description=jd
    )
    db_session.add(interview)
    await db_session.flush()

    with pytest.raises(AuthError) as error:
        await reassign_domain_mapping(
            db_session,
            mapping_id=mapping.id,
            target_organization_id=target.id,
            coordinator=CandidateTenantMigrationCoordinator(
                (ScheduledInterviewTenantMigrationParticipant(),)
            ),
            actor_user_id=None,
            correlation_id="test",
            now=clock.now(),
        )
    assert error.value.code is ErrorCode.IDENTITY_CONFLICT
    assert mapping.org_id == source.id
    assert candidate.org_id == source.id
    assert interview.org_id == source.id
