"""Auto prepares, the person sends: no more runner, dry run, hold or send.

Runs in flight are kept: one waiting for a dry run, drafting or held becomes "ready" (the person's to send); one
being sent needs the person ("check the board: it may have been sent"). What runners recorded (dry_run, drafts,
send, screenshots) stays as history. Runner tokens are revoked.

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-27 23:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("auto_runs", sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE auto_runs SET status = 'ready', ready_at = coalesce(hold_started_at, updated_at), "
        "deadline_at = NULL WHERE status IN ('dry_run', 'drafting', 'holding')"
    )
    op.execute(
        "UPDATE auto_runs SET status = 'needs_you', reason = 'AUTO_SEND_UNKNOWN', finished_at = now() "
        "WHERE status = 'sending'"
    )
    op.execute("UPDATE auto_runs SET ready_at = hold_started_at WHERE status = 'sent'")
    op.execute("DELETE FROM api_tokens WHERE kind = 'runner'")
    op.drop_index("ix_auto_runs_runner", table_name="auto_runs")
    for column in ("hold_started_at", "hold_until", "fingerprint", "runner_step", "lease_until", "lease_owner"):
        op.drop_column("auto_runs", column)
    op.drop_column("users", "auto_hold_hours")
    op.drop_column("users", "auto_draft_answers")


def downgrade() -> None:
    op.add_column(
        "users", sa.Column("auto_draft_answers", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )
    op.add_column("users", sa.Column("auto_hold_hours", sa.Float(), server_default="4", nullable=False))
    op.add_column("auto_runs", sa.Column("lease_owner", sa.String(length=100), nullable=True))
    op.add_column("auto_runs", sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("auto_runs", sa.Column("runner_step", sa.String(length=10), nullable=True))
    op.add_column("auto_runs", sa.Column("fingerprint", sa.String(length=64), nullable=True))
    op.add_column("auto_runs", sa.Column("hold_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("auto_runs", sa.Column("hold_started_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_auto_runs_runner", "auto_runs", ["runner_step", "lease_until"], unique=False)
    op.execute("UPDATE auto_runs SET hold_started_at = ready_at")
    op.execute("UPDATE auto_runs SET status = 'stopped' WHERE status = 'ready'")
    op.drop_column("auto_runs", "ready_at")
