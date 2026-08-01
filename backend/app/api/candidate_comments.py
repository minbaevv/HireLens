"""Лента комментариев HR по кандидату.

Старое поле hr_notes остаётся на месте (блок финального решения),
здесь — отдельные записи с автором и датой.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import CurrentActor, get_current_company, require_write_access
from app.core.db import get_db
from app.models.candidate_comment import CandidateComment
from app.models.models import Candidate, Company, Job

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/candidates", tags=["candidates"])

MAX_COMMENT_LENGTH = 1000


class CommentCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_COMMENT_LENGTH)


def _owned_candidate(db: Session, company_id: int, candidate_id: int) -> Candidate:
    candidate = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Job.company_id == company_id, Candidate.id == candidate_id)
        .first()
    )
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кандидат не найден",
        )
    return candidate


def _serialize(comment: CandidateComment) -> dict:
    created = comment.created_at
    return {
        "id": comment.id,
        "author_name": comment.author_name,
        "text": comment.text,
        "created_at": (created.isoformat() + "Z") if created is not None else None,
    }


def _actor_name(actor: CurrentActor) -> str:
    if actor.team_member is not None:
        return actor.team_member.name or actor.team_member.email
    return actor.company.name or actor.company.email


@router.get("/{candidate_id}/comments")
def list_comments(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company),
):
    _owned_candidate(db, current_company.id, candidate_id)
    comments = (
        db.query(CandidateComment)
        .filter(CandidateComment.candidate_id == candidate_id)
        .order_by(CandidateComment.created_at.desc(), CandidateComment.id.desc())
        .all()
    )
    return {"items": [_serialize(c) for c in comments]}


@router.post("/{candidate_id}/comments", status_code=status.HTTP_201_CREATED)
def create_comment(
    candidate_id: int,
    body: CommentCreate,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_write_access),
):
    _owned_candidate(db, actor.company.id, candidate_id)

    text = body.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Комментарий пуст",
        )

    comment = CandidateComment(
        candidate_id=candidate_id,
        author_name=_actor_name(actor)[:255],
        text=text[:MAX_COMMENT_LENGTH],
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return _serialize(comment)


@router.delete("/{candidate_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    candidate_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_write_access),
):
    _owned_candidate(db, actor.company.id, candidate_id)
    comment = (
        db.query(CandidateComment)
        .filter(
            CandidateComment.id == comment_id,
            CandidateComment.candidate_id == candidate_id,
        )
        .first()
    )
    if comment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Комментарий не найден",
        )
    db.delete(comment)
    db.commit()
    return None
