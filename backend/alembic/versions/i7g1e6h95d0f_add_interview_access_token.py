"""Add access_token to interviews (SEC-1: защита от IDOR)

Revision ID: i7g1e6h95d0f
Revises: h6f0d5g84c9e
Create Date: 2026-07-08 12:00:00.000000

"""
import secrets

from alembic import op
import sqlalchemy as sa


revision = 'i7g1e6h95d0f'
down_revision = 'h6f0d5g84c9e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('interviews', sa.Column('access_token', sa.String(length=64), nullable=True))

    # Backfill: уникальный токен каждому существующему интервью
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM interviews WHERE access_token IS NULL")).fetchall()
    for (interview_id,) in rows:
        conn.execute(
            sa.text("UPDATE interviews SET access_token = :tok WHERE id = :id"),
            {"tok": secrets.token_urlsafe(32), "id": interview_id},
        )

    op.alter_column('interviews', 'access_token', nullable=False)
    op.create_index('ix_interviews_access_token', 'interviews', ['access_token'], unique=True)


def downgrade():
    op.drop_index('ix_interviews_access_token', table_name='interviews')
    op.drop_column('interviews', 'access_token')
