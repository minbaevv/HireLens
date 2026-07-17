"""Вебхук для получения обновлений от Telegram."""
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.services.telegram_bot import handle_update, set_webhook
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Telegram отправляет сюда все сообщения от пользователей.

    SEC-2: подлинность проверяется заголовком X-Telegram-Bot-Api-Secret-Token,
    который Telegram присылает, если вебхук зарегистрирован с secret_token.
    """
    if settings.TELEGRAM_WEBHOOK_SECRET:
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not secrets.compare_digest(header_secret, settings.TELEGRAM_WEBHOOK_SECRET):
            logger.warning("Telegram webhook: неверный секрет — запрос отклонён")
            raise HTTPException(status_code=403, detail="Forbidden")
    try:
        update = await request.json()
        handle_update(update, db)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return {"ok": True}


@router.get("/set-webhook")
def register_webhook():
    """Registers webhook for HR bot (TELEGRAM_BOT_TOKEN)."""
    from app.services.telegram import _send
    url = settings.TELEGRAM_WEBHOOK_URL
    if not url:
        return {"ok": False, "error": "TELEGRAM_WEBHOOK_URL not set in .env"}
    ok = set_webhook(url, token=settings.TELEGRAM_BOT_TOKEN)
    return {"ok": ok, "webhook_url": url, "bot": "hr"}


@router.get("/set-candidate-webhook")
def register_candidate_webhook():
    """Registers webhook for candidate bot (TELEGRAM_CANDIDATE_BOT_TOKEN)."""
    import httpx
    token = settings.TELEGRAM_CANDIDATE_BOT_TOKEN
    url = settings.TELEGRAM_WEBHOOK_URL
    if not token:
        return {"ok": False, "error": "TELEGRAM_CANDIDATE_BOT_TOKEN not set in .env"}
    if not url:
        return {"ok": False, "error": "TELEGRAM_WEBHOOK_URL not set in .env"}
    try:
        payload = {"url": url}
        if settings.TELEGRAM_WEBHOOK_SECRET:
            payload["secret_token"] = settings.TELEGRAM_WEBHOOK_SECRET
        resp = httpx.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json=payload,
            timeout=10,
        )
        result = resp.json()
        ok = result.get("ok", False)
        logger.info(f"Candidate webhook set to {url}: {ok}")
        return {"ok": ok, "webhook_url": url, "bot": "candidate"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
