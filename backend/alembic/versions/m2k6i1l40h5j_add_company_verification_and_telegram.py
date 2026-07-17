"""add company email verification and telegram per-company fields

Revision ID: m2k6i1l40h5j
Revises: l0j4h9k28g3i
Create Date: 2026-07-09
"""
import secrets

import sqlalchemy as sa
from alembic import op

revision = "m2k6i1l40h5j"
down_revision = "l0j4h9k28g3i"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("companies", sa.Column("verification_code", sa.String(length=6), nullable=True))
    op.add_column("companies", sa.Column("verification_code_expires_at", sa.DateTime(), nullable=True))
    op.add_column("companies", sa.Column("telegram_chat_id", sa.String(length=64), nullable=True))
    op.add_column("companies", sa.Column("telegram_link_code", sa.String(length=32), nullable=True))
    op.create_index("ix_companies_telegram_link_code", "companies", ["telegram_link_code"], unique=True)

    # Существующие компании считаем подтверждёнными и выдаём им link-коды
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id FROM companies")).fetchall()
    for row in rows:
        bind.execute(
            sa.text(
                "UPDATE companies SET is_verified = true, telegram_link_code = :code WHERE id = :id"
            ),
            {"code": secrets.token_urlsafe(18)[:32], "id": row[0]},
        )

    op.alter_column("companies", "is_verified", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_companies_telegram_link_code", table_name="companies")
    op.drop_column("companies", "telegram_link_code")
    op.drop_column("companies", "telegram_chat_id")
    op.drop_column("companies", "verification_code_expires_at")
    op.drop_column("companies", "verification_code")
    op.drop_column("companies", "is_verified")
