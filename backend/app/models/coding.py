"""GAP-5 — Coding-ассессменты (библиотека задач + отправки кандидатов).

CodingChallenge — переиспользуемая задача компании.
CodingSubmission — назначение задачи кандидату + его решение. Доступ кандидата
— по access_token (как у интервью, SEC-1), без авторизации.
"""
import secrets

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.db import Base


def _generate_access_token() -> str:
    return secrets.token_urlsafe(32)


class CodingChallenge(Base):
    __tablename__ = "coding_challenges"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    language = Column(String(32), nullable=False, default="python")
    difficulty = Column(String(16), nullable=False, default="medium")
    starter_code = Column(Text, nullable=True)
    reference_solution = Column(Text, nullable=True)
    required_keywords = Column(Text, nullable=True)  # JSON-список подстрок
    max_score = Column(Integer, nullable=False, default=100)
    time_limit_minutes = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())

    company = relationship("Company")
    submissions = relationship(
        "CodingSubmission", back_populates="challenge", cascade="all, delete-orphan"
    )


class CodingSubmission(Base):
    __tablename__ = "coding_submissions"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(Integer, ForeignKey("coding_challenges.id"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    access_token = Column(
        String(64), nullable=False, unique=True, index=True, default=_generate_access_token
    )
    status = Column(String(16), nullable=False, default="assigned")  # assigned/submitted/reviewed
    submitted_code = Column(Text, nullable=True)
    language = Column(String(32), nullable=True)
    auto_score = Column(Float, nullable=True)
    auto_feedback = Column(Text, nullable=True)  # JSON
    requires_manual_review = Column(Boolean, nullable=False, default=True)
    manual_score = Column(Integer, nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    assigned_at = Column(DateTime, server_default=func.now())
    submitted_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    challenge = relationship("CodingChallenge", back_populates="submissions")
    candidate = relationship("Candidate")
