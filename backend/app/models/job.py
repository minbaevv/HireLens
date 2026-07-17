import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.db import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=False)
    apply_token = Column(String(64), unique=True, index=True, default=lambda: uuid.uuid4().hex)
    # Язык вакансии и AI-интервью: ru | ky | en
    language = Column(String(5), default="ru", nullable=False, server_default="ru")
    # Priority 2: настраиваемые веса критериев скоринга (JSON или NULL = равные)
    # Формат: {"technical": 0.4, "soft": 0.2, "experience": 0.3, "motivation": 0.1}
    scoring_weights = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    company = relationship("Company", back_populates="jobs")
    candidates = relationship("Candidate", back_populates="job", cascade="all, delete-orphan")
