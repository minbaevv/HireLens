"""add invited value to candidatestatus enum

Revision ID: y4x8w3v72t6u
Revises: x3w7v2u61s5t
Create Date: 2026-07-27

Pilot feedback (Dinara): отдельный шаг "Приглашён на собеседование"
(живое/очное) между "Оценены" и "Принят" + колонка в Kanban.
Postgres 16: ADD VALUE можно выполнять внутри транзакции (значение не
используется в этой же транзакции); IF NOT EXISTS делает миграцию идемпотентной.
"""
from alembic import op

revision = "y4x8w3v72t6u"
down_revision = "x3w7v2u61s5t"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE candidatestatus ADD VALUE IF NOT EXISTS 'invited'")


def downgrade():
    # Postgres не поддерживает штатное удаление значения enum — no-op.
    pass
