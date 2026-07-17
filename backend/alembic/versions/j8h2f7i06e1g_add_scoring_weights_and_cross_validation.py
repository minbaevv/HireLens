"""Add scoring_weights to jobs and cross_validation to candidates (Priority 2)

Revision ID: j8h2f7i06e1g
Revises: i7g1e6h95d0f
Create Date: 2026-07-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'j8h2f7i06e1g'
down_revision = 'i7g1e6h95d0f'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('jobs', sa.Column('scoring_weights', sa.Text(), nullable=True))
    op.add_column('candidates', sa.Column('cross_validation', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('candidates', 'cross_validation')
    op.drop_column('jobs', 'scoring_weights')
