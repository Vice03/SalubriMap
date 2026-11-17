# SPDX-License-Identifier: AGPL-3.0-or-later
"""Module « Saisons » : tables road_conditions, road_import_batches, road_reports.

Branche à part (`seasons`) : `alembic upgrade heads` l'applique avec le reste ; rejouable (tables créées
seulement si absentes) ; downgrade supprime uniquement les tables du module.

Revision ID: 0101_seasons
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op

revision = "0101_seasons"
down_revision = "0006"
branch_labels = ("seasons",)
depends_on = None

TABLES = ("road_import_batches", "road_conditions", "road_reports")


def upgrade() -> None:
    from salubri_api.modules.seasons import models  # noqa: F401
    from salubri_api.modules.seasons.interface import Base

    have = set(sa.inspect(op.get_bind()).get_table_names())
    for name in TABLES:
        if name not in have:
            Base.metadata.tables[name].create(bind=op.get_bind())


def downgrade() -> None:
    have = set(sa.inspect(op.get_bind()).get_table_names())
    for name in reversed(TABLES):
        if name in have:
            op.drop_table(name)
