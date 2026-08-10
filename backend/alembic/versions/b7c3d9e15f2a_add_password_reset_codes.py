"""add password reset codes to companies

Revision ID: b7c3d9e15f2a
Revises: a6z0y5x94v8w
Create Date: 2026-08-09

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7c3d9e15f2a'
down_revision = 'a6z0y5x94v8w'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('reset_code', sa.String(length=6), nullable=True))
    op.add_column('companies', sa.Column('reset_code_expires_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'reset_code_expires_at')
    op.drop_column('companies', 'reset_code')
