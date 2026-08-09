"""Add controlled Candidate self-registration and tenant reassignment support.

Revision ID: 002
Revises: 001
Create Date: 2026-08-09

Production recovery must use a new forward corrective revision. The downgrade is intended only
for isolated pre-release validation because it removes mapping provenance created after upgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_FOREIGN_KEYS = (
    ("candidate_profiles", "fk_candidate_profiles_user_org"),
    ("external_login_identities", "fk_external_identity_user_org"),
    ("authentication_sessions", "fk_authentication_sessions_user_org"),
)


def _replace_tenant_foreign_keys(*, onupdate: str | None) -> None:
    for table_name, constraint_name in _TENANT_FOREIGN_KEYS:
        op.drop_constraint(constraint_name, table_name, type_="foreignkey")
        op.create_foreign_key(
            constraint_name,
            table_name,
            "users",
            ["user_id", "org_id"],
            ["id", "org_id"],
            onupdate=onupdate,
        )


def _replace_session_revocation_check(*, include_mapping_reasons: bool) -> None:
    op.drop_constraint(
        "ck_authentication_sessions_revocation_reason",
        "authentication_sessions",
        type_="check",
    )
    reasons = (
        "'LOGOUT_ALL', 'ROLE_CHANGED', 'ACCOUNT_DISABLED', 'ABSOLUTE_EXPIRED', "
        "'IDLE_EXPIRED', 'SECURITY_REVOKED'"
    )
    if include_mapping_reasons:
        reasons += ", 'DOMAIN_MAPPING_REMOVED', 'DOMAIN_MAPPING_REASSIGNED'"
    op.create_check_constraint(
        "ck_authentication_sessions_revocation_reason",
        "authentication_sessions",
        f"revocation_reason IS NULL OR revocation_reason IN ({reasons})",
    )


def upgrade() -> None:
    op.create_table(
        "organization_domain_mappings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("normalized_domain", sa.String(length=253), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name="fk_organization_domain_mappings_organization",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_organization_domain_mappings_active_domain",
        "organization_domain_mappings",
        ["normalized_domain"],
        unique=True,
        postgresql_where=sa.text("removed_at IS NULL"),
    )
    op.add_column(
        "users", sa.Column("registration_domain_mapping_id", sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        "fk_users_registration_domain_mapping",
        "users",
        "organization_domain_mappings",
        ["registration_domain_mapping_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_users_registration_mapping_candidate",
        "users",
        "registration_domain_mapping_id IS NULL OR role = 'CANDIDATE'",
    )
    op.create_index(
        "ix_users_registration_domain_mapping",
        "users",
        ["registration_domain_mapping_id"],
        unique=False,
    )
    _replace_tenant_foreign_keys(onupdate="CASCADE")
    _replace_session_revocation_check(include_mapping_reasons=True)


def downgrade() -> None:
    _replace_session_revocation_check(include_mapping_reasons=False)
    _replace_tenant_foreign_keys(onupdate=None)
    op.drop_index("ix_users_registration_domain_mapping", table_name="users")
    op.drop_constraint("ck_users_registration_mapping_candidate", "users", type_="check")
    op.drop_constraint("fk_users_registration_domain_mapping", "users", type_="foreignkey")
    op.drop_column("users", "registration_domain_mapping_id")
    op.drop_index(
        "uq_organization_domain_mappings_active_domain",
        table_name="organization_domain_mappings",
    )
    op.drop_table("organization_domain_mappings")
