# SPDX-License-Identifier: AGPL-3.0-or-later
"""Index des listes lourdes (lot F) : signalements par statut et date, journal par date.

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

# IF NOT EXISTS : la migration se rejoue sans risque, les données restent en place
INDEXES = {
    "ix_reports_commune_status_reported": "reports (commune_id, status, reported_at DESC)",
    "ix_reports_device_received": "reports (device_id, received_at DESC)",
    "ix_audit_log_at": "audit_log (at DESC)",
    "ix_audit_log_entity_at": "audit_log (entity, at DESC)",
}


def upgrade() -> None:
    for name, target in INDEXES.items():
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {target}")


def downgrade() -> None:
    for name in INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
