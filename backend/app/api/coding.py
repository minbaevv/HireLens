"""GAP-5 — Coding-ассессменты: HR-управление + публичный поток кандидата."""
import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import CurrentActor, get_current_company, require_write_access
from app.core.audit import actor_fields, record_audit
from app.core.db import get_db
from app.models.coding import CodingChallenge, CodingSubmission
from app.models.models import Candidate, Company, Job
from app.services.coding_eval import evaluate_submission

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/coding", tags=["coding"])
public_router = APIRouter(prefix="/coding/public", tags=["coding-public"])


# ---------- schemas ----------
class ChallengeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    language: str = "python"
    difficulty: str = "medium"
    starter_code: Optional[str] = None
    reference_solution: Optional[str] = None
    required_keywords: Optional[List[str]] = None
    max_score: int = Field(default=100, ge=1, le=1000)
    time_limit_minutes: Optional[int] = Field(default=None, ge=1, le=600)


class ChallengeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = None
    difficulty: Optional[str] = None
    starter_code: Optional[str] = None
    reference_solution: Optional[str] = None
    required_keywords: Optional[List[str]] = None
    max_score: Optional[int] = Field(default=None, ge=1, le=1000)
    time_limit_minutes: Optional[int] = Field(default=None, ge=1, le=600)
    is_active: Optional[bool] = None


class ChallengeOut(BaseModel):
    id: int
    title: str
    description: str
    language: str
    difficulty: str
    starter_code: Optional[str]
    reference_solution: Optional[str]
    required_keywords: Optional[List[str]]
    max_score: int
    time_limit_minutes: Optional[int]
    is_active: bool
    created_at: Optional[str]


class AssignRequest(BaseModel):
    challenge_id: int
    candidate_id: int


class ReviewRequest(BaseModel):
    manual_score: int = Field(ge=0, le=1000)
    reviewer_notes: Optional[str] = None


class SubmissionOut(BaseModel):
    id: int
    challenge_id: int
    candidate_id: int
    status: str
    access_token: str
    language: Optional[str]
    submitted_code: Optional[str]
    auto_score: Optional[float]
    auto_feedback: Optional[dict]
    requires_manual_review: bool
    manual_score: Optional[int]
    reviewer_notes: Optional[str]
    assigned_at: Optional[str]
    submitted_at: Optional[str]
    reviewed_at: Optional[str]


class PublicChallengeOut(BaseModel):
    title: str
    description: str
    language: str
    difficulty: str
    starter_code: Optional[str]
    time_limit_minutes: Optional[int]
    max_score: int
    status: str


class SubmitRequest(BaseModel):
    code: str = Field(min_length=1)


class SubmitResponse(BaseModel):
    status: str
    message: str


# ---------- helpers ----------
def _challenge_out(c: CodingChallenge) -> ChallengeOut:
    return ChallengeOut(
        id=c.id,
        title=c.title,
        description=c.description,
        language=c.language,
        difficulty=c.difficulty,
        starter_code=c.starter_code,
        reference_solution=c.reference_solution,
        required_keywords=json.loads(c.required_keywords) if c.required_keywords else None,
        max_score=c.max_score,
        time_limit_minutes=c.time_limit_minutes,
        is_active=c.is_active,
        created_at=c.created_at.isoformat() if c.created_at else None,
    )


def _submission_out(s: CodingSubmission) -> SubmissionOut:
    return SubmissionOut(
        id=s.id,
        challenge_id=s.challenge_id,
        candidate_id=s.candidate_id,
        status=s.status,
        access_token=s.access_token,
        language=s.language,
        submitted_code=s.submitted_code,
        auto_score=s.auto_score,
        auto_feedback=json.loads(s.auto_feedback) if s.auto_feedback else None,
        requires_manual_review=s.requires_manual_review,
        manual_score=s.manual_score,
        reviewer_notes=s.reviewer_notes,
        assigned_at=s.assigned_at.isoformat() if s.assigned_at else None,
        submitted_at=s.submitted_at.isoformat() if s.submitted_at else None,
        reviewed_at=s.reviewed_at.isoformat() if s.reviewed_at else None,
    )


