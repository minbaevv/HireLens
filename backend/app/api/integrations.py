"""D2 — управление интеграциями: API-ключи и webhooks.

Авторизация — обычный JWT пользователь (только admin, см. require_admin).
Здесь компания выпускает/отзывает API-ключи и настраивает webhooks.
Полный API-ключ и secret webhook показываются ОДИН раз при создании.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import CurrentActor, require_admin
from app.core.audit import actor_fields, record_audit
from app.core.db import get_db
from app.core.security import generate_api_key
from app.models.api_key import ApiKey
from app.models.webhook import Webhook, WebhookDelivery
from app.services import webhook_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/integrations", tags=["integrations"])


# ============ API KEYS ============
class ApiKeyCreate(BaseModel):
    name: str = Field(default="API key", min_length=1, max_length=120)


class ApiKeyOut(BaseModel):
    id: int
    name: str
    prefix: str
    scopes: str
    revoked: bool
    last_used_at: Optional[str] = None
    created_at: Optional[str] = None


class ApiKeyCreated(ApiKeyOut):
    # Полный ключ — только в ответе на создание, больше нигде не возвращается.
    key: str


def _key_out(k: ApiKey) -> ApiKeyOut:
    return ApiKeyOut(
        id=k.id,
        name=k.name,
        prefix=k.prefix,
        scopes=k.scopes,
        revoked=bool(k.revoked),
        last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
        created_at=k.created_at.isoformat() if k.created_at else None,
    )


@router.get("/api-keys", response_model=List[ApiKeyOut], summary="Список API-ключей")
def list_api_keys(
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> List[ApiKeyOut]:
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.company_id == actor.company.id)
        .order_by(ApiKey.id.desc())
        .all()
    )
    return [_key_out(k) for k in keys]


@router.post(
    "/api-keys",
    response_model=ApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Создать API-ключ (полный ключ показывается один раз)",
)
def create_api_key(
    payload: ApiKeyCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> ApiKeyCreated:
    full_key, prefix, hashed = generate_api_key()
    key = ApiKey(
        company_id=actor.company.id,
        name=payload.name.strip() or "API key",
        prefix=prefix,
        hashed_key=hashed,
        scopes="read",
        revoked=False,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    record_audit(
        db,
        company_id=actor.company.id,
        action="api_key.create",
        entity_type="api_key",
        entity_id=key.id,
        detail={"name": key.name, "prefix": key.prefix},
        request=request,
        **actor_fields(actor),
    )
    out = _key_out(key).model_dump()
    out["key"] = full_key
    return ApiKeyCreated(**out)


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_200_OK,
    summary="Отозвать API-ключ",
)
def revoke_api_key(
    key_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> dict:
    key = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.company_id == actor.company.id)
        .first()
    )
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ключ не найден")
    key.revoked = True
    db.commit()
    record_audit(
        db,
        company_id=actor.company.id,
        action="api_key.revoke",
        entity_type="api_key",
        entity_id=key.id,
        request=request,
        **actor_fields(actor),
    )
    return {"ok": True, "revoked": True}


# ============ WEBHOOKS ============
class WebhookCreate(BaseModel):
    url: str = Field(min_length=1, max_length=512)
    events: List[str] = Field(default_factory=list)


class WebhookUpdate(BaseModel):
    url: Optional[str] = Field(default=None, max_length=512)
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None


class WebhookOut(BaseModel):
    id: int
    url: str
    events: List[str]
    is_active: bool
    failure_count: int
    last_status: Optional[int] = None
    last_delivery_at: Optional[str] = None
    created_at: Optional[str] = None


class WebhookCreated(WebhookOut):
    # secret показывается один раз при создании.
    secret: str


class DeliveryOut(BaseModel):
    id: int
    event: str
    success: bool
    status_code: Optional[int] = None
    error: Optional[str] = None
    created_at: Optional[str] = None


def _events_list(webhook: Webhook) -> List[str]:
    return [e.strip() for e in (webhook.events or "").split(",") if e.strip()]


def _webhook_out(w: Webhook) -> WebhookOut:
    return WebhookOut(
        id=w.id,
        url=w.url,
        events=_events_list(w),
        is_active=bool(w.is_active),
        failure_count=w.failure_count or 0,
        last_status=w.last_status,
        last_delivery_at=w.last_delivery_at.isoformat() if w.last_delivery_at else None,
        created_at=w.created_at.isoformat() if w.created_at else None,
    )


@router.get("/webhooks/events", response_model=List[str], summary="Список поддерживаемых событий")
def list_supported_events(
    actor: CurrentActor = Depends(require_admin),
) -> List[str]:
    return list(webhook_service.SUPPORTED_EVENTS)


@router.get("/webhooks", response_model=List[WebhookOut], summary="Список webhooks")
def list_webhooks(
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> List[WebhookOut]:
    hooks = (
        db.query(Webhook)
        .filter(Webhook.company_id == actor.company.id)
        .order_by(Webhook.id.desc())
        .all()
    )
    return [_webhook_out(w) for w in hooks]


@router.post(
    "/webhooks",
    response_model=WebhookCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Создать webhook (secret показывается один раз)",
)
def create_webhook(
    payload: WebhookCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> WebhookCreated:
    try:
        url = webhook_service.validate_webhook_url(payload.url)
        events = webhook_service.normalize_events(payload.events)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    secret = webhook_service.generate_webhook_secret()
    hook = Webhook(
        company_id=actor.company.id,
        url=url,
        secret=secret,
        events=events,
        is_active=True,
    )
    db.add(hook)
    db.commit()
    db.refresh(hook)
    record_audit(
        db,
        company_id=actor.company.id,
        action="webhook.create",
        entity_type="webhook",
        entity_id=hook.id,
        detail={"url": hook.url, "events": events},
        request=request,
        **actor_fields(actor),
    )
    out = _webhook_out(hook).model_dump()
    out["secret"] = secret
    return WebhookCreated(**out)


@router.patch("/webhooks/{webhook_id}", response_model=WebhookOut, summary="Обновить webhook")
def update_webhook(
    webhook_id: int,
    payload: WebhookUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> WebhookOut:
    hook = (
        db.query(Webhook)
        .filter(Webhook.id == webhook_id, Webhook.company_id == actor.company.id)
        .first()
    )
    if hook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook не найден")
    try:
        if payload.url is not None:
            hook.url = webhook_service.validate_webhook_url(payload.url)
        if payload.events is not None:
            hook.events = webhook_service.normalize_events(payload.events)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    if payload.is_active is not None:
        hook.is_active = payload.is_active
    db.commit()
    db.refresh(hook)
    record_audit(
        db,
        company_id=actor.company.id,
        action="webhook.update",
        entity_type="webhook",
        entity_id=hook.id,
        request=request,
        **actor_fields(actor),
    )
    return _webhook_out(hook)


@router.delete("/webhooks/{webhook_id}", summary="Удалить webhook")
def delete_webhook(
    webhook_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> dict:
    hook = (
        db.query(Webhook)
        .filter(Webhook.id == webhook_id, Webhook.company_id == actor.company.id)
        .first()
    )
    if hook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook не найден")
    db.delete(hook)
    db.commit()
    record_audit(
        db,
        company_id=actor.company.id,
        action="webhook.delete",
        entity_type="webhook",
        entity_id=webhook_id,
        request=request,
        **actor_fields(actor),
    )
    return {"ok": True, "deleted": True}


@router.post("/webhooks/{webhook_id}/test", response_model=DeliveryOut, summary="Тестовая доставка")
def test_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> DeliveryOut:
    hook = (
        db.query(Webhook)
        .filter(Webhook.id == webhook_id, Webhook.company_id == actor.company.id)
        .first()
    )
    if hook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook не найден")
    record = webhook_service.deliver(
        db, hook, "interview.completed",
        {"test": True, "message": "HireLens webhook test"},
    )
    return DeliveryOut(
        id=record.id,
        event=record.event,
        success=record.success,
        status_code=record.status_code,
        error=record.error,
        created_at=record.created_at.isoformat() if record.created_at else None,
    )


@router.get(
    "/webhooks/{webhook_id}/deliveries",
    response_model=List[DeliveryOut],
    summary="Последние доставки",
)
def webhook_deliveries(
    webhook_id: int,
    limit: int = 20,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> List[DeliveryOut]:
    hook = (
        db.query(Webhook)
        .filter(Webhook.id == webhook_id, Webhook.company_id == actor.company.id)
        .first()
    )
    if hook is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook не найден")
    limit = max(1, min(limit, 100))
    rows = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_id == hook.id)
        .order_by(WebhookDelivery.id.desc())
        .limit(limit)
        .all()
    )
    return [
        DeliveryOut(
            id=r.id,
            event=r.event,
            success=r.success,
            status_code=r.status_code,
            error=r.error,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]
