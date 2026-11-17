# SPDX-License-Identifier: AGPL-3.0-or-later
"""reports.masking : zones floutées sur le téléphone et par le serveur (masquage des visages et plaques).

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("reports")}
    if "masking" not in cols:  # 0001 (create_all) la crée déjà sur une base neuve
        op.add_column("reports", sa.Column("masking", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "masking")
