from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from app.auth.models import Base
from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.engine import Engine

EXPECTED_TABLES = {
    "organizations",
    "users",
    "external_login_identities",
    "candidate_profiles",
    "authentication_sessions",
    "oauth_transactions",
    "audit_events",
    "organization_domain_mappings",
    "job_descriptions",
    "scheduled_interviews",
}

EXPECTED_CONSTRAINTS = {
    "ck_organizations_status",
    "uq_organizations_slug",
    "ck_users_role",
    "ck_users_status",
    "uq_users_org_normalized_email",
    "uq_users_id_org",
    "uq_external_identity_subject",
    "uq_external_identity_user_provider",
    "fk_external_identity_user_org",
    "uq_candidate_profiles_user",
    "fk_candidate_profiles_user_org",
    "uq_authentication_sessions_token_digest",
    "fk_authentication_sessions_user_org",
    "ck_authentication_sessions_revocation_reason",
    "fk_users_registration_domain_mapping",
    "uq_oauth_transactions_state_digest",
    "ck_audit_events_outcome",
    "fk_job_descriptions_organization",
    "fk_job_descriptions_creator_org",
    "uq_job_descriptions_id_org",
    "uq_job_descriptions_id_creator_org",
    "ck_job_descriptions_source_type",
    "ck_job_descriptions_source_shape",
    "ck_job_descriptions_title_nonblank",
    "ck_job_descriptions_content_nonblank",
    "fk_scheduled_interviews_organization",
    "fk_scheduled_interviews_candidate_org",
    "fk_scheduled_interviews_manager_org",
    "fk_scheduled_interviews_owned_jd",
    "uq_scheduled_interviews_manager_idempotency",
    "ck_scheduled_interviews_status",
    "ck_scheduled_interviews_idempotency_digest_length",
    "ck_scheduled_interviews_fingerprint_length",
}

EXPECTED_INDEXES = {
    "ix_authentication_sessions_user_revoked",
    "ix_authentication_sessions_absolute_expires",
    "ix_authentication_sessions_idle_expires",
    "ix_oauth_transactions_expires",
    "ix_audit_events_org_occurred",
    "ix_audit_events_correlation",
    "uq_organization_domain_mappings_active_domain",
    "ix_users_registration_domain_mapping",
    "ix_job_descriptions_creator_created_id",
    "ix_job_descriptions_org_created_id",
    "ix_job_descriptions_created_id",
    "ix_scheduled_interviews_candidate_scheduled_id",
    "ix_scheduled_interviews_manager_scheduled_id",
    "ix_scheduled_interviews_org_scheduled_id",
}


def test_metadata_contains_all_authentication_tables_and_named_constraints() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES

    constraint_names = {
        constraint.name
        for table in Base.metadata.tables.values()
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint | ForeignKeyConstraint | UniqueConstraint)
        and constraint.name is not None
    }
    index_names = {
        index.name
        for table in Base.metadata.tables.values()
        for index in table.indexes
        if isinstance(index, Index) and index.name is not None
    }

    assert EXPECTED_CONSTRAINTS <= constraint_names
    assert EXPECTED_INDEXES <= index_names


def test_secret_bearing_columns_store_only_digests_or_ciphertext() -> None:
    sessions = Base.metadata.tables["authentication_sessions"].columns
    transactions = Base.metadata.tables["oauth_transactions"].columns

    assert "token" not in sessions
    assert "csrf_token" not in sessions
    assert sessions["token_digest"].nullable is False
    assert sessions["csrf_token_digest"].nullable is False
    assert "state" not in transactions
    assert "nonce" not in transactions
    assert transactions["state_digest"].nullable is False
    assert transactions["nonce_digest"].nullable is False
    assert transactions["pkce_verifier_ciphertext"].nullable is False


def test_registration_provenance_is_nullable_and_tenant_children_cascade() -> None:
    users = Base.metadata.tables["users"]
    assert users.columns["registration_domain_mapping_id"].nullable is True
    expected = {
        "fk_candidate_profiles_user_org",
        "fk_external_identity_user_org",
        "fk_authentication_sessions_user_org",
    }
    for table_name in (
        "candidate_profiles",
        "external_login_identities",
        "authentication_sessions",
    ):
        constraint = next(
            item
            for item in Base.metadata.tables[table_name].foreign_key_constraints
            if item.name in expected
        )
        assert constraint.onupdate == "CASCADE"


def test_feature_columns_are_present_and_old_role_check_is_removed() -> None:
    users = Base.metadata.tables["users"]
    assert users.columns["profile_picture_url"].nullable is True
    assert "ck_users_registration_mapping_candidate" not in {
        constraint.name for constraint in users.constraints
    }


