from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from app.auth.errors import AuthError, ErrorCode
from app.interviews import manager_router, service
from app.interviews.models import ScheduledInterview
from app.interviews.schemas import ScheduleInterviewRequest
from app.interviews.service import ManagerInterviewProjection
from starlette.responses import Response

NOW = datetime(2026, 8, 10, 9, 0, tzinfo=UTC)


def _interview() -> ScheduledInterview:
    return ScheduledInterview(
        id=UUID(int=1),
        org_id=UUID(int=2),
        candidate_user_id=UUID(int=3),
        job_description_id=UUID(int=4),
        scheduling_manager_user_id=UUID(int=5),
        scheduled_at=NOW + timedelta(hours=1),
        status="SCHEDULED",
        idempotency_key_digest=b"a" * 32,
        request_fingerprint=service.request_fingerprint(
            UUID(int=3), UUID(int=4), NOW + timedelta(hours=1)
        ),
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.asyncio
async def test_manager_candidate_and_interview_projection_helpers() -> None:
    session = AsyncMock()
    session.scalar.return_value = 1
    result = Mock()
    result.all.return_value = [(UUID(int=3), "Ada", "ada@example.test")]
    session.execute.return_value = result
    candidates, total = await service.list_manager_candidates(
        session, org_id=UUID(int=2), page=1, page_size=25
    )
    assert total == 1 and candidates[0].display_name == "Ada"

    projection_result = Mock()
    projection_result.one.return_value = ("Ada", "ada@example.test", "Engineer")
    session.execute.return_value = projection_result
    projection = await service.get_manager_interview_projection(session, _interview())
    assert projection.job_description_title == "Engineer"

    scalar_records = Mock()
    scalar_records.all.return_value = [_interview()]
    session.scalars.return_value = scalar_records
    listed, count = await service.list_manager_interviews(
        session, org_id=UUID(int=2), manager_user_id=UUID(int=5), page=1, page_size=25
    )
    assert count == 1 and listed[0].candidate_display_name == "Ada"


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["manager", "candidate", "job"])
async def test_schedule_rejects_each_missing_locked_resource(stage: str) -> None:
    session = AsyncMock()
    if stage == "manager":
        session.scalar.side_effect = [None]
    elif stage == "candidate":
        session.scalar.side_effect = [Mock(), None, None]
    else:
        session.scalar.side_effect = [Mock(), None, Mock(), None]
    with pytest.raises(AuthError) as error:
        await service.schedule_interview(
            session,
            org_id=UUID(int=2),
            manager_user_id=UUID(int=5),
            candidate_user_id=UUID(int=3),
            job_description_id=UUID(int=4),
            scheduled_at=NOW + timedelta(hours=1),
            idempotency_key="key",
            now=NOW,
            correlation_id="test",
        )
    assert error.value.code is ErrorCode.RESOURCE_NOT_FOUND


@pytest.mark.asyncio
async def test_schedule_replay_conflict_and_success(monkeypatch: pytest.MonkeyPatch) -> None:
    session = AsyncMock()
    existing = _interview()
    session.scalar.side_effect = [Mock(), existing]
    replay, replayed = await service.schedule_interview(
        session,
        org_id=UUID(int=2),
        manager_user_id=UUID(int=5),
        candidate_user_id=UUID(int=3),
        job_description_id=UUID(int=4),
        scheduled_at=NOW + timedelta(hours=1),
        idempotency_key="key",
        now=NOW,
        correlation_id="test",
    )
    assert replay is existing and replayed

    existing.request_fingerprint = b"z" * 32
    session.scalar.side_effect = [Mock(), existing]
    with pytest.raises(AuthError) as conflict:
        await service.schedule_interview(
            session,
            org_id=UUID(int=2),
            manager_user_id=UUID(int=5),
            candidate_user_id=UUID(int=3),
            job_description_id=UUID(int=4),
            scheduled_at=NOW + timedelta(hours=1),
            idempotency_key="key",
            now=NOW,
            correlation_id="test",
        )
    assert conflict.value.code is ErrorCode.IDEMPOTENCY_CONFLICT

    session.scalar.side_effect = [Mock(), None, Mock(), Mock()]
    session.add = Mock()
    monkeypatch.setattr(service, "append_audit_event", AsyncMock())
    monkeypatch.setattr(service.metrics, "increment", Mock())
    created, replayed = await service.schedule_interview(
        session,
        org_id=UUID(int=2),
        manager_user_id=UUID(int=5),
        candidate_user_id=UUID(int=3),
        job_description_id=UUID(int=4),
        scheduled_at=NOW + timedelta(hours=1),
        idempotency_key="key",
        now=NOW,
        correlation_id="test",
    )
    assert created.status == "SCHEDULED" and not replayed


@pytest.mark.asyncio
async def test_manager_routes_complete_after_await_and_validate_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    projection = ManagerInterviewProjection(
        id=UUID(int=1),
        candidate_id=UUID(int=3),
        candidate_display_name="Ada",
        candidate_email="ada@example.test",
        job_description_id=UUID(int=4),
        job_description_title="Engineer",
        scheduled_at=NOW + timedelta(hours=1),
        status="SCHEDULED",
    )
    context = SimpleNamespace(
        session=AsyncMock(), user=SimpleNamespace(id=UUID(int=5), org_id=UUID(int=2))
    )
    monkeypatch.setattr(
        manager_router,
        "list_manager_candidates",
        AsyncMock(
            return_value=(
                [service.CandidateSelectionProjection(UUID(int=3), "Ada", "ada@example.test")],
                1,
            )
        ),
    )
    candidates = await manager_router.get_manager_candidates(context, page=1, page_size=25)
    assert candidates.total_items == 1
    monkeypatch.setattr(
        manager_router, "list_manager_interviews", AsyncMock(return_value=([projection], 1))
    )
    interviews = await manager_router.get_manager_interviews(context, page=1, page_size=25)
    assert interviews.items[0].candidate.display_name == "Ada"

    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(clock=lambda: NOW)),
        state=SimpleNamespace(correlation_id="test"),
    )
    monkeypatch.setattr(manager_router, "_validate_csrf", Mock())
    payload = ScheduleInterviewRequest(
        candidateId=UUID(int=3), jobDescriptionId=UUID(int=4), scheduledAt=NOW + timedelta(hours=1)
    )
    with pytest.raises(AuthError) as invalid:
        await manager_router.post_manager_interview(payload, request, Response(), context, "bad")
    assert invalid.value.code is ErrorCode.VALIDATION_ERROR
    monkeypatch.setattr(
        manager_router, "schedule_interview", AsyncMock(return_value=(_interview(), True))
    )
    monkeypatch.setattr(
        manager_router, "get_manager_interview_projection", AsyncMock(return_value=projection)
    )
    response = Response()
    result = await manager_router.post_manager_interview(
        payload, request, response, context, "00000000-0000-0000-0000-000000000001"
    )
    assert response.status_code == 200 and result.candidate.display_name == "Ada"


def test_manager_route_csrf_forwards_request_evidence() -> None:
    policy = Mock()
    cookie_evidence = "cookie"
    header_evidence = "header"
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(csrf_policy=policy)),
        headers={"Origin": "https://app.test", "X-CSRF-Token": header_evidence},
        cookies={"mi_csrf": cookie_evidence},
    )
    context = SimpleNamespace(
        authentication_session=SimpleNamespace(csrf_token_digest=b"digest")
    )
    manager_router._validate_csrf(request, context)
    policy.validate.assert_called_once_with(
        origin="https://app.test",
        cookie_token=cookie_evidence,
        header_token=header_evidence,
        expected_digest=b"digest",
    )
