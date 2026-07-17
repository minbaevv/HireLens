JOB_PAYLOAD = {
    "title": "Backend Developer",
    "description": "Разработка backend на FastAPI",
    "requirements": "Python, FastAPI, PostgreSQL",
}


def test_create_job(client, auth_headers):
    response = client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == JOB_PAYLOAD["title"]
    assert data["apply_token"] in data["apply_link"]
    assert data["is_active"] is True


def test_create_job_without_token(client):
    response = client.post("/jobs", json=JOB_PAYLOAD)
    assert response.status_code == 401


def test_list_jobs_only_own_company(client, auth_headers):
    client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)

    client.post(
        "/auth/register",
        json={"email": "other@test.com", "password": "test1234", "company_name": "Other LLC"},
    )
    from tests.conftest import mark_verified
    mark_verified("other@test.com")
    other_login = client.post(
        "/auth/login", data={"username": "other@test.com", "password": "test1234"}
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    client.post("/jobs", json={**JOB_PAYLOAD, "title": "Other Job"}, headers=other_headers)

    response = client.get("/jobs", headers=auth_headers)
    assert response.status_code == 200
    titles = [job["title"] for job in response.json()]
    assert titles == [JOB_PAYLOAD["title"]]


def test_get_job_by_id(client, auth_headers):
    created = client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers).json()
    response = client.get(f"/jobs/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_job_not_found(client, auth_headers):
    response = client.get("/jobs/999999", headers=auth_headers)
    assert response.status_code == 404


def test_get_job_of_other_company_forbidden(client, auth_headers):
    created = client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers).json()

    client.post(
        "/auth/register",
        json={"email": "intruder@test.com", "password": "test1234", "company_name": "Intruder LLC"},
    )
    from tests.conftest import mark_verified
    mark_verified("intruder@test.com")
    intruder_login = client.post(
        "/auth/login", data={"username": "intruder@test.com", "password": "test1234"}
    )
    intruder_headers = {"Authorization": f"Bearer {intruder_login.json()['access_token']}"}

    response = client.get(f"/jobs/{created['id']}", headers=intruder_headers)
    assert response.status_code == 404


def test_update_job(client, auth_headers):
    created = client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers).json()
    response = client.patch(
        f"/jobs/{created['id']}", json={"is_active": False}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert response.json()["title"] == JOB_PAYLOAD["title"]


def test_delete_job(client, auth_headers):
    created = client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers).json()
    response = client.delete(f"/jobs/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get(f"/jobs/{created['id']}", headers=auth_headers)
    assert response.status_code == 404


def test_create_job_missing_fields(client, auth_headers):
    response = client.post("/jobs", json={"title": "Только заголовок"}, headers=auth_headers)
    assert response.status_code == 422
