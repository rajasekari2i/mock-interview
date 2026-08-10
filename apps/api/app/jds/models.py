"""Tenant-safe Manager-owned job-description persistence."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.auth.models import Base, TimestampMixin


class JobDescriptionSourceType(StrEnum):
    MANUAL = "MANUAL"
    UPLOAD = "UPLOAD"


class JobDescriptionFormat(StrEnum):
    PDF = "PDF"
    DOCX = "DOCX"
    TXT = "TXT"


class JobDescription(TimestampMixin, Base):
    __tablename__ = "job_descriptions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["created_by_user_id", "org_id"],
            ["users.id", "users.org_id"],
            name="fk_job_descriptions_creator_org",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        UniqueConstraint("id", "org_id", name="uq_job_descriptions_id_org"),
        UniqueConstraint(
            "id",
            "created_by_user_id",
            "org_id",
            name="uq_job_descriptions_id_creator_org",
        ),
        CheckConstraint(
            "source_type IN ('MANUAL', 'UPLOAD')",
            name="ck_job_descriptions_source_type",
        ),
        CheckConstraint(
            "(source_type = 'MANUAL' AND source_format IS NULL) OR "
            "(source_type = 'UPLOAD' AND source_format IN ('PDF', 'DOCX', 'TXT'))",
            name="ck_job_descriptions_source_shape",
        ),
        CheckConstraint("btrim(title) <> ''", name="ck_job_descriptions_title_nonblank"),
        CheckConstraint("btrim(content_text) <> ''", name="ck_job_descriptions_content_nonblank"),
        Index(
            "ix_job_descriptions_creator_created_id",
            "created_by_user_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
        Index(
            "ix_job_descriptions_org_created_id",
            "org_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
        Index(
            "ix_job_descriptions_created_id",
            text("created_at DESC"),
            text("id DESC"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "organizations.id",
            name="fk_job_descriptions_organization",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    created_by_user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_format: Mapped[str | None] = mapped_column(String(10))
