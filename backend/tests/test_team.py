"""Тесты командного доступа с ролями (B1)."""
from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from app.models.models import Company
from app.models.team_member import TeamMember, TeamRole
from tests.conftest import TestingSessionLocal


def register_and_login(client: TestClient, email="owner@test.com", company_name="Team LLC") -> dict:
    client.post("/auth/register", json={"email": email, "password": "test1234", "company_name": company_name})
    _vdb = TestingSessionLocal()
    _vc = _vdb.query(Company).filter(Company.email == email).first()
    if _vc:
        _vc.is_verified = True
        _vdb.commit()
    _vdb.close()
    resp = client.post("/auth/login", data={"username": email, "password": "test1234"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_active_member(email: str, password: str, role: TeamRole) -> None:
    """Создаёт уже активированного участника напрямую в БД (без флоу приглашения)."""
    db = TestingSessionLocal()
    try:
        company = db.query(Company).first()
        member = TeamMember(
            company_id=company.id,
            name="Member",
            email=email,
            hashed_password=get_password_hash(password),
            role=role,
            is_active=True,
            invite_token=None,
        )
        db.add(member)
        db.commit()
    finally:
        db.close()


def test_invite_member_as_owner(client: TestClient):
    headers = register_and_login(client)
    resp = client.post(
        "/team/invite",
        json={"email": "rec@test.com", "name": "Recruiter", "role": "recruiter"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "rec@test.com"
    assert data["role"] == "recruiter"
    assert data["is_active"] is False


def test_invite_duplicate_email(client: TestClient):
    headers = register_and_login(client)
    client.post("/team/invite", json={"email": "dup@test.com", "name": "A", "role": "viewer"}, headers=headers)
    resp = client.post("/team/invite", json={"email": "dup@test.com", "name": "B", "role": "viewer"}, headers=headers)
    assert resp.status_code == 409


def test_accept_invite_and_login(client: TestClient):
    headers = register_and_login(client)
    client.post("/team/invite", json={"email": "new@test.com", "name": "New", "role": "admin"}, headers=headers)

    db = TestingSessionLocal()
    member = db.query(TeamMember).filter(TeamMember.email == "new@test.com").first()
    token = member.invite_token
    db.close()

    resp = client.post("/team/accept-invite", json={"token": token, "password": "newpass123"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]

    login_resp = client.post("/auth/login", data={"username": "new@test.com", "password": "newpass123"})
    assert login_resp.status_code == 200


def test_accept_invite_invalid_token(client: TestClient):
    resp = client.post("/team/accept-invite", json={"token": "bogus-token", "password": "x1234567"})
    assert resp.status_code == 404


def test_accept_invite_twice_fails(client: TestClient):
    headers = register_and_login(client)
    client.post("/team/invite", json={"email": "twice@test.com", "name": "Twice", "role": "viewer"}, headers=headers)

    db = TestingSessionLocal()
    member = db.query(TeamMember).filter(TeamMember.email == "twice@test.com").first()
    token = member.invite_token
    db.close()

    first = client.post("/team/accept-invite", json={"token": token, "password": "pass12345"})
    assert first.status_code == 200

    second = client.post("/team/accept-invite", json={"token": token, "password": "pass12345"})
    assert second.status_code == 404


def test_viewer_cannot_invite(client: TestClient):
    register_and_login(client)
    _create_active_member("viewer@test.com", "viewerpass1", TeamRole.viewer)

    login_resp = client.post("/auth/login", data={"username": "viewer@test.com", "password": "viewerpass1"})
    viewer_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    resp = client.post(
        "/team/invite", json={"email": "x@test.com", "name": "X", "role": "recruiter"}, headers=viewer_headers
    )
    assert resp.status_code == 403


def test_list_team_visible_to_all_roles(client: TestClient):
    headers = register_and_login(client)
    client.post("/team/invite", json={"email": "list@test.com", "name": "Lister", "role": "recruiter"}, headers=headers)
    resp = client.get("/team", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_team_member_shares_company_resources(client: TestClient):
    """Участник команды использует существующие эндпоинты (jobs) наравне с владельцем."""
    owner_headers = register_and_login(client)
    _create_active_member("rec2@test.com", "recpass123", TeamRole.recruiter)

    login_resp = client.post("/auth/login", data={"username": "rec2@test.com", "password": "recpass123"})
    member_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    create_resp = client.post(
        "/jobs", json={"title": "QA", "description": "d", "requirements": "r"}, headers=member_headers
    )
    assert create_resp.status_code == 201

    owner_jobs = client.get("/jobs", headers=owner_headers)
    assert owner_jobs.status_code == 200
    assert len(owner_jobs.json()) == 1
