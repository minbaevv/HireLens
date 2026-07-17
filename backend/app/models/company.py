import secrets

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.db import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    plan = Column(String(50), default="free", nullable=False)
    # Ручное управление подпиской: дата окончания платного тарифа (NULL = бессрочно/free)
    plan_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # SEC-11: подтверждение email
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_code = Column(String(6), nullable=True)
    verification_code_expires_at = Column(DateTime, nullable=True)

    # Telegram HR-уведомления, привязанные к компании (мультитенантность)
    telegram_chat_id = Column(String(64), nullable=True)
    telegram_link_code = Column(
        String(32), unique=True, nullable=True,
        default=lambda: secrets.token_urlsafe(18)[:32],
    )

    # D3: реферальная программа
    referral_code = Column(
        String(16), unique=True, nullable=True, index=True,
        default=lambda: secrets.token_urlsafe(6)[:8],
    )
    referred_by_company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)

    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")
    team_members = relationship("TeamMember", back_populates="company", cascade="all, delete-orphan")
