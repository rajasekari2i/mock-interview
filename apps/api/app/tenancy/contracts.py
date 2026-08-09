"""Typed contracts for Candidate tenant-migration participants."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class CandidateTenantMigrationParticipant(Protocol):
    """One PostgreSQL module participating in an atomic Candidate tenant move."""

    name: str

    async def validate_and_lock(
        self,
        session: AsyncSession,
        candidate_user_ids: tuple[UUID, ...],
        source_org_id: UUID,
        target_org_id: UUID,
    ) -> None: ...

    async def migrate(
        self,
        session: AsyncSession,
        candidate_user_ids: tuple[UUID, ...],
        source_org_id: UUID,
        target_org_id: UUID,
        now: datetime,
    ) -> int: ...
