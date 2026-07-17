"""Тесты реферальной программы (Roadmap D3).

ВРЕМЕННО ОТКЛЮЧЕНО (v29): реферальная программа скрыта из UI и роутер
`/referral` не подключён в main.py. Сами тесты сохранены и будут вновь активированы
при повторном включении фичи (убрать pytestmark ниже).
"""
import pytest

pytestmark = pytest.mark.skip(
    reason="Реферальная программа временно отключена (v29). Вернём позже."
)


def _register(client, email, referral_code=None):
    body = {"email": email, "password": "test1234", "company_name": "Ref Co"}
    if referral_code:
        body["referral_code"] = referral_code
    return client.post("/auth/register", json=body)


def test_referral_me_generates_code(client, auth_headers):
    r = client.get("/referral/me", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["code"]
    assert data["code"] in data["share_url"]
    assert data["referred_count"] == 0
    assert data["reward_months"] == 0


def test_referral_code_is_stable(client, auth_headers):
    a = client.get("/referral/me", headers=auth_headers).json()["code"]
    b = client.get("/referral/me", headers=auth_headers).json()["code"]
    assert a == b


def test_referral_counts_referred_signup(client, auth_headers):
    code = client.get("/referral/me", headers=auth_headers).json()["code"]
    resp = _register(client, "referred@test.com", referral_code=code)
    assert resp.status_code == 201
    data = client.get("/referral/me", headers=auth_headers).json()
    assert data["referred_count"] == 1
    assert data["reward_months"] == 1


def test_invalid_referral_code_ignored(client, auth_headers):
    resp = _register(client, "noref@test.com", referral_code="NOPE_xxx")
    assert resp.status_code == 201
    data = client.get("/referral/me", headers=auth_headers).json()
    assert data["referred_count"] == 0


def test_referral_requires_auth(client):
    assert client.get("/referral/me").status_code == 401
