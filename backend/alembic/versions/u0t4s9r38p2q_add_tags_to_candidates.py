"""add tags to candidates (bulk operations)

Revision ID: u0t4s9r38p2q
Revises: t9s3r8q27o1p
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "u0t4s9r38p2q"
down_revision = "t9s3r8q27o1p"
branch_labels = None
depends_on = None


def upgrade():
    # Массовые операции: теги кандидатов (JSON-список строк в TEXT)
    op.add_column("candidates", sa.Column("tags", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("candidates", "tags")
