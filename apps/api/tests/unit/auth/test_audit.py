from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest
from app.auth.audit import append_audit_event, append_authorization_denial
from app.auth.models import AuditOutcome
from sqlalchemy.ext.asyncio import AsyncSession


class _RecordingSession:
    def __init__(self) -> None:
        self.events: list[object] = []

    def add(self, event: object) -> None:
        self.events.append(event)

    async def flush(self) -> None:
        return None


@pytest.mark.asyncio
async def test_feature_audit_metadata_is_bounded_and_identity_free() -> None:
    session = _RecordingSession()
    event = await append_audit_event(
        cast(AsyncSession, session),
        event_type="JD_CREATED",
        outcome=AuditOutcome.SUCCESS,
        reason_code="CREATED",
        correlation_id="audit-feature",
        occurred_at=datetime(2026, 8, 10, tzinfo=UTC),
        org_id=UUID(int=1),
        actor_user_id=UUID(int=2),
        resource_type="job_description",
        resource_id="safe-resource-id",
        metadata={"source_type": "UPLOAD", "source_format": "PDF", "replayed": False},
    )
    assert session.events == [event]
    assert event.event_metadata == {
        "source_type": "UPLOAD",
        "source_format": "PDF",
        "replayed": False,
    }


@pytest.mark.asyncio
async def test_audit_rejects_unapproved_metadata_and_records_minimal_denial(
    db_session: AsyncSession, factories: object, clock: object
) -> None:
    with pytest.raises(ValueError, match="unapproved"):
        await append_audit_event(
            db_session,
            event_type="BAD",
            outcome=AuditOutcome.DENIED,
            reason_code="BAD_METADATA",
            correlation_id="audit-1",
            occurred_at=clock.now(),
            metadata={"email": "private@example.com"},
        )

    organization = factories.organization()
    actor = factories.user(organization=organization)
    db_session.add_all([organization, actor])
    await db_session.flush()
    event = await append_authorization_denial(
        db_session,
        reason_code="CAPABILITY_DENIED",
        correlation_id="audit-2",
        occurred_at=clock.now(),
        org_id=organization.id,
        actor_user_id=actor.id,
        capability="ADMIN_MANAGE_USERS",
        resource_type="user",
    )
    assert event.event_metadata == {"capability": "ADMIN_MANAGE_USERS"}
    assert event.resource_id is None
    mapping_denial = await append_authorization_denial(
        db_session,
        reason_code="CAPABILITY_DENIED",
        correlation_id="audit-3",
        occurred_at=clock.now(),
        org_id=organization.id,
        actor_user_id=actor.id,
        capability="ADMIN_MANAGE_DOMAIN_MAPPINGS",
        resource_type="organization_domain_mapping",
    )
    assert mapping_denial.event_metadata == {"capability": "ADMIN_MANAGE_DOMAIN_MAPPINGS"}
    feature_event = await append_audit_event(
        db_session,
        event_type="JD_CREATED",
        outcome=AuditOutcome.SUCCESS,
        reason_code="CREATED",
        correlation_id="audit-4",
        occurred_at=clock.now(),
        org_id=organization.id,
        actor_user_id=actor.id,
        resource_type="job_description",
        resource_id="safe-resource-id",
        metadata={"source_type": "UPLOAD", "source_format": "PDF", "replayed": False},
    )
    assert feature_event.event_metadata == {
        "source_type": "UPLOAD",
        "source_format": "PDF",
        "replayed": False,
    }
