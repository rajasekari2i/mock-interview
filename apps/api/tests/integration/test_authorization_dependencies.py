from __future__ import annotations

from uuid import UUID

import httpx
import pytest
from app.auth.authorization import scoped_authorization_dependency
from app.auth.models import Role
from app.auth.policies import AuthContext, Capability, ResourceScope
from fastapi import FastAPI


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
