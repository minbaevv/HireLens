"""add language to jobs

Revision ID: a1f4c9e77b21
Revises: d8c0b5bc59fa
Create Date: 2026-07-02

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1f4c9e77b21'
down_revision = 'd8c0b5bc59fa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'jobs',
        sa.Column('language', sa.String(length=5), nullable=False, server_default='ru'),
    )


def downgrade() -> None:
    op.drop_column('jobs', 'language')
