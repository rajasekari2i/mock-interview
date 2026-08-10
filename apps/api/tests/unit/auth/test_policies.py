from __future__ import annotations

from uuid import UUID

import pytest
from app.auth.models import Role
from app.auth.policies import AuthContext, Capability, ResourceScope, authorize

ORG = UUID(int=1)
OTHER_ORG = UUID(int=2)
CANDIDATE = UUID(int=10)
MANAGER = UUID(int=20)
OTHER_MANAGER = UUID(int=21)


def test_role_interview_capabilities_are_explicit() -> None:
    assert {
        "CANDIDATE_VIEW_OWN_INTERVIEWS",
        "MANAGER_VIEW_OWN_JDS",
        "MANAGER_CREATE_JD",
        "MANAGER_VIEW_SCHEDULING_CANDIDATES",
        "MANAGER_SCHEDULE_INTERVIEW",
        "MANAGER_VIEW_OWN_INTERVIEWS",
        "ADMIN_VIEW_USERS",
        "ADMIN_VIEW_JDS",
    } <= {capability.value for capability in Capability}


def test_missing_authentication_context_is_denied() -> None:
    decision = authorize(
        None,
        ResourceScope(ORG, Capability.CANDIDATE_VIEW_OWN_PROFILE),
    )
    assert decision.reason == "AUTHENTICATION_REQUIRED"


def context(role: Role) -> AuthContext:
    user_id = {Role.CANDIDATE: CANDIDATE, Role.MANAGER: MANAGER, Role.ADMIN: UUID(int=30)}[role]
    return AuthContext(
        user_id=user_id,
        org_id=ORG,
        role=role,
        candidate_profile_id=UUID(int=40) if role is Role.CANDIDATE else None,
    )


@pytest.mark.parametrize(
    ("role", "capability"),
    [
        (Role.CANDIDATE, Capability.CANDIDATE_VIEW_OWN_PROFILE),
        (Role.CANDIDATE, Capability.CANDIDATE_VIEW_OWN_ALLOCATIONS),
        (Role.CANDIDATE, Capability.CANDIDATE_JOIN_OWN_INTERVIEW),
        (Role.MANAGER, Capability.MANAGER_UPLOAD_JD),
        (Role.MANAGER, Capability.MANAGER_ALLOCATE_INTERVIEW),
        (Role.ADMIN, Capability.ADMIN_MANAGE_USERS),
        (Role.ADMIN, Capability.ADMIN_MANAGE_APPLICATION),
        (Role.ADMIN, Capability.ADMIN_VIEW_ALL_REPORTS),
        (Role.ADMIN, Capability.ADMIN_MANAGE_DOMAIN_MAPPINGS),
    ],
)
def test_role_capabilities_allow_only_explicit_matrix(role: Role, capability: Capability) -> None:
    scope = ResourceScope(
        org_id=ORG,
        capability=capability,
        candidate_owner_user_id=CANDIDATE,
    )
    assert authorize(context(role), scope).allowed is True


def test_candidate_ownership_and_organization_mismatch_fail_closed() -> None:
    owned = ResourceScope(
        org_id=ORG,
        capability=Capability.CANDIDATE_VIEW_OWN_PROFILE,
        candidate_owner_user_id=CANDIDATE,
    )
    assert authorize(context(Role.CANDIDATE), owned).allowed
    assert not authorize(
        context(Role.CANDIDATE),
        ResourceScope(
            org_id=ORG,
            capability=owned.capability,
            candidate_owner_user_id=UUID(int=99),
        ),
    ).allowed
    assert (
        authorize(
            context(Role.CANDIDATE),
            ResourceScope(
                org_id=OTHER_ORG,
                capability=owned.capability,
                candidate_owner_user_id=CANDIDATE,
            ),
        ).reason
        == "ORGANIZATION_MISMATCH"
    )


@pytest.mark.parametrize("role", Role)
def test_missing_required_scope_never_allows(role: Role) -> None:
    decision = authorize(
        context(role),
        ResourceScope(org_id=ORG, capability=Capability.CANDIDATE_VIEW_OWN_PROFILE),
    )
    assert decision.allowed is (role is Role.ADMIN)


@pytest.mark.parametrize("role", [Role.CANDIDATE, Role.MANAGER])
def test_domain_mapping_management_is_admin_only(role: Role) -> None:
    decision = authorize(
        context(role),
        ResourceScope(org_id=ORG, capability=Capability.ADMIN_MANAGE_DOMAIN_MAPPINGS),
    )
    assert decision.allowed is False
    assert decision.reason == "CAPABILITY_DENIED"
