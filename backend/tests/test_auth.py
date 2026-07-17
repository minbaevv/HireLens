"""Тесты auth: регистрация (SEC-11), верификация email, логин."""
from tests.conftest import mark_verified


def test_register_new_company(client):
    response = client.post(
        "/auth/register",
        json={"email": "test@test.com", "password": "test1234", "company_name": "Test LLC"},
    )
    assert response.status_code == 201
    data = response.json()
    # SEC-11: register больше не выдаёт токен — сначала подтверждение email
    assert "access_token" not in data
    assert data["email"] == "test@test.com"


def test_register_duplicate_email_is_neutral(client):
    payload = {"email": "dup@test.com", "password": "test1234", "company_name": "Dup LLC"}
    first = client.post("/auth/register", json=payload)
    second = client.post("/auth/register", json=payload)
    # SEC-11: занятый email не раскрывается — ответ идентичен по статусу и форме
    assert first.status_code == second.status_code == 201
    assert set(first.json().keys()) == set(second.json().keys())
    assert "access_token" not in second.json()


def test_login_success(client):
    client.post(
        "/auth/register",
        json={"email": "login@test.com", "password": "test1234", "company_name": "Login LLC"},
    )
    mark_verified("login@test.com")
    response = client.post(
        "/auth/login",
        data={"username": "login@test.com", "password": "test1234"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        json={"email": "wrong@test.com", "password": "test1234", "company_name": "Wrong LLC"},
    )
    mark_verified("wrong@test.com")
    response = client.post(
        "/auth/login",
        data={"username": "wrong@test.com", "password": "badpass"},
    )
    assert response.status_code == 401


def test_login_blocked_without_verification(client):
    client.post(
        "/auth/register",
        json={"email": "unverified@test.com", "password": "test1234", "company_name": "Unv LLC"},
    )
    response = client.post(
        "/auth/login",
        data={"username": "unverified@test.com", "password": "test1234"},
    )
    assert response.status_code == 403


def test_protected_route_without_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_protected_route_with_token(client):
    client.post(
        "/auth/register",
        json={"email": "me@test.com", "password": "test1234", "company_name": "Me LLC"},
    )
    mark_verified("me@test.com")
    login_response = client.post(
        "/auth/login",
        data={"username": "me@test.com", "password": "test1234"},
    )
    token = login_response.json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@test.com"
    assert data["company_name"] == "Me LLC"
