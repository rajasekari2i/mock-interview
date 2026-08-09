from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from app.admin import router as admin_router
from app.auth import dependencies
from app.auth import router as auth_router
from app.auth.dependencies import AuthenticatedRequest
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import EntityStatus, Role
from app.main import create_app
from starlette.requests import Request


class _Database:
    def __init__(self, session: object) -> None:
        self.session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[object]:
        yield self.session


def _request(app: object, *, cookie: str = "") -> Request:
    headers = [(b"origin", b"http://localhost:5173")]
    if cookie:
        headers.append((b"cookie", cookie.encode()))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
            "app": app,
            "state": {},
        }
    )


@pytest.mark.asyncio
async def test_admin_async_response_and_mapping_route_returns_are_covered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 8, 9, 9, 0, tzinfo=UTC)
    organization_id = UUID(int=1)
    user_id = UUID(int=2)
    mapping_id = UUID(int=3)
    user = SimpleNamespace(
        id=user_id,
        org_id=organization_id,
        email="admin@example.test",
        display_name="Admin",
        role=Role.ADMIN.value,
        status=EntityStatus.ACTIVE.value,
    )
    session = AsyncMock()
    session.get.return_value = user
    session.scalar.return_value = None
    response = await admin_router._response(
        AuthenticatedRequest(session, user, SimpleNamespace(csrf_token_digest=b"digest"), None),
        user_id,
    )
    assert response.id == user_id

    mapping = SimpleNamespace(
        id=mapping_id,
        normalized_domain="example.test",
        org_id=organization_id,
        removed_at=None,
        created_at=now,
        updated_at=now,
    )
    app = create_app(testing=True)
    app.state.clock = lambda: now
    request = _request(app)
    context = AuthenticatedRequest(
        session, user, SimpleNamespace(csrf_token_digest=b"digest"), None
    )
    monkeypatch.setattr(admin_router, "_validate_csrf", Mock())
    monkeypatch.setattr(admin_router, "list_domain_mappings", AsyncMock(return_value=[mapping]))
    monkeypatch.setattr(admin_router, "create_domain_mapping", AsyncMock(return_value=mapping))
    monkeypatch.setattr(admin_router, "reassign_domain_mapping", AsyncMock(return_value=mapping))
    monkeypatch.setattr(admin_router, "remove_domain_mapping", AsyncMock(return_value=mapping))

    listed = await admin_router.get_domain_mappings(context, include_removed=False)
    created = await admin_router.post_domain_mapping(
        admin_router.CreateDomainMappingRequest(
            domain="example.test", organizationId=organization_id
        ),
        request,
        context,
    )
    reassigned = await admin_router.patch_domain_mapping(
        mapping_id,
        admin_router.ReassignDomainMappingRequest(organizationId=organization_id),
        request,
        context,
    )
    removed = await admin_router.delete_domain_mapping(mapping_id, request, context)
    assert listed.items[0].id == created.id == reassigned.id == mapping_id
    assert removed.status_code == 204


@pytest.mark.asyncio
async def test_candidate_dependency_resolves_profile_and_fails_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(testing=True)
    session = AsyncMock()
    app.state.database = _Database(session)
    user = SimpleNamespace(id=UUID(int=4), role=Role.CANDIDATE.value)
    auth_session = SimpleNamespace()
    monkeypatch.setattr(
        dependencies, "resolve_session", AsyncMock(return_value=(auth_session, user))
    )
    profile_id = UUID(int=5)
    session.scalar.return_value = profile_id
    generator = dependencies.authenticated_request(_request(app, cookie="mi_session_test=token"))
    context = await anext(generator)
    assert context.candidate_profile_id == profile_id
    await generator.aclose()

    session.scalar.return_value = None
    missing = dependencies.authenticated_request(_request(app, cookie="mi_session_test=token"))
    with pytest.raises(AuthError) as profile_error:
        await anext(missing)
    assert profile_error.value.code is ErrorCode.CANDIDATE_PROFILE_CONFLICT

    user.role = Role.MANAGER.value
    manager = dependencies.authenticated_request(
        _request(app, cookie="mi_session_test=token")
    )
    manager_context = await anext(manager)
    assert manager_context.candidate_profile_id is None
    await manager.aclose()


@pytest.mark.asyncio
async def test_mapping_admin_denial_returns_only_after_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_app(testing=True)
    audit_session = AsyncMock()
    app.state.database = _Database(audit_session)
    user = SimpleNamespace(id=UUID(int=6), org_id=UUID(int=7), role=Role.CANDIDATE.value)
    context = AuthenticatedRequest(AsyncMock(), user, SimpleNamespace(), UUID(int=8))
    audited = AsyncMock()
    monkeypatch.setattr(dependencies, "append_authorization_denial", audited)
    with pytest.raises(AuthError) as denied:
        await dependencies.require_domain_mapping_admin(_request(app), context)
    assert denied.value.code is ErrorCode.FORBIDDEN
    audited.assert_awaited_once()


@pytest.mark.asyncio
async def test_logout_and_callback_complete_after_async_boundaries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 8, 9, 9, 0, tzinfo=UTC)
    app = create_app(testing=True)
    session = AsyncMock()
    app.state.database = _Database(session)
    app.state.clock = lambda: now
    csrf_validate = Mock()
    app.state.csrf_policy = SimpleNamespace(validate=csrf_validate)
    logout_request = _request(app, cookie="mi_session_test=session-token; mi_csrf=csrf-token")
    monkeypatch.setattr(auth_router, "find_session", AsyncMock(return_value=None))
    logout = await auth_router.global_logout(logout_request)
    assert logout.status_code == 204
    csrf_validate.assert_called_once()

    record = SimpleNamespace(
        csrf_token_digest=b"digest", user_id=UUID(int=11), org_id=UUID(int=12)
    )
    monkeypatch.setattr(auth_router, "find_session", AsyncMock(return_value=record))
    revoke = AsyncMock(return_value=2)
    audit = AsyncMock()
    monkeypatch.setattr(auth_router, "revoke_all_sessions", revoke)
    monkeypatch.setattr(auth_router, "append_audit_event", audit)
    repeated_logout = await auth_router.global_logout(logout_request)
    assert repeated_logout.status_code == 204
    revoke.assert_awaited_once()
    audit.assert_awaited_once()

    transaction = SimpleNamespace(
        pkce_verifier="verifier", nonce_digest=b"nonce", return_path="/candidate"
    )
    oauth_service = SimpleNamespace(consume=AsyncMock(return_value=transaction))
    provider = SimpleNamespace(exchange=AsyncMock(return_value=SimpleNamespace()))
    app.state.oauth_transaction_service = oauth_service
    app.state.google_provider = provider
    app.state.frontend_application_origin = "http://localhost:5173"
    user = SimpleNamespace(id=UUID(int=9), org_id=UUID(int=10), role=Role.CANDIDATE.value)
    created = SimpleNamespace(**{"token": "test-session", "csrf_token": "test-csrf"})
    monkeypatch.setattr(auth_router, "resolve_or_bind_identity", AsyncMock(return_value=user))
    monkeypatch.setattr(auth_router, "create_session", AsyncMock(return_value=created))
    monkeypatch.setattr(auth_router, "append_audit_event", AsyncMock())
    success_metric = Mock()
    monkeypatch.setattr(auth_router, "record_login_success", success_metric)
    callback = await auth_router.google_callback(_request(app), state="state", code="code")
    assert callback.status_code == 303
    assert callback.headers["location"] == "http://localhost:5173/candidate"
    provider.exchange.assert_awaited_once()
    success_metric.assert_called_once_with(role=Role.CANDIDATE.value)
