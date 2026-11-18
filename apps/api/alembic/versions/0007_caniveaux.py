# SPDX-License-Identifier: AGPL-3.0-or-later
"""Caniveaux : type OSM des cours d'eau linéaires (drain, ditch…) et dépotoirs dans ou près d'un caniveau.

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "subkind" not in {c["name"] for c in insp.get_columns("water")}:
        op.add_column("water", sa.Column("subkind", sa.String(16), nullable=True))
    if "near_drain" not in {c["name"] for c in insp.get_columns("dump_sites")}:
        op.add_column("dump_sites", sa.Column("near_drain", sa.Boolean, nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("dump_sites", "near_drain")
    op.drop_column("water", "subkind")
