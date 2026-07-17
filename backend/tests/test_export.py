"""Тесты экспорта CSV и PDF."""
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_job_and_candidates(client, auth_headers):
    job = client.post(
        "/jobs",
        json={"title": "Dev", "description": "Backend", "requirements": "Python"},
        headers=auth_headers,
    ).json()
    c1 = client.post(f"/apply/{job['apply_token']}",
                     data={"name": "Алекс", "email": "alex@e.com", "resume_text": "5 лет Python"}).json()
    c2 = client.post(f"/apply/{job['apply_token']}",
                     data={"name": "Мария", "email": "maria@e.com", "resume_text": "3 года QA"}).json()
    return job, c1, c2


# ---------------------------------------------------------------------------
# CSV тесты
# ---------------------------------------------------------------------------

def test_export_csv_success(client: TestClient, auth_headers: dict):
    """Успешный экспорт CSV."""
    job, c1, c2 = create_job_and_candidates(client, auth_headers)

    resp = client.get("/candidates/export", headers=auth_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]
    assert ".csv" in resp.headers["content-disposition"]

    content = resp.content.decode("utf-8-sig")
    assert "Алекс" in content
    assert "Мария" in content
    assert "alex@e.com" in content


def test_export_csv_empty(client: TestClient, auth_headers: dict):
    """Пустой экспорт — только заголовок."""
    resp = client.get("/candidates/export", headers=auth_headers)
    assert resp.status_code == 200
    content = resp.content.decode("utf-8-sig")
    lines = [l for l in content.strip().split("\n") if l]
    assert len(lines) == 1  # только заголовок


def test_export_csv_filter_by_status(client: TestClient, auth_headers: dict):
    """Фильтр по статусу работает."""
    job, c1, c2 = create_job_and_candidates(client, auth_headers)
    # Перемещаем c1 в rejected
    client.patch(f"/candidates/{c1['id']}/stage", json={"stage": "rejected"}, headers=auth_headers)

    resp = client.get("/candidates/export?status=rejected", headers=auth_headers)
    assert resp.status_code == 200
    content = resp.content.decode("utf-8-sig")
    assert "Алекс" in content
    assert "Мария" not in content


def test_export_csv_requires_auth(client: TestClient):
    """Без токена → 401."""
    resp = client.get("/candidates/export")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PDF тесты
# ---------------------------------------------------------------------------

def test_export_pdf_success(client: TestClient, auth_headers: dict):
    """Успешный экспорт PDF."""
    job, c1, c2 = create_job_and_candidates(client, auth_headers)

    resp = client.get(f"/candidates/{c1['id']}/report.pdf", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert ".pdf" in resp.headers["content-disposition"]
    # PDF начинается с %PDF
    assert resp.content[:4] == b"%PDF"


def test_export_pdf_not_found(client: TestClient, auth_headers: dict):
    """Несуществующий кандидат → 404."""
    resp = client.get("/candidates/99999/report.pdf", headers=auth_headers)
    assert resp.status_code == 404


def test_export_pdf_requires_auth(client: TestClient):
    """Без токена → 401."""
    resp = client.get("/candidates/1/report.pdf")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Unit тесты generate_candidates_csv
# ---------------------------------------------------------------------------

def test_generate_csv_content():
    """Проверяем содержимое CSV."""
    from app.services.export import generate_candidates_csv
    from app.models.models import CandidateStatus
    from datetime import datetime

    mock_candidate = MagicMock()
    mock_candidate.id = 1
    mock_candidate.name = "Тест Кандидат"
    mock_candidate.email = "test@test.com"
    mock_candidate.status = CandidateStatus.completed
    mock_candidate.score = 85.5
    mock_candidate.recommendation = "hire"
    mock_candidate.job_id = 1
    mock_candidate.created_at = datetime(2026, 6, 30, 12, 0)

    result = generate_candidates_csv([mock_candidate])
    text = result.decode("utf-8-sig")

    assert "Тест Кандидат" in text
    assert "test@test.com" in text
    assert "85.5" in text
    assert "hire" in text
    assert "completed" in text
