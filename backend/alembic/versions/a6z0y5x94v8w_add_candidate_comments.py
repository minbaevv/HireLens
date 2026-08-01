"""add candidate_comments

Revision ID: a6z0y5x94v8w
Revises: z5y9x4w83u7v
Create Date: 2026-08-01

Pilot feedback (Dinara): нужна лента комментариев по кандидату —
кто и когда что заметил (например, кандидат отказался сам).
"""
from alembic import op
import sqlalchemy as sa

revision = "a6z0y5x94v8w"
down_revision = "z5y9x4w83u7v"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "candidate_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("candidate_id", sa.Integer(), nullable=False),
        sa.Column("author_name", sa.String(length=255), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candidate_comments_candidate_id",
        "candidate_comments",
        ["candidate_id"],
    )


def downgrade():
    op.drop_index("ix_candidate_comments_candidate_id", table_name="candidate_comments")
    op.drop_table("candidate_comments")
