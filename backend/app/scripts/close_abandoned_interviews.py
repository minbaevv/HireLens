"""Закрывает брошенные интервью.

Кандидат может открыть интервью, ответить на часть вопросов и закрыть вкладку.
Проверка лимита времени срабатывает только в момент, когда кандидат присылает
следующий ответ, поэтому такая запись навсегда остаётся в статусе in_progress:
ответы не оцениваются, а кандидат висит в воронке в статусе «Интервью».

Скрипт находит такие интервью и завершает их штатной функцией finish_interview:
ставится закрывающее сообщение, запускается оценка тех ответов, которые есть,
кандидат переходит в «Оценены».

Запуск на сервере из каталога проекта:

    docker compose exec -T backend python -m app.scripts.close_abandoned_interviews

Идемпотентно: интервью, которые идут нормально или уже завершены, не трогаются.
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime, timedelta

from app.ai.interview_service import finish_interview
from app.core.config import settings
from app.core.db import SessionLocal
from app.models.interview import Interview, InterviewStatus

# Запас поверх лимита времени: не закрываем тех, кто только что упёрся в лимит
# и прямо сейчас дожимает последний ответ.
GRACE_MINUTES = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("close_abandoned")


def main() -> int:
    limit = getattr(settings, "INTERVIEW_TIME_LIMIT_MINUTES", 0) or 0
    if limit <= 0:
        logger.info("Лимит времени интервью выключен — закрывать нечего.")
        return 0

    stale_after = limit + GRACE_MINUTES
    # started_at хранится в UTC без таймзоны — порог тоже делаем naive UTC.
    threshold = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=stale_after)

    db = SessionLocal()
    closed = 0
    failed = 0
    try:
        stale = (
            db.query(Interview)
            .filter(
                Interview.status == InterviewStatus.in_progress,
                Interview.started_at.isnot(None),
                Interview.started_at < threshold,
            )
            .order_by(Interview.id)
            .all()
        )
        logger.info(
            "Найдено брошенных интервью: %d (старше %d мин)",
            len(stale),
            stale_after,
        )
        for interview in stale:
            interview_id = interview.id
            try:
                finish_interview(interview_id, db)
                closed += 1
                logger.info("Интервью #%s закрыто и отправлено на оценку", interview_id)
            except Exception as err:  # noqa: BLE001 — одно падение не должно рвать весь прогон
                failed += 1
                db.rollback()
                logger.error("Интервью #%s закрыть не удалось: %s", interview_id, err)
    finally:
        db.close()

    logger.info("Готово. Закрыто: %d, ошибок: %d", closed, failed)
    return 1 if failed and closed == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
