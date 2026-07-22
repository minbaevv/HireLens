"""Фаза 3 — White-label (брендирование). Без внешних ключей.

Компания может задать своё название, логотип и акцентный цвет, которые
показываются в интерфейсе и на публичных страницах для кандидатов.
"""
import logging
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.api.deps import CurrentActor, get_current_company, require_admin
from app.core.audit import actor_fields, record_audit
from app.core.db import get_db
from app.models.company import Company

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/branding", tags=["branding"])

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class BrandingOut(BaseModel):
    enabled: bool
    name: str | None = None
    logo_url: str | None = None
    color: str | None = None

    model_config = {"from_attributes": True}


class BrandingUpdate(BaseModel):
    enabled: bool | None = None
    name: str | None = None
    logo_url: str | None = None
    color: str | None = None

    @field_validator("color")
    @classmethod
    def _validate_color(cls, v):
        if v in (None, ""):
            return None
        v = v.strip()
        if not _HEX_RE.match(v):
            raise ValueError("Цвет должен быть в формате HEX, например #2563EB")
        return v

    @field_validator("logo_url")
    @classmethod
    def _validate_logo(cls, v):
        if v in (None, ""):
            return None
        v = v.strip()
        if not (v.startswith("https://") or v.startswith("http://") or v.startswith("/")):
            raise ValueError("Ссылка на логотип должна начинаться с http(s):// или /")
        if len(v) > 500:
            raise ValueError("Слишком длинная ссылка на логотип")
        return v

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v):
        if v is None:
            return None
        v = v.strip()
        if len(v) > 120:
            raise ValueError("Название слишком длинное (макс. 120)")
        return v or None


def _to_out(company: Company) -> BrandingOut:
    return BrandingOut(
        enabled=bool(getattr(company, "brand_enabled", False)),
        name=getattr(company, "brand_name", None),
        logo_url=getattr(company, "brand_logo_url", None),
        color=getattr(company, "brand_color", None),
    )


@router.get("", response_model=BrandingOut)
def get_branding(company: Company = Depends(get_current_company)):
    """Текущий брендинг компании (виден всем авторизованным)."""
    return _to_out(company)


@router.put("", response_model=BrandingOut)
def update_branding(
    body: BrandingUpdate,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
):
    """Обновляет брендинг (только admin)."""
    company = actor.company
    data = body.model_dump(exclude_unset=True)
    if "enabled" in data and data["enabled"] is not None:
        company.brand_enabled = bool(data["enabled"])
    if "name" in data:
        company.brand_name = data["name"]
    if "logo_url" in data:
        company.brand_logo_url = data["logo_url"]
    if "color" in data:
        company.brand_color = data["color"]
    db.commit()
    db.refresh(company)
    record_audit(
        db,
        company_id=company.id,
        action="branding.update",
        detail={"enabled": bool(company.brand_enabled)},
        **actor_fields(actor),
    )
    return _to_out(company)


@router.get("/public/{company_id}", response_model=BrandingOut)
def public_branding(company_id: int, db: Session = Depends(get_db)):
    """Публичный брендинг для страниц кандидата (careers/apply). Без авторизации.

    Если брендинг выключен или компания не найдена — возвращаем enabled=false,
    не раскрывая факт существования компании.
    """
    company = db.query(Company).filter(Company.id == company_id).first()
    if company is None or not getattr(company, "brand_enabled", False):
        return BrandingOut(enabled=False)
    return _to_out(company)
