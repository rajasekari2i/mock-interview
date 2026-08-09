"""Atomic external identity resolution and first-login binding."""

from __future__ import annotations

from datetime import datetime
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.audit import append_audit_event
from app.auth.errors import AuthError, ErrorCode
from app.auth.google_oidc import GoogleClaims
from app.auth.identifiers import display_name_from_claim, normalize_verified_email
from app.auth.models import (
    AuditOutcome,
    CandidateProfile,
    EntityStatus,
    ExternalLoginIdentity,
    Organization,
    OrganizationDomainMapping,
    Role,
    User,
)

_DOMAIN_LOCK_NAMESPACE = 2_026_080_9


async def acquire_domain_lock(session: AsyncSession, normalized_domain: str) -> None:
    """Serialize missing-row lookup, registration, and mapping mutation per exact domain."""

    await session.execute(
        select(
            func.pg_advisory_xact_lock(
                func.hashtextextended(normalized_domain, _DOMAIN_LOCK_NAMESPACE)
            )
        )
    )


async def _find_identity(
    session: AsyncSession, claims: GoogleClaims
) -> ExternalLoginIdentity | None:
    return cast(
        ExternalLoginIdentity | None,
        await session.scalar(
            select(ExternalLoginIdentity).where(
                ExternalLoginIdentity.provider == "GOOGLE",
                ExternalLoginIdentity.issuer == claims.issuer,
                ExternalLoginIdentity.subject == claims.subject,
            )
        )
    )


async def _find_preprovisioned_users(
    session: AsyncSession, normalized_email: str
) -> list[User]:
    return list(
        (
            await session.scalars(
                select(User).where(User.normalized_email == normalized_email.casefold())
            )
        ).all()
    )


async def _bind_preprovisioned_user(
    session: AsyncSession,
    user: User,
    claims: GoogleClaims,
    *,
    now: datetime,
    correlation_id: str,
) -> User:
    user = await _validate_login_user(session, user)
    already_bound = await session.scalar(
        select(ExternalLoginIdentity).where(
            ExternalLoginIdentity.user_id == user.id,
            ExternalLoginIdentity.provider == "GOOGLE",
        )
    )
    if already_bound is not None:
        raise AuthError(ErrorCode.IDENTITY_CONFLICT)
    session.add(
        ExternalLoginIdentity(
            org_id=user.org_id,
            user_id=user.id,
            provider="GOOGLE",
            issuer=claims.issuer,
            subject=claims.subject,
            email_snapshot=claims.email,
            bound_at=now,
            last_authenticated_at=now,
        )
    )
    await session.flush()
    await append_audit_event(
        session,
        event_type="IDENTITY_BOUND",
        outcome=AuditOutcome.SUCCESS,
        reason_code="FIRST_VERIFIED_EMAIL_BINDING",
        correlation_id=correlation_id,
        occurred_at=now,
        org_id=user.org_id,
        actor_user_id=user.id,
        target_user_id=user.id,
        metadata={"provider": "GOOGLE"},
    )
    return user


async def _validate_login_user(session: AsyncSession, user: User) -> User:
    organization = await session.get(Organization, user.org_id)
    if (
        user.status != EntityStatus.ACTIVE.value
        or organization is None
        or organization.status != EntityStatus.ACTIVE.value
    ):
        raise AuthError(ErrorCode.ACCOUNT_DISABLED)
    if user.role == Role.CANDIDATE.value:
        profile = await session.scalar(
            select(CandidateProfile).where(CandidateProfile.user_id == user.id)
        )
        if profile is None or profile.org_id != user.org_id:
            raise AuthError(ErrorCode.CANDIDATE_PROFILE_CONFLICT)
    return user


