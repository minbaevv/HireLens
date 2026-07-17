"""B4 — Google Calendar: OAuth-креды компании + запланированные интервью.

GoogleCredential — OAuth-токены компании (одна интеграция на компанию).
ScheduledInterview — созданное в Google Calendar событие интервью со ссылкой
на Google Meet, привязанное к кандидату. Время хранится в UTC-naive.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.db import Base


class GoogleCredential(Base):
    __tablename__ = "google_credentials"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, unique=True, index=True)
    google_email = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)  # UTC-naive
    scope = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    company = relationship("Company")


class ScheduledInterview(Base):
    __tablename__ = "scheduled_interviews"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    title = Column(String(255), nullable=False, default="Interview")
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False)  # UTC-naive
    end_time = Column(DateTime, nullable=False)  # UTC-naive
    google_event_id = Column(String(255), nullable=True, index=True)
    meet_link = Column(String(512), nullable=True)
    html_link = Column(String(512), nullable=True)
    attendees = Column(Text, nullable=True)  # JSON-список email
    status = Column(String(20), nullable=False, default="scheduled")  # scheduled | cancelled
    created_by_email = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    company = relationship("Company")
    candidate = relationship("Candidate")
