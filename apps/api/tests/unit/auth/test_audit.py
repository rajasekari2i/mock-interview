from __future__ import annotations

import pytest
from app.auth.audit import append_audit_event, append_authorization_denial
from app.auth.models import AuditOutcome
from sqlalchemy.ext.asyncio import AsyncSession


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
    assert mapping_denial.event_metadata == {
        "capability": "ADMIN_MANAGE_DOMAIN_MAPPINGS"
    }
