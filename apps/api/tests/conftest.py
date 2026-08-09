from __future__ import annotations

import hashlib
import os
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from app.auth.google_oidc import GoogleClaims
from app.auth.models import (
    AuthenticationSession,
    CandidateProfile,
    EntityStatus,
    Organization,
    OrganizationDomainMapping,
    Role,
    User,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://mockinterview:local-development-only@localhost:5432/mockinterview",
)


@dataclass
class FrozenClock:
    current: datetime = datetime(2026, 8, 9, 9, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.current

    def advance(self, **delta: float) -> None:
        self.current += timedelta(**delta)


@dataclass(frozen=True)
class FakeGoogleClaims:
    issuer: str = "https://accounts.google.com"
    subject: str = "google-subject-1"
    audience: str = "test-client"
    email: str = "candidate@example.test"
    email_verified: bool = True
    nonce: str = "expected-nonce"
    expires_at: datetime = datetime(2026, 8, 9, 9, 5, tzinfo=UTC)
    name: object = "Test Candidate"


@dataclass
class FakeGoogleOIDC:
    claims: FakeGoogleClaims = field(default_factory=FakeGoogleClaims)
    provider_error: Exception | None = None
    exchanged_verifier: str | None = None

    def authorization_url(
        self, *, state: str, nonce: str, pkce_challenge: str, redirect_uri: str
    ) -> str:
        del nonce, pkce_challenge
        return f"{redirect_uri}?fake_state={state}"

    async def exchange(
        self,
        *,
        code: str,
        pkce_verifier: str,
        expected_nonce_digest: bytes,
        now: datetime,
    ) -> GoogleClaims:
        del code, now
        self.exchanged_verifier = pkce_verifier
        if self.provider_error is not None:
            raise self.provider_error
        if hashlib.sha256(self.claims.nonce.encode()).digest() != expected_nonce_digest:
            raise ValueError("Nonce digest mismatch")
        return GoogleClaims(
            self.claims.issuer,
            self.claims.subject,
            self.claims.email,
            self.claims.name if isinstance(self.claims.name, str) else None,
        )


class Factories:
    def __init__(self, clock: FrozenClock) -> None:
        self.clock = clock
        self._sequence = 1

    def uuid(self) -> UUID:
        value = UUID(int=self._sequence)
        self._sequence += 1
        return value

    def organization(self, **overrides: object) -> Organization:
        values: dict[str, object] = {
            "id": self.uuid(),
            "name": "Test Organization",
            "slug": f"test-org-{self._sequence}",
            "status": EntityStatus.ACTIVE.value,
            "created_at": self.clock.now(),
            "updated_at": self.clock.now(),
        }
        values.update(overrides)
        return Organization(**values)

    def user(self, *, organization: Organization, **overrides: object) -> User:
        values: dict[str, object] = {
            "id": self.uuid(),
            "org_id": organization.id,
            "email": f"user-{self._sequence}@example.test",
            "normalized_email": f"user-{self._sequence}@example.test",
            "display_name": "Test User",
            "role": Role.MANAGER.value,
            "status": EntityStatus.ACTIVE.value,
            "auth_generation": 1,
            "created_at": self.clock.now(),
            "updated_at": self.clock.now(),
        }
        values.update(overrides)
        return User(**values)

    def domain_mapping(
        self, *, organization: Organization, **overrides: object
    ) -> OrganizationDomainMapping:
        values: dict[str, object] = {
            "id": self.uuid(),
            "org_id": organization.id,
            "normalized_domain": "example.test",
            "removed_at": None,
            "created_at": self.clock.now(),
            "updated_at": self.clock.now(),
        }
        values.update(overrides)
        return OrganizationDomainMapping(**values)

    def candidate_profile(
        self, *, organization: Organization, user: User, **overrides: object
    ) -> CandidateProfile:
        values: dict[str, object] = {
            "id": self.uuid(),
            "org_id": organization.id,
            "user_id": user.id,
            "created_at": self.clock.now(),
            "updated_at": self.clock.now(),
        }
        values.update(overrides)
        return CandidateProfile(**values)

    def session(
        self, *, organization: Organization, user: User, **overrides: object
    ) -> AuthenticationSession:
        now = self.clock.now()
        values: dict[str, object] = {
            "id": self.uuid(),
            "org_id": organization.id,
            "user_id": user.id,
            "token_digest": bytes([self._sequence % 256]) * 32,
            "csrf_token_digest": bytes([(self._sequence + 1) % 256]) * 32,
            "auth_generation": user.auth_generation,
            "created_at": now,
            "updated_at": now,
            "last_activity_at": now,
            "absolute_expires_at": now + timedelta(hours=8),
            "idle_expires_at": now + timedelta(hours=2),
            "revoked_at": None,
            "revocation_reason": None,
        }
        values.update(overrides)
        return AuthenticationSession(**values)


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock()


@pytest.fixture
def factories(clock: FrozenClock) -> Factories:
    return Factories(clock)


@pytest.fixture
def fake_google_oidc() -> FakeGoogleOIDC:
    return FakeGoogleOIDC()


@pytest.fixture(scope="session")
def migrated_database_url() -> Iterator[str]:
    config = Config("apps/api/alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(config, "head")
    yield TEST_DATABASE_URL


@pytest_asyncio.fixture
async def db_session(migrated_database_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(migrated_database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE audit_events, external_login_identities, candidate_profiles, "
                "authentication_sessions, users, organization_domain_mappings, organizations, "
                "oauth_transactions CASCADE"
            )
        )
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


ClockFactory = Callable[[], datetime]
