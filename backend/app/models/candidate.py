import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.db import Base


class CandidateStatus(str, enum.Enum):
    applied = "applied"
    interviewing = "interviewing"
    completed = "completed"
    invited = "invited"
    hired = "hired"
    rejected = "rejected"


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(32), nullable=True)  # WhatsApp/телефон кандидата (pilot feedback: Dinara)
    resume_text = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)  # необязательное фото кандидата (pilot: Dinara)
    status = Column(Enum(CandidateStatus), default=CandidateStatus.applied, nullable=False)
    score = Column(Float, nullable=True)
    pre_score = Column(Float, nullable=True)  # AI скрининг резюме до интервью

    # C5.1 — Structured Scoring
    technical_score = Column(Integer, nullable=True)
    soft_skills_score = Column(Integer, nullable=True)
    experience_score = Column(Integer, nullable=True)
    motivation_score = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)  # 0.0-1.0
    scoring_reasoning = Column(Text, nullable=True)  # JSON

    # C1 — Anti-cheat
    anti_cheat_score = Column(Float, nullable=True)  # 0-100, чем выше — подозрительнее
    anti_cheat_flags = Column(Text, nullable=True)  # JSON-список причин

    # C5.2 — Bias Detection
    bias_flags = Column(Text, nullable=True)  # JSON-список bias warnings

    # Priority 2 — cross-validation (расхождения резюме/интервью) + evasive answers
    cross_validation = Column(Text, nullable=True)  # JSON: {"discrepancies": [...], "evasive_answers": [...]}

    # Priority 2.2 — Answer Attribution: связь оценок с номерами вопросов и Message.id
    answer_attribution = Column(Text, nullable=True)  # JSON: {"questions": [...], "attribution": {...}}

    # Ground Truth Tracking (Phase 10/10 - 1.1)
    actual_hire_decision = Column(String(20), nullable=True)  # "hired" | "rejected_final" | "pending"
    ai_feedback = Column(String(20), nullable=True)  # "correct" | "incorrect" | "partial" | null
    hr_notes = Column(Text, nullable=True)  # Комментарий HR о финальном решении
    requires_manual_review = Column(Boolean, default=False, nullable=False)  # Low confidence flag

    # Массовые операции — теги (JSON-список строк)
    tags = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    recommendation = Column(String(20), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    job = relationship("Job", back_populates="candidates")
    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")
