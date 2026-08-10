from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from app.jds import router, service
from app.jds.documents import ParsedDocument
from app.jds.models import JobDescription
from app.jds.schemas import ManualJobDescriptionRequest

NOW = datetime(2026, 8, 10, 9, 0, tzinfo=UTC)


def _record() -> JobDescription:
    return JobDescription(
        id=UUID(int=1),
        org_id=UUID(int=2),
        created_by_user_id=UUID(int=3),
        title="Platform Engineer",
        source_type="MANUAL",
        source_format=None,
        content_text="Content",
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.asyncio
async def test_jd_service_returns_created_and_paginated_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock()
    session.add = Mock()
    monkeypatch.setattr(service, "append_audit_event", AsyncMock())
    monkeypatch.setattr(service.metrics, "increment", Mock())
    created = await service.create_job_description(
        session,
        org_id=UUID(int=2),
        manager_user_id=UUID(int=3),
        title=" Platform Engineer ",
        content_text=" Content ",
        source_format=None,
        now=NOW,
        correlation_id="test",
    )
    assert created.title == "Platform Engineer"

    session.scalar.return_value = 1
    scalars_result = Mock()
    scalars_result.all.return_value = [_record()]
    session.scalars.return_value = scalars_result
    items, total = await service.list_manager_job_descriptions(
        session,
        org_id=UUID(int=2),
        manager_user_id=UUID(int=3),
        page=1,
        page_size=25,
    )
    assert total == 1 and items[0].id == UUID(int=1)


@pytest.mark.asyncio
async def test_jd_routes_return_list_manual_and_upload_responses(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _record()
    context = SimpleNamespace(
        session=AsyncMock(),
        user=SimpleNamespace(id=UUID(int=3), org_id=UUID(int=2)),
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(clock=lambda: NOW)),
        state=SimpleNamespace(correlation_id="test"),
    )
    monkeypatch.setattr(router, "_validate_csrf", Mock())
    monkeypatch.setattr(
        router, "list_manager_job_descriptions", AsyncMock(return_value=([record], 1))
    )
    listed = await router.get_manager_job_descriptions(context, page=1, page_size=25)
    assert listed.items[0].title == record.title

    monkeypatch.setattr(router, "create_job_description", AsyncMock(return_value=record))
    manual = await router.post_manual_job_description(
        ManualJobDescriptionRequest(title="Title", content="Content"), request, context
    )
    assert manual.id == record.id

    upload = SimpleNamespace(
        filename="role.txt",
        content_type="text/plain",
        read=AsyncMock(return_value=b"content"),
    )
    monkeypatch.setattr(
        router,
        "run_in_threadpool",
        AsyncMock(return_value=ParsedDocument("TXT", "Content", "role.txt")),
    )
    uploaded = await router.post_uploaded_job_description(
        request, context, title="Title", document=upload
    )
    assert uploaded.id == record.id
