"""Auth эндпоинты: регистрация, логин, текущий пользователь.

Логин и refresh работает как для владельца компании (Company), так и для
приглашённого участника команды (TeamMember, см. B1 и app/api/team.py).
"""
import logging
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import get_current_company
from app.core.config import settings
from app.core.db import get_db
from app.core.limiter import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_password_hash,
    validate_password_strength,
    verify_password,
)
from app.models.models import Company
from app.models.team_member import TeamMember
from app.services.email import notify_registration_attempt, send_verification_code

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    company_name: str
    referral_code: str | None = None


VERIFICATION_CODE_TTL_MINUTES = 15


class RegisterResponse(BaseModel):
    message: str = "Мы отправили код подтверждения на вашу почту"
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


class ResendCodeRequest(BaseModel):
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class CompanyOut(BaseModel):
    id: int
    email: str
    company_name: str
    is_verified: bool = True
    telegram_chat_id: str | None = None
    telegram_link_code: str | None = None
    telegram_bot_username: str | None = None
    telegram_candidate_bot_username: str | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_company(cls, company) -> "CompanyOut":
        from app.core.config import settings
        return cls(
            id=company.id,
            email=company.email,
            company_name=company.name,
            is_verified=getattr(company, "is_verified", True),
            telegram_chat_id=getattr(company, "telegram_chat_id", None),
            telegram_link_code=getattr(company, "telegram_link_code", None),
            telegram_bot_username=(settings.TELEGRAM_BOT_USERNAME or None),
            telegram_candidate_bot_username=(settings.TELEGRAM_CANDIDATE_BOT_USERNAME or None),
        )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    """Регистрация компании с подтверждением email.

    SEC-11: ответ одинаков независимо от того, занят ли email (против
    enumeration). Пароль хешируется во всех ветках, чтобы выровнять тайминг.
    """
    try:
        validate_password_strength(body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Хешируем ВСЕГДА: постоянная стоимость bcrypt во всех ветках — против timing-enumeration.
    hashed = get_password_hash(body.password)
    code = f"{secrets.randbelow(1000000):06d}"
    expires = datetime.utcnow() + timedelta(minutes=VERIFICATION_CODE_TTL_MINUTES)

    existing = db.query(Company).filter(Company.email == body.email).first()
    if existing is None:
        # D3: привязка к пригласившей компании по реферальному коду (неверный код игнорируется)
        referred_by_id = None
        if body.referral_code:
            _ref = db.query(Company).filter(Company.referral_code == body.referral_code).first()
            if _ref:
                referred_by_id = _ref.id
        company = Company(
            email=body.email,
            hashed_password=hashed,
            name=body.company_name,
            is_verified=False,
            verification_code=code,
            verification_code_expires_at=expires,
            referred_by_company_id=referred_by_id,
        )
        db.add(company)
        db.commit()
        send_verification_code(body.email, code)
        logger.info(f"Registration started (new): {body.email}")
    elif existing.is_verified:
        # Email занят и подтверждён — не раскрываем. Предупреждаем владельца.
        notify_registration_attempt(existing.email)
        logger.info(f"Registration attempt on existing verified email: {body.email}")
    else:
        # Занят, но не подтверждён — переотправляем свежий код.
        existing.verification_code = code
        existing.verification_code_expires_at = expires
        db.commit()
        send_verification_code(existing.email, code)
        logger.info(f"Registration re-sent code (unverified): {body.email}")

    return RegisterResponse(email=body.email)


@router.post("/verify-email", response_model=TokenResponse)
@limiter.limit("20/hour")
def verify_email(request: Request, body: VerifyEmailRequest, db: Session = Depends(get_db)):
    """Подтверждает email по 6-значному коду."""
    company = db.query(Company).filter(Company.email == body.email).first()
    invalid = HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный код подтверждения")
    if company is None or not company.verification_code:
        raise invalid
    if (
        company.verification_code_expires_at
        and datetime.utcnow() > company.verification_code_expires_at
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код подтверждения истёк, запросите новый",
        )
    if not secrets.compare_digest(company.verification_code, body.code.strip()):
        raise invalid

    company.is_verified = True
    company.verification_code = None
    company.verification_code_expires_at = None
    # Пробный период: при первой активации выдаём тариф Starter на TRIAL_DAYS дней.
    # Ровно через 3 дня проба заканчивается — доступ к платным функциям
    # блокируется (is_subscription_active), пока суперадмин не активирует оплату.
    if (company.plan or "free") == "free" and company.plan_expires_at is None:
        company.plan = settings.TRIAL_PLAN
        company.plan_expires_at = datetime.utcnow() + timedelta(days=settings.TRIAL_DAYS)
        logger.info(
            f"Trial granted: {company.email} -> {settings.TRIAL_PLAN} на {settings.TRIAL_DAYS} дн."
        )
    db.commit()
    logger.info(f"Email verified: {company.email}")
    return TokenResponse(
        access_token=create_access_token({"sub": str(company.id), "actor_type": "company"}),
        refresh_token=create_refresh_token({"sub": str(company.id), "actor_type": "company"}),
    )


@router.post("/resend-code", response_model=RegisterResponse)
@limiter.limit("1/minute")
def resend_code(request: Request, body: ResendCodeRequest, db: Session = Depends(get_db)):
    """Повторно отправляет код подтверждения (rate-limit 1/мин). Ответ нейтрален (SEC-11)."""
    company = db.query(Company).filter(Company.email == body.email).first()
    if company is not None and not company.is_verified:
        code = f"{secrets.randbelow(1000000):06d}"
        company.verification_code = code
        company.verification_code_expires_at = datetime.utcnow() + timedelta(
            minutes=VERIFICATION_CODE_TTL_MINUTES
        )
        db.commit()
        send_verification_code(company.email, code)
    return RegisterResponse(
        message="Если аккаунт существует и не подтверждён — код отправлен повторно",
        email=body.email,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login with email and password. Работает и для владельца компании, и для участника команды."""
    company = db.query(Company).filter(Company.email == form_data.username).first()
    if company and verify_password(form_data.password, company.hashed_password):
        if not company.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Подтвердите email перед входом",
            )
        logger.info(f"Company logged in: {company.email}")
        return TokenResponse(
            access_token=create_access_token({"sub": str(company.id), "actor_type": "company"}),
            refresh_token=create_refresh_token({"sub": str(company.id), "actor_type": "company"}),
        )

    member = db.query(TeamMember).filter(TeamMember.email == form_data.username).first()
    if (
        member
        and member.is_active
        and member.hashed_password
        and verify_password(form_data.password, member.hashed_password)
    ):
        logger.info(f"Team member logged in: {member.email}")
        return TokenResponse(
            access_token=create_access_token({"sub": str(member.id), "actor_type": "team_member"}),
            refresh_token=create_refresh_token({"sub": str(member.id), "actor_type": "team_member"}),
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("60/minute")
def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
    """Обновляет пару токенов по действующему refresh-токену."""
    payload = decode_refresh_token(body.refresh_token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    subject_id = int(payload["sub"])
    actor_type = payload.get("actor_type", "company")

    if actor_type == "team_member":
        member = db.query(TeamMember).filter(
            TeamMember.id == subject_id, TeamMember.is_active == True
        ).first()
        if not member:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        return TokenResponse(
            access_token=create_access_token({"sub": str(member.id), "actor_type": "team_member"}),
            refresh_token=create_refresh_token({"sub": str(member.id), "actor_type": "team_member"}),
        )

    company = db.query(Company).filter(Company.id == subject_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    return TokenResponse(
        access_token=create_access_token({"sub": str(company.id), "actor_type": "company"}),
        refresh_token=create_refresh_token({"sub": str(company.id), "actor_type": "company"}),
    )


@router.get("/me", response_model=CompanyOut)
def me(current_company: Company = Depends(get_current_company)):
    """Get current authenticated company."""
    return CompanyOut.from_orm_company(current_company)
