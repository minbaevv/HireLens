"""add structured scoring fields (C5)

Revision ID: g5e9c4f73b8d
Revises: f4d8b3e62a7c
Create Date: 2026-07-04

"""
from alembic import op
import sqlalchemy as sa


revision = 'g5e9c4f73b8d'
down_revision = 'f4d8b3e62a7c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Structured scoring (C5.1)
    op.add_column('candidates', sa.Column('technical_score', sa.Integer(), nullable=True))
    op.add_column('candidates', sa.Column('soft_skills_score', sa.Integer(), nullable=True))
    op.add_column('candidates', sa.Column('experience_score', sa.Integer(), nullable=True))
    op.add_column('candidates', sa.Column('motivation_score', sa.Integer(), nullable=True))
    op.add_column('candidates', sa.Column('confidence', sa.Float(), nullable=True))
    op.add_column('candidates', sa.Column('scoring_reasoning', sa.Text(), nullable=True))

    # Bias detection (C5.2)
    op.add_column('candidates', sa.Column('bias_flags', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('candidates', 'bias_flags')
    op.drop_column('candidates', 'scoring_reasoning')
    op.drop_column('candidates', 'confidence')
    op.drop_column('candidates', 'motivation_score')
    op.drop_column('candidates', 'experience_score')
    op.drop_column('candidates', 'soft_skills_score')
    op.drop_column('candidates', 'technical_score')
