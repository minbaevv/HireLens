"""D2 — Публичный REST API (v1) для интеграций.

Авторизация — по API-ключу (заголовок X-API-Key), см. deps.get_api_company.
Эндпоинты read-only и строго изолированы по компании владельца ключа.
Ответы намеренно компактны (без внутренних полей anti-cheat/bias reasoning).
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_api_company
from app.core.db import get_db
from app.models.models import Candidate, Company, Job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["public-api"])


# ---------- schemas ----------
class JobOut(BaseModel):
    id: int
    title: str
    description: str
    requirements: str
    language: str
    is_active: bool
    apply_url: Optional[str] = None
    created_at: Optional[str] = None


class CandidateOut(BaseModel):
    id: int
    job_id: int
    name: str
    email: str
    status: str
    overall_score: Optional[float] = None
    recommendation: Optional[str] = None
    created_at: Optional[str] = None


class PingOut(BaseModel):
    ok: bool
    company_id: int
    company: str


def _job_out(job: Job) -> JobOut:
    from app.core.config import settings

    return JobOut(
        id=job.id,
        title=job.title,
        description=job.description,
        requirements=job.requirements,
        language=job.language or "ru",
        is_active=bool(job.is_active),
        apply_url=f"{settings.FRONTEND_URL}/apply/{job.apply_token}" if job.apply_token else None,
        created_at=job.created_at.isoformat() if job.created_at else None,
    )


def _candidate_out(c: Candidate) -> CandidateOut:
    return CandidateOut(
        id=c.id,
        job_id=c.job_id,
        name=c.name,
        email=c.email,
        status=c.status.value if hasattr(c.status, "value") else str(c.status),
        overall_score=c.score,
        recommendation=c.recommendation,
        created_at=c.created_at.isoformat() if c.created_at else None,
    )


# ---------- endpoints ----------
@router.get("/ping", response_model=PingOut, summary="Проверка API-ключа")
def ping(company: Company = Depends(get_api_company)) -> PingOut:
    return PingOut(ok=True, company_id=company.id, company=company.name)


@router.get("/jobs", response_model=List[JobOut], summary="Список вакансий")
def list_jobs(
    active: Optional[bool] = Query(default=None, description="Фильтр по активности"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    company: Company = Depends(get_api_company),
) -> List[JobOut]:
    q = db.query(Job).filter(Job.company_id == company.id)
    if active is not None:
        q = q.filter(Job.is_active.is_(active))
    jobs = q.order_by(Job.id.desc()).offset(offset).limit(limit).all()
    return [_job_out(j) for j in jobs]


@router.get("/jobs/{job_id}", response_model=JobOut, summary="Вакансия по id")
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    company: Company = Depends(get_api_company),
) -> JobOut:
    job = (
        db.query(Job)
        .filter(Job.id == job_id, Job.company_id == company.id)
        .first()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вакансия не найдена")
    return _job_out(job)


@router.get("/candidates", response_model=List[CandidateOut], summary="Список кандидатов")
def list_candidates(
    job_id: Optional[int] = Query(default=None, description="Фильтр по вакансии"),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    company: Company = Depends(get_api_company),
) -> List[CandidateOut]:
    q = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Job.company_id == company.id)
    )
    if job_id is not None:
        q = q.filter(Candidate.job_id == job_id)
    if status_filter:
        q = q.filter(Candidate.status == status_filter)
    cands = q.order_by(Candidate.id.desc()).offset(offset).limit(limit).all()
    return [_candidate_out(c) for c in cands]


@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateOut,
    summary="Кандидат по id",
)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    company: Company = Depends(get_api_company),
) -> CandidateOut:
    c = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Candidate.id == candidate_id, Job.company_id == company.id)
        .first()
    )
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кандидат не найден")
    return _candidate_out(c)
