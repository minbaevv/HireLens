"""B4 — тесты Google Calendar интеграции.

Сеть не дёргаем: OAuth/Calendar-вызовы либо не выполняются (интеграция
выключена по умолчанию), либо замокаются (get_busy_intervals).
"""
from datetime import UTC, datetime

import pytest

from app.core.config import settings
from app.services import google_calendar_service as gcal
from app.services.google_calendar_service import GoogleCalendarError


def test_disabled_by_default(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    assert gcal.is_enabled() is False


def test_state_roundtrip():
    state = gcal.build_state(42)
    assert gcal.parse_state(state) == 42


def test_parse_state_invalid():
    with pytest.raises(GoogleCalendarError):
        gcal.parse_state("not-a-jwt")


def test_parse_google_dt():
    assert gcal._parse_google_dt("2026-07-20T10:00:00Z") == datetime(2026, 7, 20, 10, 0, 0)
    # с offset +03:00 → приводится к UTC
    assert gcal._parse_google_dt("2026-07-20T13:00:00+03:00") == datetime(2026, 7, 20, 10, 0, 0)


def test_overlaps():
    a0 = datetime(2026, 7, 20, 10, 0)
    a1 = datetime(2026, 7, 20, 11, 0)
    assert gcal._overlaps(a0, a1, datetime(2026, 7, 20, 10, 30), datetime(2026, 7, 20, 10, 45))
    assert not gcal._overlaps(a0, a1, datetime(2026, 7, 20, 11, 0), datetime(2026, 7, 20, 12, 0))


def test_suggest_slots(monkeypatch):
    # без сети: замокаем freeBusy пустым списком
    monkeypatch.setattr(gcal, "get_busy_intervals", lambda *a, **k: [])
    monday = datetime(2026, 7, 20, 6, 0, tzinfo=UTC)  # понедельник
    slots = gcal.suggest_slots(
        None, None, duration_minutes=30, days=1, limit=3, tz_name="UTC", now=monday,
    )
    assert len(slots) == 3
    assert slots[0]["start"].startswith("2026-07-20T10:00:00")


def test_status_endpoint(client, auth_headers):
    resp = client.get("/integrations/google/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False


def test_authorize_requires_config(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    resp = client.get("/integrations/google/authorize", headers=auth_headers)
    assert resp.status_code == 400
