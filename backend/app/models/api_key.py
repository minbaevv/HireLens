"""D2 — Публичный API: API-ключи компаний.

Ключ показывается клиенту ОДИН раз при создании. В БД хранится только
SHA-256 хеш (hashed_key) и короткий префикс (prefix) для отображения в списке.
Полный ключ восстановить из хеша нельзя — при утере клиент выпускает новый.
"""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.db import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False, default="API key")
    prefix = Column(String(16), nullable=False, index=True)
    hashed_key = Column(String(128), nullable=False, unique=True, index=True)
    scopes = Column(String(120), nullable=False, default="read")
    last_used_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, server_default=func.now())

    company = relationship("Company")
