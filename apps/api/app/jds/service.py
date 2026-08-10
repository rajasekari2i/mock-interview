"""Atomic JD persistence for authorized creators."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.audit import append_audit_event
from app.auth.models import AuditOutcome
from app.core.observability import metrics
from app.jds.models import JobDescription, JobDescriptionSourceType


async def create_job_description(
    session: AsyncSession,
    *,
    org_id: UUID,
    manager_user_id: UUID,
    title: str,
    content_text: str,
    source_format: str | None,
    now: datetime,
    correlation_id: str,
) -> JobDescription:
    source_type = (
        JobDescriptionSourceType.MANUAL.value
        if source_format is None
        else JobDescriptionSourceType.UPLOAD.value
    )
    record = JobDescription(
        org_id=org_id,
        created_by_user_id=manager_user_id,
        title=title.strip(),
        source_type=source_type,
        content_text=content_text.strip(),
        source_format=source_format,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    await session.flush()
    await append_audit_event(
        session,
        event_type="JD_CREATED",
        outcome=AuditOutcome.SUCCESS,
        reason_code="AUTHORIZED_USER_CREATED_JD",
        correlation_id=correlation_id,
        occurred_at=now,
        org_id=org_id,
        actor_user_id=manager_user_id,
        resource_type="job_description",
        resource_id=str(record.id),
        metadata={"source_type": source_type, "source_format": source_format},
    )
    metrics.increment("jd_creation_total", source_type=source_type)
    result = record
    return result


async def list_manager_job_descriptions(
    session: AsyncSession,
    *,
    org_id: UUID,
    manager_user_id: UUID,
    page: int,
    page_size: int,
) -> tuple[list[JobDescription], int]:
    predicates = (
        JobDescription.org_id == org_id,
        JobDescription.created_by_user_id == manager_user_id,
    )
    total = int(await session.scalar(select(func.count()).where(*predicates)) or 0)
    items = list(
        (
            await session.scalars(
                select(JobDescription)
                .where(*predicates)
                .order_by(JobDescription.created_at.desc(), JobDescription.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    result = (items, total)
    return result
