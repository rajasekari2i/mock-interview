"""Test-only protected routes proving reusable resource-scope enforcement."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from app.auth.authorization import scoped_authorization_dependency
from app.auth.dependencies import AuthenticatedRequest, authenticated_request
from app.auth.models import Role
from app.auth.policies import AuthContext, Capability, ResourceScope
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/test-only/protected", include_in_schema=False)


def _auth_context(request: AuthenticatedRequest) -> AuthContext:
    return AuthContext(
        user_id=request.user.id,
        org_id=request.user.org_id,
        role=Role(request.user.role),
        candidate_profile_id=request.candidate_profile_id,
    )


@router.get("/candidate/{candidate_owner_user_id}")
async def candidate_resource(
    candidate_owner_user_id: UUID,
    context: Annotated[AuthenticatedRequest, Depends(authenticated_request)],
) -> dict[str, bool]:
    scope = ResourceScope(
        capability=Capability.CANDIDATE_VIEW_OWN_DATA,
        org_id=context.user.org_id,
        candidate_owner_user_id=candidate_owner_user_id,
    )
    await scoped_authorization_dependency(_auth_context(context), scope, hide_resource=True)
    return {"allowed": True}
