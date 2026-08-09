from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from app.tenancy.coordinator import CandidateTenantMigrationCoordinator


class Participant:
    def __init__(
        self, name: str, calls: list[tuple[str, object]], *, fail: bool = False
    ) -> None:
        self.name = name
        self.calls = calls
        self.fail = fail

    async def validate_and_lock(
        self,
        session: object,
        candidate_user_ids: tuple[UUID, ...],
        source_org_id: UUID,
        target_org_id: UUID,
    ) -> None:
        del candidate_user_ids, source_org_id, target_org_id
        self.calls.append((f"validate:{self.name}", session))

    async def migrate(
        self,
        session: object,
        candidate_user_ids: tuple[UUID, ...],
        source_org_id: UUID,
        target_org_id: UUID,
        now: datetime,
    ) -> int:
        del source_org_id, target_org_id, now
        self.calls.append((f"migrate:{self.name}", session))
        if self.fail:
            raise RuntimeError("injected failure")
        return len(candidate_user_ids)


def test_registry_rejects_duplicate_or_empty_participant_names() -> None:
    calls: list[tuple[str, object]] = []
    with pytest.raises(ValueError):
        CandidateTenantMigrationCoordinator(
            (Participant("dup", calls), Participant("dup", calls))
        )
    with pytest.raises(ValueError):
        CandidateTenantMigrationCoordinator((Participant("", calls),))


@pytest.mark.asyncio
async def test_coordinator_validates_all_before_migrating_in_stable_order() -> None:
    calls: list[tuple[str, object]] = []
    session = SimpleNamespace()
    coordinator = CandidateTenantMigrationCoordinator(
        (Participant("zeta", calls), Participant("alpha", calls))
    )
    counts = await coordinator.migrate(
        session,
        candidate_user_ids=(UUID(int=2), UUID(int=1)),
        source_org_id=UUID(int=3),
        target_org_id=UUID(int=4),
        now=datetime(2026, 8, 9, tzinfo=UTC),
    )
    assert [name for name, supplied in calls] == [
        "validate:alpha",
        "validate:zeta",
        "migrate:alpha",
        "migrate:zeta",
    ]
    assert all(supplied is session for _, supplied in calls)
    assert counts == {"alpha": 2, "zeta": 2}


@pytest.mark.asyncio
async def test_participant_failure_propagates_without_running_later_participants() -> None:
    calls: list[tuple[str, object]] = []
    coordinator = CandidateTenantMigrationCoordinator(
        (Participant("alpha", calls, fail=True), Participant("zeta", calls))
    )
    with pytest.raises(RuntimeError, match="injected failure"):
        await coordinator.migrate(
            SimpleNamespace(),
            candidate_user_ids=(UUID(int=1),),
            source_org_id=UUID(int=2),
            target_org_id=UUID(int=3),
            now=datetime(2026, 8, 9, tzinfo=UTC),
        )
    assert [name for name, _ in calls] == [
        "validate:alpha",
        "validate:zeta",
        "migrate:alpha",
    ]
