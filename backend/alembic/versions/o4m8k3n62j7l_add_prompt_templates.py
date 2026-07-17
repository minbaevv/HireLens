"""add prompt_templates (Roadmap 6.2 - Prompt Versioning)

Revision ID: o4m8k3n62j7l
Revises: n3l7j2m51i6k
Create Date: 2026-07-10 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "o4m8k3n62j7l"
down_revision = "n3l7j2m51i6k"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("prompt_key", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ab_weight", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "company_id", "prompt_key", "version", name="uq_prompt_company_key_version"
        ),
    )
    op.create_index("ix_prompt_templates_id", "prompt_templates", ["id"], unique=False)
    op.create_index("ix_prompt_templates_company_id", "prompt_templates", ["company_id"], unique=False)
    op.create_index("ix_prompt_templates_prompt_key", "prompt_templates", ["prompt_key"], unique=False)
    op.create_index("ix_prompt_templates_created_at", "prompt_templates", ["created_at"], unique=False)


def downgrade():
    op.drop_index("ix_prompt_templates_created_at", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_prompt_key", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_company_id", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_id", table_name="prompt_templates")
    op.drop_table("prompt_templates")
