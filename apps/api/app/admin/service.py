"""Transactional Admin provisioning and user lifecycle operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.audit import append_audit_event
from app.auth.errors import AuthError, ErrorCode
from app.auth.identifiers import canonicalize_domain
from app.auth.models import (
    AuditOutcome,
    AuthenticationSession,
    CandidateProfile,
    EntityStatus,
    Organization,
    OrganizationDomainMapping,
    RevocationReason,
    Role,
    User,
)
from app.auth.service import acquire_domain_lock
from app.auth.sessions import revoke_all_sessions
from app.tenancy.coordinator import CandidateTenantMigrationCoordinator


@dataclass(frozen=True)
class ProvisionUserInput:
    organization_id: UUID
    email: str
    display_name: str
    role: Role
    active: bool


async def list_domain_mappings(
    session: AsyncSession, *, include_removed: bool = False
) -> list[OrganizationDomainMapping]:
    statement = select(OrganizationDomainMapping)
    if not include_removed:
        statement = statement.where(OrganizationDomainMapping.removed_at.is_(None))
    statement = statement.order_by(
        OrganizationDomainMapping.normalized_domain, OrganizationDomainMapping.id
    )
    return list((await session.scalars(statement)).all())


async def create_domain_mapping(
    session: AsyncSession,
    *,
    domain: str,
    organization_id: UUID,
    actor_user_id: UUID | None,
    correlation_id: str,
    now: datetime,
) -> OrganizationDomainMapping:
    try:
        normalized_domain = canonicalize_domain(domain)
    except ValueError as error:
        raise AuthError(ErrorCode.VALIDATION_ERROR) from error
    await acquire_domain_lock(session, normalized_domain)
    organization = await session.get(Organization, organization_id)
    if organization is None:
        raise AuthError(ErrorCode.RESOURCE_NOT_FOUND)
    if organization.status != EntityStatus.ACTIVE.value:
        raise AuthError(ErrorCode.IDENTITY_CONFLICT)
    existing = await session.scalar(
        select(OrganizationDomainMapping).where(
            OrganizationDomainMapping.normalized_domain == normalized_domain,
            OrganizationDomainMapping.removed_at.is_(None),
        )
    )
    if existing is not None:
        raise AuthError(ErrorCode.IDENTITY_CONFLICT)
    mapping = OrganizationDomainMapping(
        org_id=organization_id,
        normalized_domain=normalized_domain,
        removed_at=None,
        created_at=now,
        updated_at=now,
    )
    session.add(mapping)
    await session.flush()
    await append_audit_event(
        session,
        event_type="ORG_DOMAIN_MAPPING_CREATED",
        outcome=AuditOutcome.SUCCESS,
        reason_code="ADMIN_CREATED",
        correlation_id=correlation_id,
        occurred_at=now,
        org_id=organization_id,
        actor_user_id=actor_user_id,
        resource_type="ORGANIZATION_DOMAIN_MAPPING",
        resource_id=str(mapping.id),
    )
    return mapping


async def _lock_active_mapping(
    session: AsyncSession, mapping_id: UUID
) -> OrganizationDomainMapping:
    existing = await session.get(OrganizationDomainMapping, mapping_id)
    if existing is None:
        raise AuthError(ErrorCode.RESOURCE_NOT_FOUND)
    await acquire_domain_lock(session, existing.normalized_domain)
    mapping = await session.get(
        OrganizationDomainMapping,
        mapping_id,
        with_for_update=True,
        populate_existing=True,
    )
    if mapping is None or mapping.removed_at is not None:
        raise AuthError(ErrorCode.RESOURCE_NOT_FOUND)
    return mapping


async def _mapping_users(
    session: AsyncSession, mapping_id: UUID
) -> list[User]:
    return list(
        (
            await session.scalars(
                select(User)
                .where(User.registration_domain_mapping_id == mapping_id)
                .order_by(User.id)
                .with_for_update()
            )
        ).all()
    )


async def remove_domain_mapping(
    session: AsyncSession,
    *,
    mapping_id: UUID,
    actor_user_id: UUID | None,
    correlation_id: str,
    now: datetime,
) -> OrganizationDomainMapping:
    mapping = await _lock_active_mapping(session, mapping_id)
    users = await _mapping_users(session, mapping.id)
    revoked = 0
    for user in users:
        user.status = EntityStatus.DISABLED.value
        user.auth_generation += 1
        user.updated_at = now
        revoked += await revoke_all_sessions(
            session,
            user_id=user.id,
            reason=RevocationReason.DOMAIN_MAPPING_REMOVED,
            now=now,
        )
        await append_audit_event(
            session,
            event_type="USER_STATUS_CHANGED",
            outcome=AuditOutcome.SUCCESS,
            reason_code=RevocationReason.DOMAIN_MAPPING_REMOVED.value,
            correlation_id=correlation_id,
            occurred_at=now,
            org_id=user.org_id,
            actor_user_id=actor_user_id,
            target_user_id=user.id,
            metadata={"status": EntityStatus.DISABLED.value},
        )
    mapping.removed_at = now
    mapping.updated_at = now
    await append_audit_event(
        session,
        event_type="ORG_DOMAIN_MAPPING_REMOVED",
        outcome=AuditOutcome.SUCCESS,
        reason_code="ADMIN_REMOVED",
        correlation_id=correlation_id,
        occurred_at=now,
        org_id=mapping.org_id,
        actor_user_id=actor_user_id,
        resource_type="ORGANIZATION_DOMAIN_MAPPING",
        resource_id=str(mapping.id),
        metadata={"candidate_count": len(users), "session_count": revoked},
    )
    return mapping


async def reassign_domain_mapping(
    session: AsyncSession,
    *,
    mapping_id: UUID,
    target_organization_id: UUID,
    coordinator: CandidateTenantMigrationCoordinator,
    actor_user_id: UUID | None,
    correlation_id: str,
    now: datetime,
) -> OrganizationDomainMapping:
    mapping = await _lock_active_mapping(session, mapping_id)
    if mapping.org_id == target_organization_id:
        return mapping
    target = await session.get(Organization, target_organization_id, with_for_update=True)
    if target is None:
        raise AuthError(ErrorCode.RESOURCE_NOT_FOUND)
    if target.status != EntityStatus.ACTIVE.value:
        raise AuthError(ErrorCode.IDENTITY_CONFLICT)
    users = await _mapping_users(session, mapping.id)
    if users:
        collision = await session.scalar(
            select(User.id).where(
                User.org_id == target_organization_id,
                User.normalized_email.in_([user.normalized_email for user in users]),
            )
        )
        if collision is not None:
            raise AuthError(ErrorCode.IDENTITY_CONFLICT)
    source_organization_id = mapping.org_id
    await coordinator.migrate(
        session,
        candidate_user_ids=tuple(user.id for user in users),
        source_org_id=source_organization_id,
        target_org_id=target_organization_id,
        now=now,
    )
    mapping.org_id = target_organization_id
    mapping.updated_at = now
    for user in users:
        user.org_id = target_organization_id
        user.auth_generation += 1
        user.updated_at = now
    await session.flush()
    revoked = 0
    for user in users:
        revoked += await revoke_all_sessions(
            session,
            user_id=user.id,
            reason=RevocationReason.DOMAIN_MAPPING_REASSIGNED,
            now=now,
        )
        await append_audit_event(
            session,
            event_type="CANDIDATE_ORGANIZATION_CHANGED",
            outcome=AuditOutcome.SUCCESS,
            reason_code=RevocationReason.DOMAIN_MAPPING_REASSIGNED.value,
            correlation_id=correlation_id,
            occurred_at=now,
            org_id=target_organization_id,
            actor_user_id=actor_user_id,
            target_user_id=user.id,
            metadata={
                "source_org_id": str(source_organization_id),
                "target_org_id": str(target_organization_id),
            },
        )
    await append_audit_event(
        session,
        event_type="ORG_DOMAIN_MAPPING_REASSIGNED",
        outcome=AuditOutcome.SUCCESS,
        reason_code="ADMIN_REASSIGNED",
        correlation_id=correlation_id,
        occurred_at=now,
        org_id=target_organization_id,
        actor_user_id=actor_user_id,
        resource_type="ORGANIZATION_DOMAIN_MAPPING",
        resource_id=str(mapping.id),
        metadata={
            "candidate_count": len(users),
            "session_count": revoked,
            "source_org_id": str(source_organization_id),
            "target_org_id": str(target_organization_id),
        },
    )
    await session.refresh(mapping)
    return mapping


def normalize_email(value: str) -> str:
    try:
        validated = validate_email(value.strip(), check_deliverability=False)
    except EmailNotValidError as error:
        raise ValueError("Email address is invalid") from error
    return validated.normalized.casefold()


async def provision_user(
    session: AsyncSession,
    request: ProvisionUserInput,
    *,
    now: datetime,
    actor_user_id: UUID | None = None,
    correlation_id: str = "internal",
) -> User:
    organization = await session.get(Organization, request.organization_id)
    if organization is None:
        raise AuthError(ErrorCode.RESOURCE_NOT_FOUND)
    normalized_email = normalize_email(request.email)
    existing = await session.scalar(
        select(User).where(
            User.org_id == request.organization_id,
            User.normalized_email == normalized_email,
        )
    )
    if existing is not None:
        raise AuthError(ErrorCode.IDENTITY_CONFLICT)
    display_name = request.display_name.strip()
    if not display_name:
        raise ValueError("Display name is required")
    user = User(
        org_id=request.organization_id,
        email=normalized_email,
        normalized_email=normalized_email,
        display_name=display_name,
        role=request.role.value,
        status=EntityStatus.ACTIVE.value if request.active else EntityStatus.DISABLED.value,
        auth_generation=1,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()
    if request.role is Role.CANDIDATE:
        session.add(
            CandidateProfile(
                org_id=request.organization_id,
                user_id=user.id,
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()
        await append_audit_event(
            session,
            event_type="CANDIDATE_PROFILE_LINKED",
            outcome=AuditOutcome.SUCCESS,
            reason_code="PROFILE_CREATED",
            correlation_id=correlation_id,
            occurred_at=now,
            org_id=user.org_id,
            actor_user_id=actor_user_id,
            target_user_id=user.id,
        )
    await append_audit_event(
        session,
        event_type="USER_PROVISIONED",
        outcome=AuditOutcome.SUCCESS,
        reason_code="ADMIN_PROVISIONED",
        correlation_id=correlation_id,
        occurred_at=now,
        org_id=user.org_id,
        actor_user_id=actor_user_id,
        target_user_id=user.id,
        metadata={"role": user.role, "status": user.status},
    )
    return user


async def _revoke_all_sessions(
    session: AsyncSession,
    *,
    user: User,
    reason: RevocationReason,
    now: datetime,
) -> int:
    result = await session.execute(
        update(AuthenticationSession)
        .where(
            AuthenticationSession.user_id == user.id,
            AuthenticationSession.revoked_at.is_(None),
        )
        .values(revoked_at=now, revocation_reason=reason.value, updated_at=now)
    )
    return result.rowcount


async def change_user_role(
    session: AsyncSession,
    *,
    user_id: UUID,
    role: Role,
    actor_user_id: UUID,
    correlation_id: str,
    now: datetime,
) -> User:
    user = await session.get(User, user_id, with_for_update=True)
    if user is None:
        raise AuthError(ErrorCode.RESOURCE_NOT_FOUND)
    current_role = Role(user.role)
    if current_role is role:
        return user
    profile = await session.scalar(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    if current_role is Role.CANDIDATE and role is not Role.CANDIDATE and profile is not None:
        raise AuthError(ErrorCode.CANDIDATE_PROFILE_CONFLICT)
    if role is Role.CANDIDATE and profile is None:
        session.add(
            CandidateProfile(
                org_id=user.org_id,
                user_id=user.id,
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()
    previous = user.role
    user.role = role.value
    user.auth_generation += 1
    user.updated_at = now
    revoked = await _revoke_all_sessions(
        session, user=user, reason=RevocationReason.ROLE_CHANGED, now=now
    )
    await append_audit_event(
        session,
        event_type="USER_ROLE_CHANGED",
        outcome=AuditOutcome.SUCCESS,
        reason_code="ADMIN_ROLE_CHANGE",
        correlation_id=correlation_id,
        occurred_at=now,
        org_id=user.org_id,
        actor_user_id=actor_user_id,
        target_user_id=user.id,
        metadata={
            "role": role.value,
            "transition": f"{previous}->{role.value}",
            "session_count": revoked,
        },
    )
    return user


async def change_user_status(
    session: AsyncSession,
    *,
    user_id: UUID,
    status: EntityStatus,
    actor_user_id: UUID,
    correlation_id: str,
    now: datetime,
) -> User:
    user = await session.get(User, user_id, with_for_update=True)
    if user is None:
        raise AuthError(ErrorCode.RESOURCE_NOT_FOUND)
    if user.status == status.value:
        return user
    previous = user.status
    user.status = status.value
    user.updated_at = now
    revoked = 0
    if status is EntityStatus.DISABLED:
        user.auth_generation += 1
        revoked = await _revoke_all_sessions(
            session, user=user, reason=RevocationReason.ACCOUNT_DISABLED, now=now
        )
    await append_audit_event(
        session,
        event_type="USER_STATUS_CHANGED",
        outcome=AuditOutcome.SUCCESS,
        reason_code="ADMIN_STATUS_CHANGE",
        correlation_id=correlation_id,
        occurred_at=now,
        org_id=user.org_id,
        actor_user_id=actor_user_id,
        target_user_id=user.id,
        metadata={
            "status": status.value,
            "transition": f"{previous}->{status.value}",
            "session_count": revoked,
        },
    )
    return user
