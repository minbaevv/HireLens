"""Публичная careers-страница компании: список активных вакансий.

Публичный (без авторизации) эндпоинт для страницы /careers/{company_id} на фронте.
Отдаёт название компании и её активные вакансии со ссылками на подачу заявки —
используется существующий apply_token каждой вакансии (роут /apply/{token}).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.company import Company
from app.models.job import Job

router = APIRouter(prefix="/careers", tags=["careers"])


class CareersJob(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str
    language: str = "ru"
    apply_token: str


class CareersPageOut(BaseModel):
    company_name: str
    jobs: list[CareersJob]


@router.get(
    "/{company_id}",
    response_model=CareersPageOut,
    summary="Публичный список активных вакансий компании",
)
def get_company_careers(
    company_id: int,
    db: Session = Depends(get_db),
) -> CareersPageOut:
    """Публичная careers-страница: название компании + её активные вакансии."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Компания не найдена",
        )
    jobs = (
        db.query(Job)
        .filter(Job.company_id == company_id, Job.is_active == True)  # noqa: E712
        .order_by(Job.created_at.desc())
        .all()
    )
    return CareersPageOut(
        company_name=company.name,
        jobs=[CareersJob.model_validate(j) for j in jobs],
    )
