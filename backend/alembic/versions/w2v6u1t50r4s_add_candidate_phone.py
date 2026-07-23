"""add phone (WhatsApp) to candidates

Revision ID: w2v6u1t50r4s
Revises: v1u5t0s49q3r
Create Date: 2026-07-23

Pilot feedback (Dinara): собирать номер телефона/WhatsApp кандидата
в форме отклика, чтобы HR не выцарапывал его вручную из текста резюме.
"""
from alembic import op
import sqlalchemy as sa

revision = "w2v6u1t50r4s"
down_revision = "v1u5t0s49q3r"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("candidates", sa.Column("phone", sa.String(length=32), nullable=True))


def downgrade():
    op.drop_column("candidates", "phone")
