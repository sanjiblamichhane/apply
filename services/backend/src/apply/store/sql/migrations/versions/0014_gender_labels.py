"""Gender's choices labelled as most forms label them: "Male" and "Female" (were "Man" and "Woman").

Only the labels each person's saved answer keeps change; the values ("man", "woman") and the answers stay.

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-07 01:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RELABEL = """
UPDATE answers SET choices = (
    SELECT jsonb_agg(
        CASE c->>'value'
            WHEN 'man' THEN jsonb_set(c, '{label,en}', to_jsonb(CAST(:man AS text)))
            WHEN 'woman' THEN jsonb_set(c, '{label,en}', to_jsonb(CAST(:woman AS text)))
            ELSE c
        END
        ORDER BY CASE c->>'value' WHEN 'decline' THEN 0 WHEN 'man' THEN 1 WHEN 'woman' THEN 2 ELSE 3 END, n
    )
    FROM jsonb_array_elements(CAST(choices AS jsonb)) WITH ORDINALITY AS t(c, n)
)
WHERE key = 'gender' AND source = 'pack' AND jsonb_array_length(choices) > 0
"""


def upgrade() -> None:
    op.get_bind().exec_driver_sql(_RELABEL.replace(":man", "'Male'").replace(":woman", "'Female'"))


def downgrade() -> None:
    op.get_bind().exec_driver_sql(_RELABEL.replace(":man", "'Man'").replace(":woman", "'Woman'"))
