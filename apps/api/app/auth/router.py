"""Google login and application-session HTTP routes."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response

from app.auth.audit import append_audit_event
from app.auth.dependencies import AuthenticatedRequest, authenticated_request
from app.auth.errors import AuthError, ErrorCode, callback_error_redirect
from app.auth.google_oidc import GoogleAuthorizationEndpoint, GoogleOIDCProvider
from app.auth.models import AuditOutcome, RevocationReason, Role
from app.auth.oauth_transactions import OAuthTransactionService
from app.auth.service import resolve_or_bind_identity
from app.auth.sessions import create_session, find_session, revoke_all_sessions, token_digest
from app.core.database import Database
from app.core.observability import get_correlation_id, record_login_denial, record_login_success

router = APIRouter(prefix="/auth", tags=["authentication"])


def _frontend_location(request: Request, relative_path: str) -> str:
    origin = request.app.state.frontend_application_origin.rstrip("/")
    return f"{origin}{relative_path}"


@router.post("/logout", status_code=204)
async def global_logout(request: Request) -> Response:
    """End every session for the recognizable user; repeated calls remain safe."""

    database: Database = request.app.state.database
    policy = request.app.state.session_cookie_policy
    csrf_policy = request.app.state.csrf_policy
    session_token = request.cookies.get(policy.name, "")
    csrf_token = request.cookies.get("mi_csrf", "")
    header_token = request.headers.get("X-CSRF-Token", "")
    now = getattr(request.app.state, "clock", lambda: datetime.now(UTC))()
    correlation_id = getattr(request.state, "correlation_id", get_correlation_id())
    async with database.transaction() as session:
        record = await find_session(session, session_token) if session_token else None
        expected_digest = (
            record.csrf_token_digest if record is not None else token_digest(csrf_token)
        )
        csrf_policy.validate(
            origin=request.headers.get("Origin", ""),
            cookie_token=csrf_token,
            header_token=header_token,
            expected_digest=expected_digest,
        )
        if record is not None:
            count = await revoke_all_sessions(
                session,
                user_id=record.user_id,
                reason=RevocationReason.LOGOUT_ALL,
                now=now,
            )
            await append_audit_event(
                session,
                event_type="LOGOUT_ALL",
                outcome=AuditOutcome.SUCCESS,
                reason_code=RevocationReason.LOGOUT_ALL.value,
                correlation_id=correlation_id,
                occurred_at=now,
                org_id=record.org_id,
                actor_user_id=record.user_id,
                target_user_id=record.user_id,
                metadata={"session_count": count},
            )
    response = Response(status_code=204, headers={"Cache-Control": "no-store"})
    response.delete_cookie(policy.name, path="/", secure=policy.options["secure"])
    response.delete_cookie("mi_csrf", path="/", secure=policy.options["secure"])
    return response


@router.get("/google/login", status_code=302)
async def google_login(request: Request, return_path: str = "/") -> RedirectResponse:
    oauth_service: OAuthTransactionService | None = getattr(
        request.app.state, "oauth_transaction_service", None
    )
    if oauth_service is None:
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        challenge = secrets.token_urlsafe(32)
    else:
        database: Database = request.app.state.database
        clock = getattr(request.app.state, "clock", lambda: datetime.now(UTC))
        async with database.transaction() as session:
            transaction = await oauth_service.create(
                session, return_path=return_path, now=clock()
            )
        state, nonce, challenge = (
            transaction.state,
            transaction.nonce,
            transaction.pkce_challenge,
        )
    provider: GoogleOIDCProvider | GoogleAuthorizationEndpoint = request.app.state.google_provider
    if isinstance(provider, GoogleAuthorizationEndpoint):
        location = provider.build_url(
            state=state,
            nonce=nonce,
            pkce_challenge=challenge,
            redirect_uri=request.app.state.google_redirect_uri,
        )
    else:
        location = provider.authorization_url(
            state=state,
            nonce=nonce,
            pkce_challenge=challenge,
            redirect_uri=request.app.state.google_redirect_uri,
        )
    return RedirectResponse(location, status_code=302, headers={"Cache-Control": "no-store"})


@router.get("/google/callback")
async def google_callback(
    request: Request,
    state: str,
    code: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    correlation_id = getattr(request.state, "correlation_id", get_correlation_id())
    if error is not None:
        location = _frontend_location(
            request,
            callback_error_redirect(
                ErrorCode.OAUTH_CANCELLED, correlation_id=correlation_id
            ),
        )
        return RedirectResponse(location, status_code=303, headers={"Cache-Control": "no-store"})
    oauth_service: OAuthTransactionService | None = getattr(
        request.app.state, "oauth_transaction_service", None
    )
    if oauth_service is None or code is None:
        location = _frontend_location(
            request,
            callback_error_redirect(
                ErrorCode.OAUTH_RESPONSE_INVALID, correlation_id=correlation_id
            ),
        )
        return RedirectResponse(location, status_code=303, headers={"Cache-Control": "no-store"})
    database: Database = request.app.state.database
    provider: GoogleOIDCProvider = request.app.state.google_provider
    clock = getattr(request.app.state, "clock", lambda: datetime.now(UTC))
    try:
        async with database.transaction() as session:
            transaction = await oauth_service.consume(session, state=state, now=clock())
            claims = await provider.exchange(
                code=code,
                pkce_verifier=transaction.pkce_verifier,
                expected_nonce_digest=transaction.nonce_digest,
                now=clock(),
            )
            user = await resolve_or_bind_identity(
                session, claims, now=clock(), correlation_id=correlation_id
            )
            created = await create_session(session, user, now=clock())
            await append_audit_event(
                session,
                event_type="LOGIN_SUCCEEDED",
                outcome=AuditOutcome.SUCCESS,
                reason_code="GOOGLE_OIDC_VERIFIED",
                correlation_id=correlation_id,
                occurred_at=clock(),
                org_id=user.org_id,
                actor_user_id=user.id,
                target_user_id=user.id,
                metadata={"provider": "GOOGLE"},
            )
            record_login_success(role=user.role)
        response = RedirectResponse(
            _frontend_location(request, transaction.return_path),
            status_code=303,
            headers={"Cache-Control": "no-store"},
        )
        policy = request.app.state.session_cookie_policy
        response.set_cookie(policy.name, created.token, max_age=28_800, **policy.options)
        response.set_cookie(
            "mi_csrf",
            created.csrf_token,
            max_age=28_800,
            secure=policy.options["secure"],
            httponly=False,
            samesite="lax",
            path="/",
        )
        return response
    except AuthError as auth_error:
        record_login_denial(
            reason=auth_error.code.value,
            provider_failure=auth_error.code is ErrorCode.OAUTH_PROVIDER_UNAVAILABLE,
        )
        async with database.transaction() as audit_session:
            await append_audit_event(
                audit_session,
                event_type="LOGIN_DENIED",
                outcome=AuditOutcome.DENIED,
                reason_code=auth_error.code.value,
                correlation_id=correlation_id,
                occurred_at=clock(),
                metadata={"provider": "GOOGLE"},
            )
        location = _frontend_location(
            request,
            callback_error_redirect(auth_error.code, correlation_id=correlation_id),
        )
        return RedirectResponse(location, status_code=303, headers={"Cache-Control": "no-store"})


@router.get("/me")
async def current_user(
    context: Annotated[AuthenticatedRequest, Depends(authenticated_request)],
) -> dict[str, object]:
    user: dict[str, object] = {
        "id": str(context.user.id),
        "organizationId": str(context.user.org_id),
        "displayName": context.user.display_name,
        "role": context.user.role,
    }
    if context.user.role == Role.CANDIDATE.value:
        user["candidateProfileId"] = str(context.candidate_profile_id)
    return {
        "user": user,
        "session": {
            "absoluteExpiresAt": context.authentication_session.absolute_expires_at.isoformat(),
            "idleExpiresAt": context.authentication_session.idle_expires_at.isoformat(),
        },
    }
