"""Тесты аналитики Dashboard."""
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def setup_data(client, auth_headers):
    """Создаёт вакансию + 2 кандидата. Returns (job, c1_id, c2_id)."""
    job = client.post(
        "/jobs",
        json={"title": "Dev", "description": "Backend", "requirements": "Python"},
        headers=auth_headers,
    ).json()
    c1 = client.post(f"/apply/{job['apply_token']}",
                     data={"name": "А", "email": "a@a.com", "resume_text": "ok"}).json()["id"]
    c2 = client.post(f"/apply/{job['apply_token']}",
                     data={"name": "Б", "email": "b@b.com", "resume_text": "ok"}).json()["id"]
    return job, c1, c2


# ---------------------------------------------------------------------------
# Тесты
# ---------------------------------------------------------------------------

def test_analytics_empty(client: TestClient, auth_headers: dict):
    """Пустая компания — все нули."""
    resp = client.get("/analytics/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_jobs"] == 0
    assert data["total_candidates"] == 0
    assert data["avg_score"] is None
    assert data["hire_rate"] == 0.0


def test_analytics_counts(client: TestClient, auth_headers: dict):
    """Количества считаются правильно."""
    job, c1, c2 = setup_data(client, auth_headers)

    resp = client.get("/analytics/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_jobs"] == 1
    assert data["active_jobs"] == 1
    assert data["total_candidates"] == 2


def test_analytics_by_status(client: TestClient, auth_headers: dict):
    """Распределение по статусам корректно."""
    job, c1, c2 = setup_data(client, auth_headers)
    client.patch(f"/candidates/{c1}/stage", json={"stage": "rejected"}, headers=auth_headers)

    resp = client.get("/analytics/summary", headers=auth_headers)
    data = resp.json()
    statuses = {item["status"]: item["count"] for item in data["by_status"]}
    assert statuses.get("applied", 0) == 1
    assert statuses.get("rejected", 0) == 1


def test_analytics_top_jobs(client: TestClient, auth_headers: dict):
    """Топ вакансий возвращается."""
    job, c1, c2 = setup_data(client, auth_headers)

    resp = client.get("/analytics/summary", headers=auth_headers)
    data = resp.json()
    assert len(data["top_jobs"]) == 1
    assert data["top_jobs"][0]["title"] == "Dev"
    assert data["top_jobs"][0]["total_candidates"] == 2


def test_analytics_filter_by_job(client: TestClient, auth_headers: dict):
    """Фильтр по job_id работает."""
    from tests.conftest import grant_plan
    grant_plan("jobs@test.com")  # 2 вакансии → нужен платный тариф (free = 1)
    job1 = client.post("/jobs",
        json={"title": "Job1", "description": "d", "requirements": "r"},
        headers=auth_headers).json()
    job2 = client.post("/jobs",
        json={"title": "Job2", "description": "d", "requirements": "r"},
        headers=auth_headers).json()
    client.post(f"/apply/{job1['apply_token']}",
                data={"name": "И", "email": "i@i.com", "resume_text": "ok"})
    client.post(f"/apply/{job2['apply_token']}",
                data={"name": "М", "email": "m@m.com", "resume_text": "ok"})

    resp = client.get(f"/analytics/summary?job_id={job1['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total_candidates"] == 1


def test_analytics_requires_auth(client: TestClient):
    """Без токена → 401."""
    resp = client.get("/analytics/summary")
    assert resp.status_code == 401
