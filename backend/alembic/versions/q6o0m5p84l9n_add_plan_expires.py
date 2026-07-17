"""add plan_expires_at to companies (manual subscriptions)

Revision ID: q6o0m5p84l9n
Revises: p5n9l4o73k8m
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "q6o0m5p84l9n"
down_revision = "p5n9l4o73k8m"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("companies", sa.Column("plan_expires_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("companies", "plan_expires_at")
