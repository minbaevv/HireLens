"""Командный доступ: приглашения, роли (B1)."""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.api.deps import CurrentActor, get_current_actor, require_admin
from app.core.config import settings
from app.core.db import get_db
from app.core.audit import actor_fields, record_audit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    validate_password_strength,
)
from app.models.team_member import TeamMember, TeamRole

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/team", tags=["team"])


class InviteRequest(BaseModel):
    email: EmailStr
    name: str
    role: TeamRole = TeamRole.recruiter


class TeamMemberOut(BaseModel):
    id: int
    name: str
    email: str
    role: TeamRole
    is_active: bool

    model_config = {"from_attributes": True}


class AcceptInviteRequest(BaseModel):
    token: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RoleUpdateRequest(BaseModel):
    role: TeamRole


@router.post("/invite", response_model=TeamMemberOut, status_code=status.HTTP_201_CREATED)
def invite_member(
    body: InviteRequest,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
):
    """Приглашает нового участника команды (только admin)."""
    existing = db.query(TeamMember).filter(TeamMember.email == body.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Этот email уже приглашён")

    member = TeamMember(
        company_id=actor.company.id,
        name=body.name,
        email=body.email,
        role=body.role,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    invite_link = f"{settings.FRONTEND_URL}/team/accept?token={member.invite_token}"
    try:
        from app.services.email import _send_email
        _send_email(
            member.email,
            f"Приглашение в команду {actor.company.name}",
            f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2>Вас пригласили в команду {actor.company.name}</h2>
                <p>Роль: <strong>{body.role.value}</strong></p>
                <p><a href="{invite_link}">Принять приглашение</a></p>
                <p style="color: #9CA3AF; font-size: 12px; margin-top: 30px;">HireLens</p>
            </div>
            """,
        )
    except Exception as e:
        logger.warning(f"Invite email не отправлен: {e}")

    logger.info(f"Team invite: {member.email} -> company #{actor.company.id} as {body.role.value}")
    record_audit(db, company_id=actor.company.id, action="team.invite", entity_type="team_member", entity_id=member.id, detail={"email": member.email, "role": body.role.value}, **actor_fields(actor))
    return TeamMemberOut.model_validate(member)


@router.post("/accept-invite", response_model=TokenResponse)
def accept_invite(body: AcceptInviteRequest, db: Session = Depends(get_db)):
    """Принимает приглашение: задаёт пароль, активирует участника. Публичный эндпоинт."""
    try:
        validate_password_strength(body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    member = db.query(TeamMember).filter(TeamMember.invite_token == body.token).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Приглашение не найдено или уже использовано",
        )
    if member.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Приглашение уже принято")

    member.hashed_password = get_password_hash(body.password)
    member.is_active = True
    member.accepted_at = datetime.now(UTC)
    member.invite_token = None
    db.commit()
    db.refresh(member)

    logger.info(f"Team invite accepted: {member.email}")
    record_audit(db, company_id=member.company_id, action="team.accept_invite", actor_type="team_member", actor_id=member.id, actor_email=member.email, entity_type="team_member", entity_id=member.id)
    return TokenResponse(
        access_token=create_access_token({"sub": str(member.id), "actor_type": "team_member"}),
        refresh_token=create_refresh_token({"sub": str(member.id), "actor_type": "team_member"}),
    )


@router.get("", response_model=list[TeamMemberOut])
def list_team(
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(get_current_actor),
):
    """Список участников команды (виден всем авторизованным в компании)."""
    members = db.query(TeamMember).filter(TeamMember.company_id == actor.company.id).all()
    return [TeamMemberOut.model_validate(m) for m in members]


@router.patch("/{member_id}/role", response_model=TeamMemberOut)
def update_role(
    member_id: int,
    body: RoleUpdateRequest,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
):
    """Меняет роль участника (только admin)."""
    member = db.query(TeamMember).filter(
        TeamMember.id == member_id, TeamMember.company_id == actor.company.id
    ).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Участник не найден")
    member.role = body.role
    db.commit()
    db.refresh(member)
    record_audit(db, company_id=actor.company.id, action="team.role_update", entity_type="team_member", entity_id=member.id, detail={"role": body.role.value}, **actor_fields(actor))
    return TeamMemberOut.model_validate(member)


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    member_id: int,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
):
    """Удаляет участника команды (только admin)."""
    member = db.query(TeamMember).filter(
        TeamMember.id == member_id, TeamMember.company_id == actor.company.id
    ).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Участник не найден")
    _rm_email, _rm_id = member.email, member.id
    db.delete(member)
    db.commit()
    record_audit(db, company_id=actor.company.id, action="team.remove_member", entity_type="team_member", entity_id=_rm_id, detail={"email": _rm_email}, **actor_fields(actor))
