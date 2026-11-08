"""Review and the Application kit: claim checks and review on documents, rendered PDFs, saved answers, submissions.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-26 19:06:20.221096
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "answers",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("pack", sa.String(length=40), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("question", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("answer", sa.Text(), server_default="", nullable=False),
        sa.Column("answer_type", sa.String(length=10), server_default="text", nullable=False),
        sa.Column(
            "choices", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column("is_sensitive", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=10), server_default="user", nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], name=op.f("fk_answers_owner_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pack"], ["packs.key"], name=op.f("fk_answers_pack_packs")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_answers")),
        sa.UniqueConstraint("owner_id", "pack", "key", name=op.f("uq_answers_owner_id_pack_key")),
    )
    op.create_index(op.f("ix_answers_owner_id"), "answers", ["owner_id"], unique=False)
    op.create_table(
        "submissions",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("application_id", sa.String(length=26), nullable=False),
        sa.Column("channel", sa.String(length=12), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "documents", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column(
            "answers", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False
        ),
        sa.Column("note", sa.Text(), server_default="", nullable=False),
        sa.Column("previous_stage_id", sa.String(length=26), nullable=True),
        sa.Column("undone_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["applications.id"],
            name=op.f("fk_submissions_application_id_applications"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_submissions_owner_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_submissions")),
    )
    op.create_index(op.f("ix_submissions_application_id"), "submissions", ["application_id"], unique=False)
    op.create_index(op.f("ix_submissions_owner_id"), "submissions", ["owner_id"], unique=False)
    op.create_table(
        "rendered_files",
        sa.Column("owner_id", sa.String(length=26), nullable=False),
        sa.Column("document_id", sa.String(length=26), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["application_documents.id"],
            name=op.f("fk_rendered_files_document_id_application_documents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_rendered_files_owner_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rendered_files")),
        sa.UniqueConstraint("document_id", "kind", "sha256", name=op.f("uq_rendered_files_document_id_kind_sha256")),
    )
    op.create_index(op.f("ix_rendered_files_document_id"), "rendered_files", ["document_id"], unique=False)
    op.create_index(op.f("ix_rendered_files_owner_id"), "rendered_files", ["owner_id"], unique=False)
    op.add_column(
        "application_documents",
        sa.Column("claims_status", sa.String(length=10), server_default="pending", nullable=False),
    )
    op.add_column("application_documents", sa.Column("claims_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("application_documents", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("application_documents", "reviewed_at")
    op.drop_column("application_documents", "claims_checked_at")
    op.drop_column("application_documents", "claims_status")
    op.drop_index(op.f("ix_rendered_files_owner_id"), table_name="rendered_files")
    op.drop_index(op.f("ix_rendered_files_document_id"), table_name="rendered_files")
    op.drop_table("rendered_files")
    op.drop_index(op.f("ix_submissions_owner_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_application_id"), table_name="submissions")
    op.drop_table("submissions")
    op.drop_index(op.f("ix_answers_owner_id"), table_name="answers")
    op.drop_table("answers")
