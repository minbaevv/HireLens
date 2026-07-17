"""Add ground truth tracking fields to candidates

Revision ID: h6f0d5g84c9e
Revises: g5e9c4f73b8d
Create Date: 2026-07-04 20:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'h6f0d5g84c9e'
down_revision = 'g5e9c4f73b8d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('candidates', sa.Column('actual_hire_decision', sa.String(length=20), nullable=True))
    op.add_column('candidates', sa.Column('ai_feedback', sa.String(length=20), nullable=True))
    op.add_column('candidates', sa.Column('hr_notes', sa.Text(), nullable=True))
    op.add_column('candidates', sa.Column('requires_manual_review', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    op.drop_column('candidates', 'requires_manual_review')
    op.drop_column('candidates', 'hr_notes')
    op.drop_column('candidates', 'ai_feedback')
    op.drop_column('candidates', 'actual_hire_decision')
