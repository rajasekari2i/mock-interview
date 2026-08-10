"""Admin provisioning HTTP contract."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select

from app.admin.service import (
    ProvisionUserInput,
    change_user_role,
    change_user_status,
    create_domain_mapping,
    create_organization,
    get_admin_user,
    list_admin_job_descriptions,
    list_admin_users,
    list_domain_mappings,
    list_organizations,
    provision_user,
    reassign_domain_mapping,
    remove_domain_mapping,
)
from app.auth.dependencies import (
    AuthenticatedRequest,
    require_admin,
    require_domain_mapping_admin,
)
from app.auth.models import (
    CandidateProfile,
    EntityStatus,
    Organization,
    OrganizationDomainMapping,
    Role,
    User,
)
from app.auth.security import CsrfPolicy
from app.core.observability import get_correlation_id
from app.tenancy.coordinator import CandidateTenantMigrationCoordinator

router = APIRouter(prefix="/admin", tags=["admin"])


class ProvisionUserRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: UUID = Field(alias="organizationId")
    email: EmailStr
    display_name: str = Field(alias="displayName", min_length=1, max_length=200)
    role: Role
    status: EntityStatus


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    organization_id: UUID = Field(alias="organizationId")
    email: str
    display_name: str = Field(alias="displayName")
    role: str
    status: str
    candidate_profile_id: UUID | None = Field(default=None, alias="candidateProfileId")
    profile_picture_url: str | None = Field(default=None, alias="profilePictureUrl")


class AdminUserListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    organization_id: UUID = Field(alias="organizationId")
    email: str
    display_name: str = Field(alias="displayName")
    role: str
    status: str


class AdminUserPage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[AdminUserListResponse]
    page: int
    page_size: int = Field(alias="pageSize")
    total_items: int = Field(alias="totalItems")
    total_pages: int = Field(alias="totalPages")


class AdminCreatorResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    display_name: str = Field(alias="displayName")


class AdminJobDescriptionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    organization_id: UUID = Field(alias="organizationId")
    title: str
    source_type: str = Field(alias="sourceType")
    source_format: str | None = Field(alias="sourceFormat")
    created_at: datetime = Field(alias="createdAt")
    created_by: AdminCreatorResponse = Field(alias="createdBy")


class AdminJobDescriptionPage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[AdminJobDescriptionResponse]
    page: int
    page_size: int = Field(alias="pageSize")
    total_items: int = Field(alias="totalItems")
    total_pages: int = Field(alias="totalPages")


class CreateOrganizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=100)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    name: str
    slug: str
    status: EntityStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class OrganizationListResponse(BaseModel):
    items: list[OrganizationResponse]


class ChangeRoleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Role


class ChangeStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: EntityStatus


class DomainMappingStatus(StrEnum):
    ACTIVE = "ACTIVE"
    REMOVED = "REMOVED"


class CreateDomainMappingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    domain: str = Field(min_length=1, max_length=253)
    organization_id: UUID = Field(alias="organizationId")


class ReassignDomainMappingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    organization_id: UUID = Field(alias="organizationId")


class DomainMappingResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    domain: str
    organization_id: UUID = Field(alias="organizationId")
    status: DomainMappingStatus
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    removed_at: datetime | None = Field(alias="removedAt")


class DomainMappingListResponse(BaseModel):
    items: list[DomainMappingResponse]


def _mapping_response(mapping: OrganizationDomainMapping) -> DomainMappingResponse:
    return DomainMappingResponse(
        id=mapping.id,
        domain=mapping.normalized_domain,
        organizationId=mapping.org_id,
        status=(
            DomainMappingStatus.REMOVED
            if mapping.removed_at is not None
            else DomainMappingStatus.ACTIVE
        ),
        createdAt=mapping.created_at,
        updatedAt=mapping.updated_at,
        removedAt=mapping.removed_at,
    )


def _validate_csrf(request: Request, context: AuthenticatedRequest) -> None:
    csrf_policy: CsrfPolicy = request.app.state.csrf_policy
    csrf_policy.validate(
        origin=request.headers.get("Origin", ""),
        cookie_token=request.cookies.get("mi_csrf", ""),
        header_token=request.headers.get("X-CSRF-Token", ""),
        expected_digest=context.authentication_session.csrf_token_digest,
    )


async def _response(context: AuthenticatedRequest, user_id: UUID) -> AdminUserResponse:
    user = await context.session.get(User, user_id)
    if user is None:
        raise RuntimeError("Mutated user disappeared")
    candidate_profile_id = await context.session.scalar(
        select(CandidateProfile.id).where(CandidateProfile.user_id == user.id)
    )
    return AdminUserResponse(
        id=user.id,
        organizationId=user.org_id,
        email=user.email,
        displayName=user.display_name,
        role=user.role,
        status=user.status,
        candidateProfileId=candidate_profile_id,
        profilePictureUrl=user.profile_picture_url,
    )


def _user_list_response(user: User) -> AdminUserListResponse:
    return AdminUserListResponse(
        id=user.id,
        organizationId=user.org_id,
        email=user.email,
        displayName=user.display_name,
        role=user.role,
        status=user.status,
    )


def _organization_response(organization: Organization) -> OrganizationResponse:
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        status=EntityStatus(organization.status),
        createdAt=organization.created_at,
        updatedAt=organization.updated_at,
    )


async def _user_response(context: AuthenticatedRequest, user: User) -> AdminUserResponse:
    candidate_profile_id = await context.session.scalar(
        select(CandidateProfile.id).where(CandidateProfile.user_id == user.id)
    )
    return AdminUserResponse(
        id=user.id,
        organizationId=user.org_id,
        email=user.email,
        displayName=user.display_name,
        role=user.role,
        status=user.status,
        candidateProfileId=candidate_profile_id,
        profilePictureUrl=user.profile_picture_url,
    )


@router.get("/users", response_model=AdminUserPage)
async def get_users(
    context: Annotated[AuthenticatedRequest, Depends(require_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 25,
) -> AdminUserPage:
    users, total = await list_admin_users(context.session, page=page, page_size=page_size)
    return AdminUserPage(
        items=[_user_list_response(user) for user in users],
        page=page,
        pageSize=page_size,
        totalItems=total,
        totalPages=(total + page_size - 1) // page_size,
    )


@router.get("/organizations", response_model=OrganizationListResponse)
async def get_organizations(
    context: Annotated[AuthenticatedRequest, Depends(require_admin)],
) -> OrganizationListResponse:
    organizations = await list_organizations(context.session)
    return OrganizationListResponse(
        items=[_organization_response(organization) for organization in organizations]
    )


@router.post(
    "/organizations",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_organization(
    payload: CreateOrganizationRequest,
    request: Request,
    context: Annotated[AuthenticatedRequest, Depends(require_admin)],
) -> OrganizationResponse:
    _validate_csrf(request, context)
    now = getattr(request.app.state, "clock", lambda: datetime.now(UTC))()
    organization = await create_organization(
        context.session,
        name=payload.name,
        slug=payload.slug,
        actor_user_id=context.user.id,
        correlation_id=getattr(request.state, "correlation_id", get_correlation_id()),
        now=now,
    )
    return _organization_response(organization)


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user_details(
    user_id: UUID,
    context: Annotated[AuthenticatedRequest, Depends(require_admin)],
) -> AdminUserResponse:
    user = await get_admin_user(context.session, user_id=user_id)
    return await _user_response(context, user)


@router.get("/job-descriptions", response_model=AdminJobDescriptionPage)
async def get_job_descriptions(
    context: Annotated[AuthenticatedRequest, Depends(require_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 25,
) -> AdminJobDescriptionPage:
    items, total = await list_admin_job_descriptions(
        context.session, page=page, page_size=page_size
    )
    return AdminJobDescriptionPage(
        items=[
            AdminJobDescriptionResponse(
                id=item.record.id,
                organizationId=item.record.org_id,
                title=item.record.title,
                sourceType=item.record.source_type,
                sourceFormat=item.record.source_format,
                createdAt=item.record.created_at,
                createdBy=AdminCreatorResponse(
                    id=item.record.created_by_user_id,
                    displayName=item.creator_display_name,
                ),
            )
            for item in items
        ],
        page=page,
        pageSize=page_size,
        totalItems=total,
        totalPages=(total + page_size - 1) // page_size,
    )


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: ProvisionUserRequest,
    request: Request,
    context: Annotated[AuthenticatedRequest, Depends(require_admin)],
) -> AdminUserResponse:
    now = getattr(request.app.state, "clock", lambda: datetime.now(UTC))()
    _validate_csrf(request, context)
    user = await provision_user(
        context.session,
        ProvisionUserInput(
            organization_id=payload.organization_id,
            email=str(payload.email),
            display_name=payload.display_name,
            role=payload.role,
            active=payload.status is EntityStatus.ACTIVE,
        ),
        now=now,
        actor_user_id=context.user.id,
        correlation_id=getattr(request.state, "correlation_id", get_correlation_id()),
    )
    return await _response(context, user.id)


@router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
async def update_role(
    user_id: UUID,
    payload: ChangeRoleRequest,
    request: Request,
    context: Annotated[AuthenticatedRequest, Depends(require_admin)],
) -> AdminUserResponse:
    _validate_csrf(request, context)
    now = getattr(request.app.state, "clock", lambda: datetime.now(UTC))()
    user = await change_user_role(
        context.session,
        user_id=user_id,
        role=payload.role,
        actor_user_id=context.user.id,
        correlation_id=getattr(request.state, "correlation_id", get_correlation_id()),
        now=now,
    )
    return await _response(context, user.id)


@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
async def update_status(
    user_id: UUID,
    payload: ChangeStatusRequest,
    request: Request,
    context: Annotated[AuthenticatedRequest, Depends(require_admin)],
) -> AdminUserResponse:
    _validate_csrf(request, context)
    now = getattr(request.app.state, "clock", lambda: datetime.now(UTC))()
    user = await change_user_status(
        context.session,
        user_id=user_id,
        status=payload.status,
        actor_user_id=context.user.id,
        correlation_id=getattr(request.state, "correlation_id", get_correlation_id()),
        now=now,
    )
    return await _response(context, user.id)


@router.get(
    "/organization-domain-mappings",
    response_model=DomainMappingListResponse,
)
async def get_domain_mappings(
    context: Annotated[AuthenticatedRequest, Depends(require_domain_mapping_admin)],
    include_removed: bool = False,
) -> DomainMappingListResponse:
    mappings = await list_domain_mappings(context.session, include_removed=include_removed)
    return DomainMappingListResponse(items=[_mapping_response(item) for item in mappings])


@router.post(
    "/organization-domain-mappings",
    response_model=DomainMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_domain_mapping(
    payload: CreateDomainMappingRequest,
    request: Request,
    context: Annotated[AuthenticatedRequest, Depends(require_domain_mapping_admin)],
) -> DomainMappingResponse:
    _validate_csrf(request, context)
    now = getattr(request.app.state, "clock", lambda: datetime.now(UTC))()
    mapping = await create_domain_mapping(
        context.session,
        domain=payload.domain,
        organization_id=payload.organization_id,
        actor_user_id=context.user.id,
        correlation_id=getattr(request.state, "correlation_id", get_correlation_id()),
        now=now,
    )
    return _mapping_response(mapping)


@router.patch(
    "/organization-domain-mappings/{mapping_id}",
    response_model=DomainMappingResponse,
)
async def patch_domain_mapping(
    mapping_id: UUID,
    payload: ReassignDomainMappingRequest,
    request: Request,
    context: Annotated[AuthenticatedRequest, Depends(require_domain_mapping_admin)],
) -> DomainMappingResponse:
    _validate_csrf(request, context)
    now = getattr(request.app.state, "clock", lambda: datetime.now(UTC))()
    coordinator = getattr(
        request.app.state,
        "candidate_tenant_migration_coordinator",
        CandidateTenantMigrationCoordinator(),
    )
    mapping = await reassign_domain_mapping(
        context.session,
        mapping_id=mapping_id,
        target_organization_id=payload.organization_id,
        coordinator=coordinator,
        actor_user_id=context.user.id,
        correlation_id=getattr(request.state, "correlation_id", get_correlation_id()),
        now=now,
    )
    return _mapping_response(mapping)


@router.delete(
    "/organization-domain-mappings/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_domain_mapping(
    mapping_id: UUID,
    request: Request,
    context: Annotated[AuthenticatedRequest, Depends(require_domain_mapping_admin)],
) -> Response:
    _validate_csrf(request, context)
    now = getattr(request.app.state, "clock", lambda: datetime.now(UTC))()
    await remove_domain_mapping(
        context.session,
        mapping_id=mapping_id,
        actor_user_id=context.user.id,
        correlation_id=getattr(request.state, "correlation_id", get_correlation_id()),
        now=now,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
