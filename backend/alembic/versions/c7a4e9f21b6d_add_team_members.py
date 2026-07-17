"""add team_members table

Revision ID: c7a4e9f21b6d
Revises: a1f4c9e77b21
Create Date: 2026-07-03

"""
from alembic import op
import sqlalchemy as sa


revision = 'c7a4e9f21b6d'
down_revision = 'a1f4c9e77b21'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'team_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=True),
        sa.Column('role', sa.Enum('admin', 'recruiter', 'viewer', name='teamrole'), nullable=False, server_default='recruiter'),
        sa.Column('invite_token', sa.String(length=64), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('invited_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_team_members_id'), 'team_members', ['id'])
    op.create_index(op.f('ix_team_members_email'), 'team_members', ['email'], unique=True)
    op.create_index(op.f('ix_team_members_invite_token'), 'team_members', ['invite_token'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_team_members_invite_token'), table_name='team_members')
    op.drop_index(op.f('ix_team_members_email'), table_name='team_members')
    op.drop_index(op.f('ix_team_members_id'), table_name='team_members')
    op.drop_table('team_members')
    sa.Enum(name='teamrole').drop(op.get_bind(), checkfirst=True)
