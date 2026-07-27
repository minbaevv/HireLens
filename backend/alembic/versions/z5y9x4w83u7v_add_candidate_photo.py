"""add photo_url to candidates

Revision ID: z5y9x4w83u7v
Revises: y4x8w3v72t6u
Create Date: 2026-07-27

Pilot feedback (Dinara): рекрутёр хочет видеть, как выглядят кандидаты.
Фото необязательное (nullable): некоторые кандидаты стесняются.
"""
from alembic import op
import sqlalchemy as sa

revision = "z5y9x4w83u7v"
down_revision = "y4x8w3v72t6u"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("candidates", sa.Column("photo_url", sa.String(length=500), nullable=True))


def downgrade():
    op.drop_column("candidates", "photo_url")
