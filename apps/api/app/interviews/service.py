"""Role-scoped scheduled-interview queries and mutations."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.audit import append_audit_event
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import AuditOutcome, EntityStatus, Role, User
from app.core.observability import metrics
from app.interviews.models import ScheduledInterview
from app.jds.models import JobDescription


def idempotency_digest(key: str) -> bytes:
    return hashlib.sha256(key.encode("utf-8")).digest()


def request_fingerprint(
    candidate_user_id: UUID, job_description_id: UUID, scheduled_at: datetime
) -> bytes:
    canonical = "|".join(
        (
            str(candidate_user_id),
            str(job_description_id),
            scheduled_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).digest()


def validate_scheduled_at(value: datetime, *, now: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None or value <= now:
        raise AuthError(ErrorCode.VALIDATION_ERROR)
    return value.astimezone(UTC)


@dataclass(frozen=True)
class CandidateInterviewProjection:
    id: UUID
    job_description_id: UUID
    job_description_title: str
    scheduled_at: datetime
    status: str


@dataclass(frozen=True)
class CandidateSelectionProjection:
    id: UUID
    display_name: str
    email: str


@dataclass(frozen=True)
class ManagerInterviewProjection:
    id: UUID
    candidate_id: UUID
    candidate_display_name: str
    candidate_email: str
    job_description_id: UUID
    job_description_title: str
    scheduled_at: datetime
    status: str


async def list_candidate_interviews(
    session: AsyncSession,
    *,
    candidate_user_id: UUID,
    org_id: UUID,
    page: int,
    page_size: int,
) -> tuple[list[CandidateInterviewProjection], int]:
    predicates = (
        ScheduledInterview.candidate_user_id == candidate_user_id,
        ScheduledInterview.org_id == org_id,
    )
    total = int(
        await session.scalar(select(func.count(ScheduledInterview.id)).where(*predicates)) or 0
    )
    rows = (
        await session.execute(
            select(ScheduledInterview, JobDescription.title)
            .join(
                JobDescription,
                (JobDescription.id == ScheduledInterview.job_description_id)
                & (JobDescription.org_id == ScheduledInterview.org_id),
            )
            .where(*predicates)
            .order_by(ScheduledInterview.scheduled_at, ScheduledInterview.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    projections: list[CandidateInterviewProjection] = []
    for interview, title in rows:
        projections.append(
            CandidateInterviewProjection(
                id=interview.id,
                job_description_id=interview.job_description_id,
                job_description_title=title,
                scheduled_at=interview.scheduled_at,
                status=interview.status,
            )
        )
    return projections, total


async def list_manager_candidates(
    session: AsyncSession, *, org_id: UUID, page: int, page_size: int
) -> tuple[list[CandidateSelectionProjection], int]:
    predicates = (
        User.org_id == org_id,
        User.role == Role.CANDIDATE.value,
        User.status == EntityStatus.ACTIVE.value,
    )
    total = int(await session.scalar(select(func.count(User.id)).where(*predicates)) or 0)
    rows = (
        await session.execute(
            select(User.id, User.display_name, User.email)
            .where(*predicates)
            .order_by(User.display_name, User.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return [CandidateSelectionProjection(*row) for row in rows], total


async def schedule_interview(
    session: AsyncSession,
    *,
    org_id: UUID,
    manager_user_id: UUID,
    candidate_user_id: UUID,
    job_description_id: UUID,
    scheduled_at: datetime,
    idempotency_key: str,
    now: datetime,
    correlation_id: str,
) -> tuple[ScheduledInterview, bool]:
    instant = validate_scheduled_at(scheduled_at, now=now)
    key_digest = idempotency_digest(idempotency_key)
    fingerprint = request_fingerprint(candidate_user_id, job_description_id, instant)
    manager = await session.scalar(
        select(User)
        .where(
            User.id == manager_user_id,
            User.org_id == org_id,
            User.role == Role.MANAGER.value,
            User.status == EntityStatus.ACTIVE.value,
        )
        .with_for_update()
    )
    if manager is None:
        raise AuthError(ErrorCode.RESOURCE_NOT_FOUND)
    existing = await session.scalar(
        select(ScheduledInterview)
        .where(
            ScheduledInterview.scheduling_manager_user_id == manager_user_id,
            ScheduledInterview.idempotency_key_digest == key_digest,
        )
        .with_for_update()
    )
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise AuthError(ErrorCode.IDEMPOTENCY_CONFLICT)
        return existing, True
    candidate = await session.scalar(
        select(User)
        .where(
            User.id == candidate_user_id,
            User.org_id == org_id,
            User.role == Role.CANDIDATE.value,
            User.status == EntityStatus.ACTIVE.value,
        )
        .with_for_update()
    )
    if candidate is None:
        raise AuthError(ErrorCode.RESOURCE_NOT_FOUND)
    job_description = await session.scalar(
        select(JobDescription)
        .where(
            JobDescription.id == job_description_id,
            JobDescription.org_id == org_id,
            JobDescription.created_by_user_id == manager_user_id,
        )
        .with_for_update()
    )
    if job_description is None:
        raise AuthError(ErrorCode.RESOURCE_NOT_FOUND)
    record = ScheduledInterview(
        org_id=org_id,
        candidate_user_id=candidate_user_id,
        job_description_id=job_description_id,
        scheduling_manager_user_id=manager_user_id,
        scheduled_at=instant,
        status="SCHEDULED",
        idempotency_key_digest=key_digest,
        request_fingerprint=fingerprint,
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    await session.flush()
    await append_audit_event(
        session,
        event_type="INTERVIEW_SCHEDULED",
        outcome=AuditOutcome.SUCCESS,
        reason_code="MANAGER_SCHEDULED",
        correlation_id=correlation_id,
        occurred_at=now,
        org_id=org_id,
        actor_user_id=manager_user_id,
        target_user_id=candidate_user_id,
        resource_type="scheduled_interview",
        resource_id=str(record.id),
        metadata={"replayed": False},
    )
    metrics.increment("interview_scheduling_total", status="created")
    return record, False


async def _manager_projection(
    session: AsyncSession, interview: ScheduledInterview
) -> ManagerInterviewProjection:
    row = (
        await session.execute(
            select(User.display_name, User.email, JobDescription.title)
            .join(
                JobDescription,
                (JobDescription.id == interview.job_description_id)
                & (JobDescription.org_id == interview.org_id),
            )
            .where(User.id == interview.candidate_user_id, User.org_id == interview.org_id)
        )
    ).one()
    return ManagerInterviewProjection(
        id=interview.id,
        candidate_id=interview.candidate_user_id,
        candidate_display_name=row[0],
        candidate_email=row[1],
        job_description_id=interview.job_description_id,
        job_description_title=row[2],
        scheduled_at=interview.scheduled_at,
        status=interview.status,
    )


async def get_manager_interview_projection(
    session: AsyncSession, interview: ScheduledInterview
) -> ManagerInterviewProjection:
    return await _manager_projection(session, interview)


async def list_manager_interviews(
    session: AsyncSession,
    *,
    org_id: UUID,
    manager_user_id: UUID,
    page: int,
    page_size: int,
) -> tuple[list[ManagerInterviewProjection], int]:
    predicates = (
        ScheduledInterview.org_id == org_id,
        ScheduledInterview.scheduling_manager_user_id == manager_user_id,
    )
    total = int(
        await session.scalar(select(func.count(ScheduledInterview.id)).where(*predicates)) or 0
    )
    records = list(
        (
            await session.scalars(
                select(ScheduledInterview)
                .where(*predicates)
                .order_by(ScheduledInterview.scheduled_at, ScheduledInterview.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
    )
    return [await _manager_projection(session, record) for record in records], total
