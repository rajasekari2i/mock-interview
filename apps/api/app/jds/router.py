"""Manager-owned JD listing and shared Manager/Admin creation routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.auth.dependencies import AuthenticatedRequest, require_manager, require_manager_or_admin
from app.auth.errors import AuthError, ErrorCode
from app.auth.security import CsrfPolicy
from app.core.observability import get_correlation_id
from app.jds.documents import MAX_UPLOAD_BYTES, parse_document
from app.jds.models import JobDescription
from app.jds.schemas import (
    ManagerJobDescriptionPage,
    ManagerJobDescriptionResponse,
    ManualJobDescriptionRequest,
)
from app.jds.service import create_job_description, list_manager_job_descriptions

router = APIRouter(prefix="/manager/job-descriptions", tags=["manager"])


def _validate_csrf(request: Request, context: AuthenticatedRequest) -> None:
    policy: CsrfPolicy = request.app.state.csrf_policy
    policy.validate(
        origin=request.headers.get("Origin", ""),
        cookie_token=request.cookies.get("mi_csrf", ""),
        header_token=request.headers.get("X-CSRF-Token", ""),
        expected_digest=context.authentication_session.csrf_token_digest,
    )


def _response(record: JobDescription) -> ManagerJobDescriptionResponse:
    return ManagerJobDescriptionResponse(
        id=record.id,
        title=record.title,
        sourceType=record.source_type,
        sourceFormat=record.source_format,
        createdAt=record.created_at,
    )


@router.get("", response_model=ManagerJobDescriptionPage)
async def get_manager_job_descriptions(
    context: Annotated[AuthenticatedRequest, Depends(require_manager)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 25,
) -> ManagerJobDescriptionPage:
    items, total = await list_manager_job_descriptions(
        context.session,
        org_id=context.user.org_id,
        manager_user_id=context.user.id,
        page=page,
        page_size=page_size,
    )
    responses = [_response(item) for item in items]
    result = ManagerJobDescriptionPage(
        items=responses,
        page=page,
        pageSize=page_size,
        totalItems=total,
        totalPages=(total + page_size - 1) // page_size,
    )
    return result


@router.post("", response_model=ManagerJobDescriptionResponse, status_code=status.HTTP_201_CREATED)
async def post_manual_job_description(
    payload: ManualJobDescriptionRequest,
    request: Request,
    context: Annotated[AuthenticatedRequest, Depends(require_manager_or_admin)],
) -> ManagerJobDescriptionResponse:
    _validate_csrf(request, context)
    record = await create_job_description(
        context.session,
        org_id=context.user.org_id,
        manager_user_id=context.user.id,
        title=payload.title,
        content_text=payload.content,
        source_format=None,
        now=getattr(request.app.state, "clock", lambda: datetime.now(UTC))(),
        correlation_id=getattr(request.state, "correlation_id", get_correlation_id()),
    )
    response = _response(record)
    return response


@router.post(
    "/upload",
    response_model=ManagerJobDescriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_uploaded_job_description(
    request: Request,
    context: Annotated[AuthenticatedRequest, Depends(require_manager_or_admin)],
    title: Annotated[str, Form(min_length=1, max_length=200)],
    document: Annotated[UploadFile, File()],
) -> ManagerJobDescriptionResponse:
    _validate_csrf(request, context)
    payload = await document.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise AuthError(ErrorCode.UPLOAD_TOO_LARGE)
    parsed = await run_in_threadpool(
        parse_document,
        filename=document.filename or "document",
        content_type=document.content_type or "application/octet-stream",
        payload=payload,
    )
    if not title.strip():
        raise AuthError(ErrorCode.VALIDATION_ERROR)
    record = await create_job_description(
        context.session,
        org_id=context.user.org_id,
        manager_user_id=context.user.id,
        title=title,
        content_text=parsed.text,
        source_format=parsed.source_format,
        now=getattr(request.app.state, "clock", lambda: datetime.now(UTC))(),
        correlation_id=getattr(request.state, "correlation_id", get_correlation_id()),
    )
    response = _response(record)
    return response
