"""Discovery: sources, searches, matches and briefings; where an opportunity came from; when to brief whom.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-26 18:41:13.532600
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "briefings",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("date", sa.String(length=10), nullable=False),
        sa.Column(
            "content", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_briefings_owner_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_briefings")),
        sa.UniqueConstraint("owner_id", "date", name=op.f("uq_briefings_owner_id_date")),
    )
    op.create_index(op.f("ix_briefings_owner_id"), "briefings", ["owner_id"], unique=False)
    op.create_table(
        "sources",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("pack", sa.String(length=40), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("interval_hours", sa.Float(), server_default="6", nullable=False),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=12), server_default="never", nullable=False),
        sa.Column("last_error_code", sa.String(length=60), nullable=True),
        sa.Column("last_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name=op.f("fk_sources_owner_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pack"], ["packs.key"], name=op.f("fk_sources_pack_packs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sources")),
    )
    op.create_index(op.f("ix_sources_owner_id"), "sources", ["owner_id"], unique=False)
    op.create_table(
        "searches",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("pack", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "criteria", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("profile_id", sa.String(length=26), nullable=True),
        sa.Column("min_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_searches_owner_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["pack"], ["packs.key"], name=op.f("fk_searches_pack_packs")),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["profiles.id"], name=op.f("fk_searches_profile_id_profiles"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_searches")),
    )
    op.create_index(op.f("ix_searches_owner_id"), "searches", ["owner_id"], unique=False)
    op.create_table(
        "matches",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("opportunity_id", sa.String(length=26), nullable=False),
        sa.Column(
            "search_ids", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column("status", sa.String(length=12), server_default="new", nullable=False),
        sa.Column(
            "prefilter", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column(
            "score_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "dealbreakers",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("score_status", sa.String(length=12), server_default="pending", nullable=False),
        sa.Column("score_error_code", sa.String(length=60), nullable=True),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("profile_id", sa.String(length=26), nullable=True),
        sa.Column("application_id", sa.String(length=26), nullable=True),
        sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_matches_application_id_applications"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            name=op.f("fk_matches_opportunity_id_opportunities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name=op.f("fk_matches_owner_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["profiles.id"], name=op.f("fk_matches_profile_id_profiles"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_matches")),
        sa.UniqueConstraint("owner_id", "opportunity_id", name=op.f("uq_matches_owner_id_opportunity_id")),
    )
    op.create_index("ix_matches_inbox", "matches", ["owner_id", "status", "score", "id"], unique=False)
    op.create_index(op.f("ix_matches_owner_id"), "matches", ["owner_id"], unique=False)
    op.add_column("opportunities", sa.Column("source_id", sa.String(length=26), nullable=True))
    op.add_column("opportunities", sa.Column("dedupe_key", sa.String(length=500), nullable=True))
    op.add_column("opportunities", sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_opportunities_dedupe", "opportunities", ["owner_id", "dedupe_key"], unique=False)
    op.create_foreign_key(
        op.f("fk_opportunities_source_id_sources"),
        "opportunities",
        "sources",
        ["source_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("users", sa.Column("time_zone", sa.String(length=64), server_default="UTC", nullable=False))
    op.add_column("users", sa.Column("briefing_hour", sa.Integer(), server_default="7", nullable=False))


def downgrade() -> None:
    op.drop_column("users", "briefing_hour")
    op.drop_column("users", "time_zone")
    op.drop_constraint(op.f("fk_opportunities_source_id_sources"), "opportunities", type_="foreignkey")
    op.drop_index("ix_opportunities_dedupe", table_name="opportunities")
    op.drop_column("opportunities", "posted_at")
    op.drop_column("opportunities", "dedupe_key")
    op.drop_column("opportunities", "source_id")
    op.drop_index(op.f("ix_matches_owner_id"), table_name="matches")
    op.drop_index("ix_matches_inbox", table_name="matches")
    op.drop_table("matches")
    op.drop_index(op.f("ix_searches_owner_id"), table_name="searches")
    op.drop_table("searches")
    op.drop_index(op.f("ix_sources_owner_id"), table_name="sources")
    op.drop_table("sources")
    op.drop_index(op.f("ix_briefings_owner_id"), table_name="briefings")
    op.drop_table("briefings")
