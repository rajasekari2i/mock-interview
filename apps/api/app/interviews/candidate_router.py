"""Candidate-owned scheduled-interview routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import AuthenticatedRequest, require_candidate
from app.interviews.schemas import (
    CandidateInterviewPage,
    CandidateInterviewResponse,
    JobDescriptionSummary,
)
from app.interviews.service import list_candidate_interviews

router = APIRouter(prefix="/candidate", tags=["candidate"])


@router.get("/interviews", response_model=CandidateInterviewPage)
async def get_candidate_interviews(
    context: Annotated[AuthenticatedRequest, Depends(require_candidate)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 25,
) -> CandidateInterviewPage:
    items, total = await list_candidate_interviews(
        context.session,
        candidate_user_id=context.user.id,
        org_id=context.user.org_id,
        page=page,
        page_size=page_size,
    )
    responses: list[CandidateInterviewResponse] = []
    for item in items:
        responses.append(
            CandidateInterviewResponse(
                id=item.id,
                jobDescription=JobDescriptionSummary(
                    id=item.job_description_id, title=item.job_description_title
                ),
                scheduledAt=item.scheduled_at,
                status=item.status,
            )
        )
    return CandidateInterviewPage(
        items=responses,
        page=page,
        pageSize=page_size,
        totalItems=total,
        totalPages=(total + page_size - 1) // page_size,
    )
