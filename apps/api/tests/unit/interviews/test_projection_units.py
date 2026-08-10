from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from app.interviews import candidate_router, service
from app.interviews.service import CandidateInterviewProjection

NOW = datetime(2026, 8, 10, 9, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_candidate_service_and_router_project_rows_without_identity_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    interview = SimpleNamespace(
        id=UUID(int=1),
        job_description_id=UUID(int=2),
        scheduled_at=NOW,
        status="SCHEDULED",
    )
    session = AsyncMock()
    session.scalar.return_value = 1
    execute_result = Mock()
    execute_result.all.return_value = [(interview, "Platform Engineer")]
    session.execute.return_value = execute_result
    items, total = await service.list_candidate_interviews(
        session,
        candidate_user_id=UUID(int=3),
        org_id=UUID(int=4),
        page=1,
        page_size=25,
    )
    assert total == 1
    assert items[0].job_description_title == "Platform Engineer"

    projection = CandidateInterviewProjection(
        id=UUID(int=1),
        job_description_id=UUID(int=2),
        job_description_title="Platform Engineer",
        scheduled_at=NOW,
        status="SCHEDULED",
    )
    monkeypatch.setattr(
        candidate_router,
        "list_candidate_interviews",
        AsyncMock(return_value=([projection], 1)),
    )
    context = SimpleNamespace(
        session=session,
        user=SimpleNamespace(id=UUID(int=3), org_id=UUID(int=4)),
    )
    result = await candidate_router.get_candidate_interviews(context, page=1, page_size=25)
    assert result.items[0].job_description.title == "Platform Engineer"
