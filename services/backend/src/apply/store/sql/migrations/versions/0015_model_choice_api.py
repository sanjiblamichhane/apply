"""The model choice keeps only which API its server speaks: "native" (/api/chat) or "v1" (/v1/chat/completions).

The product a server was guessed to be (its ``kind``) is dropped: servers are known by what they answer. A choice
saved before this, under the old API names, is cleared: the settings' model is used until one is chosen again.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-08 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM model_choice WHERE api NOT IN ('native', 'v1')")
    op.drop_column("model_choice", "kind")


def downgrade() -> None:
    op.add_column("model_choice", sa.Column("kind", sa.String(32), nullable=False, server_default="v1"))
    op.execute("UPDATE model_choice SET kind = api")
    op.alter_column("model_choice", "kind", server_default=None)