@pytest.fixture
def migrated_engine() -> Iterator[Engine]:
    database_url = os.environ["TEST_DATABASE_URL"]
    config = Config("apps/api/alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(database_url)
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        command.upgrade(config, "head")


@pytest.mark.integration
def test_migration_round_trips_and_recovers_forward(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)

    assert EXPECTED_TABLES <= set(inspector.get_table_names())
    assert {item["name"] for item in inspector.get_unique_constraints("users")} >= {
        "uq_users_org_normalized_email",
        "uq_users_id_org",
    }
    assert {
        item["name"] for item in inspector.get_unique_constraints("external_login_identities")
    } >= {
        "uq_external_identity_subject",
        "uq_external_identity_user_provider",
    }
    assert {item["name"] for item in inspector.get_unique_constraints("candidate_profiles")} >= {
        "uq_candidate_profiles_user"
    }
    assert {
        item["name"] for item in inspector.get_unique_constraints("authentication_sessions")
    } >= {"uq_authentication_sessions_token_digest"}
    assert {item["name"] for item in inspector.get_unique_constraints("oauth_transactions")} >= {
        "uq_oauth_transactions_state_digest"
    }
    with migrated_engine.connect() as connection:
        default_organization = connection.execute(
            text("SELECT name, slug, status FROM organizations WHERE slug = 'ideas2it'")
        ).one()
        default_mapping = connection.execute(
            text(
                "SELECT m.normalized_domain, o.slug "
                "FROM organization_domain_mappings m "
                "JOIN organizations o ON o.id = m.org_id "
                "WHERE m.normalized_domain = 'ideas2it.com' "
                "AND m.removed_at IS NULL"
            )
        ).one()
    assert default_organization == ("ideas2it", "ideas2it", "ACTIVE")
    assert default_mapping == ("ideas2it.com", "ideas2it")


@pytest.mark.integration
def test_populated_001_upgrade_preserves_users_and_cascades_tenant_children() -> None:
    database_url = os.environ["TEST_DATABASE_URL"]
    config = Config("apps/api/alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "001")
    engine = create_engine(database_url)
    now = datetime(2026, 8, 9, tzinfo=UTC)
    source_org_id = UUID(int=1)
    target_org_id = UUID(int=2)
    user_id = UUID(int=3)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO organizations "
                    "(id, name, slug, status, created_at, updated_at) VALUES "
                    "(:source, 'Source', 'source', 'ACTIVE', :now, :now), "
                    "(:target, 'Target', 'target', 'ACTIVE', :now, :now)"
                ),
                {"source": source_org_id, "target": target_org_id, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO users (id, org_id, email, normalized_email, display_name, "
                    "role, status, auth_generation, created_at, updated_at) VALUES "
                    "(:user, :org, 'candidate@example.test', 'candidate@example.test', "
                    "'Candidate', 'CANDIDATE', 'ACTIVE', 1, :now, :now)"
                ),
                {"user": user_id, "org": source_org_id, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO candidate_profiles "
                    "(id, org_id, user_id, created_at, updated_at) "
                    "VALUES (:id, :org, :user, :now, :now)"
                ),
                {"id": UUID(int=4), "org": source_org_id, "user": user_id, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO external_login_identities "
                    "(id, org_id, user_id, provider, issuer, subject, email_snapshot, "
                    "bound_at, last_authenticated_at) VALUES "
                    "(:id, :org, :user, 'GOOGLE', 'https://accounts.google.com', "
                    "'subject', 'candidate@example.test', :now, :now)"
                ),
                {"id": UUID(int=5), "org": source_org_id, "user": user_id, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO authentication_sessions "
                    "(id, org_id, user_id, token_digest, csrf_token_digest, auth_generation, "
                    "last_activity_at, absolute_expires_at, idle_expires_at, revoked_at, "
                    "revocation_reason, created_at, updated_at) VALUES "
                    "(:id, :org, :user, :token, :csrf, 1, :now, :absolute, :idle, NULL, NULL, "
                    ":now, :now)"
                ),
                {
                    "id": UUID(int=6),
                    "org": source_org_id,
                    "user": user_id,
                    "token": b"t" * 32,
                    "csrf": b"c" * 32,
                    "now": now,
                    "absolute": now + timedelta(hours=8),
                    "idle": now + timedelta(hours=2),
                },
            )
        command.upgrade(config, "head")
        with engine.begin() as connection:
            provenance = connection.scalar(
                text("SELECT registration_domain_mapping_id FROM users WHERE id = :user"),
                {"user": user_id},
            )
            assert provenance is None
            connection.execute(
                text("UPDATE users SET org_id = :target WHERE id = :user"),
                {"target": target_org_id, "user": user_id},
            )
            for table_name in (
                "candidate_profiles",
                "external_login_identities",
                "authentication_sessions",
            ):
                child_org = connection.scalar(
                    text(f"SELECT org_id FROM {table_name} WHERE user_id = :user"),  # noqa: S608
                    {"user": user_id},
                )
                assert child_org == target_org_id
    finally:
        engine.dispose()
        command.downgrade(config, "base")
        command.upgrade(config, "head")
