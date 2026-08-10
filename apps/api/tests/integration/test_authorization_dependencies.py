from __future__ import annotations

from typing import cast
from uuid import UUID

import httpx
import pytest
from app.auth.authorization import scoped_authorization_dependency
from app.auth.dependencies import (
    AuthenticatedRequest,
    require_admin,
    require_candidate,
    require_manager,
    require_manager_or_admin,
)
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import AuthenticationSession, Role, User
from app.auth.policies import AuthContext, Capability, ResourceScope
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_fastapi_dependency_allows_scope_and_denies_cross_org_without_disclosure() -> None:
    app = FastAPI()
    context = AuthContext(UUID(int=1), UUID(int=10), Role.CANDIDATE, UUID(int=2))

    @app.get("/owned")
    async def owned() -> dict[str, bool]:
        await scoped_authorization_dependency(
            context,
            ResourceScope(
                org_id=UUID(int=10),
                capability=Capability.CANDIDATE_VIEW_OWN_PROFILE,
                candidate_owner_user_id=UUID(int=1),
            ),
        )
        return {"allowed": True}

    @app.get("/cross-org")
    async def cross_org() -> None:
        await scoped_authorization_dependency(
            context,
            ResourceScope(
                org_id=UUID(int=99),
                capability=Capability.CANDIDATE_VIEW_OWN_PROFILE,
                candidate_owner_user_id=UUID(int=1),
            ),
            hide_resource=True,
        )

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/owned")).status_code == 200
        assert (await client.get("/cross-org")).status_code == 404


@pytest.mark.asyncio
async def test_role_dependencies_deny_every_other_supported_role() -> None:
    for role, dependency in (
        (Role.CANDIDATE, require_candidate),
        (Role.MANAGER, require_manager),
        (Role.ADMIN, require_admin),
    ):
        allowed = AuthenticatedRequest(
            session=cast(AsyncSession, object()),
            user=User(role=role.value),
            authentication_session=AuthenticationSession(),
            candidate_profile_id=UUID(int=2) if role is Role.CANDIDATE else None,
        )
        assert await dependency(allowed) is allowed
        denied = AuthenticatedRequest(
            session=cast(AsyncSession, object()),
            user=User(role=(Role.ADMIN if role is not Role.ADMIN else Role.MANAGER).value),
            authentication_session=AuthenticationSession(),
            candidate_profile_id=None,
        )
        with pytest.raises(AuthError) as error:
            await dependency(denied)
        assert error.value.code is ErrorCode.FORBIDDEN


@pytest.mark.asyncio
async def test_manager_or_admin_dependency_allows_both_roles_and_denies_candidate() -> None:
    for role in (Role.MANAGER, Role.ADMIN):
        context = AuthenticatedRequest(
            session=cast(AsyncSession, object()),
            user=User(role=role.value),
            authentication_session=AuthenticationSession(),
            candidate_profile_id=None,
        )
        assert await require_manager_or_admin(context) is context
    candidate = AuthenticatedRequest(
        session=cast(AsyncSession, object()),
        user=User(role=Role.CANDIDATE.value),
        authentication_session=AuthenticationSession(),
        candidate_profile_id=UUID(int=2),
    )
    with pytest.raises(AuthError) as error:
        await require_manager_or_admin(candidate)
    assert error.value.code is ErrorCode.FORBIDDEN
