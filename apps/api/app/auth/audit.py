"""Append-only, allowlisted, secret-safe authentication audit events."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import AuditEvent, AuditOutcome

_ALLOWED_METADATA_KEYS = frozenset(
    {
        "candidate_count",
        "capability",
        "provider",
        "role",
        "session_count",
        "source_org_id",
        "status",
        "target_org_id",
        "transition",
        "source_type",
        "source_format",
        "replayed",
    }
)


async def append_audit_event(
    session: AsyncSession,
    *,
    event_type: str,
    outcome: AuditOutcome,
    reason_code: str,
    correlation_id: str,
    occurred_at: datetime,
    org_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    target_user_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: Mapping[str, object] | None = None,
) -> AuditEvent:
    safe_metadata = dict(metadata or {})
    if not set(safe_metadata) <= _ALLOWED_METADATA_KEYS:
        raise ValueError("Audit metadata contains an unapproved key")
    event = AuditEvent(
        org_id=org_id,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        event_type=event_type,
        outcome=outcome.value,
        reason_code=reason_code,
        resource_type=resource_type,
        resource_id=resource_id,
        correlation_id=correlation_id,
        event_metadata=safe_metadata,
        occurred_at=occurred_at,
    )
    session.add(event)
    await session.flush()
    return event


async def append_authorization_denial(
    session: AsyncSession,
    *,
    reason_code: str,
    correlation_id: str,
    occurred_at: datetime,
    org_id: UUID | None,
    actor_user_id: UUID | None,
    capability: str,
    resource_type: str | None = None,
) -> AuditEvent:
    """Record a denial without resource IDs or identity-bearing metadata."""

    return await append_audit_event(
        session,
        event_type="AUTHORIZATION_DENIED",
        outcome=AuditOutcome.DENIED,
        reason_code=reason_code,
        correlation_id=correlation_id,
        occurred_at=occurred_at,
        org_id=org_id,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        metadata={"capability": capability},
    )
