"""FastAPI application composition."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.admin.router import router as admin_router
from app.auth.errors import AuthError, encode_error
from app.auth.google_oidc import AuthlibGoogleOIDCAdapter, GoogleAuthorizationEndpoint
from app.auth.oauth_transactions import OAuthTransactionService
from app.auth.router import router as auth_router
from app.auth.security import CsrfPolicy, SessionCookiePolicy
from app.core.config import AppEnvironment, Settings
from app.core.database import Database
from app.core.observability import AuthMetricsMiddleware, CorrelationMiddleware, get_correlation_id
from app.core.security_headers import ProtectedResponseHeadersMiddleware
from app.tenancy.coordinator import CandidateTenantMigrationCoordinator


def create_app(*, testing: bool = False, settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="MockInterview Authentication API", version="0.1.0")
    app.state.candidate_tenant_migration_coordinator = CandidateTenantMigrationCoordinator()
    origins = (
        settings.frontend_origins
        if settings is not None
        else (["http://localhost:5173"] if testing else [])
    )
    app.add_middleware(CorrelationMiddleware)
    app.add_middleware(AuthMetricsMiddleware)
    app.add_middleware(ProtectedResponseHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Correlation-ID"],
    )
    if settings is None:
        app.state.session_cookie_policy = SessionCookiePolicy.development("mi_session_test")
        app.state.google_provider = GoogleAuthorizationEndpoint("test-client")
        app.state.google_redirect_uri = "http://localhost:8000/api/v1/auth/google/callback"
        app.state.frontend_application_origin = origins[0]
        app.state.csrf_policy = CsrfPolicy(tuple(origins))
    else:
        app.state.database = Database(settings)
        app.state.session_cookie_policy = (
            SessionCookiePolicy.production()
            if settings.app_env is AppEnvironment.PRODUCTION
            else SessionCookiePolicy.development(settings.session_cookie_name)
        )
        app.state.google_redirect_uri = settings.google_oidc_redirect_uri
        app.state.frontend_application_origin = settings.frontend_application_origin
        app.state.google_provider = AuthlibGoogleOIDCAdapter(
            client_id=settings.google_oidc_client_id,
            client_secret=settings.google_oidc_client_secret,
            issuer=settings.google_oidc_issuer,
            redirect_uri=settings.google_oidc_redirect_uri,
        )
        keys = tuple((item.key_id, item.key) for item in settings.oauth_encryption_keys)
        app.state.oauth_transaction_service = OAuthTransactionService(
            keys,
            allowed_return_paths=settings.allowed_return_paths,
            ttl_seconds=settings.oauth_transaction_ttl_seconds,
        )
        app.state.csrf_policy = CsrfPolicy(tuple(settings.csrf_allowed_origins))

    @app.exception_handler(AuthError)
    async def auth_error_handler(request: Request, error: AuthError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", get_correlation_id())
        status_code, body = encode_error(error, correlation_id=correlation_id)
        return JSONResponse(body, status_code=status_code, headers={"Cache-Control": "no-store"})

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    return app


def build_app() -> FastAPI:
    return create_app(settings=Settings())  # type: ignore[call-arg]
