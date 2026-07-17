"""Тесты Kanban доски кандидатов."""
import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_job(client, auth_headers):
    resp = client.post(
        "/jobs",
        json={"title": "Dev", "description": "Backend", "requirements": "Python"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


def apply_candidate(client, token, name, email):
    resp = client.post(
        f"/apply/{token}",
        data={"name": name, "email": email, "resume_text": f"Опыт {name}"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# GET /candidates/kanban
# ---------------------------------------------------------------------------

def test_kanban_board_empty(client: TestClient, auth_headers: dict):
    """Пустая доска — 5 колонок, все пустые."""
    resp = client.get("/candidates/kanban", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert len(data["columns"]) == 5
    statuses = [col["status"] for col in data["columns"]]
    assert statuses == ["applied", "interviewing", "completed", "hired", "rejected"]


def test_kanban_board_with_candidates(client: TestClient, auth_headers: dict):
    """Кандидаты попадают в правильные колонки."""
    job = create_job(client, auth_headers)
    token = job["apply_token"]

    c1 = apply_candidate(client, token, "Алекс", "alex@k.com")
    c2 = apply_candidate(client, token, "Борис", "boris@k.com")

    # Перемещаем c2 в rejected
    client.patch(f"/candidates/{c2}/stage", json={"stage": "interviewing"}, headers=auth_headers)
    client.patch(f"/candidates/{c2}/stage", json={"stage": "rejected"}, headers=auth_headers)

    resp = client.get("/candidates/kanban", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2

    cols = {col["status"]: col for col in data["columns"]}
    assert cols["applied"]["count"] == 1
    assert cols["rejected"]["count"] == 1
    assert cols["applied"]["candidates"][0]["name"] == "Алекс"


def test_kanban_board_filter_by_job(client: TestClient, auth_headers: dict):
    """Фильтр по job_id работает."""
    from tests.conftest import grant_plan
    grant_plan("jobs@test.com")  # 2 вакансии → нужен платный тариф (free = 1)
    job1 = create_job(client, auth_headers)
    job2 = create_job(client, auth_headers)

    apply_candidate(client, job1["apply_token"], "Иван", "ivan@k.com")
    apply_candidate(client, job2["apply_token"], "Мария", "maria@k.com")

    resp = client.get(f"/candidates/kanban?job_id={job1['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_kanban_board_invalid_job(client: TestClient, auth_headers: dict):
    """Несуществующая вакансия → 404."""
    resp = client.get("/candidates/kanban?job_id=99999", headers=auth_headers)
    assert resp.status_code == 404


def test_kanban_requires_auth(client: TestClient):
    """Без токена → 401."""
    resp = client.get("/candidates/kanban")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /candidates/{id}/stage
# ---------------------------------------------------------------------------

def test_stage_move_applied_to_interviewing(client: TestClient, auth_headers: dict):
    """Переход applied → interviewing — допустим."""
    job = create_job(client, auth_headers)
    c_id = apply_candidate(client, job["apply_token"], "Тест", "t1@k.com")

    resp = client.patch(f"/candidates/{c_id}/stage", json={"stage": "interviewing"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "interviewing"


def test_stage_move_applied_to_rejected(client: TestClient, auth_headers: dict):
    """Переход applied → rejected — допустим."""
    job = create_job(client, auth_headers)
    c_id = apply_candidate(client, job["apply_token"], "Тест2", "t2@k.com")

    resp = client.patch(f"/candidates/{c_id}/stage", json={"stage": "rejected"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_stage_move_invalid_transition(client: TestClient, auth_headers: dict):
    """Недопустимый переход applied → hired → 422."""
    job = create_job(client, auth_headers)
    c_id = apply_candidate(client, job["apply_token"], "Тест3", "t3@k.com")

    resp = client.patch(f"/candidates/{c_id}/stage", json={"stage": "hired"}, headers=auth_headers)
    assert resp.status_code == 422
    assert "Недопустимый" in resp.json()["detail"]


def test_stage_move_same_status(client: TestClient, auth_headers: dict):
    """Переход в тот же статус — 200, ничего не меняется."""
    job = create_job(client, auth_headers)
    c_id = apply_candidate(client, job["apply_token"], "Тест4", "t4@k.com")

    resp = client.patch(f"/candidates/{c_id}/stage", json={"stage": "applied"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"


def test_stage_move_not_found(client: TestClient, auth_headers: dict):
    """Несуществующий кандидат → 404."""
    resp = client.patch("/candidates/99999/stage", json={"stage": "interviewing"}, headers=auth_headers)
    assert resp.status_code == 404


def test_stage_full_flow(client: TestClient, auth_headers: dict):
    """Полный цикл: applied → interviewing → completed → hired."""
    job = create_job(client, auth_headers)
    c_id = apply_candidate(client, job["apply_token"], "Топ", "top@k.com")

    for stage in ["interviewing", "completed", "hired"]:
        resp = client.patch(f"/candidates/{c_id}/stage", json={"stage": stage}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == stage


def test_stage_rejected_can_reopen(client: TestClient, auth_headers: dict):
    """Отклонённый кандидат можно вернуть в applied."""
    job = create_job(client, auth_headers)
    c_id = apply_candidate(client, job["apply_token"], "Реопен", "reopen@k.com")

    client.patch(f"/candidates/{c_id}/stage", json={"stage": "rejected"}, headers=auth_headers)
    resp = client.patch(f"/candidates/{c_id}/stage", json={"stage": "applied"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"
