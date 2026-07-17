"""Answer Attribution tests (batch #5, Priority 2.2)."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.ai.prompts import SCORING_SYSTEM_PROMPT, SCORING_JSON_SCHEMA


def _create_job_and_candidate(client: TestClient, auth_headers: dict):
    job_resp = client.post(
        "/jobs",
        json={"title": "Backend Engineer", "description": "API", "requirements": "Python, SQL"},
        headers=auth_headers,
    )
    assert job_resp.status_code == 201
    job = job_resp.json()
    apply_resp = client.post(
        f"/apply/{job['apply_token']}",
        data={"name": "Attr", "email": "attr_iv@example.com", "resume_text": "5 years Python and SQL"},
    )
    assert apply_resp.status_code == 201
    return job["id"], apply_resp.json()["id"]


MOCK_Q = "Tell me about your SQL experience?"
MOCK_COMPLETE = "Thanks! [INTERVIEW_COMPLETE]"
MOCK_SCORING = '''{
  "technical_skills": {"score": 80, "reasoning": "Q1: precise SQL JOIN example", "confidence": 0.9},
  "soft_skills": {"score": 70, "reasoning": "Q2 ok", "confidence": 0.8},
  "experience": {"score": 75, "reasoning": "ok", "confidence": 0.8},
  "motivation": {"score": 72, "reasoning": "ok", "confidence": 0.7},
  "overall_score": 76,
  "recommendation": "maybe",
  "summary": "Solid backend candidate",
  "discrepancies": [],
  "evasive_answers": [],
  "attribution": {"technical_skills": [1, 99], "soft_skills": [2], "experience": [], "motivation": [1]},
  "red_flags": [],
  "bias_detected": false
}'''


def test_scoring_prompt_and_schema_have_attribution():
    assert "ATTRIBUTION" in SCORING_SYSTEM_PROMPT
    assert "[Q1]" in SCORING_SYSTEM_PROMPT
    assert "attribution" in SCORING_JSON_SCHEMA


@patch("app.ai.interview_service._call_groq")
def test_scoring_details_resolves_attribution(mock_groq, client: TestClient, auth_headers: dict, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "SCORING_MIN_AI_QUESTIONS", 0)

    _, candidate_id = _create_job_and_candidate(client, auth_headers)

    mock_groq.return_value = MOCK_Q
    start = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    assert start.status_code == 201
    interview_id = start.json()["interview_id"]
    iv_token = start.json()["access_token"]

    mock_groq.side_effect = [MOCK_COMPLETE, MOCK_SCORING]
    msg = client.post(
        f"/interviews/{interview_id}/message",
        json={"content": "I used SQL joins daily"},
        headers={**auth_headers, "X-Interview-Token": iv_token},
    )
    assert msg.status_code == 200
    assert msg.json()["is_complete"] is True

    resp = client.get(f"/candidates/{candidate_id}/scoring-details", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert len(data["questions"]) >= 1
    attr = data["attribution"]
    tech = attr["technical_skills"]
    assert len(tech) == 1
    assert tech[0]["n"] == 1
    assert tech[0]["message_id"] is not None
    assert isinstance(tech[0]["question"], str) and tech[0]["question"]

    all_ns = [ref["n"] for lst in attr.values() for ref in lst]
    assert 99 not in all_ns
    assert all(n in (1, 2) for n in all_ns)
