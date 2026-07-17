"""add referral columns to companies (Roadmap D3 - referral program)

Revision ID: p5n9l4o73k8m
Revises: o4m8k3n62j7l
Create Date: 2026-07-10 01:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "p5n9l4o73k8m"
down_revision = "o4m8k3n62j7l"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("companies", sa.Column("referral_code", sa.String(length=16), nullable=True))
    op.add_column("companies", sa.Column("referred_by_company_id", sa.Integer(), nullable=True))
    op.create_index("ix_companies_referral_code", "companies", ["referral_code"], unique=True)
    op.create_foreign_key(
        "fk_companies_referred_by",
        "companies",
        "companies",
        ["referred_by_company_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_companies_referred_by", "companies", type_="foreignkey")
    op.drop_index("ix_companies_referral_code", table_name="companies")
    op.drop_column("companies", "referred_by_company_id")
    op.drop_column("companies", "referral_code")
