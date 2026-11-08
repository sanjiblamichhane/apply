"""The first schema: accounts, packs and pipelines, profiles, opportunities, applications, documents, jobs.

Revision ID: 0001
Revises:
Create Date: 2026-10-26 17:30:13.572149
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("kind", sa.String(length=100), nullable=False),
        sa.Column("queue", sa.String(length=40), server_default="default", nullable=False),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=12), server_default="pending", nullable=False),
        sa.Column("run_after", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
        sa.Column("locked_by", sa.String(length=200), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("key", sa.String(length=200), nullable=True),
        sa.Column("owner_id", sa.String(length=26), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index("ix_jobs_claim", "jobs", ["queue", "status", "priority", "run_after"], unique=False)
    op.create_index("ix_jobs_finished", "jobs", ["finished_at"], unique=False)
    op.create_index("ix_jobs_lease", "jobs", ["status", "locked_until"], unique=False)
    op.create_index(
        "uq_jobs_kind_key_open",
        "jobs",
        ["kind", "key"],
        unique=True,
        postgresql_where=sa.text("key IS NOT NULL AND status IN ('pending', 'running')"),
    )
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=200), nullable=False),
        sa.Column("locale", sa.String(length=5), server_default="en", nullable=False),
        sa.Column("is_owner", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("failed_sign_ins", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sign_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "packs",
        sa.Column("owner_id", sa.String(length=26), nullable=True),
        sa.Column("key", sa.String(length=40), nullable=False),
        sa.Column("version", sa.String(length=20), nullable=False),
        sa.Column("label", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("description", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("profile_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("opportunity_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("document_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name=op.f("fk_packs_owner_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_packs")),
        sa.UniqueConstraint("key", name=op.f("uq_packs_key")),
    )
    op.create_index(op.f("ix_packs_owner_id"), "packs", ["owner_id"], unique=False)
    op.create_table(
        "sessions",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_agent", sa.String(length=300), server_default="", nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_sessions_owner_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )
    op.create_index(op.f("ix_sessions_owner_id"), "sessions", ["owner_id"], unique=False)
    op.create_table(
        "opportunities",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("pack", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=500), server_default="", nullable=False),
        sa.Column("issuer_name", sa.String(length=300), server_default="", nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("apply_url", sa.String(length=2048), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=12), server_default="open", nullable=False),
        sa.Column(
            "attributes", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("external_ref", sa.String(length=2100), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("source_text", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "extraction", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_opportunities_owner_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["pack"], ["packs.key"], name=op.f("fk_opportunities_pack_packs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_opportunities")),
        sa.UniqueConstraint("owner_id", "external_ref", name=op.f("uq_opportunities_owner_id_external_ref")),
    )
    op.create_index(op.f("ix_opportunities_owner_id"), "opportunities", ["owner_id"], unique=False)
    op.create_table(
        "pipelines",
        sa.Column("owner_id", sa.String(length=26), nullable=True),
        sa.Column("pack", sa.String(length=40), nullable=False),
        sa.Column("key", sa.String(length=60), nullable=False),
        sa.Column("label", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_pipelines_owner_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["pack"], ["packs.key"], name=op.f("fk_pipelines_pack_packs"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pipelines")),
        sa.UniqueConstraint(
            "owner_id", "pack", "key", name=op.f("uq_pipelines_owner_id_pack_key"), postgresql_nulls_not_distinct=True
        ),
    )
    op.create_index(op.f("ix_pipelines_owner_id"), "pipelines", ["owner_id"], unique=False)
    op.create_table(
        "profiles",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("pack", sa.String(length=40), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "attributes", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("tone_instructions", sa.Text(), server_default="", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_profiles_owner_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["pack"], ["packs.key"], name=op.f("fk_profiles_pack_packs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profiles")),
    )
    op.create_index(op.f("ix_profiles_owner_id"), "profiles", ["owner_id"], unique=False)
    op.create_index(
        "uq_profiles_one_default", "profiles", ["owner_id", "pack"], unique=True, postgresql_where=sa.text("is_default")
    )
    op.create_table(
        "stages",
        sa.Column("owner_id", sa.String(length=26), nullable=True),
        sa.Column("pipeline_id", sa.String(length=26), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("label", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("action_type", sa.String(length=20), nullable=False),
        sa.Column("is_terminal", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("follow_up_after_days", sa.Integer(), nullable=True),
        sa.Column("expected_duration_days", sa.Integer(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name=op.f("fk_stages_owner_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["pipeline_id"], ["pipelines.id"], name=op.f("fk_stages_pipeline_id_pipelines"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stages")),
        sa.UniqueConstraint("pipeline_id", "code", name=op.f("uq_stages_pipeline_id_code")),
    )
    op.create_index(op.f("ix_stages_owner_id"), "stages", ["owner_id"], unique=False)
    op.create_table(
        "applications",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("opportunity_id", sa.String(length=26), nullable=False),
        sa.Column("profile_id", sa.String(length=26), nullable=True),
        sa.Column("pipeline_id", sa.String(length=26), nullable=False),
        sa.Column("stage_id", sa.String(length=26), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "analysis", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
            name=op.f("fk_applications_opportunity_id_opportunities"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_applications_owner_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], name=op.f("fk_applications_pipeline_id_pipelines")),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["profiles.id"], name=op.f("fk_applications_profile_id_profiles"), ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["stage_id"], ["stages.id"], name=op.f("fk_applications_stage_id_stages")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_applications")),
        sa.UniqueConstraint("owner_id", "opportunity_id", name=op.f("uq_applications_owner_id_opportunity_id")),
    )
    op.create_index(op.f("ix_applications_owner_id"), "applications", ["owner_id"], unique=False)
    op.create_index("ix_applications_stage", "applications", ["owner_id", "stage_id"], unique=False)
    op.create_table(
        "application_documents",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("application_id", sa.String(length=26), nullable=False),
        sa.Column("profile_id", sa.String(length=26), nullable=True),
        sa.Column("document_type", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=10), server_default="pending", nullable=False),
        sa.Column("error_code", sa.String(length=60), nullable=True),
        sa.Column("version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("content_markdown", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "claim_warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=20), server_default="generated", nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("generation_ms", sa.Integer(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_application_documents_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_application_documents_owner_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name=op.f("fk_application_documents_profile_id_profiles"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_application_documents")),
    )
    op.create_index(
        "ix_application_documents_app", "application_documents", ["application_id", "document_type"], unique=False
    )
    op.create_index(op.f("ix_application_documents_owner_id"), "application_documents", ["owner_id"], unique=False)
    op.create_index(
        "uq_application_documents_active",
        "application_documents",
        ["application_id", "document_type"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.create_index(
        "uq_application_documents_pending",
        "application_documents",
        ["application_id", "document_type"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "uq_application_documents_version",
        "application_documents",
        ["application_id", "document_type", "version"],
        unique=True,
        postgresql_where=sa.text("version > 0"),
    )
    op.create_table(
        "stage_history",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("application_id", sa.String(length=26), nullable=False),
        sa.Column("stage_id", sa.String(length=26), nullable=False),
        sa.Column("entered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("exited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=20), server_default="", nullable=False),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_stage_history_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_stage_history_owner_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["stage_id"], ["stages.id"], name=op.f("fk_stage_history_stage_id_stages")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stage_history")),
    )
    op.create_index(op.f("ix_stage_history_application_id"), "stage_history", ["application_id"], unique=False)
    op.create_index(op.f("ix_stage_history_owner_id"), "stage_history", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_stage_history_owner_id"), table_name="stage_history")
    op.drop_index(op.f("ix_stage_history_application_id"), table_name="stage_history")
    op.drop_table("stage_history")
    op.drop_index(
        "uq_application_documents_version", table_name="application_documents", postgresql_where=sa.text("version > 0")
    )
    op.drop_index(
        "uq_application_documents_pending",
        table_name="application_documents",
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.drop_index(
        "uq_application_documents_active", table_name="application_documents", postgresql_where=sa.text("is_active")
    )
    op.drop_index(op.f("ix_application_documents_owner_id"), table_name="application_documents")
    op.drop_index("ix_application_documents_app", table_name="application_documents")
    op.drop_table("application_documents")
    op.drop_index("ix_applications_stage", table_name="applications")
    op.drop_index(op.f("ix_applications_owner_id"), table_name="applications")
    op.drop_table("applications")
    op.drop_index(op.f("ix_stages_owner_id"), table_name="stages")
    op.drop_table("stages")
    op.drop_index("uq_profiles_one_default", table_name="profiles", postgresql_where=sa.text("is_default"))
    op.drop_index(op.f("ix_profiles_owner_id"), table_name="profiles")
    op.drop_table("profiles")
    op.drop_index(op.f("ix_pipelines_owner_id"), table_name="pipelines")
    op.drop_table("pipelines")
    op.drop_index(op.f("ix_opportunities_owner_id"), table_name="opportunities")
    op.drop_table("opportunities")
    op.drop_index(op.f("ix_sessions_owner_id"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_index(op.f("ix_packs_owner_id"), table_name="packs")
    op.drop_table("packs")
    op.drop_table("users")
    op.drop_index(
        "uq_jobs_kind_key_open",
        table_name="jobs",
        postgresql_where=sa.text("key IS NOT NULL AND status IN ('pending', 'running')"),
    )
    op.drop_index("ix_jobs_lease", table_name="jobs")
    op.drop_index("ix_jobs_finished", table_name="jobs")
    op.drop_index("ix_jobs_claim", table_name="jobs")
    op.drop_table("jobs")
