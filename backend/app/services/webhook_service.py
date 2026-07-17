"""D2 — доставка webhook-событий с HMAC-подписью и SSRF-защитой.

Безопасность:
- Каждый запрос подписывается HMAC-SHA256 (заголовок X-HireLens-Signature),
  чтобы получатель мог проверить подлинность и целостность тела.
- URL проверяется от SSRF: только http/https, в production — только https,
  приватные/loopback/link-local адреса блокируются.
- Доставка best-effort: ошибки никогда не пробрасываются в основной поток.
"""
import hashlib
import hmac
import ipaddress
import json
import logging
import socket
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.webhook import Webhook, WebhookDelivery

logger = logging.getLogger(__name__)

# Поддерживаемые события (для валидации подписок)
SUPPORTED_EVENTS = [
    "interview.completed",
    "candidate.scored",
    "candidate.created",
]

SIGNATURE_HEADER = "X-HireLens-Signature"
EVENT_HEADER = "X-HireLens-Event"
DELIVERY_HEADER = "X-HireLens-Delivery"


class WebhookUrlError(ValueError):
    """Некорректный или небезопасный URL webhook."""


def generate_webhook_secret() -> str:
    """Секрет для HMAC-подписи (показывается клиенту при создании)."""
    import secrets as _secrets

    return "whsec_" + _secrets.token_urlsafe(32)[:40]


def _is_blocked_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def validate_webhook_url(url: str) -> str:
    """Проверяет URL webhook. При ошибке бросает WebhookUrlError.

    Правила:
    - схема только http или https;
    - в production — только https;
    - приватные/loopback/link-local адреса запрещены (SSRF), кроме dev
      или явного WEBHOOK_ALLOW_PRIVATE_URLS=true.
    """
    raw = (url or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        raise WebhookUrlError("URL должен начинаться с http:// или https://")
    if not parsed.hostname:
        raise WebhookUrlError("Некорректный URL: отсутствует хост")
    if settings.ENVIRONMENT == "production" and parsed.scheme != "https":
        raise WebhookUrlError("В production webhook URL должен использовать https")

    allow_private = (
        settings.WEBHOOK_ALLOW_PRIVATE_URLS or settings.ENVIRONMENT != "production"
    )
    if not allow_private:
        try:
            infos = socket.getaddrinfo(parsed.hostname, None)
        except OSError:
            raise WebhookUrlError("Не удалось разрешить хост URL")
        for info in infos:
            ip = info[4][0]
            if _is_blocked_ip(ip):
                raise WebhookUrlError(
                    "URL указывает на приватный/локальный адрес — запрещено"
                )
    return raw


def normalize_events(events) -> str:
    """Приводит список/строку событий к нормализованной строке через запятую.

    Проверяет, что все события поддерживаются (либо "*"). Бросает ValueError.
    """
    if isinstance(events, str):
        items = [e.strip() for e in events.split(",")]
    else:
        items = [str(e).strip() for e in (events or [])]
    items = [e for e in items if e]
    if not items:
        raise ValueError("Укажите хотя бы одно событие")
    for e in items:
        if e != "*" and e not in SUPPORTED_EVENTS:
            raise ValueError(f"Неизвестное событие: {e}")
    seen = []
    for e in items:
        if e not in seen:
            seen.append(e)
    return ",".join(seen)


def sign_payload(secret: str, body: bytes) -> str:
    """HMAC-SHA256 подпись тела в формате 'sha256=<hex>'."""
    digest = hmac.new(
        (secret or "").encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return f"sha256={digest}"


def _subscribed(webhook: Webhook, event: str) -> bool:
    subs = {e.strip() for e in (webhook.events or "").split(",") if e.strip()}
    return "*" in subs or event in subs


def deliver(db: Session, webhook: Webhook, event: str, payload: dict) -> WebhookDelivery:
    """Отправляет одно событие на один webhook с повтором. Никогда не бросает.

    Пишет запись в webhook_deliveries и обновляет статус webhook.
    """
    import uuid

    delivery_id = str(uuid.uuid4())
    envelope = {
        "id": delivery_id,
        "event": event,
        "created_at": datetime.now(UTC).isoformat(),
        "data": payload,
    }
    body = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        EVENT_HEADER: event,
        DELIVERY_HEADER: delivery_id,
        SIGNATURE_HEADER: sign_payload(webhook.secret, body),
        "User-Agent": "HireLens-Webhook/1.0",
    }

    status_code = None
    error = None
    for attempt in range(1, 3):  # 2 попытки
        try:
            resp = httpx.post(
                webhook.url,
                content=body,
                headers=headers,
                timeout=settings.WEBHOOK_TIMEOUT_SECONDS,
            )
            status_code = resp.status_code
            if 200 <= resp.status_code < 300:
                error = None
                break
            error = f"HTTP {resp.status_code}"
        except Exception as e:  # сеть/таймаут/DNS
            error = str(e)[:500]

    success = status_code is not None and 200 <= status_code < 300
    record = WebhookDelivery(
        webhook_id=webhook.id,
        company_id=webhook.company_id,
        event=event,
        success=success,
        status_code=status_code,
        error=error,
    )
    webhook.last_status = status_code
    webhook.last_delivery_at = datetime.now(UTC)
    webhook.failure_count = 0 if success else (webhook.failure_count or 0) + 1
    try:
        db.add(record)
        db.commit()
    except Exception as e:
        logger.warning("Не удалось сохранить webhook delivery: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
    return record


def dispatch_event(db: Session, company_id: int, event: str, payload: dict) -> int:
    """Рассылает событие на все активные webhooks компании, подписанные на него.

    Best-effort: любые ошибки логируются, но не пробрасываются. Возвращает число
    попыток доставки.
    """
    if event not in SUPPORTED_EVENTS:
        logger.warning("dispatch_event: неизвестное событие %s", event)
        return 0
    try:
        hooks = (
            db.query(Webhook)
            .filter(Webhook.company_id == company_id, Webhook.is_active.is_(True))
            .all()
        )
    except Exception as e:
        logger.warning("dispatch_event: не удалось загрузить webhooks: %s", e)
        return 0

    count = 0
    for hook in hooks:
        if not _subscribed(hook, event):
            continue
        try:
            deliver(db, hook, event, payload)
            count += 1
        except Exception as e:  # перестраховка — deliver и так не бросает
            logger.warning("Ошибка доставки webhook #%s: %s", hook.id, e)
    return count
