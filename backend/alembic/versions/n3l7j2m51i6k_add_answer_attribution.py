"""add answer_attribution to candidates (Priority 2.2)

Revision ID: n3l7j2m51i6k
Revises: m2k6i1l40h5j
Create Date: 2026-07-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "n3l7j2m51i6k"
down_revision = "m2k6i1l40h5j"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("candidates", sa.Column("answer_attribution", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("candidates", "answer_attribution")
