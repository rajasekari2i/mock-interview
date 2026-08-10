"""Add profile pictures, job descriptions, and scheduled interviews.

Revision ID: 005
Revises: 004
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("profile_picture_url", sa.String(2048), nullable=True))
    op.drop_constraint("ck_users_registration_mapping_candidate", "users", type_="check")

    op.create_table(
        "job_descriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("source_format", sa.String(10), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_descriptions"),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name="fk_job_descriptions_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id", "org_id"],
            ["users.id", "users.org_id"],
            name="fk_job_descriptions_creator_org",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.UniqueConstraint("id", "org_id", name="uq_job_descriptions_id_org"),
        sa.UniqueConstraint(
            "id",
            "created_by_user_id",
            "org_id",
            name="uq_job_descriptions_id_creator_org",
        ),
        sa.CheckConstraint(
            "source_type IN ('MANUAL', 'UPLOAD')",
            name="ck_job_descriptions_source_type",
        ),
        sa.CheckConstraint(
            "(source_type = 'MANUAL' AND source_format IS NULL) OR "
            "(source_type = 'UPLOAD' AND source_format IN ('PDF', 'DOCX', 'TXT'))",
            name="ck_job_descriptions_source_shape",
        ),
        sa.CheckConstraint("btrim(title) <> ''", name="ck_job_descriptions_title_nonblank"),
        sa.CheckConstraint(
            "btrim(content_text) <> ''", name="ck_job_descriptions_content_nonblank"
        ),
    )
    op.create_index(
        "ix_job_descriptions_creator_created_id",
        "job_descriptions",
        ["created_by_user_id", sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_job_descriptions_org_created_id",
        "job_descriptions",
        ["org_id", sa.text("created_at DESC"), sa.text("id DESC")],
    )
    op.create_index(
        "ix_job_descriptions_created_id",
        "job_descriptions",
        [sa.text("created_at DESC"), sa.text("id DESC")],
    )

    op.create_table(
        "scheduled_interviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("candidate_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_description_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduling_manager_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("idempotency_key_digest", sa.LargeBinary(32), nullable=False),
        sa.Column("request_fingerprint", sa.LargeBinary(32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scheduled_interviews"),
        sa.ForeignKeyConstraint(
            ["org_id"],
            ["organizations.id"],
            name="fk_scheduled_interviews_organization",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_user_id", "org_id"],
            ["users.id", "users.org_id"],
            name="fk_scheduled_interviews_candidate_org",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["scheduling_manager_user_id", "org_id"],
            ["users.id", "users.org_id"],
            name="fk_scheduled_interviews_manager_org",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["job_description_id", "scheduling_manager_user_id", "org_id"],
            [
                "job_descriptions.id",
                "job_descriptions.created_by_user_id",
                "job_descriptions.org_id",
            ],
            name="fk_scheduled_interviews_owned_jd",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        sa.UniqueConstraint(
            "scheduling_manager_user_id",
            "idempotency_key_digest",
            name="uq_scheduled_interviews_manager_idempotency",
        ),
        sa.CheckConstraint("status = 'SCHEDULED'", name="ck_scheduled_interviews_status"),
        sa.CheckConstraint(
            "octet_length(idempotency_key_digest) = 32",
            name="ck_scheduled_interviews_idempotency_digest_length",
        ),
        sa.CheckConstraint(
            "octet_length(request_fingerprint) = 32",
            name="ck_scheduled_interviews_fingerprint_length",
        ),
    )
    op.create_index(
        "ix_scheduled_interviews_candidate_scheduled_id",
        "scheduled_interviews",
        ["candidate_user_id", sa.text("scheduled_at ASC"), sa.text("id ASC")],
    )
    op.create_index(
        "ix_scheduled_interviews_manager_scheduled_id",
        "scheduled_interviews",
        ["scheduling_manager_user_id", sa.text("scheduled_at ASC"), sa.text("id ASC")],
    )
    op.create_index(
        "ix_scheduled_interviews_org_scheduled_id",
        "scheduled_interviews",
        ["org_id", sa.text("scheduled_at ASC"), sa.text("id ASC")],
    )


def downgrade() -> None:
    op.drop_table("scheduled_interviews")
    op.drop_table("job_descriptions")
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "IF EXISTS (SELECT 1 FROM users WHERE registration_domain_mapping_id IS NOT NULL "
            "AND role <> 'CANDIDATE') THEN "
            "RAISE EXCEPTION 'cannot restore candidate-only provenance check'; "
            "END IF; END $$"
        )
    )
    op.create_check_constraint(
        "ck_users_registration_mapping_candidate",
        "users",
        "registration_domain_mapping_id IS NULL OR role = 'CANDIDATE'",
    )
    op.drop_column("users", "profile_picture_url")
