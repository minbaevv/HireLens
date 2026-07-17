"""Зависимости авторизации.

JWT может принадлежать либо владельцу компании (Company), либо участнику
команды (TeamMember, см. B1). Различаются по claim "actor_type" в токене;
старые токены без этого claim трактуются как "company" (обратная совместимость).
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.security import decode_access_token, hash_api_key
from app.models.models import Company
from app.models.api_key import ApiKey
from app.models.team_member import TeamMember, TeamRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


@dataclass
class CurrentActor:
    """Текущий авторизованный пользователь: владелец компании или участник команды."""

    company: Company
    role: TeamRole
    team_member: Optional[TeamMember] = None

    @property
    def is_owner(self) -> bool:
        return self.team_member is None


def _resolve_actor(token: str, db: Session) -> CurrentActor:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    subject_id = payload.get("sub")
    if subject_id is None:
        raise credentials_exception

    actor_type = payload.get("actor_type", "company")

    if actor_type == "team_member":
        member = db.query(TeamMember).filter(TeamMember.id == int(subject_id)).first()
        if member is None or not member.is_active:
            raise credentials_exception
        return CurrentActor(company=member.company, role=member.role, team_member=member)

    company = db.query(Company).filter(Company.id == int(subject_id)).first()
    if company is None:
        raise credentials_exception
    return CurrentActor(company=company, role=TeamRole.admin, team_member=None)


def get_current_company(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Company:
    """Возвращает компанию текущего пользователя (владелец ИЛИ участник команды).

    Существующие эндпоинты (jobs/candidates/interviews/analytics) продолжают
    работать без изменений — токен теперь может принадлежать как владельцу,
    так и приглашённому участнику команды.
    """
    return _resolve_actor(token, db).company


def get_current_actor(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> CurrentActor:
    """Возвращает текущего актёра с ролью — для эндпоинтов с проверкой прав."""
    return _resolve_actor(token, db)


def require_admin(actor: CurrentActor = Depends(get_current_actor)) -> CurrentActor:
    """Только владелец компании или участник с ролью admin."""
    if actor.role != TeamRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора",
        )
    return actor


def require_write_access(actor: CurrentActor = Depends(get_current_actor)) -> CurrentActor:
    """Запрещает изменяющие операции участникам с ролью viewer (B1.2).

    viewer может только смотреть данные (через get_current_company/
    get_current_actor напрямую), но не создавать/изменять/удалять
    вакансии и кандидатов. admin и recruiter проходят без ограничений.
    """
    if actor.role == TeamRole.viewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Роль viewer позволяет только просмотр",
        )
    return actor


def is_subscription_active(company: Company) -> bool:
    """Активна ли подписка компании.

    free-тариф активен всегда. Платный тариф активен, пока не истёк
    plan_expires_at (NULL трактуется как бессрочный доступ, выданный вручную).
    """
    if (company.plan or "free") == "free":
        return True
    if company.plan_expires_at is None:
        return True
    return company.plan_expires_at >= datetime.utcnow()


def require_active_subscription(
    company: Company = Depends(get_current_company),
) -> Company:
    """Блокирует действие, если платная подписка истекла (402)."""
    if not is_subscription_active(company):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Подписка истекла. Продлите тариф, чтобы продолжить.",
        )
    return company


def require_superadmin(
    company: Company = Depends(get_current_company),
) -> Company:
    """Только суперадмин (email в SUPERADMIN_EMAILS)."""
    if (company.email or "").lower() not in settings.superadmin_emails:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права суперадминистратора",
        )
    return company


def get_api_company(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> Company:
    """D2 — авторизация публичного API по ключу из заголовка X-API-Key.

    Ключ сверяется по SHA-256 хешу. Отозванные ключи и ключи без компании
    отклоняются (401). При истёкшей платной подписке — 402.
    """
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Некорректный или отсутствующий API-ключ",
        headers={"WWW-Authenticate": "ApiKey"},
    )
    if not x_api_key or not x_api_key.strip():
        raise invalid
    key = (
        db.query(ApiKey)
        .filter(ApiKey.hashed_key == hash_api_key(x_api_key.strip()))
        .first()
    )
    if key is None or key.revoked:
        raise invalid
    company = db.query(Company).filter(Company.id == key.company_id).first()
    if company is None:
        raise invalid
    # last_used_at — best-effort, не критично при сбое
    try:
        key.last_used_at = datetime.utcnow()
        db.commit()
    except Exception:
        db.rollback()
    if not is_subscription_active(company):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Подписка истекла. Продлите тариф для доступа к API.",
        )
    return company
