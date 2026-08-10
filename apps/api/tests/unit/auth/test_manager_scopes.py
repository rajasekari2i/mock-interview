from __future__ import annotations

from uuid import UUID

from app.auth.models import Role
from app.auth.policies import AuthContext, Capability, ResourceScope, authorize


def test_manager_candidate_data_is_limited_to_allocating_manager() -> None:
    manager = AuthContext(UUID(int=1), UUID(int=10), Role.MANAGER, None)
    own = ResourceScope(
        org_id=UUID(int=10),
        capability=Capability.MANAGER_VIEW_ALLOCATION_CANDIDATE,
        allocating_manager_user_id=manager.user_id,
    )
    other = ResourceScope(
        org_id=UUID(int=10),
        capability=Capability.MANAGER_VIEW_ALLOCATION_CANDIDATE,
        allocating_manager_user_id=UUID(int=2),
    )
    assert authorize(manager, own).allowed
    assert not authorize(manager, other).allowed


def test_manager_readiness_is_limited_to_managing_manager() -> None:
    manager = AuthContext(UUID(int=1), UUID(int=10), Role.MANAGER, None)
    own = ResourceScope(
        org_id=UUID(int=10),
        capability=Capability.MANAGER_VIEW_MANAGED_READINESS,
        managing_manager_user_id=manager.user_id,
    )
    missing = ResourceScope(
        org_id=UUID(int=10), capability=Capability.MANAGER_VIEW_MANAGED_READINESS
    )
    assert authorize(manager, own).allowed
    assert not authorize(manager, missing).allowed
    assert not authorize(
        manager,
        ResourceScope(
            org_id=UUID(int=10),
            capability=Capability.ADMIN_VIEW_ALL_REPORTS,
            managing_manager_user_id=manager.user_id,
        ),
    ).allowed
