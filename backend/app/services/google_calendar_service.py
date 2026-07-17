"""B4 — Google Calendar: OAuth-флоу и работа с календарём через REST (httpx).

Без google-* SDK — только httpx, чтобы не тянуть тяжёлые зависимости.
Интеграция включается ТОЛЬКО когда заданы GOOGLE_OAUTH_CLIENT_ID и
GOOGLE_OAUTH_CLIENT_SECRET (settings.google_oauth_enabled).

Token’ы компании хранятся в GoogleCredential; access_token обновляется по
refresh_token автоматически при истечении. Время везде внутри — UTC-naive.
"""
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Optional
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import httpx
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.google_integration import GoogleCredential

logger = logging.getLogger(__name__)

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
USERINFO_URI = "https://www.googleapis.com/oauth2/v3/userinfo"
CALENDAR_BASE = "https://www.googleapis.com/calendar/v3"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    # freeBusy («Свободные слоты») требует доступа на чтение календаря —
    # одного calendar.events недостаточно (иначе 403 Forbidden).
    "https://www.googleapis.com/auth/calendar.readonly",
    "openid",
    "email",
]

_STATE_KIND = "google_oauth"
_STATE_TTL_SECONDS = 600


class GoogleCalendarError(Exception):
    """Ошибка обращения к Google Calendar API / OAuth."""


def is_enabled() -> bool:
    return settings.google_oauth_enabled


# ─── временные хелперы ───

def _now_utc_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_utc_naive(dt: datetime) -> datetime:
    """Приводит datetime к UTC-naive (для хранения в БД и сравнений)."""
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _rfc3339(dt: datetime) -> str:
    """UTC-naive → RFC3339 с суффиксом Z."""
    return dt.replace(microsecond=0).isoformat() + "Z"


