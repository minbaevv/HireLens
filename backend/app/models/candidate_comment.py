"""Комментарии HR к кандидату (лента заметок).

Pilot feedback (Dinara): кандидат может подходить, но отказаться сам —
такие детали должны оставаться в системе, а не в памяти рекрутёра.
"""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.db import Base


class CandidateComment(Base):
    __tablename__ = "candidate_comments"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_name = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    candidate = relationship("Candidate")
