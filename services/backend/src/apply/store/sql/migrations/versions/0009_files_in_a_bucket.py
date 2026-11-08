"""Files in a bucket (PDFs, screenshots: a key here, the bytes there), and profiles made from an uploaded resume.

The bytes already kept here stay until the API or worker starts and moves them to the bucket (logic/files.py),
which needs the bucket's settings, so it isn't done here.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-27 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMPTY = sa.text("'{}'::jsonb")


def upgrade() -> None:
    for table in ("rendered_files", "auto_screenshots"):
        op.add_column(table, sa.Column("object_key", sa.String(length=300), nullable=True))
        op.alter_column(table, "data", existing_type=sa.LargeBinary(), nullable=True)
    op.add_column("profiles", sa.Column("source", postgresql.JSONB(), server_default=EMPTY, nullable=False))
    op.add_column("profiles", sa.Column("source_text", sa.Text(), server_default="", nullable=False))
    op.add_column("profiles", sa.Column("reading", postgresql.JSONB(), server_default=EMPTY, nullable=False))


def downgrade() -> None:
    op.drop_column("profiles", "reading")
    op.drop_column("profiles", "source_text")
    op.drop_column("profiles", "source")
    for table in ("rendered_files", "auto_screenshots"):
        # A file only in the bucket can't come back here: those rows go (a PDF is made again when asked for).
        op.execute(sa.text(f"DELETE FROM {table} WHERE data IS NULL"))
        op.alter_column(table, "data", existing_type=sa.LargeBinary(), nullable=False)
        op.drop_column(table, "object_key")
