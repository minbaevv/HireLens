import enum
import secrets

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.db import Base
from sqlalchemy import func


def _generate_access_token() -> str:
    """SEC-1: непредсказуемый токен доступа кандидата к своему интервью."""
    return secrets.token_urlsafe(32)


class InterviewStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class MessageRole(str, enum.Enum):
    ai = "ai"
    user = "user"


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False)
    # SEC-1: токен доступа кандидата — защита от IDOR по последовательному id
    access_token = Column(
        String(64), nullable=False, unique=True, index=True, default=_generate_access_token
    )
    status = Column(Enum(InterviewStatus), default=InterviewStatus.pending, nullable=False)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    candidate = relationship("Candidate", back_populates="interviews")
    messages = relationship("Message", back_populates="interview", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    video_url = Column(String(500), nullable=True)  # C2: путь к видеофайлу
    video_duration = Column(Float, nullable=True)  # C2: длительность видео в секундах
    video_analysis = Column(Text, nullable=True)  # C2: JSON результат Claude Vision
    created_at = Column(DateTime, server_default=func.now())

    interview = relationship("Interview", back_populates="messages")
