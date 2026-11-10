"""A document can be written again from the person's corrections and notes: its brief is kept on it.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-09 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("application_documents", sa.Column("revision", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("application_documents", "revision")
