from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import app.auth.service as identity_service
import pytest
from app.auth.errors import AuthError, ErrorCode
from app.auth.google_oidc import GoogleClaims
from app.auth.models import (
    CandidateProfile,
    EntityStatus,
    ExternalLoginIdentity,
    Role,
    User,
)
from app.auth.service import _validate_login_user, resolve_or_bind_identity
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_first_login_binds_verified_email_then_subject_only_survives_email_drift(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    user = factories.user(
        organization=organization,
        email="person@example.test",
        normalized_email="person@example.test",
        role=Role.MANAGER.value,
    )
    db_session.add_all([organization, user])
    await db_session.flush()

    first = await resolve_or_bind_identity(
        db_session,
        GoogleClaims("https://accounts.google.com", "subject-1", "person@example.test"),
        now=clock.now(),
    )
    later = await resolve_or_bind_identity(
        db_session,
        GoogleClaims("https://accounts.google.com", "subject-1", "changed@example.test"),
        now=clock.now(),
    )

    assert first.id == later.id == user.id
    identity = await db_session.scalar(select(ExternalLoginIdentity))
    assert identity is not None and identity.subject == "subject-1"


@pytest.mark.asyncio
async def test_mapped_unknown_user_is_created_as_candidate_with_provenance(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    mapping = factories.domain_mapping(organization=organization)
    db_session.add_all([organization, mapping])
    await db_session.flush()

    user = await resolve_or_bind_identity(
        db_session,
        GoogleClaims(
            "https://accounts.google.com",
            "new-subject",
            "new@example.test",
            "  New   Candidate ",
            "https://images.example.test/new.png",
        ),
        now=clock.now(),
    )

    profile = await db_session.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    identity = await db_session.scalar(
        select(ExternalLoginIdentity).where(ExternalLoginIdentity.user_id == user.id)
    )
    assert user.role == Role.CANDIDATE.value
    assert user.display_name == "New Candidate"
    assert user.profile_picture_url == "https://images.example.test/new.png"
    assert user.registration_domain_mapping_id == mapping.id
    assert profile is not None and profile.org_id == organization.id
    assert identity is not None and identity.org_id == organization.id


@pytest.mark.asyncio
async def test_successful_login_refreshes_verified_identity_fields(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    user = factories.user(
        organization=organization,
        email="person@example.test",
        normalized_email="person@example.test",
        display_name="Old Name",
        profile_picture_url="https://images.example.test/old.png",
    )
    identity = ExternalLoginIdentity(
        org_id=organization.id,
        user_id=user.id,
        provider="GOOGLE",
        issuer="https://accounts.google.com",
        subject="refresh-subject",
        email_snapshot=user.email,
        bound_at=clock.now(),
        last_authenticated_at=clock.now(),
    )
    db_session.add_all([organization, user])
    await db_session.flush()
    db_session.add(identity)
    await db_session.flush()

    resolved = await resolve_or_bind_identity(
        db_session,
        GoogleClaims(
            "https://accounts.google.com",
            "refresh-subject",
            "person@example.test",
            "  Refreshed   Person ",
            "https://images.example.test/refreshed.png",
        ),
        now=clock.now(),
    )

    assert resolved.display_name == "Refreshed Person"
    assert resolved.profile_picture_url == "https://images.example.test/refreshed.png"


@pytest.mark.asyncio
async def test_absent_identity_claims_use_safe_name_and_picture_fallback(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    user = factories.user(
        organization=organization,
        email="fallback@example.test",
        normalized_email="fallback@example.test",
        display_name="Old Name",
        profile_picture_url="https://images.example.test/old.png",
    )
    db_session.add_all([organization, user])
    await db_session.flush()

    resolved = await resolve_or_bind_identity(
        db_session,
        GoogleClaims(
            "https://accounts.google.com",
            "fallback-subject",
            "fallback@example.test",
        ),
        now=clock.now(),
    )

    assert resolved.display_name == "fallback"
    assert resolved.profile_picture_url is None


@pytest.mark.asyncio
async def test_preprovisioned_binding_wins_over_mapping_in_another_organization(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    mapped_org = factories.organization()
    provisioned_org = factories.organization()
    mapping = factories.domain_mapping(organization=mapped_org)
    provisioned = factories.user(
        organization=provisioned_org,
        email="person@example.test",
        normalized_email="person@example.test",
    )
    db_session.add_all([mapped_org, provisioned_org, mapping, provisioned])
    await db_session.flush()

    resolved = await resolve_or_bind_identity(
        db_session,
        GoogleClaims("https://accounts.google.com", "subject", "person@example.test"),
        now=clock.now(),
    )
    assert resolved.id == provisioned.id
    assert resolved.registration_domain_mapping_id is None
    assert await db_session.scalar(select(User).where(User.id != provisioned.id)) is None


@pytest.mark.asyncio
async def test_removed_mapping_does_not_authorize_registration(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    mapping = factories.domain_mapping(organization=organization, removed_at=clock.now())
    db_session.add_all([organization, mapping])
    await db_session.flush()
    with pytest.raises(AuthError) as denied:
        await resolve_or_bind_identity(
            db_session,
            GoogleClaims("https://accounts.google.com", "subject", "person@example.test"),
            now=clock.now(),
        )
    assert denied.value.code is ErrorCode.ACCESS_NOT_PROVISIONED


@pytest.mark.asyncio
async def test_unknown_disabled_and_subject_collision_are_denied(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    disabled = factories.user(
        organization=organization,
        email="disabled@example.test",
        normalized_email="disabled@example.test",
        status="DISABLED",
    )
    db_session.add_all([organization, disabled])
    await db_session.flush()

    with pytest.raises(AuthError) as unknown:
        await resolve_or_bind_identity(
            db_session,
            GoogleClaims("https://accounts.google.com", "unknown", "unknown@example.test"),
            now=clock.now(),
        )
    with pytest.raises(AuthError) as inactive:
        await resolve_or_bind_identity(
            db_session,
            GoogleClaims("https://accounts.google.com", "disabled", "disabled@example.test"),
            now=clock.now(),
        )

    assert unknown.value.code is ErrorCode.ACCESS_NOT_PROVISIONED
    assert inactive.value.code is ErrorCode.ACCOUNT_DISABLED


@pytest.mark.asyncio
async def test_ambiguous_email_existing_binding_and_candidate_profile_conflict_are_denied(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    first_org = factories.organization()
    second_org = factories.organization()
    first = factories.user(
        organization=first_org,
        email="shared@example.test",
        normalized_email="shared@example.test",
    )
    second = factories.user(
        organization=second_org,
        email="shared@example.test",
        normalized_email="shared@example.test",
    )
    db_session.add_all([first_org, second_org, first, second])
    await db_session.flush()
    with pytest.raises(AuthError) as ambiguous:
        await resolve_or_bind_identity(
            db_session,
            GoogleClaims("https://accounts.google.com", "new-subject", "shared@example.test"),
            now=clock.now(),
        )
    assert ambiguous.value.code is ErrorCode.IDENTITY_CONFLICT

    bound = ExternalLoginIdentity(
        org_id=first.org_id,
        user_id=first.id,
        provider="GOOGLE",
        issuer="https://accounts.google.com",
        subject="existing-subject",
        email_snapshot=first.email,
        bound_at=clock.now(),
        last_authenticated_at=clock.now(),
    )
    db_session.add(bound)
    await db_session.flush()
    with pytest.raises(AuthError) as already_bound:
        await resolve_or_bind_identity(
            db_session,
            GoogleClaims("https://accounts.google.com", "different-subject", first.email),
            now=clock.now(),
        )
    assert already_bound.value.code is ErrorCode.IDENTITY_CONFLICT

    candidate = factories.user(
        organization=first_org,
        email="candidate-conflict@example.test",
        normalized_email="candidate-conflict@example.test",
        role=Role.CANDIDATE.value,
    )
    db_session.add(candidate)
    await db_session.flush()
    with pytest.raises(AuthError) as profile_conflict:
        await resolve_or_bind_identity(
            db_session,
            GoogleClaims("https://accounts.google.com", "candidate-subject", candidate.email),
            now=clock.now(),
        )
    assert profile_conflict.value.code is ErrorCode.CANDIDATE_PROFILE_CONFLICT

    first_org.status = EntityStatus.DISABLED.value
    with pytest.raises(AuthError) as org_disabled:
        await resolve_or_bind_identity(
            db_session,
            GoogleClaims("https://accounts.google.com", "existing-subject", "changed@example.test"),
            now=clock.now(),
        )
    assert org_disabled.value.code is ErrorCode.ACCOUNT_DISABLED


@pytest.mark.asyncio
async def test_unique_email_with_existing_other_subject_binding_is_denied(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    user = factories.user(
        organization=organization,
        email="unique-bound@example.test",
        normalized_email="unique-bound@example.test",
    )
    db_session.add_all([organization, user])
    await db_session.flush()
    db_session.add(
        ExternalLoginIdentity(
            org_id=user.org_id,
            user_id=user.id,
            provider="GOOGLE",
            issuer="https://accounts.google.com",
            subject="old-subject",
            email_snapshot=user.email,
            bound_at=clock.now(),
            last_authenticated_at=clock.now(),
        )
    )
    await db_session.flush()
    with pytest.raises(AuthError) as conflict:
        await resolve_or_bind_identity(
            db_session,
            GoogleClaims("https://accounts.google.com", "new-subject", user.email),
            now=clock.now(),
        )
    assert conflict.value.code is ErrorCode.IDENTITY_CONFLICT


@pytest.mark.asyncio
async def test_orphan_identity_and_cross_org_candidate_profile_fail_closed() -> None:
    orphan_session = AsyncMock()
    orphan_session.scalar.return_value = SimpleNamespace(user_id=UUID(int=1))
    orphan_session.get.return_value = None
    with pytest.raises(AuthError) as orphan:
        await resolve_or_bind_identity(
            orphan_session,
            GoogleClaims("https://accounts.google.com", "subject", "person@example.test"),
            now=datetime(2026, 8, 9, 9, 0, tzinfo=UTC),
        )
    assert orphan.value.code is ErrorCode.IDENTITY_CONFLICT

    profile_session = AsyncMock()
    user = SimpleNamespace(
        id=UUID(int=2),
        org_id=UUID(int=3),
        status=EntityStatus.ACTIVE.value,
        role=Role.CANDIDATE.value,
    )
    profile_session.get.return_value = SimpleNamespace(status=EntityStatus.ACTIVE.value)
    profile_session.scalar.return_value = SimpleNamespace(org_id=UUID(int=4))
    with pytest.raises(AuthError) as mismatch:
        await _validate_login_user(profile_session, user)
    assert mismatch.value.code is ErrorCode.CANDIDATE_PROFILE_CONFLICT


@pytest.mark.asyncio
async def test_invalid_email_and_missing_registration_mapping_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock()
    with pytest.raises(AuthError) as invalid:
        await resolve_or_bind_identity(
            session,
            GoogleClaims("https://accounts.google.com", "subject", "not-an-email"),
            now=datetime(2026, 8, 9, 9, 0, tzinfo=UTC),
        )
    assert invalid.value.code is ErrorCode.OAUTH_RESPONSE_INVALID

    mapping_id = UUID(int=9)
    user = SimpleNamespace(
        id=UUID(int=2),
        org_id=UUID(int=3),
        status=EntityStatus.ACTIVE.value,
        role=Role.MANAGER.value,
        registration_domain_mapping_id=mapping_id,
    )
    monkeypatch.setattr(
        identity_service,
        "_find_identity",
        AsyncMock(return_value=SimpleNamespace(user_id=user.id)),
    )
    session.get.side_effect = [user, None]
    with pytest.raises(AuthError) as missing_mapping:
        await resolve_or_bind_identity(
            session,
            GoogleClaims("https://accounts.google.com", "subject", "person@example.test"),
            now=datetime(2026, 8, 9, 9, 0, tzinfo=UTC),
        )
    assert missing_mapping.value.code is ErrorCode.IDENTITY_CONFLICT


@pytest.mark.asyncio
async def test_existing_self_registered_identity_coordinates_mapping_and_validates_profile(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization()
    mapping = factories.domain_mapping(organization=organization)
    user = factories.user(
        organization=organization,
        role=Role.CANDIDATE.value,
        registration_domain_mapping_id=mapping.id,
    )
    identity = ExternalLoginIdentity(
        org_id=organization.id,
        user_id=user.id,
        provider="GOOGLE",
        issuer="https://accounts.google.com",
        subject="repeat-subject",
        email_snapshot=user.email,
        bound_at=clock.now(),
        last_authenticated_at=clock.now(),
    )
    db_session.add_all([organization, mapping, user])
    await db_session.flush()
    db_session.add_all(
        [factories.candidate_profile(organization=organization, user=user), identity]
    )
    await db_session.flush()

    resolved = await resolve_or_bind_identity(
        db_session,
        GoogleClaims(
            "https://accounts.google.com",
            "repeat-subject",
            "changed@example.test",
        ),
        now=clock.now(),
    )
    assert resolved.id == user.id
    assert identity.email_snapshot == "changed@example.test"


@pytest.mark.asyncio
async def test_concurrent_identity_recheck_handles_success_and_orphan(
    db_session: AsyncSession,
    factories: object,
    clock: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organization = factories.organization()
    user = factories.user(organization=organization)
    db_session.add_all([organization, user])
    await db_session.flush()
    identity = SimpleNamespace(user_id=user.id)
    monkeypatch.setattr(identity_service, "_find_identity", AsyncMock(side_effect=[None, identity]))
    monkeypatch.setattr(identity_service, "_find_preprovisioned_users", AsyncMock(return_value=[]))
    resolved = await resolve_or_bind_identity(
        db_session,
        GoogleClaims("https://accounts.google.com", "subject", "new@example.test"),
        now=clock.now(),
    )
    assert resolved.id == user.id

    monkeypatch.setattr(identity_service, "_find_identity", AsyncMock(side_effect=[None, identity]))
    await db_session.delete(user)
    await db_session.flush()
    with pytest.raises(AuthError) as orphan:
        await resolve_or_bind_identity(
            db_session,
            GoogleClaims("https://accounts.google.com", "subject", "new@example.test"),
            now=clock.now(),
        )
    assert orphan.value.code is ErrorCode.IDENTITY_CONFLICT


@pytest.mark.asyncio
async def test_concurrent_preprovision_recheck_binds_one_and_rejects_many(
    db_session: AsyncSession,
    factories: object,
    clock: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_org = factories.organization()
    second_org = factories.organization()
    first = factories.user(
        organization=first_org,
        email="race@example.test",
        normalized_email="race@example.test",
    )
    second = factories.user(
        organization=second_org,
        email="race@example.test",
        normalized_email="race@example.test",
    )
    db_session.add_all([first_org, second_org, first, second])
    await db_session.flush()
    monkeypatch.setattr(identity_service, "_find_identity", AsyncMock(return_value=None))
    monkeypatch.setattr(
        identity_service,
        "_find_preprovisioned_users",
        AsyncMock(side_effect=[[], [first]]),
    )
    resolved = await resolve_or_bind_identity(
        db_session,
        GoogleClaims("https://accounts.google.com", "race-one", "race@example.test"),
        now=clock.now(),
    )
    assert resolved.id == first.id

    monkeypatch.setattr(
        identity_service,
        "_find_preprovisioned_users",
        AsyncMock(side_effect=[[], [first, second]]),
    )
    with pytest.raises(AuthError) as ambiguous:
        await resolve_or_bind_identity(
            db_session,
            GoogleClaims("https://accounts.google.com", "race-many", "race@example.test"),
            now=clock.now(),
        )
    assert ambiguous.value.code is ErrorCode.IDENTITY_CONFLICT


@pytest.mark.asyncio
async def test_mapped_registration_rejects_disabled_organization(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    organization = factories.organization(status=EntityStatus.DISABLED.value)
    mapping = factories.domain_mapping(organization=organization)
    db_session.add_all([organization, mapping])
    await db_session.flush()
    with pytest.raises(AuthError) as denied:
        await resolve_or_bind_identity(
            db_session,
            GoogleClaims("https://accounts.google.com", "subject", "person@example.test"),
            now=clock.now(),
        )
    assert denied.value.code is ErrorCode.ACCESS_NOT_PROVISIONED
