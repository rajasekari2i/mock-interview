"""Typed relational model for authentication, sessions, and safe audit history."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Role(StrEnum):
    CANDIDATE = "CANDIDATE"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class EntityStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class RevocationReason(StrEnum):
    LOGOUT_ALL = "LOGOUT_ALL"
    ROLE_CHANGED = "ROLE_CHANGED"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    ABSOLUTE_EXPIRED = "ABSOLUTE_EXPIRED"
    IDLE_EXPIRED = "IDLE_EXPIRED"
    SECURITY_REVOKED = "SECURITY_REVOKED"
    DOMAIN_MAPPING_REMOVED = "DOMAIN_MAPPING_REMOVED"
    DOMAIN_MAPPING_REASSIGNED = "DOMAIN_MAPPING_REASSIGNED"


class AuditOutcome(StrEnum):
    SUCCESS = "SUCCESS"
    DENIED = "DENIED"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_organizations_slug"),
        CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="ck_organizations_status"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)


class OrganizationDomainMapping(TimestampMixin, Base):
    __tablename__ = "organization_domain_mappings"
    __table_args__ = (
        Index(
            "uq_organization_domain_mappings_active_domain",
            "normalized_domain",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            name="fk_organization_domain_mappings_organization",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    normalized_domain: Mapped[str] = mapped_column(String(253), nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("org_id", "normalized_email", name="uq_users_org_normalized_email"),
        UniqueConstraint("id", "org_id", name="uq_users_id_org"),
        CheckConstraint("role IN ('CANDIDATE', 'MANAGER', 'ADMIN')", name="ck_users_role"),
        CheckConstraint("status IN ('ACTIVE', 'DISABLED')", name="ck_users_status"),
        CheckConstraint("auth_generation >= 1", name="ck_users_auth_generation"),
        Index("ix_users_registration_domain_mapping", "registration_domain_mapping_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", name="fk_users_organization"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    normalized_email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    profile_picture_url: Mapped[str | None] = mapped_column(String(2048))
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    auth_generation: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    registration_domain_mapping_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "organization_domain_mappings.id",
            name="fk_users_registration_domain_mapping",
            ondelete="RESTRICT",
        ),
    )


class ExternalLoginIdentity(Base):
    __tablename__ = "external_login_identities"
    __table_args__ = (
        UniqueConstraint("provider", "issuer", "subject", name="uq_external_identity_subject"),
        UniqueConstraint("user_id", "provider", name="uq_external_identity_user_provider"),
        ForeignKeyConstraint(
            ["user_id", "org_id"],
            ["users.id", "users.org_id"],
            name="fk_external_identity_user_org",
            onupdate="CASCADE",
        ),
        CheckConstraint("provider = 'GOOGLE'", name="ck_external_identity_provider"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False, default="GOOGLE")
    issuer: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email_snapshot: Mapped[str | None] = mapped_column(String(320))
    bound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_authenticated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CandidateProfile(TimestampMixin, Base):
    __tablename__ = "candidate_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_candidate_profiles_user"),
        ForeignKeyConstraint(
            ["user_id", "org_id"],
            ["users.id", "users.org_id"],
            name="fk_candidate_profiles_user_org",
            onupdate="CASCADE",
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)


class AuthenticationSession(TimestampMixin, Base):
    __tablename__ = "authentication_sessions"
    __table_args__ = (
        UniqueConstraint("token_digest", name="uq_authentication_sessions_token_digest"),
        ForeignKeyConstraint(
            ["user_id", "org_id"],
            ["users.id", "users.org_id"],
            name="fk_authentication_sessions_user_org",
            onupdate="CASCADE",
        ),
        CheckConstraint(
            "revocation_reason IS NULL OR revocation_reason IN "
            "('LOGOUT_ALL', 'ROLE_CHANGED', 'ACCOUNT_DISABLED', 'ABSOLUTE_EXPIRED', "
            "'IDLE_EXPIRED', 'SECURITY_REVOKED', 'DOMAIN_MAPPING_REMOVED', "
            "'DOMAIN_MAPPING_REASSIGNED')",
            name="ck_authentication_sessions_revocation_reason",
        ),
        Index("ix_authentication_sessions_user_revoked", "user_id", "revoked_at"),
        Index("ix_authentication_sessions_absolute_expires", "absolute_expires_at"),
        Index("ix_authentication_sessions_idle_expires", "idle_expires_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    token_digest: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    csrf_token_digest: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    auth_generation: Mapped[int] = mapped_column(BigInteger, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revocation_reason: Mapped[str | None] = mapped_column(String(40))


class OAuthTransaction(Base):
    __tablename__ = "oauth_transactions"
    __table_args__ = (
        UniqueConstraint("state_digest", name="uq_oauth_transactions_state_digest"),
        Index("ix_oauth_transactions_expires", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    state_digest: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    nonce_digest: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    pkce_verifier_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encryption_key_id: Mapped[str] = mapped_column(String(100), nullable=False)
    return_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("outcome IN ('SUCCESS', 'DENIED')", name="ck_audit_events_outcome"),
        Index("ix_audit_events_org_occurred", "org_id", "occurred_at"),
        Index("ix_audit_events_correlation", "correlation_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("organizations.id", name="fk_audit_events_organization"),
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", name="fk_audit_events_actor")
    )
    target_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", name="fk_audit_events_target")
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(80))
    resource_id: Mapped[str | None] = mapped_column(String(255))
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


SERVICE_INVARIANTS = frozenset(
    {
        "candidate_user_requires_same_org_profile",
        "candidate_role_transition_is_atomic",
        "role_or_disable_revokes_all_sessions",
        "external_identity_first_binding_is_atomic",
        "audit_events_are_append_only",
        "registration_domain_mapping_provenance_is_immutable",
        "candidate_tenant_migration_is_atomic",
    }
)
