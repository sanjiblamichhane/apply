"""Known devices: browsers an account has signed in from, which a sign-in lock doesn't shut out.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-26 23:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "known_devices",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_known_devices_owner_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_known_devices")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_known_devices_token_hash")),
    )
    op.create_index(op.f("ix_known_devices_owner_id"), "known_devices", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_known_devices_owner_id"), table_name="known_devices")
    op.drop_table("known_devices")
