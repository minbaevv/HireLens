"""Тесты ролевых ограничений на существующих эндпоинтах (B1.2)."""
from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from app.models.models import Company
from app.models.team_member import TeamMember, TeamRole
from tests.conftest import TestingSessionLocal


def register_and_login(client: TestClient, email="owner@test.com", company_name="RoleTest LLC") -> dict:
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


def _login_as_member(email: str, password: str, role: TeamRole) -> dict:
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


def _create_job(client: TestClient, headers: dict) -> int:
    resp = client.post(
        "/jobs", json={"title": "QA", "description": "d", "requirements": "r"}, headers=headers
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_viewer_cannot_create_job(client: TestClient):
    owner_headers = register_and_login(client)
    _create_job(client, owner_headers)  # чтобы в компании была хотя бы одна вакансия

    _login_as_member("viewer@test.com", "viewerpass1", TeamRole.viewer)
    login_resp = client.post("/auth/login", data={"username": "viewer@test.com", "password": "viewerpass1"})
    viewer_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    resp = client.post(
        "/jobs", json={"title": "Backend", "description": "d", "requirements": "r"}, headers=viewer_headers
    )
    assert resp.status_code == 403


def test_viewer_cannot_update_or_delete_job(client: TestClient):
    owner_headers = register_and_login(client)
    job_id = _create_job(client, owner_headers)

    _login_as_member("viewer2@test.com", "viewerpass2", TeamRole.viewer)
    login_resp = client.post("/auth/login", data={"username": "viewer2@test.com", "password": "viewerpass2"})
    viewer_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    update_resp = client.patch(f"/jobs/{job_id}", json={"title": "Hacked"}, headers=viewer_headers)
    assert update_resp.status_code == 403

    delete_resp = client.delete(f"/jobs/{job_id}", headers=viewer_headers)
    assert delete_resp.status_code == 403


def test_viewer_can_still_read_jobs(client: TestClient):
    owner_headers = register_and_login(client)
    _create_job(client, owner_headers)

    _login_as_member("viewer3@test.com", "viewerpass3", TeamRole.viewer)
    login_resp = client.post("/auth/login", data={"username": "viewer3@test.com", "password": "viewerpass3"})
    viewer_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    resp = client.get("/jobs", headers=viewer_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_recruiter_can_create_and_delete_job(client: TestClient):
    register_and_login(client)

    _login_as_member("rec@test.com", "recpass123", TeamRole.recruiter)
    login_resp = client.post("/auth/login", data={"username": "rec@test.com", "password": "recpass123"})
    rec_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    job_id = _create_job(client, rec_headers)

    delete_resp = client.delete(f"/jobs/{job_id}", headers=rec_headers)
    assert delete_resp.status_code == 204


def test_viewer_cannot_change_candidate_status(client: TestClient):
    owner_headers = register_and_login(client)
    job_resp = client.post(
        "/jobs", json={"title": "QA", "description": "d", "requirements": "r"}, headers=owner_headers
    )
    apply_token = job_resp.json()["apply_token"]
    apply_resp = client.post(
        f"/apply/{apply_token}",
        data={"name": "Анна", "email": "anna@test.com", "resume_text": "opyt"},
    )
    candidate_id = apply_resp.json()["id"]

    _login_as_member("viewer4@test.com", "viewerpass4", TeamRole.viewer)
    login_resp = client.post("/auth/login", data={"username": "viewer4@test.com", "password": "viewerpass4"})
    viewer_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    resp = client.patch(
        f"/candidates/{candidate_id}/status?new_status=hired", headers=viewer_headers
    )
    assert resp.status_code == 403


def test_viewer_can_still_view_candidate(client: TestClient):
    owner_headers = register_and_login(client)
    job_resp = client.post(
        "/jobs", json={"title": "QA", "description": "d", "requirements": "r"}, headers=owner_headers
    )
    apply_token = job_resp.json()["apply_token"]
    apply_resp = client.post(
        f"/apply/{apply_token}",
        data={"name": "Борис", "email": "boris@test.com", "resume_text": "opyt"},
    )
    candidate_id = apply_resp.json()["id"]

    _login_as_member("viewer5@test.com", "viewerpass5", TeamRole.viewer)
    login_resp = client.post("/auth/login", data={"username": "viewer5@test.com", "password": "viewerpass5"})
    viewer_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    resp = client.get(f"/candidates/{candidate_id}", headers=viewer_headers)
    assert resp.status_code == 200
