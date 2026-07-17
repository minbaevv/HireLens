"""Тесты для Candidate Flow."""
import io
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_job(client: TestClient, auth_headers: dict) -> dict:
    resp = client.post(
        "/jobs",
        json={"title": "Python Dev", "description": "FastAPI разработчик", "requirements": "Python 3+"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Публичные эндпоинты
# ---------------------------------------------------------------------------

def test_get_job_by_token(client: TestClient, auth_headers: dict):
    """Кандидат может получить информацию о вакансии по токену."""
    job = create_job(client, auth_headers)
    token = job["apply_token"]

    resp = client.get(f"/apply/{token}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Python Dev"
    assert "description" in data
    assert "requirements" in data
    # Приватные поля не должны утекать
    assert "apply_token" not in data
    assert "company_id" not in data


def test_get_job_by_invalid_token(client: TestClient):
    """Несуществующий токен → 404."""
    resp = client.get("/apply/nonexistent-token-xyz")
    assert resp.status_code == 404


def test_apply_with_text_resume(client: TestClient, auth_headers: dict):
    """Кандидат подаёт заявку с текстовым резюме."""
    job = create_job(client, auth_headers)
    token = job["apply_token"]

    resp = client.post(
        f"/apply/{token}",
        data={
            "name": "Иван Иванов",
            "email": "ivan@example.com",
            "resume_text": "5 лет опыта Python, FastAPI, PostgreSQL",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Иван Иванов"
    assert data["email"] == "ivan@example.com"
    assert data["status"] == "applied"
    assert data["resume_text"] == "5 лет опыта Python, FastAPI, PostgreSQL"


def test_apply_without_resume(client: TestClient, auth_headers: dict):
    """Заявка без резюме — допустима (резюме опционально)."""
    job = create_job(client, auth_headers)
    token = job["apply_token"]

    resp = client.post(
        f"/apply/{token}",
        data={"name": "Анна", "email": "anna@example.com"},
    )
    assert resp.status_code == 201
    assert resp.json()["resume_text"] is None


def test_apply_duplicate_email(client: TestClient, auth_headers: dict):
    """Повторная заявка с тем же email → 409."""
    job = create_job(client, auth_headers)
    token = job["apply_token"]

    data = {"name": "Дубль", "email": "dup@example.com"}
    client.post(f"/apply/{token}", data=data)
    resp = client.post(f"/apply/{token}", data=data)
    assert resp.status_code == 409


def test_apply_with_txt_file(client: TestClient, auth_headers: dict):
    """Кандидат загружает .txt файл резюме."""
    job = create_job(client, auth_headers)
    token = job["apply_token"]

    txt_content = b"Senior Python Developer. 7 years experience."
    resp = client.post(
        f"/apply/{token}",
        data={"name": "Файл Тест", "email": "file@example.com"},
        files={"resume_file": ("resume.txt", io.BytesIO(txt_content), "text/plain")},
    )
    assert resp.status_code == 201
    assert "Senior Python Developer" in resp.json()["resume_text"]


def test_apply_invalid_file_extension(client: TestClient, auth_headers: dict):
    """Неподдерживаемый формат файла → 422."""
    job = create_job(client, auth_headers)
    token = job["apply_token"]

    resp = client.post(
        f"/apply/{token}",
        data={"name": "Тест", "email": "ext@example.com"},
        files={"resume_file": ("resume.exe", io.BytesIO(b"bad"), "application/octet-stream")},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# HR эндпоинты
# ---------------------------------------------------------------------------

def test_list_candidates(client: TestClient, auth_headers: dict):
    """HR видит кандидатов своей компании."""
    job = create_job(client, auth_headers)
    token = job["apply_token"]

    client.post(f"/apply/{token}", data={"name": "A", "email": "a@a.com"})
    client.post(f"/apply/{token}", data={"name": "B", "email": "b@b.com"})

    resp = client.get("/candidates", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_get_candidate_detail(client: TestClient, auth_headers: dict):
    """HR получает детали конкретного кандидата."""
    job = create_job(client, auth_headers)
    token = job["apply_token"]

    apply_resp = client.post(
        f"/apply/{token}",
        data={"name": "Детали", "email": "detail@example.com", "resume_text": "Опыт 3 года"},
    )
    candidate_id = apply_resp.json()["id"]

    resp = client.get(f"/candidates/{candidate_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Детали"
    assert data["resume_text"] == "Опыт 3 года"


def test_list_candidates_requires_review_filter(client: TestClient, auth_headers: dict, db):
    """Фильтр requires_review=true возвращает только помеченных на ручную проверку."""
    job = create_job(client, auth_headers)
    token = job["apply_token"]

    a = client.post(f"/apply/{token}", data={"name": "Flagged", "email": "flag@a.com"}).json()
    client.post(f"/apply/{token}", data={"name": "Normal", "email": "norm@a.com"})

    from app.models.models import Candidate
    cand = db.query(Candidate).filter(Candidate.id == a["id"]).first()
    cand.requires_manual_review = True
    db.commit()

    resp = client.get("/candidates", headers=auth_headers, params={"requires_review": "true"})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Flagged"
    assert items[0]["requires_manual_review"] is True
