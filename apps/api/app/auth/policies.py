"""Deny-by-default role, organization, ownership, and Manager scope policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.auth.models import Role


class Capability(StrEnum):
    CANDIDATE_VIEW_OWN_PROFILE = "CANDIDATE_VIEW_OWN_PROFILE"
    CANDIDATE_VIEW_OWN_ALLOCATIONS = "CANDIDATE_VIEW_OWN_ALLOCATIONS"
    CANDIDATE_JOIN_OWN_INTERVIEW = "CANDIDATE_JOIN_OWN_INTERVIEW"
    MANAGER_UPLOAD_JD = "MANAGER_UPLOAD_JD"
    MANAGER_ALLOCATE_INTERVIEW = "MANAGER_ALLOCATE_INTERVIEW"
    MANAGER_VIEW_ALLOCATION_CANDIDATE = "MANAGER_VIEW_ALLOCATION_CANDIDATE"
    MANAGER_VIEW_MANAGED_READINESS = "MANAGER_VIEW_MANAGED_READINESS"
    ADMIN_MANAGE_USERS = "ADMIN_MANAGE_USERS"
    ADMIN_MANAGE_DOMAIN_MAPPINGS = "ADMIN_MANAGE_DOMAIN_MAPPINGS"
    ADMIN_MANAGE_APPLICATION = "ADMIN_MANAGE_APPLICATION"
    ADMIN_VIEW_ALL_REPORTS = "ADMIN_VIEW_ALL_REPORTS"


@dataclass(frozen=True)
class AuthContext:
    user_id: UUID
    org_id: UUID
    role: Role
    candidate_profile_id: UUID | None


@dataclass(frozen=True)
class ResourceScope:
    org_id: UUID
    capability: Capability
    candidate_owner_user_id: UUID | None = None
    allocating_manager_user_id: UUID | None = None
    managing_manager_user_id: UUID | None = None
    resource_id: str | None = None


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    reason: str


_CANDIDATE_CAPABILITIES = frozenset(
    {
        Capability.CANDIDATE_VIEW_OWN_PROFILE,
        Capability.CANDIDATE_VIEW_OWN_ALLOCATIONS,
        Capability.CANDIDATE_JOIN_OWN_INTERVIEW,
    }
)
_MANAGER_CAPABILITIES = frozenset(
    {
        Capability.MANAGER_UPLOAD_JD,
        Capability.MANAGER_ALLOCATE_INTERVIEW,
        Capability.MANAGER_VIEW_ALLOCATION_CANDIDATE,
        Capability.MANAGER_VIEW_MANAGED_READINESS,
    }
)
_ROLE_CAPABILITIES = {
    Role.CANDIDATE: _CANDIDATE_CAPABILITIES,
    Role.MANAGER: _MANAGER_CAPABILITIES,
    Role.ADMIN: frozenset(Capability),
}


def authorize(
    context: AuthContext | None, scope: ResourceScope
) -> AuthorizationDecision:
    if context is None:
        return AuthorizationDecision(False, "AUTHENTICATION_REQUIRED")
    if context.org_id != scope.org_id:
        return AuthorizationDecision(False, "ORGANIZATION_MISMATCH")
    if scope.capability not in _ROLE_CAPABILITIES[context.role]:
        return AuthorizationDecision(False, "CAPABILITY_DENIED")
    if context.role is Role.ADMIN:
        return AuthorizationDecision(True, "ALLOWED")
    if scope.capability in _CANDIDATE_CAPABILITIES:
        if (
            context.candidate_profile_id is None
            or scope.candidate_owner_user_id is None
            or scope.candidate_owner_user_id != context.user_id
        ):
            return AuthorizationDecision(False, "CANDIDATE_OWNERSHIP_MISMATCH")
    if scope.capability is Capability.MANAGER_VIEW_ALLOCATION_CANDIDATE and (
        scope.allocating_manager_user_id is None
        or scope.allocating_manager_user_id != context.user_id
    ):
        return AuthorizationDecision(False, "ALLOCATION_MANAGER_MISMATCH")
    if scope.capability is Capability.MANAGER_VIEW_MANAGED_READINESS and (
        scope.managing_manager_user_id is None
        or scope.managing_manager_user_id != context.user_id
    ):
        return AuthorizationDecision(False, "MANAGING_MANAGER_MISMATCH")
    return AuthorizationDecision(True, "ALLOWED")
