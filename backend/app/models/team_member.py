"""Участник команды компании с ролью (B1 — командный доступ).

В отличие от Company (владелец аккаунта, всегда admin), TeamMember —
приглашённый сотрудник с ограниченными правами. До принятия приглашения
(is_active=False) у участника нет пароля — он задаётся в POST /team/accept-invite.
"""
import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.db import Base


class TeamRole(str, enum.Enum):
    admin = "admin"
    recruiter = "recruiter"
    viewer = "viewer"


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    role = Column(Enum(TeamRole), default=TeamRole.recruiter, nullable=False)
    invite_token = Column(String(64), unique=True, index=True, nullable=True, default=lambda: uuid.uuid4().hex)
    is_active = Column(Boolean, default=False, nullable=False)
    invited_at = Column(DateTime, server_default=func.now())
    accepted_at = Column(DateTime, nullable=True)

    company = relationship("Company", back_populates="team_members")
