"""add video fields to messages

Revision ID: f4d8b3e62a7c
Revises: e3f7a1c9d2b4
Create Date: 2026-07-04

"""
from alembic import op
import sqlalchemy as sa


revision = 'f4d8b3e62a7c'
down_revision = 'e3f7a1c9d2b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('messages', sa.Column('video_url', sa.String(500), nullable=True))
    op.add_column('messages', sa.Column('video_duration', sa.Float(), nullable=True))
    op.add_column('messages', sa.Column('video_analysis', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('messages', 'video_analysis')
    op.drop_column('messages', 'video_duration')
    op.drop_column('messages', 'video_url')
