"""Add white-label branding + privacy retention columns (Phase 3, no keys)

Revision ID: u0t4s9r38p2q
Revises: t9s3r8q27o1p
Create Date: 2026-07-22 22:40:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'u0t4s9r38p2q'
down_revision = 't9s3r8q27o1p'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('companies', sa.Column('brand_enabled', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('companies', sa.Column('brand_name', sa.String(length=120), nullable=True))
    op.add_column('companies', sa.Column('brand_logo_url', sa.String(length=500), nullable=True))
    op.add_column('companies', sa.Column('brand_color', sa.String(length=9), nullable=True))
    op.add_column('companies', sa.Column('data_retention_days', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('companies', 'data_retention_days')
    op.drop_column('companies', 'brand_color')
    op.drop_column('companies', 'brand_logo_url')
    op.drop_column('companies', 'brand_name')
    op.drop_column('companies', 'brand_enabled')
