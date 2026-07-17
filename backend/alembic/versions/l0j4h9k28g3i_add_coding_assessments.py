"""Add coding assessments (GAP-5)

Revision ID: l0j4h9k28g3i
Revises: k9i3g8j17f2h
Create Date: 2026-07-09 02:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'l0j4h9k28g3i'
down_revision = 'k9i3g8j17f2h'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'coding_challenges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('language', sa.String(length=32), nullable=False, server_default='python'),
        sa.Column('difficulty', sa.String(length=16), nullable=False, server_default='medium'),
        sa.Column('starter_code', sa.Text(), nullable=True),
        sa.Column('reference_solution', sa.Text(), nullable=True),
        sa.Column('required_keywords', sa.Text(), nullable=True),
        sa.Column('max_score', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('time_limit_minutes', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_coding_challenges_id'), 'coding_challenges', ['id'])
    op.create_index('ix_coding_challenges_company_id', 'coding_challenges', ['company_id'])

    op.create_table(
        'coding_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('challenge_id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('access_token', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='assigned'),
        sa.Column('submitted_code', sa.Text(), nullable=True),
        sa.Column('language', sa.String(length=32), nullable=True),
        sa.Column('auto_score', sa.Float(), nullable=True),
        sa.Column('auto_feedback', sa.Text(), nullable=True),
        sa.Column('requires_manual_review', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('manual_score', sa.Integer(), nullable=True),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['challenge_id'], ['coding_challenges.id'], ),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_coding_submissions_id'), 'coding_submissions', ['id'])
    op.create_index('ix_coding_submissions_challenge_id', 'coding_submissions', ['challenge_id'])
    op.create_index('ix_coding_submissions_candidate_id', 'coding_submissions', ['candidate_id'])
    op.create_index('ix_coding_submissions_company_id', 'coding_submissions', ['company_id'])
    op.create_index(op.f('ix_coding_submissions_access_token'), 'coding_submissions', ['access_token'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_coding_submissions_access_token'), table_name='coding_submissions')
    op.drop_index('ix_coding_submissions_company_id', table_name='coding_submissions')
    op.drop_index('ix_coding_submissions_candidate_id', table_name='coding_submissions')
    op.drop_index('ix_coding_submissions_challenge_id', table_name='coding_submissions')
    op.drop_index(op.f('ix_coding_submissions_id'), table_name='coding_submissions')
    op.drop_table('coding_submissions')
    op.drop_index('ix_coding_challenges_company_id', table_name='coding_challenges')
    op.drop_index(op.f('ix_coding_challenges_id'), table_name='coding_challenges')
    op.drop_table('coding_challenges')
