# SPDX-License-Identifier: AGPL-3.0-or-later
"""login_failures : échecs de connexion partagés entre l'API et la console (verrouillage par login et adresse).

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "login_failures" in sa.inspect(op.get_bind()).get_table_names():  # base neuve : 0001 l'a déjà créée
        return
    op.create_table(
        "login_failures",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("login", sa.String(64), nullable=False),
        sa.Column("ip", sa.String(64), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_login_failures_login_at", "login_failures", ["login", "at"])
    op.create_index("ix_login_failures_ip_at", "login_failures", ["ip", "at"])


def downgrade() -> None:
    op.drop_table("login_failures")
