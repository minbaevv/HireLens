"""add google_credentials, scheduled_interviews (B4 — Google Calendar)

Revision ID: t9s3r8q27o1p
Revises: s8q2o7r06n1p
Create Date: 2026-07-15
"""
from alembic import op
import sqlalchemy as sa

revision = "t9s3r8q27o1p"
down_revision = "s8q2o7r06n1p"
branch_labels = None
depends_on = None


def upgrade():
    # — OAuth-креды Google (одна запись на компанию) —
    op.create_table(
        "google_credentials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("google_email", sa.String(length=255), nullable=True),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expiry", sa.DateTime(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_google_credentials_company_id", "google_credentials", ["company_id"], unique=True
    )

    # — Запланированные интервью —
    op.create_table(
        "scheduled_interviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidates.id"), nullable=False),
        sa.Column("job_id", sa.Integer(), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="Interview"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("google_event_id", sa.String(length=255), nullable=True),
        sa.Column("meet_link", sa.String(length=512), nullable=True),
        sa.Column("html_link", sa.String(length=512), nullable=True),
        sa.Column("attendees", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="scheduled"),
        sa.Column("created_by_email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_scheduled_interviews_company_id", "scheduled_interviews", ["company_id"])
    op.create_index("ix_scheduled_interviews_candidate_id", "scheduled_interviews", ["candidate_id"])
    op.create_index(
        "ix_scheduled_interviews_google_event_id", "scheduled_interviews", ["google_event_id"]
    )


def downgrade():
    op.drop_index("ix_scheduled_interviews_google_event_id", table_name="scheduled_interviews")
    op.drop_index("ix_scheduled_interviews_candidate_id", table_name="scheduled_interviews")
    op.drop_index("ix_scheduled_interviews_company_id", table_name="scheduled_interviews")
    op.drop_table("scheduled_interviews")
    op.drop_index("ix_google_credentials_company_id", table_name="google_credentials")
    op.drop_table("google_credentials")
