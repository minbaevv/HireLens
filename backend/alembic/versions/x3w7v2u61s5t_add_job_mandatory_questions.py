"""add mandatory_questions to jobs

Revision ID: x3w7v2u61s5t
Revises: w2v6u1t50r4s
Create Date: 2026-07-23

Pilot feedback (Dinara): рекрутёр хочет задать свои обязательные
(предварительные) вопросы, которые AI обязан включить в интервью
(например: возраст, город проживания, учится или нет).
Храним как JSON-массив строк в TEXT (NULL = нет обязательных вопросов).
"""
from alembic import op
import sqlalchemy as sa

revision = "x3w7v2u61s5t"
down_revision = "w2v6u1t50r4s"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("mandatory_questions", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("jobs", "mandatory_questions")
