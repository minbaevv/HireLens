import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentActor, get_current_company, require_active_subscription, require_write_access
from app.api.schemas import JobCreate, JobOut, JobUpdate
from app.core.config import settings
from app.core.db import get_db
from app.core.audit import actor_fields, record_audit
from app.core.plans import enforce_job_quota
from app.models.models import Company, Job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


def _get_owned_job_or_404(job_id: int, company: Company, db: Session) -> Job:
    job = db.query(Job).filter(Job.id == job_id, Job.company_id == company.id).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вакансия не найдена")
    return job


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    data: JobCreate,
    actor: CurrentActor = Depends(require_write_access),
    _sub: Company = Depends(require_active_subscription),
    db: Session = Depends(get_db),
):
    # B5-lite: строгая проверка лимита вакансий тарифа (free=1, starter=3, pro=безлимит)
    enforce_job_quota(db, actor.company)

    job = Job(
        company_id=actor.company.id,
        title=data.title,
        description=data.description,
        requirements=data.requirements,
        language=data.language,
        scoring_weights=json.dumps(data.scoring_weights) if data.scoring_weights else None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    logger.info("Создана вакансия id=%s company_id=%s", job.id, actor.company.id)
    record_audit(db, company_id=actor.company.id, action="job.create", entity_type="job", entity_id=job.id, detail={"title": job.title}, **actor_fields(actor))

    return JobOut.from_job(job, settings.FRONTEND_URL)


@router.get("", response_model=list[JobOut])
def list_jobs(
    current_company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(Job)
        .filter(Job.company_id == current_company.id)
        .order_by(Job.created_at.desc())
        .all()
    )
    return [JobOut.from_job(job, settings.FRONTEND_URL) for job in jobs]


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: int,
    current_company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
):
    job = _get_owned_job_or_404(job_id, current_company, db)
    return JobOut.from_job(job, settings.FRONTEND_URL)


@router.patch("/{job_id}", response_model=JobOut)
def update_job(
    job_id: int,
    data: JobUpdate,
    actor: CurrentActor = Depends(require_write_access),
    db: Session = Depends(get_db),
):
    job = _get_owned_job_or_404(job_id, actor.company, db)

    update_data = data.model_dump(exclude_unset=True)
    if "scoring_weights" in update_data:
        sw = update_data.pop("scoring_weights")
        job.scoring_weights = json.dumps(sw) if sw else None
    for field, value in update_data.items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)

    logger.info("Обновлена вакансия id=%s company_id=%s", job.id, actor.company.id)
    record_audit(db, company_id=actor.company.id, action="job.update", entity_type="job", entity_id=job.id, **actor_fields(actor))

    return JobOut.from_job(job, settings.FRONTEND_URL)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    actor: CurrentActor = Depends(require_write_access),
    db: Session = Depends(get_db),
):
    job = _get_owned_job_or_404(job_id, actor.company, db)
    db.delete(job)
    db.commit()

    logger.info("Удалена вакансия id=%s company_id=%s", job_id, actor.company.id)
    record_audit(db, company_id=actor.company.id, action="job.delete", entity_type="job", entity_id=job_id, **actor_fields(actor))
