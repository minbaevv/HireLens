"""Тесты подтверждения email при регистрации (SEC-11 + верификация)."""
import time
from datetime import datetime, timedelta

from app.models.models import Company
from tests.conftest import TestingSessionLocal


def _get_company(email):
    _db = TestingSessionLocal()
    try:
        return _db.query(Company).filter(Company.email == email).first()
    finally:
        _db.close()


def _code_of(email):
    c = _get_company(email)
    return c.verification_code if c else None


def test_register_returns_neutral_no_token(client):
    r = client.post("/auth/register", json={"email": "v1@test.com", "password": "test1234", "company_name": "V1"})
    assert r.status_code == 201
    data = r.json()
    assert "access_token" not in data
    assert data["email"] == "v1@test.com"
    c = _get_company("v1@test.com")
    assert c is not None and c.is_verified is False
    assert c.verification_code is not None


def test_verify_correct_code(client):
    client.post("/auth/register", json={"email": "v2@test.com", "password": "test1234", "company_name": "V2"})
    code = _code_of("v2@test.com")
    r = client.post("/auth/verify-email", json={"email": "v2@test.com", "code": code})
    assert r.status_code == 200
    assert "access_token" in r.json()
    c = _get_company("v2@test.com")
    assert c.is_verified is True
    assert c.verification_code is None


def test_verify_wrong_code(client):
    client.post("/auth/register", json={"email": "v3@test.com", "password": "test1234", "company_name": "V3"})
    r = client.post("/auth/verify-email", json={"email": "v3@test.com", "code": "000000"})
    assert r.status_code == 400
    assert _get_company("v3@test.com").is_verified is False


def test_verify_expired_code(client):
    client.post("/auth/register", json={"email": "v4@test.com", "password": "test1234", "company_name": "V4"})
    code = _code_of("v4@test.com")
    _db = TestingSessionLocal()
    c = _db.query(Company).filter(Company.email == "v4@test.com").first()
    c.verification_code_expires_at = datetime.utcnow() - timedelta(minutes=1)
    _db.commit()
    _db.close()
    r = client.post("/auth/verify-email", json={"email": "v4@test.com", "code": code})
    assert r.status_code == 400
    # Отдельное сообщение про истёкший код, не путать с "неверный"
    assert "истёк" in r.json()["detail"].lower()
    assert _get_company("v4@test.com").is_verified is False


def test_login_blocked_until_verified(client):
    client.post("/auth/register", json={"email": "v5@test.com", "password": "test1234", "company_name": "V5"})
    r = client.post("/auth/login", data={"username": "v5@test.com", "password": "test1234"})
    assert r.status_code == 403
    code = _code_of("v5@test.com")
    client.post("/auth/verify-email", json={"email": "v5@test.com", "code": code})
    r2 = client.post("/auth/login", data={"username": "v5@test.com", "password": "test1234"})
    assert r2.status_code == 200


def test_register_existing_email_identical_body_and_timing(client):
    # Свободный email
    t0 = time.perf_counter()
    r_free = client.post("/auth/register", json={"email": "free@test.com", "password": "test1234", "company_name": "Free"})
    dt_free = time.perf_counter() - t0
    # Занятый (тот же) email — ответ идентичен по форме и статусу (SEC-11)
    t1 = time.perf_counter()
    r_taken = client.post("/auth/register", json={"email": "free@test.com", "password": "test1234", "company_name": "Free2"})
    dt_taken = time.perf_counter() - t1
    assert r_free.status_code == r_taken.status_code == 201
    assert set(r_free.json().keys()) == set(r_taken.json().keys())
    assert "access_token" not in r_taken.json()
    # Тайминг: обе ветки хешируют пароль, разница не должна быть порядковой (толерантно)
    slow, fast = max(dt_free, dt_taken), min(dt_free, dt_taken)
    assert slow <= fast * 5 + 0.5


def test_resend_code_neutral(client):
    client.post("/auth/register", json={"email": "v6@test.com", "password": "test1234", "company_name": "V6"})
    r = client.post("/auth/resend-code", json={"email": "v6@test.com"})
    assert r.status_code == 200
    # На несуществующий email — тот же нейтральный ответ
    r2 = client.post("/auth/resend-code", json={"email": "nobody@test.com"})
    assert r2.status_code == 200
