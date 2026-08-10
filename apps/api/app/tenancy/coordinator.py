"""Same-transaction Candidate tenant-migration coordinator."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.tenancy.contracts import CandidateTenantMigrationParticipant


class CandidateTenantMigrationCoordinator:
    """Run registered participants in a deterministic, fail-closed order."""

    def __init__(self, participants: Iterable[CandidateTenantMigrationParticipant] = ()) -> None:
        ordered = tuple(sorted(participants, key=lambda participant: participant.name))
        names = tuple(participant.name for participant in ordered)
        if any(not name for name in names) or len(names) != len(set(names)):
            raise ValueError("Tenant migration participant names must be non-empty and unique")
        self.participants = ordered

    async def migrate(
        self,
        session: AsyncSession,
        *,
        candidate_user_ids: tuple[UUID, ...],
        source_org_id: UUID,
        target_org_id: UUID,
        now: datetime,
    ) -> dict[str, int]:
        ordered_ids = tuple(sorted(candidate_user_ids))
        for participant in self.participants:
            await participant.validate_and_lock(session, ordered_ids, source_org_id, target_org_id)
        counts: dict[str, int] = {}
        for participant in self.participants:
            counts[participant.name] = await participant.migrate(
                session, ordered_ids, source_org_id, target_org_id, now
            )
        return counts
