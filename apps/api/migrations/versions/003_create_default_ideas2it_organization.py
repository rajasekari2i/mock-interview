"""Create the default ideas2it organization.

Revision ID: 003
Revises: 002
Create Date: 2026-08-09

An existing organization with the same slug is preserved rather than overwritten.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_ORGANIZATION_ID = "9b2654a0-7f48-4ad1-bef4-cdbd98f5434e"


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO organizations "
            "(id, name, slug, status, created_at, updated_at) "
            "VALUES (CAST(:id AS UUID), 'ideas2it', 'ideas2it', 'ACTIVE', now(), now()) "
            "ON CONFLICT (slug) DO NOTHING"
        ).bindparams(id=_DEFAULT_ORGANIZATION_ID)
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM organizations WHERE id = CAST(:id AS UUID) AND slug = 'ideas2it'"
        ).bindparams(id=_DEFAULT_ORGANIZATION_ID)
    )
