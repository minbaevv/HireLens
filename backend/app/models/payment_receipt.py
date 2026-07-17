"""Заявки на оплату переводом: загруженные чеки (ручной режим биллинга).

Клиент прикрепляет чек (скрин или PDF) на странице /billing. Суперадмин видит
заявку в /admin, открывает файл, проверяет и выставляет тариф вручную.
Файлы хранятся в uploads/receipts/<company_id>/.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.db import Base


class PaymentReceipt(Base):
    __tablename__ = "payment_receipts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    plan_requested = Column(String(50), nullable=False, default="starter")
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    content_type = Column(String(128), nullable=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    note = Column(Text, nullable=True)
    reviewed_by = Column(String(255), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    company = relationship("Company")
