"""Reusable authenticated request context dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.audit import append_authorization_denial
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import AuthenticationSession, CandidateProfile, Role, User
from app.auth.policies import Capability
from app.auth.sessions import resolve_session
from app.core.database import Database
from app.core.observability import get_correlation_id


@dataclass(frozen=True)
class AuthenticatedRequest:
    session: AsyncSession
    user: User
    authentication_session: AuthenticationSession
    candidate_profile_id: UUID | None


async def authenticated_request(request: Request) -> AsyncIterator[AuthenticatedRequest]:
    cookie_name: str = request.app.state.session_cookie_policy.name
    token = request.cookies.get(cookie_name)
    if token is None:
        raise AuthError(ErrorCode.AUTHENTICATION_REQUIRED)
    database: Database = request.app.state.database
    clock = getattr(request.app.state, "clock", lambda: datetime.now(UTC))
    async with database.transaction() as session:
        authentication_session, user = await resolve_session(session, token, now=clock())
        profile_id = None
        if user.role == Role.CANDIDATE.value:
            profile_id = await session.scalar(
                select(CandidateProfile.id).where(CandidateProfile.user_id == user.id)
            )
            if profile_id is None:
                raise AuthError(ErrorCode.CANDIDATE_PROFILE_CONFLICT)
        yield AuthenticatedRequest(session, user, authentication_session, profile_id)


async def require_admin(
    context: Annotated[AuthenticatedRequest, Depends(authenticated_request)],
) -> AuthenticatedRequest:
    if context.user.role != Role.ADMIN.value:
        raise AuthError(ErrorCode.FORBIDDEN)
    return context


async def require_domain_mapping_admin(
    request: Request,
    context: Annotated[AuthenticatedRequest, Depends(authenticated_request)],
) -> AuthenticatedRequest:
    """Require the mapping capability and persist a safe denial independently."""

    if context.user.role == Role.ADMIN.value:
        return context
    database: Database = request.app.state.database
    clock = getattr(request.app.state, "clock", lambda: datetime.now(UTC))
    async with database.transaction() as audit_session:
        await append_authorization_denial(
            audit_session,
            reason_code="CAPABILITY_DENIED",
            correlation_id=getattr(
                request.state, "correlation_id", get_correlation_id()
            ),
            occurred_at=clock(),
            org_id=context.user.org_id,
            actor_user_id=context.user.id,
            capability=Capability.ADMIN_MANAGE_DOMAIN_MAPPINGS.value,
            resource_type="organization_domain_mapping",
        )
    raise AuthError(ErrorCode.FORBIDDEN)
