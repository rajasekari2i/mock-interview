"""Framework integration for resource-scoped policy enforcement."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.auth.errors import AuthError, ErrorCode
from app.auth.policies import AuthContext, ResourceScope, authorize
from app.core.observability import metrics


async def scoped_authorization_dependency(
    context: AuthContext,
    scope: ResourceScope,
    *,
    hide_resource: bool = False,
) -> None:
    decision = authorize(context, scope)
    if decision.allowed:
        return
    metrics.increment("auth_authorization_denied_total", reason=decision.reason)
    if hide_resource and decision.reason in {
        "ORGANIZATION_MISMATCH",
        "CANDIDATE_OWNERSHIP_MISMATCH",
        "ALLOCATION_MANAGER_MISMATCH",
        "MANAGING_MANAGER_MISMATCH",
    }:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource unavailable")
    raise AuthError(ErrorCode.FORBIDDEN)