def _parse_google_dt(value: str) -> datetime:
    """Парсит dateTime из Google (с offset или Z) → UTC-naive."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    return _to_utc_naive(dt)


def _overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and start_b < end_a


# ─── state (CSRF-защита OAuth) ───

def build_state(company_id: int) -> str:
    payload = {
        "kind": _STATE_KIND,
        "company_id": company_id,
        "nonce": secrets.token_urlsafe(8),
        "exp": datetime.now(UTC) + timedelta(seconds=_STATE_TTL_SECONDS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def parse_state(state: str) -> int:
    try:
        payload = jwt.decode(state, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise GoogleCalendarError("Некорректный или истёкший state") from e
    if payload.get("kind") != _STATE_KIND:
        raise GoogleCalendarError("Некорректный state")
    company_id = payload.get("company_id")
    if not isinstance(company_id, int):
        raise GoogleCalendarError("Некорректный state")
    return company_id


# ─── OAuth ───

def build_auth_url(company_id: int) -> str:
    params = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": build_state(company_id),
    }
    return AUTH_URI + "?" + urlencode(params)


def exchange_code(code: str) -> dict:
    data = {
        "code": code,
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "grant_type": "authorization_code",
    }
    try:
        with httpx.Client(timeout=settings.GOOGLE_HTTP_TIMEOUT_SECONDS) as client:
            resp = client.post(TOKEN_URI, data=data)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.warning("Google token exchange failed: %s", e)
        raise GoogleCalendarError("Не удалось обменять код авторизации") from e


def get_userinfo(access_token: str) -> dict:
    try:
        with httpx.Client(timeout=settings.GOOGLE_HTTP_TIMEOUT_SECONDS) as client:
            resp = client.get(USERINFO_URI, headers={"Authorization": f"Bearer {access_token}"})
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.warning("Google userinfo failed: %s", e)
        return {}


def _refresh_access_token(cred: GoogleCredential) -> dict:
    if not cred.refresh_token:
        raise GoogleCalendarError("Нет refresh_token — переподключите Google Calendar")
    data = {
        "refresh_token": cred.refresh_token,
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "grant_type": "refresh_token",
    }
    try:
        with httpx.Client(timeout=settings.GOOGLE_HTTP_TIMEOUT_SECONDS) as client:
            resp = client.post(TOKEN_URI, data=data)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.warning("Google token refresh failed: %s", e)
        raise GoogleCalendarError("Не удалось обновить токен Google") from e


# ─── хранение кредов ───

def get_credential(db: Session, company_id: int) -> Optional[GoogleCredential]:
    return (
        db.query(GoogleCredential)
        .filter(GoogleCredential.company_id == company_id)
        .first()
    )


def save_credential(
    db: Session,
    company_id: int,
    token_payload: dict,
    userinfo: Optional[dict] = None,
) -> GoogleCredential:
    cred = get_credential(db, company_id)
    access_token = token_payload.get("access_token")
    refresh_token = token_payload.get("refresh_token")
    expires_in = token_payload.get("expires_in")
    scope = token_payload.get("scope")
    email = (userinfo or {}).get("email")

    if cred is None:
        cred = GoogleCredential(company_id=company_id, access_token=access_token or "")
        db.add(cred)
    if access_token:
        cred.access_token = access_token
    # refresh_token приходит только при первом consent — не затираем существующий
    if refresh_token:
        cred.refresh_token = refresh_token
    if expires_in:
        cred.token_expiry = _now_utc_naive() + timedelta(seconds=int(expires_in) - 60)
    if scope:
        cred.scope = scope
    if email:
        cred.google_email = email
    db.commit()
    db.refresh(cred)
    return cred


def disconnect(db: Session, company_id: int) -> None:
    cred = get_credential(db, company_id)
    if cred is not None:
        db.delete(cred)
        db.commit()


def _valid_access_token(db: Session, cred: GoogleCredential) -> str:
    """Возвращает актуальный access_token, обновляя его при истечении."""
    if cred.token_expiry is None or cred.token_expiry <= _now_utc_naive():
        payload = _refresh_access_token(cred)
        save_credential(db, cred.company_id, payload)
        db.refresh(cred)
    return cred.access_token


# ─── Calendar API ───

def _api_request(
    db: Session,
    cred: GoogleCredential,
    method: str,
    path: str,
    *,
    params: Optional[dict] = None,
    json_body: Optional[dict] = None,
) -> dict:
    token = _valid_access_token(db, cred)
    url = CALENDAR_BASE + path
    try:
        with httpx.Client(timeout=settings.GOOGLE_HTTP_TIMEOUT_SECONDS) as client:
            resp = client.request(
                method, url, params=params, json=json_body,
                headers={"Authorization": f"Bearer {token}"},
            )
            # один авто-ретрай при 401 (токен протух между проверкой и запросом)
            if resp.status_code == 401:
                payload = _refresh_access_token(cred)
                save_credential(db, cred.company_id, payload)
                db.refresh(cred)
                resp = client.request(
                    method, url, params=params, json=json_body,
                    headers={"Authorization": f"Bearer {cred.access_token}"},
                )
            resp.raise_for_status()
            if resp.status_code == 204 or not resp.content:
                return {}
            return resp.json()
    except httpx.HTTPError as e:
        logger.warning("Google Calendar API error %s %s: %s", method, path, e)
        raise GoogleCalendarError("Ошибка обращения к Google Calendar") from e


def get_busy_intervals(db, cred, time_min: datetime, time_max: datetime):
    body = {
        "timeMin": _rfc3339(time_min),
        "timeMax": _rfc3339(time_max),
        "items": [{"id": "primary"}],
    }
    data = _api_request(db, cred, "POST", "/freeBusy", json_body=body)
    cal = (data.get("calendars") or {}).get("primary") or {}
    intervals = []
    for b in cal.get("busy", []):
        try:
            intervals.append((_parse_google_dt(b["start"]), _parse_google_dt(b["end"])))
        except Exception:
            continue
    return intervals


def suggest_slots(
    db,
    cred,
    *,
    duration_minutes: int,
    days: int = 7,
    limit: int = 10,
    tz_name: Optional[str] = None,
    work_start: Optional[int] = None,
    work_end: Optional[int] = None,
    now: Optional[datetime] = None,
):
    """Подбирает свободные слоты (Пн–Пт, рабочие часы, без пересечений с busy).

    Возвращает список {"start": RFC3339, "end": RFC3339} (всё в UTC).
    Параметр now — для тестируемости (по умолчанию — текущее время).
    """
    tz_name = tz_name or settings.SCHEDULING_TIMEZONE
    work_start = work_start if work_start is not None else settings.SCHEDULING_WORK_START_HOUR
    work_end = work_end if work_end is not None else settings.SCHEDULING_WORK_END_HOUR
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")

    if now is not None:
        now_aware = now if now.tzinfo else now.replace(tzinfo=UTC)
        now_utc = now_aware.astimezone(UTC).replace(tzinfo=None)
        now_local = now_aware.astimezone(tz)
    else:
        now_utc = _now_utc_naive()
        now_local = datetime.now(tz)

    time_max = now_utc + timedelta(days=days)
    busy = get_busy_intervals(db, cred, now_utc, time_max)

    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=settings.SCHEDULING_SLOT_MINUTES)
    slots = []
    for day_offset in range(days + 1):
        day = (now_local + timedelta(days=day_offset)).date()
        if datetime(day.year, day.month, day.day).weekday() >= 5:  # Сб/Вс
            continue
        cursor = datetime(day.year, day.month, day.day, work_start, 0, tzinfo=tz)
        day_end = datetime(day.year, day.month, day.day, work_end, 0, tzinfo=tz)
        while cursor + duration <= day_end:
            start_utc = _to_utc_naive(cursor)
            end_utc = start_utc + duration
            if start_utc <= now_utc:
                cursor += step
                continue
            conflict = any(_overlaps(start_utc, end_utc, bs, be) for bs, be in busy)
            if not conflict:
                slots.append({"start": _rfc3339(start_utc), "end": _rfc3339(end_utc)})
                if len(slots) >= limit:
                    return slots
            cursor += step
    return slots


def create_event(
    db,
    cred,
    *,
    summary: str,
    description: str,
    start_time: datetime,
    end_time: datetime,
    attendees: Optional[list] = None,
    add_meet: bool = True,
    send_updates: str = "all",
) -> dict:
    """Создаёт событие с Google Meet. start/end — UTC-naive."""
    event = {
        "summary": summary,
        "description": description or "",
        "start": {"dateTime": _rfc3339(start_time), "timeZone": "UTC"},
        "end": {"dateTime": _rfc3339(end_time), "timeZone": "UTC"},
    }
    if attendees:
        event["attendees"] = [{"email": e} for e in attendees if e]
    params = {"sendUpdates": send_updates}
    if add_meet:
        params["conferenceDataVersion"] = 1
        event["conferenceData"] = {
            "createRequest": {
                "requestId": secrets.token_urlsafe(16),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }
    data = _api_request(db, cred, "POST", "/calendars/primary/events", params=params, json_body=event)
    meet_link = None
    for ep in (data.get("conferenceData") or {}).get("entryPoints") or []:
        if ep.get("entryPointType") == "video":
            meet_link = ep.get("uri")
            break
    if not meet_link:
        meet_link = data.get("hangoutLink")
    return {
        "id": data.get("id"),
        "html_link": data.get("htmlLink"),
        "meet_link": meet_link,
    }


def delete_event(db, cred, event_id: str, send_updates: str = "all") -> None:
    _api_request(
        db, cred, "DELETE", f"/calendars/primary/events/{event_id}",
        params={"sendUpdates": send_updates},
    )
