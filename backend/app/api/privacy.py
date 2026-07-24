"""Фаза 3 — Приватность / GDPR. Без внешних ключей.

- GET  /privacy/export           — экспорт всех данных компании (data portability)
- GET  /privacy/retention        — текущая retention-политика
- PUT  /privacy/retention        — задать срок хранения данных
- POST /privacy/erase-candidates — удалить все данные кандидатов (right to erasure)

Полное удаление аккаунта компании НЕ реализовано здесь: часть связанных таблиц
(audit_logs, api_keys, webhooks и др.) не имеют ON DELETE CASCADE — это требует
отдельной миграции и вынесено в follow-up.
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import CurrentActor, get_current_company, require_admin
from app.core.audit import actor_fields, record_audit
from app.core.db import get_db
from app.models.candidate import Candidate
from app.models.company import Company
from app.models.job import Job
from app.models.team_member import TeamMember

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/privacy", tags=["privacy"])

# Поля, которые не выгружаются (секреты / токены).
_SENSITIVE = {
    "hashed_password",
    "verification_code",
    "telegram_link_code",
    "invite_token",
}


def _row(obj) -> dict:
    out = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name, None)
        if isinstance(val, datetime):
            val = val.isoformat()
        elif not isinstance(val, (str, int, float, bool, type(None))):
            val = str(val)
        out[col.name] = val
    return out


def _safe_row(obj) -> dict:
    return {k: v for k, v in _row(obj).items() if k not in _SENSITIVE}


class RetentionUpdate(BaseModel):
    days: int | None = None


class EraseRequest(BaseModel):
    confirm_email: str


@router.get("/export")
def export_data(
    request: Request,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
):
    """Полный экспорт данных компании (GDPR data portability). Только admin."""
    company = actor.company
    jobs = db.query(Job).filter(Job.company_id == company.id).all()
    job_ids = [j.id for j in jobs]
    candidates = (
        db.query(Candidate).filter(Candidate.job_id.in_(job_ids)).all() if job_ids else []
    )
    members = db.query(TeamMember).filter(TeamMember.company_id == company.id).all()
    export = {
        "exported_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
        "company": _safe_row(company),
        "jobs": [_safe_row(j) for j in jobs],
        "candidates": [_safe_row(c) for c in candidates],
        "team_members": [_safe_row(m) for m in members],
        "counts": {
            "jobs": len(jobs),
            "candidates": len(candidates),
            "team_members": len(members),
        },
    }
    record_audit(
        db,
        company_id=company.id,
        action="privacy.export",
        detail={"jobs": len(jobs), "candidates": len(candidates)},
        request=request,
        **actor_fields(actor),
    )
    return export


@router.get("/retention")
def get_retention(company: Company = Depends(get_current_company)):
    return {"days": getattr(company, "data_retention_days", None)}


@router.put("/retention")
def set_retention(
    body: RetentionUpdate,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
):
    """Задаёт срок хранения данных кандидатов (дни). Пусто = бессрочно."""
    days = body.days
    if days is not None and (days < 1 or days > 3650):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Срок хранения — от 1 до 3650 дней или пусто (бессрочно)",
        )
    actor.company.data_retention_days = days
    db.commit()
    record_audit(
        db,
        company_id=actor.company.id,
        action="privacy.retention_update",
        detail={"days": days},
        **actor_fields(actor),
    )
    return {"days": days}


@router.post("/erase-candidates")
def erase_candidates(
    body: EraseRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
):
    """Удаляет ВСЕ данные кандидатов компании (right to erasure).

    Каскадно удаляет интервью и сообщения (тот же путь, что и удаление вакансии).
    Только владелец компании; требует подтверждения email.
    """
    if not actor.is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Удалить данные кандидатов может только владелец компании",
        )
    company = actor.company
    if (body.confirm_email or "").strip().lower() != (company.email or "").lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Подтверждающий email не совпадает",
        )
    jobs = db.query(Job).filter(Job.company_id == company.id).all()
    job_ids = [j.id for j in jobs]
    candidates = (
        db.query(Candidate).filter(Candidate.job_id.in_(job_ids)).all() if job_ids else []
    )
    deleted = len(candidates)
    for c in candidates:
        db.delete(c)
    db.commit()
    record_audit(
        db,
        company_id=company.id,
        action="privacy.erase_candidates",
        detail={"deleted": deleted},
        request=request,
        **actor_fields(actor),
    )
    return {"deleted": deleted}
