"""Ручное управление подписками компаний (суперадмин).

Пока нет платёжного шлюза: суперадмин вручную выставляет тариф и дату окончания
после того, как клиент оплатил переводом и прикрепил чек. Также можно начислить
реферальный бонус (продление на N месяцев). Доступ — только для email из SUPERADMIN_EMAILS.
"""
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_superadmin
from app.core.audit import record_audit
from app.core.db import get_db
from app.models.models import Company, PaymentReceipt

router = APIRouter(prefix="/admin", tags=["admin"])

VALID_PLANS = {"free", "starter", "pro"}
VALID_REVIEW = {"approved", "rejected"}


class CompanyRow(BaseModel):
    id: int
    name: str
    email: str
    plan: str
    plan_expires_at: str | None
    referred_count: int


class SetPlanRequest(BaseModel):
    plan: str
    months: int | None = Field(default=None, ge=1, le=36)


class GrantBonusRequest(BaseModel):
    months: int = Field(default=1, ge=1, le=36)


class ReceiptRow(BaseModel):
    id: int
    company_id: int
    company_name: str
    company_email: str
    plan_requested: str
    filename: str
    status: str
    created_at: str


class ReviewRequest(BaseModel):
    status: str
    note: str | None = None


def _row(db: Session, c: Company) -> CompanyRow:
    referred = (
        db.query(func.count(Company.id))
        .filter(Company.referred_by_company_id == c.id)
        .scalar()
        or 0
    )
    return CompanyRow(
        id=c.id,
        name=c.name,
        email=c.email,
        plan=c.plan or "free",
        plan_expires_at=c.plan_expires_at.isoformat() if c.plan_expires_at else None,
        referred_count=referred,
    )


def _receipt_row(r: PaymentReceipt) -> ReceiptRow:
    c = r.company
    return ReceiptRow(
        id=r.id,
        company_id=r.company_id,
        company_name=c.name if c else "—",
        company_email=c.email if c else "—",
        plan_requested=r.plan_requested,
        filename=r.filename,
        status=r.status,
        created_at=r.created_at.isoformat() if r.created_at else "",
    )


def _get_company_or_404(company_id: int, db: Session) -> Company:
    c = db.query(Company).filter(Company.id == company_id).first()
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Компания не найдена")
    return c


@router.get("/companies", response_model=list[CompanyRow])
def list_companies(
    db: Session = Depends(get_db),
    _: Company = Depends(require_superadmin),
):
    """Список всех компаний с тарифом, сроком и числом рефералов."""
    companies = db.query(Company).order_by(Company.created_at.desc()).all()
    return [_row(db, c) for c in companies]


@router.post("/companies/{company_id}/plan", response_model=CompanyRow)
def set_plan(
    company_id: int,
    body: SetPlanRequest,
    db: Session = Depends(get_db),
    admin: Company = Depends(require_superadmin),
):
    """Выставить тариф компании вручную. months продлевает срок от текущей даты."""
    if body.plan not in VALID_PLANS:
        raise HTTPException(status_code=422, detail=f"Неизвестный тариф: {body.plan}")
    c = _get_company_or_404(company_id, db)
    c.plan = body.plan
    if body.plan == "free":
        c.plan_expires_at = None
    elif body.months:
        base = max(c.plan_expires_at or datetime.utcnow(), datetime.utcnow())
        c.plan_expires_at = base + timedelta(days=30 * body.months)
    db.commit()
    db.refresh(c)
    record_audit(
        db,
        company_id=admin.id,
        action="admin.set_plan",
        actor_type="company",
        actor_id=admin.id,
        actor_email=admin.email,
        entity_type="company",
        entity_id=c.id,
        detail={"plan": c.plan, "expires": c.plan_expires_at.isoformat() if c.plan_expires_at else None},
    )
    return _row(db, c)


@router.post("/companies/{company_id}/grant-bonus", response_model=CompanyRow)
def grant_bonus(
    company_id: int,
    body: GrantBonusRequest,
    db: Session = Depends(get_db),
    admin: Company = Depends(require_superadmin),
):
    """Начислить реферальный бонус: продлить срок на N месяцев."""
    c = _get_company_or_404(company_id, db)
    if (c.plan or "free") == "free":
        c.plan = "starter"
    base = max(c.plan_expires_at or datetime.utcnow(), datetime.utcnow())
    c.plan_expires_at = base + timedelta(days=30 * body.months)
    db.commit()
    db.refresh(c)
    record_audit(
        db,
        company_id=admin.id,
        action="admin.grant_bonus",
        actor_type="company",
        actor_id=admin.id,
        actor_email=admin.email,
        entity_type="company",
        entity_id=c.id,
        detail={"months": body.months},
    )
    return _row(db, c)


@router.get("/receipts", response_model=list[ReceiptRow])
def list_receipts(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _: Company = Depends(require_superadmin),
):
    """Заявки на оплату (загруженные чеки). status_filter: pending/approved/rejected."""
    q = db.query(PaymentReceipt).order_by(PaymentReceipt.created_at.desc())
    if status_filter:
        q = q.filter(PaymentReceipt.status == status_filter)
    return [_receipt_row(r) for r in q.all()]


@router.get("/receipts/{receipt_id}/file")
def get_receipt_file(
    receipt_id: int,
    db: Session = Depends(get_db),
    _: Company = Depends(require_superadmin),
):
    """Отдать файл чека суперадмину для проверки."""
    r = db.query(PaymentReceipt).filter(PaymentReceipt.id == receipt_id).first()
    if r is None or not os.path.exists(r.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чек не найден")
    return FileResponse(
        r.file_path,
        filename=r.filename,
        media_type=r.content_type or "application/octet-stream",
    )


@router.post("/receipts/{receipt_id}/review", response_model=ReceiptRow)
def review_receipt(
    receipt_id: int,
    body: ReviewRequest,
    db: Session = Depends(get_db),
    admin: Company = Depends(require_superadmin),
):
    """Отметить чек подтверждённым или отклонённым. Тариф выставляется отдельно."""
    if body.status not in VALID_REVIEW:
        raise HTTPException(status_code=422, detail="status: approved | rejected")
    r = db.query(PaymentReceipt).filter(PaymentReceipt.id == receipt_id).first()
    if r is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чек не найден")
    r.status = body.status
    r.note = body.note
    r.reviewed_by = admin.email
    r.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(r)
    record_audit(
        db,
        company_id=admin.id,
        action="admin.review_receipt",
        actor_type="company",
        actor_id=admin.id,
        actor_email=admin.email,
        entity_type="payment_receipt",
        entity_id=r.id,
        detail={"status": r.status},
    )
    return _receipt_row(r)
