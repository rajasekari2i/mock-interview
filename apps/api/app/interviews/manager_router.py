"""Manager scheduling routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response, status

from app.auth.dependencies import AuthenticatedRequest, require_manager
from app.auth.errors import AuthError, ErrorCode
from app.auth.security import CsrfPolicy
from app.core.observability import get_correlation_id
from app.interviews.schemas import (
    CandidateSelectionResponse,
    JobDescriptionSummary,
    ManagerCandidatePage,
    ManagerInterviewPage,
    ManagerInterviewResponse,
    ScheduleInterviewRequest,
)
from app.interviews.service import (
    ManagerInterviewProjection,
    get_manager_interview_projection,
    list_manager_candidates,
    list_manager_interviews,
    schedule_interview,
)

router = APIRouter(prefix="/manager", tags=["manager"])


def _validate_csrf(request: Request, context: AuthenticatedRequest) -> None:
    policy: CsrfPolicy = request.app.state.csrf_policy
    policy.validate(
        origin=request.headers.get("Origin", ""),
        cookie_token=request.cookies.get("mi_csrf", ""),
        header_token=request.headers.get("X-CSRF-Token", ""),
        expected_digest=context.authentication_session.csrf_token_digest,
    )


def _response(item: ManagerInterviewProjection) -> ManagerInterviewResponse:
    return ManagerInterviewResponse(
        id=item.id,
        candidate=CandidateSelectionResponse(
            id=item.candidate_id,
            displayName=item.candidate_display_name,
            email=item.candidate_email,
        ),
        jobDescription=JobDescriptionSummary(
            id=item.job_description_id, title=item.job_description_title
        ),
        scheduledAt=item.scheduled_at,
        status=item.status,
    )


@router.get("/candidates", response_model=ManagerCandidatePage)
async def get_manager_candidates(
    context: Annotated[AuthenticatedRequest, Depends(require_manager)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 25,
) -> ManagerCandidatePage:
    items, total = await list_manager_candidates(
        context.session, org_id=context.user.org_id, page=page, page_size=page_size
    )
    return ManagerCandidatePage(
        items=[
            CandidateSelectionResponse(id=item.id, displayName=item.display_name, email=item.email)
            for item in items
        ],
        page=page,
        pageSize=page_size,
        totalItems=total,
        totalPages=(total + page_size - 1) // page_size,
    )


@router.get("/interviews", response_model=ManagerInterviewPage)
async def get_manager_interviews(
    context: Annotated[AuthenticatedRequest, Depends(require_manager)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 25,
) -> ManagerInterviewPage:
    items, total = await list_manager_interviews(
        context.session,
        org_id=context.user.org_id,
        manager_user_id=context.user.id,
        page=page,
        page_size=page_size,
    )
    return ManagerInterviewPage(
        items=[_response(item) for item in items],
        page=page,
        pageSize=page_size,
        totalItems=total,
        totalPages=(total + page_size - 1) // page_size,
    )


@router.post(
    "/interviews", response_model=ManagerInterviewResponse, status_code=status.HTTP_201_CREATED
)
async def post_manager_interview(
    payload: ScheduleInterviewRequest,
    request: Request,
    response: Response,
    context: Annotated[AuthenticatedRequest, Depends(require_manager)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)],
) -> ManagerInterviewResponse:
    _validate_csrf(request, context)
    try:
        key = str(UUID(idempotency_key))
    except ValueError as error:
        raise AuthError(ErrorCode.VALIDATION_ERROR) from error
    record, replayed = await schedule_interview(
        context.session,
        org_id=context.user.org_id,
        manager_user_id=context.user.id,
        candidate_user_id=payload.candidateId,
        job_description_id=payload.jobDescriptionId,
        scheduled_at=payload.scheduledAt,
        idempotency_key=key,
        now=getattr(request.app.state, "clock", lambda: datetime.now(UTC))(),
        correlation_id=getattr(request.state, "correlation_id", get_correlation_id()),
    )
    response.status_code = status.HTTP_200_OK if replayed else status.HTTP_201_CREATED
    response.headers["Idempotency-Replayed"] = str(replayed).lower()
    projection = await get_manager_interview_projection(context.session, record)
    return _response(projection)
