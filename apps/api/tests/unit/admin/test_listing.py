from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from app.admin import router, service
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import EntityStatus, Role, User
from app.jds.models import JobDescription

NOW = datetime(2026, 8, 10, 9, 0, tzinfo=UTC)


def _user() -> User:
    return User(
        id=UUID(int=1),
        org_id=UUID(int=2),
        email="ada@example.test",
        normalized_email="ada@example.test",
        display_name="Ada",
        profile_picture_url=None,
        role=Role.MANAGER.value,
        status=EntityStatus.ACTIVE.value,
        auth_generation=1,
        created_at=NOW,
        updated_at=NOW,
    )


def _jd() -> JobDescription:
    return JobDescription(
        id=UUID(int=3),
        org_id=UUID(int=2),
        created_by_user_id=UUID(int=1),
        title="Engineer",
        source_type="MANUAL",
        source_format=None,
        content_text="Content",
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.mark.asyncio
async def test_admin_listing_services_return_rows_and_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock()
    session.scalar.return_value = 1
    scalars = Mock()
    scalars.all.return_value = [_user()]
    session.scalars.return_value = scalars
    monkeypatch.setattr(service.metrics, "increment", Mock())
    users, total = await service.list_admin_users(session, page=1, page_size=25)
    assert total == 1 and users[0].display_name == "Ada"

    result = Mock()
    result.all.return_value = [(_jd(), "Ada")]
    session.execute.return_value = result
    jds, total = await service.list_admin_job_descriptions(session, page=1, page_size=25)
    assert total == 1 and jds[0].creator_display_name == "Ada"

    session.get.return_value = _user()
    assert await service.get_admin_user(session, user_id=UUID(int=1)) is not None
    session.get.return_value = None
    with pytest.raises(AuthError) as missing:
        await service.get_admin_user(session, user_id=UUID(int=9))
    assert missing.value.code is ErrorCode.RESOURCE_NOT_FOUND


@pytest.mark.asyncio
async def test_admin_listing_routes_complete_after_await(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = SimpleNamespace(session=AsyncMock())
    context.session.scalar.return_value = None
    monkeypatch.setattr(router, "list_admin_users", AsyncMock(return_value=([_user()], 1)))
    users = await router.get_users(context, page=1, page_size=25)
    assert users.items[0].display_name == "Ada"

    monkeypatch.setattr(router, "get_admin_user", AsyncMock(return_value=_user()))
    details = await router.get_user_details(UUID(int=1), context)
    assert details.profile_picture_url is None

    monkeypatch.setattr(
        router,
        "list_admin_job_descriptions",
        AsyncMock(return_value=([service.AdminJobDescriptionProjection(_jd(), "Ada")], 1)),
    )
    jds = await router.get_job_descriptions(context, page=1, page_size=25)
    assert jds.items[0].created_by.display_name == "Ada"
