"""add payment_receipts table (manual billing receipts)

Revision ID: r7p1n6q95m0o
Revises: q6o0m5p84l9n
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "r7p1n6q95m0o"
down_revision = "q6o0m5p84l9n"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "payment_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("plan_requested", sa.String(length=50), nullable=False, server_default="starter"),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_payment_receipts_company_id", "payment_receipts", ["company_id"])
    op.create_index("ix_payment_receipts_status", "payment_receipts", ["status"])


def downgrade():
    op.drop_index("ix_payment_receipts_status", table_name="payment_receipts")
    op.drop_index("ix_payment_receipts_company_id", table_name="payment_receipts")
    op.drop_table("payment_receipts")
