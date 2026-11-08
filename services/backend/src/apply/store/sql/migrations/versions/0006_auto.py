"""Auto: the account's settings, each search's switch, runs and their screenshots.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-26 23:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = postgresql.JSONB(astext_type=sa.Text())


def _row() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("users", sa.Column("auto_paused", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("users", sa.Column("auto_min_score", sa.Integer(), server_default="80", nullable=False))
    op.add_column("users", sa.Column("auto_daily_cap", sa.Integer(), server_default="5", nullable=False))
    op.add_column("users", sa.Column("auto_hold_hours", sa.Float(), server_default="4", nullable=False))
    op.add_column(
        "users", sa.Column("auto_draft_answers", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )
    op.add_column("searches", sa.Column("auto_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False))

    op.create_table(
        "auto_runs",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("match_id", sa.String(length=26), nullable=False),
        sa.Column("application_id", sa.String(length=26), nullable=True),
        sa.Column("search_id", sa.String(length=26), nullable=True),
        sa.Column("status", sa.String(length=12), server_default="starting", nullable=False),
        sa.Column("reason", sa.String(length=60), nullable=True),
        sa.Column("reason_detail", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="0", nullable=False),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hold_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hold_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=True),
        sa.Column("runner_step", sa.String(length=10), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_owner", sa.String(length=100), nullable=True),
        sa.Column("dry_run", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("drafts", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("send", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("submission_id", sa.String(length=26), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        *_row(),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_auto_runs_application_id_applications"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["match_id"], ["matches.id"], name=op.f("fk_auto_runs_match_id_matches"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_auto_runs_owner_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["search_id"], ["searches.id"], name=op.f("fk_auto_runs_search_id_searches"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auto_runs")),
        sa.UniqueConstraint("owner_id", "match_id", name=op.f("uq_auto_runs_owner_id_match_id")),
    )
    op.create_index(op.f("ix_auto_runs_owner_id"), "auto_runs", ["owner_id"], unique=False)
    op.create_index("ix_auto_runs_status", "auto_runs", ["owner_id", "status"], unique=False)
    op.create_index("ix_auto_runs_runner", "auto_runs", ["runner_step", "lease_until"], unique=False)

    op.create_table(
        "auto_screenshots",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("run_id", sa.String(length=26), nullable=False),
        sa.Column("step", sa.String(length=20), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        *_row(),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_auto_screenshots_owner_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["run_id"], ["auto_runs.id"], name=op.f("fk_auto_screenshots_run_id_auto_runs"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auto_screenshots")),
    )
    op.create_index(op.f("ix_auto_screenshots_owner_id"), "auto_screenshots", ["owner_id"], unique=False)
    op.create_index(op.f("ix_auto_screenshots_run_id"), "auto_screenshots", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_table("auto_screenshots")
    op.drop_table("auto_runs")
    op.drop_column("searches", "auto_enabled")
    for column in ("auto_draft_answers", "auto_hold_hours", "auto_daily_cap", "auto_min_score", "auto_paused"):
        op.drop_column("users", column)
