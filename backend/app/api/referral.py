"""Реферальная программа (Roadmap D3).

Каждая компания получает уникальный реферальный код и ссылку. Когда по ссылке
(?ref=CODE → передаётся в /auth/register) регистрируется новая компания,
она привязывается к пригласившему. Эндпоинт отдаёт код, ссылку и статистику.
"""
import secrets

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_company
from app.core.config import settings
from app.core.db import get_db
from app.models.models import Company

router = APIRouter(prefix="/referral", tags=["referral"])

# Сколько месяцев бонуса начисляется за каждого приглашённого (метаданные для UI).
REWARD_MONTHS_PER_REFERRAL = 1


def _generate_code(db: Session) -> str:
    for _ in range(10):
        code = secrets.token_urlsafe(6)[:8]
        if not db.query(Company.id).filter(Company.referral_code == code).first():
            return code
    return secrets.token_urlsafe(12)[:16]


def ensure_referral_code(db: Session, company: Company) -> str:
    """Гарантирует наличие кода (ленивая генерация для старых компаний)."""
    if not company.referral_code:
        company.referral_code = _generate_code(db)
        db.commit()
        db.refresh(company)
    return company.referral_code


def resolve_referrer_id(db: Session, code: str | None) -> int | None:
    """Возвращает id пригласившей компании по коду или None."""
    if not code:
        return None
    ref = db.query(Company).filter(Company.referral_code == code).first()
    return ref.id if ref else None


class ReferralInfo(BaseModel):
    code: str
    share_url: str
    referred_count: int
    reward_months: int


@router.get("/me", response_model=ReferralInfo)
def get_my_referral(
    db: Session = Depends(get_db),
    company: Company = Depends(get_current_company),
) -> ReferralInfo:
    """Реферальный код, ссылка и статистика текущей компании."""
    code = ensure_referral_code(db, company)
    referred_count = (
        db.query(func.count(Company.id))
        .filter(Company.referred_by_company_id == company.id)
        .scalar()
        or 0
    )
    base = (settings.FRONTEND_URL or "http://localhost:3000").rstrip("/")
    return ReferralInfo(
        code=code,
        share_url=f"{base}/register?ref={code}",
        referred_count=referred_count,
        reward_months=referred_count * REWARD_MONTHS_PER_REFERRAL,
    )
