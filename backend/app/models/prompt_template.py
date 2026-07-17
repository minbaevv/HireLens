"""Версионируемые системные промпты (Roadmap 6.2 — Prompt Versioning).

Позволяет менять промпты интервью/скоринга/скрининга из админ-панели без
деплоя, хранить историю версий и запускать A/B-тест между несколькими
активными вариантами одного ключа. Если для (company_id, prompt_key) нет ни
одной активной версии в БД — сервис откатывается на code-default из
app.ai.prompts (полная обратная совместимость).
"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.db import Base


class PromptTemplate(Base):
    """Одна версия одного промпта в рамках компании.

    - prompt_key: какой именно промпт (interview_system / scoring_system / prescreen).
    - version: авто-инкремент в пределах (company_id, prompt_key).
    - is_active: участвует ли версия в выдаче. Активных может быть несколько —
      тогда включается A/B-режим и выбор идёт случайно по весу ab_weight.
    """

    __tablename__ = "prompt_templates"
    __table_args__ = (
        UniqueConstraint("company_id", "prompt_key", "version", name="uq_prompt_company_key_version"),
    )

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    prompt_key = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    name = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    ab_weight = Column(Integer, nullable=False, default=1)
    created_by_email = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    company = relationship("Company")
