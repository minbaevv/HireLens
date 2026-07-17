"""B4 — Google Calendar: OAuth-подключение и автопланирование интервью.

Эндпоинты под /integrations/google. Весь функционал активен только когда
заданы GOOGLE_OAUTH_CLIENT_ID / SECRET и компания подключила аккаунт.
"""
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import (
    CurrentActor,
    get_current_actor,
    get_current_company,
    require_admin,
    require_write_access,
)
from app.core.audit import actor_fields, record_audit
from app.core.config import settings
from app.core.db import get_db
from app.models.candidate import Candidate, CandidateStatus
from app.models.company import Company
from app.models.google_integration import ScheduledInterview
from app.models.job import Job
from app.services import google_calendar_service as gcal
from app.services.google_calendar_service import GoogleCalendarError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations/google", tags=["google-calendar"])


class ScheduleIn(BaseModel):
    candidate_id: int
    start: str  # ISO 8601
    duration_minutes: int = Field(default=30, ge=10, le=240)
    title: Optional[str] = None
    notes: Optional[str] = None
    invite_candidate: bool = True


def _parse_iso_to_utc_naive(value: str) -> datetime:
    try:
        v = value.strip()
        if v.endswith("Z"):
            v = v[:-1] + "+00:00"
        dt = datetime.fromisoformat(v)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=422, detail="Некорректный формат даты (ожидается ISO 8601)")
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _scheduled_out(si: ScheduledInterview) -> dict:
    attendees = []
    if si.attendees:
        try:
            attendees = json.loads(si.attendees)
        except Exception:
            attendees = []
    return {
        "id": si.id,
        "candidate_id": si.candidate_id,
        "job_id": si.job_id,
        "title": si.title,
        "description": si.description,
        "start_time": (si.start_time.isoformat() + "Z") if si.start_time else None,
        "end_time": (si.end_time.isoformat() + "Z") if si.end_time else None,
        "google_event_id": si.google_event_id,
        "meet_link": si.meet_link,
        "html_link": si.html_link,
        "attendees": attendees,
        "status": si.status,
        "created_by_email": si.created_by_email,
        "created_at": si.created_at.isoformat() if si.created_at else None,
    }


@router.get("/status")
def google_status(
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
):
    cred = gcal.get_credential(db, company.id)
    return {
        "enabled": gcal.is_enabled(),
        "connected": cred is not None,
        "email": cred.google_email if cred else None,
        "redirect_uri": settings.google_oauth_redirect_uri,
    }


@router.get("/authorize")
def google_authorize(actor: CurrentActor = Depends(require_admin)):
    if not gcal.is_enabled():
        raise HTTPException(status_code=400, detail="Интеграция Google Calendar не настроена на сервере")
    return {"url": gcal.build_auth_url(actor.company.id)}


@router.get("/callback", include_in_schema=False)
def google_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
):
    front = settings.FRONTEND_URL.rstrip("/")
    if error or not code or not state:
        return RedirectResponse(url=f"{front}/integrations?google=error")
    try:
        company_id = gcal.parse_state(state)
        token_payload = gcal.exchange_code(code)
        userinfo = gcal.get_userinfo(token_payload.get("access_token", ""))
        gcal.save_credential(db, company_id, token_payload, userinfo)
    except GoogleCalendarError as e:
        logger.warning("Google callback error: %s", e)
        return RedirectResponse(url=f"{front}/integrations?google=error")
    except Exception as e:  # noqa: BLE001 — никогда не роняем redirect
        logger.exception("Google callback unexpected error: %s", e)
        return RedirectResponse(url=f"{front}/integrations?google=error")
    return RedirectResponse(url=f"{front}/integrations?google=connected")


@router.post("/disconnect")
def google_disconnect(
    request: Request,
    actor: CurrentActor = Depends(require_admin),
    db: Session = Depends(get_db),
):
    gcal.disconnect(db, actor.company.id)
    record_audit(
        db, company_id=actor.company.id, action="google.disconnect",
        **actor_fields(actor), request=request,
    )
    return {"ok": True}


