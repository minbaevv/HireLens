"""Тесты мультиязычности вакансий (шаг A6.1)."""

JOB_PAYLOAD = {
    "title": "Backend Developer",
    "description": "Разработка API",
    "requirements": "Python, FastAPI",
}


def test_create_job_default_language_is_ru(client, auth_headers):
    resp = client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["language"] == "ru"


def test_create_job_with_kyrgyz_language(client, auth_headers):
    resp = client.post("/jobs", json={**JOB_PAYLOAD, "language": "ky"}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["language"] == "ky"


def test_create_job_with_english_language(client, auth_headers):
    resp = client.post("/jobs", json={**JOB_PAYLOAD, "language": "en"}, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["language"] == "en"


def test_create_job_unsupported_language_rejected(client, auth_headers):
    resp = client.post("/jobs", json={**JOB_PAYLOAD, "language": "de"}, headers=auth_headers)
    assert resp.status_code == 422


def test_update_job_language(client, auth_headers):
    created = client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers).json()
    resp = client.patch(
        f"/jobs/{created['id']}", json={"language": "ky"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["language"] == "ky"
