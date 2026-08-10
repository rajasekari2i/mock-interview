"""Fail-closed migration participant for multi-owner interview rows."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import AuthError, ErrorCode
from app.interviews.models import ScheduledInterview


class ScheduledInterviewTenantMigrationParticipant:
    name = "scheduled_interviews"

    async def validate_and_lock(
        self,
        session: AsyncSession,
        candidate_user_ids: tuple[UUID, ...],
        source_org_id: UUID,
        target_org_id: UUID,
    ) -> None:
        del target_org_id
        if not candidate_user_ids:
            return
        rows = (
            await session.execute(
                select(ScheduledInterview.id)
                .where(
                    ScheduledInterview.org_id == source_org_id,
                    or_(
                        ScheduledInterview.candidate_user_id.in_(candidate_user_ids),
                        ScheduledInterview.scheduling_manager_user_id.in_(candidate_user_ids),
                    ),
                )
                .order_by(ScheduledInterview.id)
                .with_for_update()
            )
        ).all()
        if rows:
            raise AuthError(ErrorCode.IDENTITY_CONFLICT)

    async def migrate(
        self,
        session: AsyncSession,
        candidate_user_ids: tuple[UUID, ...],
        source_org_id: UUID,
        target_org_id: UUID,
        now: datetime,
    ) -> int:
        del session, candidate_user_ids, source_org_id, target_org_id, now
        return 0
