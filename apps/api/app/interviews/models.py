"""Atomic Candidate allocation and Manager scheduling persistence."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.auth.models import Base, TimestampMixin


class InterviewStatus(StrEnum):
    SCHEDULED = "SCHEDULED"


class ScheduledInterview(TimestampMixin, Base):
    __tablename__ = "scheduled_interviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["candidate_user_id", "org_id"],
            ["users.id", "users.org_id"],
            name="fk_scheduled_interviews_candidate_org",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["scheduling_manager_user_id", "org_id"],
            ["users.id", "users.org_id"],
            name="fk_scheduled_interviews_manager_org",
            ondelete="RESTRICT",
            onupdate="RESTRICT",
        ),
        ForeignKeyConstraint(
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
        UniqueConstraint(
            "scheduling_manager_user_id",
            "idempotency_key_digest",
            name="uq_scheduled_interviews_manager_idempotency",
        ),
        CheckConstraint("status = 'SCHEDULED'", name="ck_scheduled_interviews_status"),
        CheckConstraint(
            "octet_length(idempotency_key_digest) = 32",
            name="ck_scheduled_interviews_idempotency_digest_length",
        ),
        CheckConstraint(
            "octet_length(request_fingerprint) = 32",
            name="ck_scheduled_interviews_fingerprint_length",
        ),
        Index(
            "ix_scheduled_interviews_candidate_scheduled_id",
            "candidate_user_id",
            text("scheduled_at ASC"),
            text("id ASC"),
        ),
        Index(
            "ix_scheduled_interviews_manager_scheduled_id",
            "scheduling_manager_user_id",
            text("scheduled_at ASC"),
            text("id ASC"),
        ),
        Index(
            "ix_scheduled_interviews_org_scheduled_id",
            "org_id",
            text("scheduled_at ASC"),
            text("id ASC"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            name="fk_scheduled_interviews_organization",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    candidate_user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    job_description_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    scheduling_manager_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    idempotency_key_digest: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    request_fingerprint: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
