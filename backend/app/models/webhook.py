"""D2 — Webhooks: подписки компаний на события + журнал доставок.

Компания регистрирует URL и список событий. При наступлении события мы
отправляем POST с JSON-телом, подписанным HMAC-SHA256 (заголовок
X-HireLens-Signature: sha256=<hex>). secret показывается клиенту при создании
и хранится для подписи запросов, чтобы получатель мог проверить подлинность.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.db import Base


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    url = Column(String(512), nullable=False)
    secret = Column(String(80), nullable=False)
    # Список событий через запятую ("*" = все поддерживаемые события)
    events = Column(Text, nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True)
    failure_count = Column(Integer, nullable=False, default=0)
    last_status = Column(Integer, nullable=True)
    last_delivery_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    company = relationship("Company")


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    event = Column(String(64), nullable=False)
    success = Column(Boolean, nullable=False, default=False)
    status_code = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
