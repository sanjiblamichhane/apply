"""Imports: what an import (apply-export) made from what, so a second run adds only what is new.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-26 17:48:37.093902
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "imports",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("source_ref", sa.String(length=200), nullable=False),
        sa.Column("target", sa.String(length=40), nullable=False),
        sa.Column("target_id", sa.String(length=26), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name=op.f("fk_imports_owner_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_imports")),
        sa.UniqueConstraint("owner_id", "source", "source_ref", name=op.f("uq_imports_owner_id_source_source_ref")),
    )
    op.create_index(op.f("ix_imports_owner_id"), "imports", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_imports_owner_id"), table_name="imports")
    op.drop_table("imports")
