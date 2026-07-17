"""Тесты AI Interview Engine (с mock Groq API)."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


@pytest.fixture
def no_scoring_penalties(monkeypatch):
    """Отключает штрафы confidence (короткое интервью / нет резюме),
    чтобы проверять чистую формулу скоринга."""
    monkeypatch.setattr(settings, "SCORING_MIN_AI_QUESTIONS", 0)
    monkeypatch.setattr(settings, "SCORING_NO_RESUME_PENALTY", 1.0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_job_and_candidate(client: TestClient, auth_headers: dict) -> tuple[int, int, str]:
    """Returns (job_id, candidate_id, apply_token)."""
    job_resp = client.post(
        "/jobs",
        json={"title": "QA Engineer", "description": "Testing", "requirements": "Python, pytest"},
        headers=auth_headers,
    )
    assert job_resp.status_code == 201
    job = job_resp.json()

    apply_resp = client.post(
        f"/apply/{job['apply_token']}",
        data={"name": "Тест Кандидат", "email": "test_iv@example.com", "resume_text": "3 года QA"},
    )
    assert apply_resp.status_code == 201
    candidate_id = apply_resp.json()["id"]
    return job["id"], candidate_id, job["apply_token"]


MOCK_FIRST_QUESTION = "Здравствуйте! Расскажите о себе."
MOCK_NEXT_QUESTION = "Какой у вас опыт в Python?"
MOCK_FINAL_ANSWER = "Спасибо! [INTERVIEW_COMPLETE]"
MOCK_SCORING_JSON = '''{
  "technical_skills": {"score": 85, "reasoning": "Хорошее знание Python и pytest", "confidence": 0.8},
  "soft_skills": {"score": 70, "reasoning": "Коммуникация на среднем уровне", "confidence": 0.7},
  "experience": {"score": 80, "reasoning": "3 года QA опыта", "confidence": 0.85},
  "motivation": {"score": 75, "reasoning": "Заинтересован в позиции", "confidence": 0.6},
  "overall_score": 78,
  "recommendation": "hire",
  "summary": "Хороший кандидат с опытом",
  "red_flags": [],
  "bias_detected": false
}'''


# ---------------------------------------------------------------------------
# Тесты
# ---------------------------------------------------------------------------

@patch("app.ai.interview_service._call_groq", return_value=MOCK_FIRST_QUESTION)
def test_start_interview(mock_groq, client: TestClient, auth_headers: dict):
    """Запуск интервью — получаем первый вопрос."""
    _, candidate_id, _ = create_job_and_candidate(client, auth_headers)

    resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["message"] == MOCK_FIRST_QUESTION
    assert data["is_complete"] is False
    assert "interview_id" in data


@patch("app.ai.interview_service._call_groq", return_value=MOCK_FIRST_QUESTION)
def test_start_interview_candidate_not_found(mock_groq, client: TestClient, auth_headers: dict):
    """Несуществующий кандидат → 404."""
    resp = client.post("/interviews/99999/start", headers=auth_headers)
    assert resp.status_code == 404


@patch("app.ai.interview_service._call_groq", return_value=MOCK_NEXT_QUESTION)
def test_send_message(mock_groq, client: TestClient, auth_headers: dict):
    """Отправка ответа — получаем следующий вопрос."""
    _, candidate_id, _ = create_job_and_candidate(client, auth_headers)

    with patch("app.ai.interview_service._call_groq", return_value=MOCK_FIRST_QUESTION):
        start_resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    interview_id = start_resp.json()["interview_id"]
    iv_token = start_resp.json()["access_token"]  # SEC-1

    resp = client.post(
        f"/interviews/{interview_id}/message",
        json={"content": "Меня зовут Алекс"},
        headers={**auth_headers, "X-Interview-Token": iv_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == MOCK_NEXT_QUESTION
    assert data["is_complete"] is False


@patch("app.ai.interview_service._call_groq")
def test_interview_completes_with_scoring(mock_groq, client: TestClient, auth_headers: dict):
    """При [INTERVIEW_COMPLETE] — запускается скоринг."""
    _, candidate_id, _ = create_job_and_candidate(client, auth_headers)

    mock_groq.return_value = MOCK_FIRST_QUESTION
    start_resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    interview_id = start_resp.json()["interview_id"]
    iv_token = start_resp.json()["access_token"]  # SEC-1

    mock_groq.side_effect = [MOCK_FINAL_ANSWER, MOCK_SCORING_JSON]
    resp = client.post(
        f"/interviews/{interview_id}/message",
        json={"content": "У меня 5 лет опыта"},
        headers={**auth_headers, "X-Interview-Token": iv_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_complete"] is True
    assert "[INTERVIEW_COMPLETE]" not in data["message"]


@patch("app.ai.interview_service._call_groq", return_value=MOCK_FIRST_QUESTION)
def test_cannot_start_interview_twice(mock_groq, client: TestClient, auth_headers: dict):
    """Нельзя запустить два интервью для одного кандидата."""
    _, candidate_id, _ = create_job_and_candidate(client, auth_headers)

    client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    assert resp.status_code == 400


@patch("app.ai.interview_service._call_groq", return_value=MOCK_FIRST_QUESTION)
def test_get_interview_history(mock_groq, client: TestClient, auth_headers: dict):
    """Получение истории сообщений интервью."""
    _, candidate_id, _ = create_job_and_candidate(client, auth_headers)

    start_resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    interview_id = start_resp.json()["interview_id"]
    iv_token = start_resp.json()["access_token"]  # SEC-1

    resp = client.get(f"/interviews/{interview_id}", headers={**auth_headers, "X-Interview-Token": iv_token})
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == interview_id
    assert len(data["messages"]) == 1
    assert data["messages"][0]["role"] == "ai"


@patch("app.ai.interview_service._call_groq", return_value=MOCK_NEXT_QUESTION)
def test_message_to_completed_interview(mock_groq, client: TestClient, auth_headers: dict):
    """Отправка сообщения в завершённое интервью → 400."""
    _, candidate_id, _ = create_job_and_candidate(client, auth_headers)

    with patch("app.ai.interview_service._call_groq", return_value=MOCK_FIRST_QUESTION):
        start_resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    interview_id = start_resp.json()["interview_id"]
    iv_token = start_resp.json()["access_token"]  # SEC-1

    with patch("app.ai.interview_service._call_groq", side_effect=[MOCK_FINAL_ANSWER, MOCK_SCORING_JSON]):
        client.post(f"/interviews/{interview_id}/message", json={"content": "Готово"}, headers={**auth_headers, "X-Interview-Token": iv_token})

    resp = client.post(f"/interviews/{interview_id}/message", json={"content": "Ещё одно"}, headers={**auth_headers, "X-Interview-Token": iv_token})
    assert resp.status_code == 400


@patch("app.ai.interview_service._call_groq", return_value=MOCK_FIRST_QUESTION)
def test_get_interview_not_found(mock_groq, client: TestClient, auth_headers: dict):
    """Несуществующее интервью → 404."""
    resp = client.get("/interviews/99999", headers=auth_headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# C5: Structured Scoring & Bias Detection Tests
# ---------------------------------------------------------------------------

@patch("app.ai.interview_service._call_groq")
def test_structured_scoring_all_components(mock_groq, client: TestClient, auth_headers: dict, no_scoring_penalties):
    """C5.1: После скоринга сохраняются все 4 компонента + confidence + reasoning."""
    _, candidate_id, _ = create_job_and_candidate(client, auth_headers)

    mock_groq.return_value = MOCK_FIRST_QUESTION
    start_resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    interview_id = start_resp.json()["interview_id"]
    iv_token = start_resp.json()["access_token"]  # SEC-1

    mock_groq.side_effect = [MOCK_FINAL_ANSWER, MOCK_SCORING_JSON]
    client.post(
        f"/interviews/{interview_id}/message",
        json={"content": "У меня 3 года опыта в QA"},
        headers={**auth_headers, "X-Interview-Token": iv_token},
    )

    # Проверяем что кандидат получил детализированный скоринг
    cand_resp = client.get(f"/candidates/{candidate_id}", headers=auth_headers)
    assert cand_resp.status_code == 200
    candidate = cand_resp.json()

    assert candidate["score"] == 78  # overall_score
    assert candidate["technical_score"] == 85
    assert candidate["soft_skills_score"] == 70
    assert candidate["experience_score"] == 80
    assert candidate["motivation_score"] == 75
    assert candidate["confidence"] == 0.7375  # (0.8 + 0.7 + 0.85 + 0.6) / 4
    assert candidate["recommendation"] == "hire"
    assert candidate["summary"] == "Хороший кандидат с опытом"

    # Проверяем что reasoning сохранён как JSON
    import json
    reasoning = json.loads(candidate["scoring_reasoning"])
    assert "technical_skills" in reasoning
    assert reasoning["technical_skills"] == "Хорошее знание Python и pytest"
    assert reasoning["soft_skills"] == "Коммуникация на среднем уровне"
    assert reasoning["experience"] == "3 года QA опыта"
    assert reasoning["motivation"] == "Заинтересован в позиции"


@patch("app.services.email.notify_interview_result")
@patch("app.services.telegram.notify_interview_complete")
@patch("app.ai.interview_service._call_groq")
def test_scoring_notifications_receive_overall_score(
    mock_groq, mock_tg, mock_email, client: TestClient, auth_headers: dict
):
    """Регресс: HR-уведомления должны получать overall_score (78), а не 0.

    Раньше _run_scoring читал result.get("score") — несуществующий ключ,
    поэтому Telegram/email всегда уходили со score=0.
    """
    _, candidate_id, _ = create_job_and_candidate(client, auth_headers)

    mock_groq.return_value = MOCK_FIRST_QUESTION
    start_resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    interview_id = start_resp.json()["interview_id"]
    iv_token = start_resp.json()["access_token"]  # SEC-1

    mock_groq.side_effect = [MOCK_FINAL_ANSWER, MOCK_SCORING_JSON]
    client.post(
        f"/interviews/{interview_id}/message",
        json={"content": "У меня 3 года опыта в QA"},
        headers={**auth_headers, "X-Interview-Token": iv_token},
    )

    assert mock_tg.called, "Telegram-уведомление HR не вызвано"
    assert mock_tg.call_args.kwargs["score"] == 78.0

    assert mock_email.called, "Email-уведомление HR не вызвано"
    assert mock_email.call_args.kwargs["score"] == 78.0


@patch("app.ai.interview_service._call_groq")
def test_bias_detection_flags(mock_groq, client: TestClient, auth_headers: dict):
    """C5.2: При bias_detected=true сохраняются bias_flags."""
    _, candidate_id, _ = create_job_and_candidate(client, auth_headers)

    mock_groq.return_value = MOCK_FIRST_QUESTION
    start_resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    interview_id = start_resp.json()["interview_id"]
    iv_token = start_resp.json()["access_token"]  # SEC-1

    mock_bias_scoring = '''{
      "technical_skills": {"score": 60, "reasoning": "Недостаточно опыта", "confidence": 0.5},
      "soft_skills": {"score": 50, "reasoning": "Слабые коммуникативные навыки", "confidence": 0.4},
      "experience": {"score": 40, "reasoning": "Молодой кандидат, мало опыта", "confidence": 0.6},
      "motivation": {"score": 70, "reasoning": "Мотивирован", "confidence": 0.7},
      "overall_score": 55,
      "recommendation": "reject",
      "summary": "Недостаточно опыта",
      "red_flags": ["Молодой возраст", "Недостаточно опыта"],
      "bias_detected": true
    }'''

    mock_groq.side_effect = [MOCK_FINAL_ANSWER, mock_bias_scoring]
    client.post(
        f"/interviews/{interview_id}/message",
        json={"content": "Мне 22 года"},
        headers={**auth_headers, "X-Interview-Token": iv_token},
    )

    cand_resp = client.get(f"/candidates/{candidate_id}", headers=auth_headers)
    candidate = cand_resp.json()

    # Проверяем bias_flags
    import json
    bias_flags = json.loads(candidate["bias_flags"])
    assert "AI detected potential bias in reasoning" in bias_flags
    assert "Молодой возраст" in bias_flags
    assert "Недостаточно опыта" in bias_flags


@patch("app.ai.interview_service._call_groq")
def test_no_bias_flags_when_clean(mock_groq, client: TestClient, auth_headers: dict, no_scoring_penalties):
    """C5.2: Если bias_detected=false и нет red_flags — bias_flags=None."""
    _, candidate_id, _ = create_job_and_candidate(client, auth_headers)

    mock_groq.return_value = MOCK_FIRST_QUESTION
    start_resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    interview_id = start_resp.json()["interview_id"]
    iv_token = start_resp.json()["access_token"]  # SEC-1

    mock_groq.side_effect = [MOCK_FINAL_ANSWER, MOCK_SCORING_JSON]
    client.post(
        f"/interviews/{interview_id}/message",
        json={"content": "Отличный опыт"},
        headers={**auth_headers, "X-Interview-Token": iv_token},
    )

    cand_resp = client.get(f"/candidates/{candidate_id}", headers=auth_headers)
    candidate = cand_resp.json()

    # bias_flags должен быть None если нет проблем
    assert candidate["bias_flags"] is None


@patch("app.ai.interview_service._call_groq")
def test_confidence_calculated_as_average(mock_groq, client: TestClient, auth_headers: dict, no_scoring_penalties):
    """C5.1: Confidence — это среднее от 4 компонентов."""
    _, candidate_id, _ = create_job_and_candidate(client, auth_headers)

    mock_groq.return_value = MOCK_FIRST_QUESTION
    start_resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    interview_id = start_resp.json()["interview_id"]
    iv_token = start_resp.json()["access_token"]  # SEC-1

    mock_custom_confidence = '''{
      "technical_skills": {"score": 90, "reasoning": "Отлично", "confidence": 1.0},
      "soft_skills": {"score": 80, "reasoning": "Хорошо", "confidence": 0.9},
      "experience": {"score": 70, "reasoning": "Нормально", "confidence": 0.5},
      "motivation": {"score": 60, "reasoning": "Средне", "confidence": 0.2},
      "overall_score": 75,
      "recommendation": "maybe",
      "summary": "Смешанные результаты",
      "red_flags": [],
      "bias_detected": false
    }'''

    mock_groq.side_effect = [MOCK_FINAL_ANSWER, mock_custom_confidence]
    client.post(
        f"/interviews/{interview_id}/message",
        json={"content": "Ответ"},
        headers={**auth_headers, "X-Interview-Token": iv_token},
    )

    cand_resp = client.get(f"/candidates/{candidate_id}", headers=auth_headers)
    candidate = cand_resp.json()

    # confidence = (1.0 + 0.9 + 0.5 + 0.2) / 4 = 2.6 / 4 = 0.65
    assert candidate["confidence"] == 0.65


# ---------------------------------------------------------------------------
# 1.3: Scoring Validation Tests
# ---------------------------------------------------------------------------

def _run_interview_with_scoring(client, auth_headers, mock_groq, scoring_payload):
    """Хелпер: доводит интервью до завершения и возвращает кандидата после скоринга."""
    _, candidate_id, _ = create_job_and_candidate(client, auth_headers)
    mock_groq.return_value = MOCK_FIRST_QUESTION
    start_resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    interview_id = start_resp.json()["interview_id"]
    iv_token = start_resp.json()["access_token"]  # SEC-1

    mock_groq.side_effect = [MOCK_FINAL_ANSWER, scoring_payload]
    client.post(
        f"/interviews/{interview_id}/message",
        json={"content": "Финальный ответ"},
        headers={**auth_headers, "X-Interview-Token": iv_token},
    )
    return client.get(f"/candidates/{candidate_id}", headers=auth_headers).json()


@patch("app.ai.interview_service._call_groq")
def test_scoring_invalid_score_flags_manual_review(mock_groq, client: TestClient, auth_headers: dict):
    """1.3: overall_score вне 0-100 → кандидат на ручную проверку, мусор не сохранён."""
    bad = '''{
      "technical_skills": {"score": 90, "reasoning": "x", "confidence": 0.9},
      "soft_skills": {"score": 80, "reasoning": "x", "confidence": 0.9},
      "experience": {"score": 70, "reasoning": "x", "confidence": 0.9},
      "motivation": {"score": 60, "reasoning": "x", "confidence": 0.9},
      "overall_score": 150,
      "recommendation": "hire",
      "summary": "Отлично"
    }'''
    candidate = _run_interview_with_scoring(client, auth_headers, mock_groq, bad)
    assert candidate["requires_manual_review"] is True
    assert candidate["score"] != 150  # невалидный score не сохранён


@patch("app.ai.interview_service._call_groq")
def test_scoring_empty_summary_flags_manual_review(mock_groq, client: TestClient, auth_headers: dict):
    """1.3: пустой summary → ручная проверка."""
    bad = '''{
      "technical_skills": {"score": 90, "reasoning": "x", "confidence": 0.9},
      "soft_skills": {"score": 80, "reasoning": "x", "confidence": 0.9},
      "experience": {"score": 70, "reasoning": "x", "confidence": 0.9},
      "motivation": {"score": 60, "reasoning": "x", "confidence": 0.9},
      "overall_score": 75,
      "recommendation": "hire",
      "summary": "   "
    }'''
    candidate = _run_interview_with_scoring(client, auth_headers, mock_groq, bad)
    assert candidate["requires_manual_review"] is True


@patch("app.ai.interview_service._call_groq")
def test_scoring_unparseable_json_flags_manual_review(mock_groq, client: TestClient, auth_headers: dict):
    """1.3: невалидный JSON от LLM → не крашится, кандидат на ручную проверку."""
    candidate = _run_interview_with_scoring(client, auth_headers, mock_groq, "не JSON вовсе")
    assert candidate["requires_manual_review"] is True
    assert candidate["status"] == "completed"


@patch("app.ai.interview_service._call_groq")
def test_scoring_invalid_recommendation_flags_manual_review(mock_groq, client: TestClient, auth_headers: dict):
    """1.3: recommendation не из hire/maybe/reject → ручная проверка."""
    bad = '''{
      "technical_skills": {"score": 90, "reasoning": "x", "confidence": 0.9},
      "soft_skills": {"score": 80, "reasoning": "x", "confidence": 0.9},
      "experience": {"score": 70, "reasoning": "x", "confidence": 0.9},
      "motivation": {"score": 60, "reasoning": "x", "confidence": 0.9},
      "overall_score": 75,
      "recommendation": "definitely_hire",
      "summary": "Хороший кандидат"
    }'''
    candidate = _run_interview_with_scoring(client, auth_headers, mock_groq, bad)
    assert candidate["requires_manual_review"] is True


# ---------------------------------------------------------------------------
# Штрафы confidence (Roadmap P1)
# ---------------------------------------------------------------------------

@patch("app.ai.interview_service._call_groq")
def test_short_interview_caps_confidence(mock_groq, client: TestClient, auth_headers: dict):
    """P1: интервью короче SCORING_MIN_AI_QUESTIONS → confidence ограничен 0.3 + флаг."""
    _, candidate_id, _ = create_job_and_candidate(client, auth_headers)

    mock_groq.return_value = MOCK_FIRST_QUESTION
    start_resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    interview_id = start_resp.json()["interview_id"]
    iv_token = start_resp.json()["access_token"]  # SEC-1

    mock_groq.side_effect = [MOCK_FINAL_ANSWER, MOCK_SCORING_JSON]
    client.post(
        f"/interviews/{interview_id}/message",
        json={"content": "Короткий ответ"},
        headers={**auth_headers, "X-Interview-Token": iv_token},
    )

    candidate = client.get(f"/candidates/{candidate_id}", headers=auth_headers).json()
    # Всего 2 вопроса AI (< 4 по умолчанию) → cap 0.3 вместо 0.7375
    assert candidate["confidence"] <= 0.3
    assert candidate["bias_flags"] is not None
    assert "Interview too short" in candidate["bias_flags"]


# ---------------------------------------------------------------------------
# SEC-1: защита от IDOR по access_token
# ---------------------------------------------------------------------------

@patch("app.ai.interview_service._call_groq", return_value=MOCK_FIRST_QUESTION)
def test_interview_requires_access_token(mock_groq, client: TestClient, auth_headers: dict):
    """SEC-1: без X-Interview-Token или с неверным токеном → 403."""
    _, candidate_id, _ = create_job_and_candidate(client, auth_headers)

    start_resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    interview_id = start_resp.json()["interview_id"]
    token = start_resp.json()["access_token"]
    assert len(token) >= 32

    # Без токена — 403 (IDOR по последовательному id больше не работает)
    resp = client.post(f"/interviews/{interview_id}/message", json={"content": "x"})
    assert resp.status_code == 403
    resp = client.get(f"/interviews/{interview_id}")
    assert resp.status_code == 403

    # С неверным токеном — 403
    resp = client.get(
        f"/interviews/{interview_id}", headers={"X-Interview-Token": "wrong-token"}
    )
    assert resp.status_code == 403

    # С верным токеном — 200
    resp = client.get(f"/interviews/{interview_id}", headers={"X-Interview-Token": token})
    assert resp.status_code == 200