def _get_owned_challenge_or_404(challenge_id: int, company: Company, db: Session) -> CodingChallenge:
    c = (
        db.query(CodingChallenge)
        .filter(CodingChallenge.id == challenge_id, CodingChallenge.company_id == company.id)
        .first()
    )
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    return c


def _get_owned_submission_or_404(submission_id: int, company: Company, db: Session) -> CodingSubmission:
    s = (
        db.query(CodingSubmission)
        .filter(CodingSubmission.id == submission_id, CodingSubmission.company_id == company.id)
        .first()
    )
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отправка не найдена")
    return s


def _get_submission_by_token(token: str, db: Session) -> CodingSubmission:
    s = db.query(CodingSubmission).filter(CodingSubmission.access_token == token).first()
    if s is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задание не найдено")
    return s


# ---------- HR: challenges ----------
@router.post("/challenges", response_model=ChallengeOut, status_code=status.HTTP_201_CREATED)
def create_challenge(
    data: ChallengeCreate,
    actor: CurrentActor = Depends(require_write_access),
    db: Session = Depends(get_db),
):
    c = CodingChallenge(
        company_id=actor.company.id,
        title=data.title,
        description=data.description,
        language=data.language,
        difficulty=data.difficulty,
        starter_code=data.starter_code,
        reference_solution=data.reference_solution,
        required_keywords=json.dumps(data.required_keywords, ensure_ascii=False)
        if data.required_keywords
        else None,
        max_score=data.max_score,
        time_limit_minutes=data.time_limit_minutes,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    logger.info("Создана coding-задача id=%s company_id=%s", c.id, actor.company.id)
    record_audit(
        db,
        company_id=actor.company.id,
        action="coding.challenge_create",
        entity_type="coding_challenge",
        entity_id=c.id,
        detail={"title": c.title},
        **actor_fields(actor),
    )
    return _challenge_out(c)


@router.get("/challenges", response_model=List[ChallengeOut])
def list_challenges(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company),
):
    q = db.query(CodingChallenge).filter(CodingChallenge.company_id == company.id)
    if not include_inactive:
        q = q.filter(CodingChallenge.is_active.is_(True))
    rows = q.order_by(CodingChallenge.created_at.desc()).all()
    return [_challenge_out(c) for c in rows]


@router.get("/challenges/{challenge_id}", response_model=ChallengeOut)
def get_challenge(
    challenge_id: int,
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company),
):
    return _challenge_out(_get_owned_challenge_or_404(challenge_id, company, db))


@router.patch("/challenges/{challenge_id}", response_model=ChallengeOut)
def update_challenge(
    challenge_id: int,
    data: ChallengeUpdate,
    actor: CurrentActor = Depends(require_write_access),
    db: Session = Depends(get_db),
):
    c = _get_owned_challenge_or_404(challenge_id, actor.company, db)
    fields = data.model_dump(exclude_unset=True)
    for key, value in fields.items():
        if key == "required_keywords":
            c.required_keywords = json.dumps(value, ensure_ascii=False) if value else None
        else:
            setattr(c, key, value)
    db.commit()
    db.refresh(c)
    record_audit(
        db,
        company_id=actor.company.id,
        action="coding.challenge_update",
        entity_type="coding_challenge",
        entity_id=c.id,
        **actor_fields(actor),
    )
    return _challenge_out(c)


@router.delete("/challenges/{challenge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_challenge(
    challenge_id: int,
    actor: CurrentActor = Depends(require_write_access),
    db: Session = Depends(get_db),
):
    c = _get_owned_challenge_or_404(challenge_id, actor.company, db)
    cid = c.id
    db.delete(c)
    db.commit()
    record_audit(
        db,
        company_id=actor.company.id,
        action="coding.challenge_delete",
        entity_type="coding_challenge",
        entity_id=cid,
        **actor_fields(actor),
    )
    return None


