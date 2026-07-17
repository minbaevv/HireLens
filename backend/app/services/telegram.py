"""Телеграм уведомления для HR."""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

RECOMMENDATION_EMOJI = {
    "hire": "✅",
    "maybe": "🟡",
    "reject": "❌",
}


def _send(chat_id: str, text: str) -> bool:
    """Отправляет сообщение в Telegram. Возвращает True если успешно."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token or not chat_id:
        logger.debug("Telegram не настроен, уведомление пропущено")
        return False
    try:
        url = TELEGRAM_API.format(token=token)
        resp = httpx.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.warning(f"Telegram ошибка: {e}")
        return False


def _resolve_hr_chat(company, chat_id: str = "") -> str:
    """chat_id для HR-уведомления с привязкой к компании (мультитенантность).

    Приоритет: явный chat_id -> company.telegram_chat_id. Глобальный
    settings.TELEGRAM_HR_CHAT_ID остаётся ТОЛЬКО как dev-fallback: в проде он
    слал бы данные о кандидатах всех компаний в один чат (утечка).
    """
    if chat_id:
        return chat_id
    if company is not None:
        # Явный контекст компании: только её chat_id, без глобального fallback (изоляция).
        return getattr(company, "telegram_chat_id", "") or ""
    if settings.ENVIRONMENT == "development" and settings.TELEGRAM_HR_CHAT_ID:
        return settings.TELEGRAM_HR_CHAT_ID
    return ""


def notify_new_candidate(
    candidate_name: str,
    candidate_email: str,
    job_title: str,
    company=None,
    chat_id: str = "",
) -> None:
    """Уведомляет HR о новом кандидате (per-company)."""
    target = _resolve_hr_chat(company, chat_id)
    if not target:
        logger.info("Telegram HR-чат не привязан к компании — уведомление о кандидате пропущено")
        return
    text = (
        f"📩 <b>Новый кандидат!</b>\n"
        f"👤 <b>Имя:</b> {candidate_name}\n"
        f"📧 <b>Email:</b> {candidate_email}\n"
        f"💼 <b>Вакансия:</b> {job_title}\n"
        f"\nИнтервью ещё не начато."
    )
    _send(target, text)


def notify_interview_complete(
    candidate_name: str,
    job_title: str,
    score: float,
    recommendation: str,
    summary: str,
    frontend_url: str,
    candidate_id: int,
    company=None,
    chat_id: str = "",
) -> None:
    """Уведомляет HR о завершённом интервью с оценкой (per-company)."""
    target = _resolve_hr_chat(company, chat_id)
    if not target:
        logger.info("Telegram HR-чат не привязан к компании — уведомление о результате пропущено")
        return
    emoji = RECOMMENDATION_EMOJI.get(recommendation, "🟡")
    base = (frontend_url or "http://localhost:3000").rstrip("/")
    link = f"{base}/candidates/{candidate_id}"
    text = (
        f"🎞️ <b>Интервью завершено!</b>\n"
        f"👤 <b>Кандидат:</b> {candidate_name}\n"
        f"💼 <b>Вакансия:</b> {job_title}\n"
        f"⭐ <b>Оценка:</b> {score:.0f}/100\n"
        f"{emoji} <b>Рекомендация:</b> {recommendation.upper()}\n"
        f"\n📝 <b>Резюме:</b> {summary}\n"
        f"\n🔗 <a href='{link}'>Открыть профиль</a>"
    )
    _send(target, text)
