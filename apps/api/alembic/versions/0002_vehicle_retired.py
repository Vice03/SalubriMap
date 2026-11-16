# SPDX-License-Identifier: AGPL-3.0-or-later
"""vehicles.retired : retirer un camion sans perdre l'historique des plans.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("vehicles")}
    if "retired" not in cols:  # 0001 crée le schéma courant : colonne déjà là sur une base neuve
        op.add_column("vehicles", sa.Column("retired", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("vehicles", "retired")
