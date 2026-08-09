from __future__ import annotations

import pytest
from app.admin.service import ProvisionUserInput, normalize_email, provision_user
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import CandidateProfile, Organization, Role, User
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_admin_preprovisions_candidate_and_profile_atomically(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    db_session.add(organization)
    await db_session.flush()

    result = await provision_user(
        db_session,
        ProvisionUserInput(
            organization_id=organization.id,
            email="  Candidate@Example.COM ",
            display_name="Candidate Person",
            role=Role.CANDIDATE,
            active=True,
        ),
        now=clock.now(),
    )
    await db_session.flush()

    assert result.normalized_email == "candidate@example.com"
    assert result.role == Role.CANDIDATE.value
    assert await db_session.scalar(
        select(func.count())
        .select_from(CandidateProfile)
        .where(CandidateProfile.user_id == result.id)
    ) == 1


def test_email_normalization_rejects_invalid_addresses() -> None:
    assert normalize_email(" Admin@Example.COM ") == "admin@example.com"
    with pytest.raises(ValueError):
        normalize_email("not-an-email")


@pytest.mark.asyncio
async def test_org_email_uniqueness_denies_duplicate_without_partial_user(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization: Organization = factories.organization()
    db_session.add(organization)
    await db_session.flush()
    request = ProvisionUserInput(
        organization_id=organization.id,
        email="manager@example.com",
        display_name="Manager",
        role=Role.MANAGER,
        active=True,
    )
    await provision_user(db_session, request, now=clock.now())
    await db_session.flush()

    with pytest.raises(AuthError) as error:
        await provision_user(db_session, request, now=clock.now())

    assert error.value.code is ErrorCode.IDENTITY_CONFLICT
    assert await db_session.scalar(select(func.count()).select_from(User)) == 1


@pytest.mark.asyncio
async def test_provisioning_rejects_missing_org_and_blank_name(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    with pytest.raises(AuthError) as no_org:
        await provision_user(
            db_session,
            ProvisionUserInput(
                factories.uuid(), "person@example.com", "Person", Role.MANAGER, True
            ),
            now=clock.now(),
        )
    assert no_org.value.code is ErrorCode.RESOURCE_NOT_FOUND

    organization = factories.organization()
    db_session.add(organization)
    await db_session.flush()
    with pytest.raises(ValueError, match="Display name"):
        await provision_user(
            db_session,
            ProvisionUserInput(
                organization.id, "blank-name@example.com", "   ", Role.MANAGER, True
            ),
            now=clock.now(),
        )
