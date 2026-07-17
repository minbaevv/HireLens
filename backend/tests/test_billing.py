"""Тесты ручного управления подпиской: billing + admin + ограничение доступа."""
from datetime import datetime, timedelta

from app.core.config import settings
from app.models.models import Company


def _company(db):
    return db.query(Company).filter(Company.email == "jobs@test.com").first()


def test_billing_me_defaults_free(client, auth_headers):
    r = client.get("/billing/me", headers=auth_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["plan"] == "free"
    assert data["is_free"] is True
    assert data["active"] is True
    assert "payment_info" in data


def test_admin_requires_superadmin(client, auth_headers):
    settings.SUPERADMIN_EMAILS = ""
    r = client.get("/admin/companies", headers=auth_headers)
    assert r.status_code == 403


def test_admin_set_plan_then_billing_active(client, auth_headers, db):
    settings.SUPERADMIN_EMAILS = "jobs@test.com"
    cid = _company(db).id
    r = client.post(f"/admin/companies/{cid}/plan", headers=auth_headers, json={"plan": "starter", "months": 2})
    assert r.status_code == 200, r.text
    assert r.json()["plan"] == "starter"
    b = client.get("/billing/me", headers=auth_headers).json()
    assert b["plan"] == "starter"
    assert b["active"] is True
    assert b["days_left"] is not None and b["days_left"] >= 55
    # возврат к free, чтобы не влиять на другие тесты
    c = _company(db)
    c.plan = "free"
    c.plan_expires_at = None
    db.commit()


def test_grant_bonus_extends(client, auth_headers, db):
    settings.SUPERADMIN_EMAILS = "jobs@test.com"
    cid = _company(db).id
    r = client.post(f"/admin/companies/{cid}/grant-bonus", headers=auth_headers, json={"months": 1})
    assert r.status_code == 200, r.text
    assert r.json()["plan"] in {"starter", "pro"}
    c = _company(db)
    c.plan = "free"
    c.plan_expires_at = None
    db.commit()


def test_expired_subscription_blocks_job_creation(client, auth_headers, db):
    settings.SUPERADMIN_EMAILS = ""
    c = _company(db)
    c.plan = "starter"
    c.plan_expires_at = datetime.utcnow() - timedelta(days=1)
    db.commit()
    r = client.post(
        "/jobs",
        headers=auth_headers,
        json={"title": "T", "description": "D", "requirements": "R", "language": "ru"},
    )
    assert r.status_code == 402
    # сброс обратно к free
    c = _company(db)
    c.plan = "free"
    c.plan_expires_at = None
    db.commit()


def test_trial_granted_on_verify(client, db):
    """Новая компания при подтверждении email получает Starter на 3 дня (пробный период)."""
    settings.SUPERADMIN_EMAILS = ""
    email = "trial@test.com"
    client.post(
        "/auth/register",
        json={"email": email, "password": "test1234", "company_name": "Trial LLC"},
    )
    c = db.query(Company).filter(Company.email == email).first()
    code = c.verification_code
    assert code, "код подтверждения должен быть сохранён при регистрации"
    r = client.post("/auth/verify-email", json={"email": email, "code": code})
    assert r.status_code == 200, r.text

    db.expire_all()
    c = db.query(Company).filter(Company.email == email).first()
    assert c.plan == "starter"
    assert c.plan_expires_at is not None
    delta = c.plan_expires_at - datetime.utcnow()
    # ровно 3 дня (с округлением вниз .days даёт 2, т.к. прошло несколько мс)
    assert 2 <= delta.days <= 3


def test_trial_expires_and_blocks(client, db):
    """После окончания пробного Starter доступ к платным функциям блокируется (402)."""
    settings.SUPERADMIN_EMAILS = ""
    email = "trialexp@test.com"
    client.post(
        "/auth/register",
        json={"email": email, "password": "test1234", "company_name": "TrialExp LLC"},
    )
    c = db.query(Company).filter(Company.email == email).first()
    code = c.verification_code
    r = client.post("/auth/verify-email", json={"email": email, "code": code})
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # эмулируем окончание пробы
    c.plan_expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()

    jr = client.post(
        "/jobs",
        headers=headers,
        json={"title": "T", "description": "D", "requirements": "R", "language": "ru"},
    )
    assert jr.status_code == 402
