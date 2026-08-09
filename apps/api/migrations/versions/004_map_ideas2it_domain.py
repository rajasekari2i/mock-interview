"""Map the ideas2it.com Google domain to the default organization.

Revision ID: 004
Revises: 003
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_MAPPING_ID = "1d39cb66-a066-4b6f-a981-1b76dfd37d84"


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO organization_domain_mappings "
            "(id, org_id, normalized_domain, created_at, updated_at, removed_at) "
            "SELECT CAST(:id AS UUID), id, 'ideas2it.com', now(), now(), NULL "
            "FROM organizations WHERE slug = 'ideas2it'"
        ).bindparams(id=_DEFAULT_MAPPING_ID)
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM organization_domain_mappings "
            "WHERE id = CAST(:id AS UUID) AND normalized_domain = 'ideas2it.com'"
        ).bindparams(id=_DEFAULT_MAPPING_ID)
    )