@router.get("/free-slots")
def google_free_slots(
    days: int = Query(7, ge=1, le=30),
    duration: int = Query(0, ge=0, le=240),
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
):
    cred = gcal.get_credential(db, company.id)
    if cred is None:
        raise HTTPException(status_code=400, detail="Google Calendar не подключён")
    dur = duration or settings.SCHEDULING_SLOT_MINUTES
    try:
        return gcal.suggest_slots(db, cred, duration_minutes=dur, days=days, limit=12)
    except GoogleCalendarError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/scheduled")
def google_scheduled(
    candidate_id: Optional[int] = None,
    company: Company = Depends(get_current_company),
    db: Session = Depends(get_db),
):
    q = db.query(ScheduledInterview).filter(ScheduledInterview.company_id == company.id)
    if candidate_id is not None:
        q = q.filter(ScheduledInterview.candidate_id == candidate_id)
    items = q.order_by(ScheduledInterview.start_time.desc()).all()
    return [_scheduled_out(i) for i in items]


@router.post("/schedule", status_code=201)
def google_schedule(
    body: ScheduleIn,
    request: Request,
    actor: CurrentActor = Depends(require_write_access),
    db: Session = Depends(get_db),
):
    company = actor.company
    cred = gcal.get_credential(db, company.id)
    if cred is None:
        raise HTTPException(status_code=400, detail="Google Calendar не подключён")
    candidate = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Candidate.id == body.candidate_id, Job.company_id == company.id)
        .first()
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Кандидат не найден")

    start = _parse_iso_to_utc_naive(body.start)
    end = start + timedelta(minutes=body.duration_minutes)
    title = body.title or f"Интервью: {candidate.name}"

    attendees = []
    if body.invite_candidate and candidate.email:
        attendees.append(candidate.email)
    if company.email:
        attendees.append(company.email)

    try:
        result = gcal.create_event(
            db, cred,
            summary=title,
            description=body.notes or "",
            start_time=start,
            end_time=end,
            attendees=attendees,
        )
    except GoogleCalendarError as e:
        raise HTTPException(status_code=502, detail=str(e))

    created_by_email = getattr(actor.team_member, "email", None) or company.email
    si = ScheduledInterview(
        company_id=company.id,
        candidate_id=candidate.id,
        job_id=candidate.job_id,
        title=title,
        description=body.notes,
        start_time=start,
        end_time=end,
        google_event_id=result.get("id"),
        meet_link=result.get("meet_link"),
        html_link=result.get("html_link"),
        attendees=json.dumps(attendees, ensure_ascii=False),
        status="scheduled",
        created_by_email=created_by_email,
    )
    db.add(si)
    if candidate.status == CandidateStatus.applied:
        candidate.status = CandidateStatus.interviewing
    db.commit()
    db.refresh(si)

    record_audit(
        db, company_id=company.id, action="interview.schedule",
        entity_type="candidate", entity_id=candidate.id,
        detail={"scheduled_interview_id": si.id, "start": start.isoformat()},
        **actor_fields(actor), request=request,
    )
    return _scheduled_out(si)


@router.delete("/scheduled/{scheduled_id}")
def google_cancel(
    scheduled_id: int,
    request: Request,
    actor: CurrentActor = Depends(require_write_access),
    db: Session = Depends(get_db),
):
    company = actor.company
    si = (
        db.query(ScheduledInterview)
        .filter(ScheduledInterview.id == scheduled_id, ScheduledInterview.company_id == company.id)
        .first()
    )
    if si is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if si.status != "cancelled" and si.google_event_id:
        cred = gcal.get_credential(db, company.id)
        if cred is not None:
            try:
                gcal.delete_event(db, cred, si.google_event_id)
            except GoogleCalendarError as e:
                logger.warning("Не удалось удалить событие Google: %s", e)

    si.status = "cancelled"
    db.commit()
    db.refresh(si)

    record_audit(
        db, company_id=company.id, action="interview.cancel",
        entity_type="candidate", entity_id=si.candidate_id,
        detail={"scheduled_interview_id": si.id},
        **actor_fields(actor), request=request,
    )
    return _scheduled_out(si)
