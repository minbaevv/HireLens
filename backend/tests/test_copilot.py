"""Тесты AI-copilot для HR (C4) — с mock LLM."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.ai.prompts import COPILOT_REFS_MARKER


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_candidate(client: TestClient, auth_headers: dict, name: str, email: str) -> int:
    """Создаёт вакансию + кандидата, возвращает candidate_id."""
    job = client.post(
        "/jobs",
        json={"title": "Backend Dev", "description": "FastAPI", "requirements": "Python, FastAPI"},
        headers=auth_headers,
    ).json()
    resp = client.post(
        f"/apply/{job['apply_token']}",
        data={"name": name, "email": email, "resume_text": "5 лет Python, FastAPI, PostgreSQL"},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def second_company_headers(client: TestClient) -> dict:
    """Регистрирует и логинит вторую компанию, возвращает её заголовки."""
    client.post(
        "/auth/register",
        json={"email": "other@test.com", "password": "test1234", "company_name": "Other LLC"},
    )
    from tests.conftest import mark_verified
    mark_verified("other@test.com")
    token = client.post(
        "/auth/login", data={"username": "other@test.com", "password": "test1234"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Тесты
# ---------------------------------------------------------------------------

def test_copilot_requires_auth(client: TestClient):
    """Без токена → 401."""
    resp = client.post("/copilot/chat", json={"message": "топ кандидатов"})
    assert resp.status_code == 401


def test_copilot_empty_db(client: TestClient, auth_headers: dict):
    """Пустая база — дружелюбный ответ без вызова LLM."""
    with patch("app.ai.copilot_service._call_copilot_llm") as mock_llm:
        resp = client.post("/copilot/chat", json={"message": "кто лучший?"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["candidates_analyzed"] == 0
    assert data["referenced_candidates"] == []
    assert data["answer"]  # непустой текст
    mock_llm.assert_not_called()


def test_copilot_answers_from_candidates(client: TestClient, auth_headers: dict):
    """Нормальный ответ: LLM вызван, текст возвращён, кандидаты проанализированы."""
    cid = create_candidate(client, auth_headers, "Иван Петров", "ivan@test.com")

    mock_answer = f"Лучший кандидат — Иван Петров.\n{COPILOT_REFS_MARKER}{cid}"
    with patch("app.ai.copilot_service._call_copilot_llm", return_value=mock_answer) as mock_llm:
        resp = client.post(
            "/copilot/chat", json={"message": "кто лучший на бэкенд?"}, headers=auth_headers
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["candidates_analyzed"] == 1
    assert "Иван Петров" in data["answer"]
    # Маркер не должен попасть в текст ответа
    assert COPILOT_REFS_MARKER not in data["answer"]
    mock_llm.assert_called_once()


def test_copilot_parses_referenced_candidates(client: TestClient, auth_headers: dict):
    """Referenced ids из маркера превращаются в кликабельные чипы с именами."""
    from tests.conftest import grant_plan
    grant_plan("jobs@test.com")  # два кандидата = две вакансии → нужен платный тариф
    c1 = create_candidate(client, auth_headers, "Алиса", "alice@test.com")
    c2 = create_candidate(client, auth_headers, "Боб", "bob@test.com")

    mock_answer = f"Топ-2: Алиса и Боб.\n{COPILOT_REFS_MARKER}{c1},{c2}"
    with patch("app.ai.copilot_service._call_copilot_llm", return_value=mock_answer):
        resp = client.post("/copilot/chat", json={"message": "топ-2"}, headers=auth_headers)
    data = resp.json()
    refs = data["referenced_candidates"]
    assert [r["id"] for r in refs] == [c1, c2]
    assert {r["name"] for r in refs} == {"Алиса", "Боб"}


def test_copilot_ignores_hallucinated_ids(client: TestClient, auth_headers: dict):
    """Несуществующие id из ответа LLM отбрасываются."""
    cid = create_candidate(client, auth_headers, "Реальный", "real@test.com")

    mock_answer = f"Ответ.\n{COPILOT_REFS_MARKER}{cid},99999"
    with patch("app.ai.copilot_service._call_copilot_llm", return_value=mock_answer):
        resp = client.post("/copilot/chat", json={"message": "?"}, headers=auth_headers)
    refs = resp.json()["referenced_candidates"]
    assert [r["id"] for r in refs] == [cid]


def test_copilot_company_isolation(client: TestClient, auth_headers: dict):
    """Copilot видит только кандидатов своей компании: чужие не попадают в контекст LLM."""
    # Кандидат первой компании
    create_candidate(client, auth_headers, "Свой", "mine@test.com")

    other_headers = second_company_headers(client)

    captured = {}

    def _capture(messages, system, temperature=0.3):
        captured["system"] = system
        return "Ответ."

    # Вторая компания спрашивает — в её контексте не должно быть "Свой"
    with patch("app.ai.copilot_service._call_copilot_llm", side_effect=_capture):
        resp = client.post("/copilot/chat", json={"message": "кто есть?"}, headers=other_headers)
    assert resp.status_code == 200
    # У второй компании нет кандидатов → LLM даже не вызывается
    assert resp.json()["candidates_analyzed"] == 0
    assert "system" not in captured


def test_copilot_other_company_candidate_not_in_context(client: TestClient, auth_headers: dict):
    """Если у обеих компаний есть кандидаты — контекст строго свой."""
    create_candidate(client, auth_headers, "Компания1 Кандидат", "c1@test.com")

    other_headers = second_company_headers(client)
    create_candidate(client, other_headers, "Компания2 Кандидат", "c2@test.com")

    captured = {}

    def _capture(messages, system, temperature=0.3):
        captured["system"] = system
        return "Ответ."

    with patch("app.ai.copilot_service._call_copilot_llm", side_effect=_capture):
        client.post("/copilot/chat", json={"message": "кто есть?"}, headers=other_headers)

    assert "Компания2 Кандидат" in captured["system"]
    assert "Компания1 Кандидат" not in captured["system"]


def test_copilot_no_refs_marker(client: TestClient, auth_headers: dict):
    """Ответ без маркера — просто текст, пустой список referenced."""
    create_candidate(client, auth_headers, "Кандидат", "c@test.com")

    with patch("app.ai.copilot_service._call_copilot_llm", return_value="Просто ответ без маркера."):
        resp = client.post("/copilot/chat", json={"message": "?"}, headers=auth_headers)
    data = resp.json()
    assert data["answer"] == "Просто ответ без маркера."
    assert data["referenced_candidates"] == []
