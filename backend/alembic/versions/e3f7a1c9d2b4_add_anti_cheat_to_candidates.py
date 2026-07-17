"""add anti-cheat fields to candidates

Revision ID: e3f7a1c9d2b4
Revises: c7a4e9f21b6d
Create Date: 2026-07-03

"""
from alembic import op
import sqlalchemy as sa


revision = 'e3f7a1c9d2b4'
down_revision = 'c7a4e9f21b6d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('candidates', sa.Column('anti_cheat_score', sa.Float(), nullable=True))
    op.add_column('candidates', sa.Column('anti_cheat_flags', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('candidates', 'anti_cheat_flags')
    op.drop_column('candidates', 'anti_cheat_score')
