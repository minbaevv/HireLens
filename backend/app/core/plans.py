"""B5-lite — enforcement лимитов тарифных планов.

Числа СИНХРОНИЗИРОВАНЫ с маркетингом на лендинге (app/api/landing.py):
    Free:    1 активная вакансия,    5 кандидатов/месяц
    Starter: 3 активные вакансии, 100 кандидатов/месяц
    Pro:     безлимит вакансий,   300 кандидатов/месяц

`None` означает «без лимита». Месяц считается по календарю (UTC), с 1-го числа.

Если платный тариф ИСТЁК (plan_expires_at в прошлом), компания откатывается
к free-лимитам — это согласуется с require_active_subscription в deps.py.
Примечание по Pro: «далее 45 сом за кандидата» (overage) требует платёжного
шлюза и пока НЕ подключено — 300 трактуется как жёсткий месячный лимит.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.candidate import Candidate
from app.models.job import Job

DEFAULT_PLAN = "free"

# max_active_jobs / max_candidates_per_month; None = безлимит
PLAN_LIMITS: dict[str, dict[str, Optional[int]]] = {
    "free":    {"max_active_jobs": 1,    "max_candidates_per_month": 5},
    "starter": {"max_active_jobs": 3,    "max_candidates_per_month": 100},
    "pro":     {"max_active_jobs": None, "max_candidates_per_month": 300},
}


def effective_plan(company) -> str:
    """Действующий тариф с учётом истечения срока.

    free — всегда free. Платный с истёкшим plan_expires_at откатывается к free.
    plan_expires_at == None у платного = бессрочный доступ (выдан вручную).
    """
    plan = (getattr(company, "plan", None) or DEFAULT_PLAN).lower()
    if plan not in PLAN_LIMITS or plan == DEFAULT_PLAN:
        return DEFAULT_PLAN
    expires = getattr(company, "plan_expires_at", None)
    if expires is not None and expires < datetime.now(timezone.utc).replace(tzinfo=None):
        return DEFAULT_PLAN
    return plan


def limits_for(company) -> dict:
    return PLAN_LIMITS[effective_plan(company)]


def _month_start(now: Optional[datetime] = None) -> datetime:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    return datetime(now.year, now.month, 1)


def active_jobs_count(db: Session, company_id: int) -> int:
    return (
        db.query(Job)
        .filter(Job.company_id == company_id, Job.is_active == True)  # noqa: E712
        .count()
    )


def candidates_this_month(db: Session, company_id: int) -> int:
    return (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Job.company_id == company_id, Candidate.created_at >= _month_start())
        .count()
    )


def enforce_job_quota(db: Session, company) -> None:
    """Бросает 402, если достигнут лимит активных вакансий тарифа."""
    limit = limits_for(company)["max_active_jobs"]
    if limit is None:
        return
    if active_jobs_count(db, company.id) >= limit:
        word = "активной вакансии" if limit == 1 else "активных вакансий"
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Достигнут лимит тарифа: не более {limit} {word}. "
                "Обновите тариф или деактивируйте существующую вакансию."
            ),
        )


def enforce_candidate_quota(db: Session, company) -> None:
    """Бросает 403, если исчерпан месячный лимит кандидатов тарифа.

    Вызывается на ПУБЛИЧНОМ эндпоинте подачи заявки — текст нейтральный,
    без упоминания внутренних тарифов работодателя.
    """
    limit = limits_for(company)["max_candidates_per_month"]
    if limit is None:
        return
    if candidates_this_month(db, company.id) >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Приём заявок на эту вакансию временно приостановлен. Попробуйте позже.",
        )
