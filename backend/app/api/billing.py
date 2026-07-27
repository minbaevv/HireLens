"""Подписка компании: статус, реквизиты оплаты и загрузка чеков (ручной режим).

Пока платёжный шлюз (FreedomPay) не подключён, оплата принимается переводом на
карту Visa, а тариф активирует суперадмин вручную (см. /admin). Клиент может
прикрепить чек об оплате прямо здесь — заявка появится у суперадмина.
"""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_company, is_subscription_active
from app.core.audit import record_audit
from app.core.config import settings
from app.core.db import get_db
from app.core.payments import PAYMENT_INFO
from app.core.plans import active_jobs_count, candidates_this_month, limits_for
from app.models.models import Company, PaymentReceipt

router = APIRouter(prefix="/billing", tags=["billing"])

RECEIPT_ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
RECEIPT_MAX_MB = 10
PAID_PLANS = {"starter", "pro"}


class BillingStatus(BaseModel):
    plan: str
    plan_expires_at: str | None
    active: bool
    days_left: int | None
    is_free: bool
    is_superadmin: bool
    payment_info: dict
    # Использование квот текущего месяца (баннер лимита на дашборде).
    # None в *_limit = безлимит.
    candidates_used: int = 0
    candidates_limit: int | None = None
    jobs_used: int = 0
    jobs_limit: int | None = None


class ReceiptOut(BaseModel):
    id: int
    plan_requested: str
    filename: str
    status: str
    note: str | None
    created_at: str


def _receipt_out(r: PaymentReceipt) -> ReceiptOut:
    return ReceiptOut(
        id=r.id,
        plan_requested=r.plan_requested,
        filename=r.filename,
        status=r.status,
        note=r.note,
        created_at=r.created_at.isoformat() if r.created_at else "",
    )


@router.get("/me", response_model=BillingStatus)
def get_my_billing(
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company),
) -> BillingStatus:
    """Статус подписки текущей компании + реквизиты для ручной оплаты."""
    plan = company.plan or "free"
    is_free = plan == "free"
    active = is_subscription_active(company)
    days_left = None
    if not is_free and company.plan_expires_at is not None:
        days_left = (company.plan_expires_at - datetime.now(timezone.utc).replace(tzinfo=None)).days
    # Квоты берём из того же источника, что и enforcement (app.core.plans),
    # чтобы цифра на дашборде не расходилась с реальной блокировкой заявок.
    plan_limits = limits_for(company)
    return BillingStatus(
        plan=plan,
        plan_expires_at=company.plan_expires_at.isoformat() if company.plan_expires_at else None,
        active=active,
        days_left=days_left,
        is_free=is_free,
        is_superadmin=(company.email or "").lower() in settings.superadmin_emails,
        payment_info=PAYMENT_INFO,
        candidates_used=candidates_this_month(db, company.id),
        candidates_limit=plan_limits["max_candidates_per_month"],
        jobs_used=active_jobs_count(db, company.id),
        jobs_limit=plan_limits["max_active_jobs"],
    )


@router.post("/receipt", response_model=ReceiptOut, status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    plan: str = Form(...),
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company),
) -> ReceiptOut:
    """Клиент прикрепляет чек об оплате переводом. Заявку проверяет суперадмин."""
    if plan not in PAID_PLANS:
        raise HTTPException(status_code=422, detail=f"Неизвестный тариф: {plan}")

    filename = file.filename or "receipt"
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext not in RECEIPT_ALLOWED_EXT:
        raise HTTPException(
            status_code=422,
            detail=f"Разрешены форматы: {', '.join(sorted(RECEIPT_ALLOWED_EXT))}",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="Пустой файл")
    if len(data) > RECEIPT_MAX_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Файл слишком большой. Максимум {RECEIPT_MAX_MB} MB")
    # SEC: проверяем реальную сигнатуру файла (magic bytes), а не только расширение —
    # чтобы под видом чека нельзя было залить произвольный/исполняемый контент.
    if ext == ".pdf":
        if not data.startswith(b"%PDF"):
            raise HTTPException(status_code=422, detail="Файл не является корректным PDF")
    elif ext in {".jpg", ".jpeg"}:
        if not data.startswith(b"\xff\xd8\xff"):
            raise HTTPException(status_code=422, detail="Файл не является корректным JPEG")
    elif ext == ".png":
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(status_code=422, detail="Файл не является корректным PNG")
    elif ext == ".webp":
        if not (data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
            raise HTTPException(status_code=422, detail="Файл не является корректным WEBP")

    upload_dir = Path("uploads/receipts") / str(company.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y%m%d_%H%M%S')}{ext}"
    path = upload_dir / stored_name
    with open(path, "wb") as f:
        f.write(data)

    receipt = PaymentReceipt(
        company_id=company.id,
        plan_requested=plan,
        filename=filename[:255],
        file_path=str(path),
        content_type=file.content_type,
        status="pending",
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)

    record_audit(
        db,
        company_id=company.id,
        action="billing.upload_receipt",
        actor_type="company",
        actor_id=company.id,
        actor_email=company.email,
        entity_type="payment_receipt",
        entity_id=receipt.id,
        detail={"plan": plan},
        request=request,
    )
    return _receipt_out(receipt)


@router.get("/receipts", response_model=list[ReceiptOut])
def my_receipts(
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company),
) -> list[ReceiptOut]:
    """Список чеков, загруженных текущей компанией, с их статусами."""
    rows = (
        db.query(PaymentReceipt)
        .filter(PaymentReceipt.company_id == company.id)
        .order_by(PaymentReceipt.created_at.desc())
        .all()
    )
    return [_receipt_out(r) for r in rows]
