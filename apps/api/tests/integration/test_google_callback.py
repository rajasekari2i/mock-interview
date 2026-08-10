from __future__ import annotations

import hashlib
from dataclasses import replace

import httpx
import pytest
from app.auth.errors import AuthError, ErrorCode
from app.auth.models import (
    AuthenticationSession,
    CandidateProfile,
    ExternalLoginIdentity,
    OAuthTransaction,
    OrganizationDomainMapping,
    Role,
    User,
)
from app.auth.oauth_transactions import OAuthTransactionService
from app.core.config import AppEnvironment, Settings
from app.main import create_app
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_oauth_transaction_is_encrypted_expiring_and_one_time(
    db_session: AsyncSession, clock: object
) -> None:
    key = Fernet.generate_key().decode()
    service = OAuthTransactionService((("current", key),), allowed_return_paths=("/", "/candidate"))
    created = await service.create(db_session, return_path="/candidate", now=clock.now())
    await db_session.flush()

    consumed = await service.consume(db_session, state=created.state, now=clock.now())
    assert consumed.nonce_digest == hashlib.sha256(created.nonce.encode()).digest()
    assert consumed.pkce_verifier
    assert consumed.return_path == "/candidate"

    with pytest.raises(AuthError) as replay:
        await service.consume(db_session, state=created.state, now=clock.now())
    assert replay.value.code is ErrorCode.OAUTH_RESPONSE_INVALID


@pytest.mark.asyncio
async def test_oauth_return_path_is_allowlisted(db_session: AsyncSession, clock: object) -> None:
    with pytest.raises(ValueError):
        OAuthTransactionService((), allowed_return_paths=("/",))
    service = OAuthTransactionService(
        (("current", Fernet.generate_key().decode()),), allowed_return_paths=("/",)
    )
    with pytest.raises(ValueError):
        await service.create(db_session, return_path="https://attacker.example", now=clock.now())


@pytest.mark.asyncio
async def test_oauth_unknown_key_and_corrupt_ciphertext_fail_closed(
    db_session: AsyncSession, clock: object
) -> None:
    key = Fernet.generate_key().decode()
    service = OAuthTransactionService((("current", key),), allowed_return_paths=("/",))
    unknown = await service.create(db_session, return_path="/", now=clock.now())
    await db_session.flush()
    row = await db_session.scalar(
        select(OAuthTransaction).where(OAuthTransaction.state_digest.is_not(None))
    )
    assert row is not None
    row.encryption_key_id = "removed"
    with pytest.raises(AuthError):
        await service.consume(db_session, state=unknown.state, now=clock.now())

    row.encryption_key_id = "current"
    row.pkce_verifier_ciphertext = b"corrupt"
    with pytest.raises(AuthError):
        await service.consume(db_session, state=unknown.state, now=clock.now())


@pytest.mark.asyncio
async def test_previous_rotation_key_decrypts_existing_transaction(
    db_session: AsyncSession, clock: object
) -> None:
    previous = Fernet.generate_key().decode()
    created = await OAuthTransactionService(
        (("previous", previous),), allowed_return_paths=("/",)
    ).create(db_session, return_path="/", now=clock.now())
    await db_session.flush()
    stored = await db_session.scalar(select(OAuthTransaction))
    assert stored is not None
    assert created.state.encode() not in stored.pkce_verifier_ciphertext
    assert created.nonce.encode() not in stored.pkce_verifier_ciphertext

    rotated = OAuthTransactionService(
        (("current", Fernet.generate_key().decode()), ("previous", previous)),
        allowed_return_paths=("/",),
    )
    consumed = await rotated.consume(db_session, state=created.state, now=clock.now())
    assert consumed.pkce_verifier


@pytest.mark.asyncio
async def test_callback_atomically_binds_identity_creates_session_and_denies_replay(
    db_session: AsyncSession,
    factories: object,
    clock: object,
    fake_google_oidc: object,
    migrated_database_url: str,
) -> None:
    organization = factories.organization()
    mapping = factories.domain_mapping(organization=organization)
    db_session.add_all([organization, mapping])
    await db_session.commit()
    key = Fernet.generate_key().decode()
    provider_credentials = {"google_oidc_client_secret": "test-only"}
    settings = Settings(
        app_env=AppEnvironment.TEST,
        database_url=migrated_database_url,
        google_oidc_client_id="test-client",
        google_oidc_issuer="https://accounts.google.com",
        google_oidc_redirect_uri="http://localhost:8000/api/v1/auth/google/callback",
        oauth_transaction_encryption_keys=f"current={key}",
        oauth_transaction_ttl_seconds=600,
        oauth_return_paths="/",
        session_absolute_seconds=28_800,
        session_idle_seconds=7_200,
        session_cookie_name="mi_session_test",
        session_cookie_secure=False,
        frontend_origins=["http://localhost:5173"],
        csrf_allowed_origins=["http://localhost:5173"],
        frontend_application_origin="http://localhost:5173",
        enable_fake_oidc=True,
        **provider_credentials,
    )
    app = create_app(settings=settings)
    app.state.google_provider = fake_google_oidc
    app.state.clock = clock.now
    async with app.state.database.transaction() as session:
        created = await app.state.oauth_transaction_service.create(
            session, return_path="/", now=clock.now()
        )
    fake_google_oidc.claims = replace(fake_google_oidc.claims, nonce=created.nonce)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=False
    ) as client:
        login = await client.get("/api/v1/auth/google/login", params={"return_path": "/"})
        response = await client.get(
            "/api/v1/auth/google/callback", params={"state": created.state, "code": "code"}
        )
        replay = await client.get(
            "/api/v1/auth/google/callback", params={"state": created.state, "code": "code"}
        )
        async with app.state.database.transaction() as session:
            failed_transaction = await app.state.oauth_transaction_service.create(
                session, return_path="/", now=clock.now()
            )
        fake_google_oidc.provider_error = AuthError(ErrorCode.OAUTH_PROVIDER_UNAVAILABLE)
        provider_failure = await client.get(
            "/api/v1/auth/google/callback",
            params={"state": failed_transaction.state, "code": "code"},
        )

    assert login.status_code == 302
    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:5173/"
    cookies = response.headers.get_list("set-cookie")
    assert any("mi_session_test=" in cookie and "HttpOnly" in cookie for cookie in cookies)
    assert any("mi_csrf=" in cookie and "HttpOnly" not in cookie for cookie in cookies)
    assert replay.status_code == 303
    assert "OAUTH_RESPONSE_INVALID" in replay.headers["location"]
    assert replay.headers["location"].startswith("http://localhost:5173/auth/error?")
    assert "OAUTH_PROVIDER_UNAVAILABLE" in provider_failure.headers["location"]
    async with app.state.database.transaction() as session:
        assert await session.scalar(select(func.count()).select_from(ExternalLoginIdentity)) == 1
        assert await session.scalar(select(func.count()).select_from(AuthenticationSession)) == 1
        assert await session.scalar(select(func.count()).select_from(CandidateProfile)) == 1
        registered = await session.scalar(select(User))
        assert registered is not None
        assert registered.role == Role.CANDIDATE.value
        assert registered.registration_domain_mapping_id == mapping.id
        mapping_count = await session.scalar(
            select(func.count()).select_from(OrganizationDomainMapping)
        )
        assert mapping_count == 1
    await app.state.database.dispose()
