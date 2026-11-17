# SPDX-License-Identifier: AGPL-3.0-or-later
"""Module « Assistant » : table assistant_passages (branche à part, rejouable, sans perte : la table est
reconstruite à chaque démarrage depuis les documents du dépôt).

Revision ID: 0201_assistant
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op

revision = "0201_assistant"
down_revision = "0006"
branch_labels = ("assistant",)
depends_on = None


def upgrade() -> None:
    from salubri_api.modules.assistant import models  # noqa: F401
    from salubri_api.modules.assistant.interface import Base

    if "assistant_passages" not in sa.inspect(op.get_bind()).get_table_names():
        Base.metadata.tables["assistant_passages"].create(bind=op.get_bind())


def downgrade() -> None:
    if "assistant_passages" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("assistant_passages")
