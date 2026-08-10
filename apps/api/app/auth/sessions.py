"""Opaque PostgreSQL-backed application session creation and lifecycle."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import AuthError, ErrorCode
from app.auth.models import (
    AuthenticationSession,
    EntityStatus,
    Organization,
    RevocationReason,
    User,
)
from app.core.observability import metrics

ABSOLUTE_LIFETIME = timedelta(hours=8)
IDLE_LIFETIME = timedelta(hours=2)


def token_digest(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


@dataclass(frozen=True)
class CreatedSession:
    token: str
    csrf_token: str
    record: AuthenticationSession


async def create_session(session: AsyncSession, user: User, *, now: datetime) -> CreatedSession:
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    record = AuthenticationSession(
        org_id=user.org_id,
        user_id=user.id,
        token_digest=token_digest(token),
        csrf_token_digest=token_digest(csrf_token),
        auth_generation=user.auth_generation,
        created_at=now,
        updated_at=now,
        last_activity_at=now,
        absolute_expires_at=now + ABSOLUTE_LIFETIME,
        idle_expires_at=now + IDLE_LIFETIME,
        revoked_at=None,
        revocation_reason=None,
    )
    session.add(record)
    await session.flush()
    metrics.increment("auth_session_created_total")
    return CreatedSession(token=token, csrf_token=csrf_token, record=record)


async def resolve_session(
    session: AsyncSession, token: str, *, now: datetime
) -> tuple[AuthenticationSession, User]:
    record = await session.scalar(
        select(AuthenticationSession).where(
            AuthenticationSession.token_digest == token_digest(token)
        )
    )
    if record is None:
        raise AuthError(ErrorCode.AUTHENTICATION_REQUIRED)
    if record.revoked_at is not None:
        metrics.increment("auth_session_revoked_total", reason="already_revoked")
        raise AuthError(ErrorCode.SESSION_REVOKED)
    if now >= record.absolute_expires_at:
        record.revoked_at = now
        record.revocation_reason = RevocationReason.ABSOLUTE_EXPIRED.value
        record.updated_at = now
        await session.flush()
        metrics.increment("auth_session_expired_total", reason="absolute")
        raise AuthError(ErrorCode.SESSION_EXPIRED)
    if now >= record.idle_expires_at:
        record.revoked_at = now
        record.revocation_reason = RevocationReason.IDLE_EXPIRED.value
        record.updated_at = now
        await session.flush()
        metrics.increment("auth_session_expired_total", reason="idle")
        raise AuthError(ErrorCode.SESSION_EXPIRED)
    user = await session.get(User, record.user_id)
    organization = await session.get(Organization, record.org_id)
    if (
        user is None
        or organization is None
        or user.status != EntityStatus.ACTIVE.value
        or organization.status != EntityStatus.ACTIVE.value
        or user.org_id != record.org_id
        or user.auth_generation != record.auth_generation
    ):
        metrics.increment("auth_session_revoked_total", reason="security_context")
        raise AuthError(ErrorCode.SESSION_REVOKED)
    record.last_activity_at = now
    record.idle_expires_at = min(now + IDLE_LIFETIME, record.absolute_expires_at)
    record.updated_at = now
    return record, user


async def find_session(session: AsyncSession, token: str) -> AuthenticationSession | None:
    """Find a session by opaque token without changing its lifecycle state."""

    return cast(
        AuthenticationSession | None,
        await session.scalar(
            select(AuthenticationSession).where(
                AuthenticationSession.token_digest == token_digest(token)
            )
        ),
    )


async def revoke_all_sessions(
    session: AsyncSession,
    *,
    user_id: UUID,
    reason: RevocationReason,
    now: datetime,
) -> int:
    """Revoke every live session for a user; repeated calls are harmless."""

    result = await session.execute(
        update(AuthenticationSession)
        .where(
            AuthenticationSession.user_id == user_id,
            AuthenticationSession.revoked_at.is_(None),
        )
        .values(revoked_at=now, revocation_reason=reason.value, updated_at=now)
    )
    if result.rowcount:
        metrics.increment("auth_session_revoked_total", amount=result.rowcount, reason=reason.value)
    return result.rowcount
