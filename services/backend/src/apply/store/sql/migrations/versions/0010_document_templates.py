"""Each person's own templates for their resumes and letters.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-27 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_templates",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("html", sa.Text(), nullable=False),
        sa.Column("filename", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id", "kind"),
    )
    op.create_index(op.f("ix_document_templates_owner_id"), "document_templates", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_templates_owner_id"), table_name="document_templates")
    op.drop_table("document_templates")
