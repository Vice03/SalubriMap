# SPDX-License-Identifier: AGPL-3.0-or-later
"""Initial schema: PostGIS extension and all Salubri tables.

The schema is built from the SQLAlchemy models so that models and migration
can never drift during the hackathon; later migrations are regular diffs.

Revision ID: 0001
Revises:
"""

from alembic import op

from salubri_api.models import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