async def resolve_or_bind_identity(
    session: AsyncSession,
    claims: GoogleClaims,
    *,
    now: datetime,
    correlation_id: str = "internal",
) -> User:
    try:
        normalized_email, domain, local_part = normalize_verified_email(claims.email)
    except ValueError as error:
        raise AuthError(ErrorCode.OAUTH_RESPONSE_INVALID) from error
    identity = await _find_identity(session, claims)
    if identity is not None:
        user = await session.get(User, identity.user_id)
        if user is None:
            raise AuthError(ErrorCode.IDENTITY_CONFLICT)
        if user.registration_domain_mapping_id is not None:
            mapping = await session.get(
                OrganizationDomainMapping, user.registration_domain_mapping_id
            )
            if mapping is None:
                raise AuthError(ErrorCode.IDENTITY_CONFLICT)
            await acquire_domain_lock(session, mapping.normalized_domain)
            await session.get(
                OrganizationDomainMapping,
                mapping.id,
                with_for_update=True,
                populate_existing=True,
            )
        identity.email_snapshot = normalized_email
        identity.last_authenticated_at = now
        return await _validate_login_user(session, user)

    candidates = await _find_preprovisioned_users(session, normalized_email)
    if len(candidates) != 1:
        if candidates:
            raise AuthError(ErrorCode.IDENTITY_CONFLICT)
    else:
        return await _bind_preprovisioned_user(
            session,
            candidates[0],
            claims,
            now=now,
            correlation_id=correlation_id,
        )

    await acquire_domain_lock(session, domain)
    concurrent_identity = await _find_identity(session, claims)
    if concurrent_identity is not None:
        concurrent_user = await session.get(User, concurrent_identity.user_id)
        if concurrent_user is None:
            raise AuthError(ErrorCode.IDENTITY_CONFLICT)
        return await _validate_login_user(session, concurrent_user)
    concurrent_candidates = await _find_preprovisioned_users(session, normalized_email)
    if len(concurrent_candidates) == 1:
        return await _bind_preprovisioned_user(
            session,
            concurrent_candidates[0],
            claims,
            now=now,
            correlation_id=correlation_id,
        )
    if concurrent_candidates:
        raise AuthError(ErrorCode.IDENTITY_CONFLICT)
    mapping = await session.scalar(
        select(OrganizationDomainMapping)
        .where(
            OrganizationDomainMapping.normalized_domain == domain,
            OrganizationDomainMapping.removed_at.is_(None),
        )
        .with_for_update()
    )
    if mapping is None:
        raise AuthError(ErrorCode.ACCESS_NOT_PROVISIONED)
    organization = await session.get(Organization, mapping.org_id)
    if organization is None or organization.status != EntityStatus.ACTIVE.value:
        raise AuthError(ErrorCode.ACCESS_NOT_PROVISIONED)
    user = User(
        org_id=mapping.org_id,
        email=normalized_email,
        normalized_email=normalized_email.casefold(),
        display_name=display_name_from_claim(claims.name, fallback=local_part),
        role=Role.CANDIDATE.value,
        status=EntityStatus.ACTIVE.value,
        auth_generation=1,
        registration_domain_mapping_id=mapping.id,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()
    session.add_all(
        [
            CandidateProfile(
                org_id=user.org_id,
                user_id=user.id,
                created_at=now,
                updated_at=now,
            ),
            ExternalLoginIdentity(
                org_id=user.org_id,
                user_id=user.id,
                provider="GOOGLE",
                issuer=claims.issuer,
                subject=claims.subject,
                email_snapshot=normalized_email,
                bound_at=now,
                last_authenticated_at=now,
            ),
        ]
    )
    await session.flush()
    await append_audit_event(
        session,
        event_type="CANDIDATE_SELF_REGISTERED",
        outcome=AuditOutcome.SUCCESS,
        reason_code="APPROVED_DOMAIN_MAPPING",
        correlation_id=correlation_id,
        occurred_at=now,
        org_id=user.org_id,
        actor_user_id=user.id,
        target_user_id=user.id,
        metadata={"provider": "GOOGLE"},
    )
    return user