# ---------- HR: assign & submissions ----------
@router.post("/assign", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
def assign_challenge(
    data: AssignRequest,
    actor: CurrentActor = Depends(require_write_access),
    db: Session = Depends(get_db),
):
    challenge = _get_owned_challenge_or_404(data.challenge_id, actor.company, db)
    candidate = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Candidate.id == data.candidate_id, Job.company_id == actor.company.id)
        .first()
    )
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кандидат не найден")
    sub = CodingSubmission(
        challenge_id=challenge.id,
        candidate_id=candidate.id,
        company_id=actor.company.id,
        language=challenge.language,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    logger.info("Назначена coding-задача challenge_id=%s candidate_id=%s", challenge.id, candidate.id)
    record_audit(
        db,
        company_id=actor.company.id,
        action="coding.assign",
        entity_type="coding_submission",
        entity_id=sub.id,
        detail={"challenge_id": challenge.id, "candidate_id": candidate.id},
        **actor_fields(actor),
    )
    return _submission_out(sub)


@router.get("/submissions", response_model=List[SubmissionOut])
def list_submissions(
    candidate_id: Optional[int] = None,
    challenge_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company),
):
    q = db.query(CodingSubmission).filter(CodingSubmission.company_id == company.id)
    if candidate_id is not None:
        q = q.filter(CodingSubmission.candidate_id == candidate_id)
    if challenge_id is not None:
        q = q.filter(CodingSubmission.challenge_id == challenge_id)
    if status_filter:
        q = q.filter(CodingSubmission.status == status_filter)
    rows = q.order_by(CodingSubmission.assigned_at.desc()).all()
    return [_submission_out(s) for s in rows]


@router.get("/submissions/{submission_id}", response_model=SubmissionOut)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company),
):
    return _submission_out(_get_owned_submission_or_404(submission_id, company, db))


@router.post("/submissions/{submission_id}/review", response_model=SubmissionOut)
def review_submission(
    submission_id: int,
    data: ReviewRequest,
    actor: CurrentActor = Depends(require_write_access),
    db: Session = Depends(get_db),
):
    s = _get_owned_submission_or_404(submission_id, actor.company, db)
    s.manual_score = data.manual_score
    s.reviewer_notes = data.reviewer_notes
    s.requires_manual_review = False
    s.status = "reviewed"
    s.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    record_audit(
        db,
        company_id=actor.company.id,
        action="coding.review",
        entity_type="coding_submission",
        entity_id=s.id,
        detail={"manual_score": data.manual_score},
        **actor_fields(actor),
    )
    return _submission_out(s)


# ---------- public: candidate flow (token) ----------
@public_router.get("/{token}", response_model=PublicChallengeOut)
def public_get_challenge(token: str, db: Session = Depends(get_db)):
    sub = _get_submission_by_token(token, db)
    c = sub.challenge
    return PublicChallengeOut(
        title=c.title,
        description=c.description,
        language=c.language,
        difficulty=c.difficulty,
        starter_code=c.starter_code,
        time_limit_minutes=c.time_limit_minutes,
        max_score=c.max_score,
        status=sub.status,
    )


@public_router.post("/{token}/submit", response_model=SubmitResponse)
def public_submit(token: str, data: SubmitRequest, db: Session = Depends(get_db)):
    sub = _get_submission_by_token(token, db)
    if sub.status == "reviewed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Задание уже проверено, повторная отправка недоступна",
        )
    challenge = sub.challenge
    kws = json.loads(challenge.required_keywords) if challenge.required_keywords else None
    result = evaluate_submission(data.code, challenge.language, kws, challenge.max_score)
    sub.submitted_code = data.code
    sub.language = challenge.language
    sub.auto_score = result["auto_score"]
    sub.auto_feedback = json.dumps(result["feedback"], ensure_ascii=False)
    sub.requires_manual_review = result["requires_manual_review"]
    sub.status = "submitted"
    sub.submitted_at = datetime.utcnow()
    db.commit()
    logger.info("Получено решение coding submission_id=%s", sub.id)
    return SubmitResponse(
        status="submitted", message="Решение получено. HR рассмотрит его вручную."
    )
