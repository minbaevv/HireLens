"""Adaptive interview flow tests (batch #4)."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.ai.prompts import INTERVIEW_SYSTEM_PROMPT
from app.core.config import settings


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
        data={"name": "Test", "email": "adaptive_iv@example.com", "resume_text": "5 years Python"},
    )
    assert apply_resp.status_code == 201
    return job["id"], apply_resp.json()["id"]


MOCK_Q = "Tell me more about your experience?"
MOCK_COMPLETE = "Thanks for the chat! [INTERVIEW_COMPLETE]"
MOCK_SCORING_JSON = '''{
  "technical_skills": {"score": 80, "reasoning": "ok", "confidence": 0.8},
  "soft_skills": {"score": 70, "reasoning": "ok", "confidence": 0.7},
  "experience": {"score": 75, "reasoning": "ok", "confidence": 0.8},
  "motivation": {"score": 72, "reasoning": "ok", "confidence": 0.6},
  "overall_score": 75,
  "recommendation": "maybe",
  "summary": "Decent candidate",
  "red_flags": [],
  "bias_detected": false
}'''


def test_interview_prompt_is_adaptive():
    p = INTERVIEW_SYSTEM_PROMPT
    assert "{min_questions}" in p and "{max_questions}" in p
    assert "ADAPTIVE" in p
    assert "DEEPER" in p or "HARDER" in p
    assert "follow-up" in p
    assert "UNCOVERED" in p


def test_interview_prompt_renders_bounds():
    out = INTERVIEW_SYSTEM_PROMPT.format(
        data_handling_rule="DH",
        job_title="QA",
        job_requirements="Python",
        resume_text="RES",
        interview_language="Russian",
        min_questions=settings.INTERVIEW_MIN_QUESTIONS,
        max_questions=settings.INTERVIEW_MAX_QUESTIONS,
    )
    assert str(settings.INTERVIEW_MIN_QUESTIONS) in out
    assert str(settings.INTERVIEW_MAX_QUESTIONS) in out
    assert "{" not in out and "}" not in out


def test_adaptive_settings_sane():
    assert settings.INTERVIEW_MIN_QUESTIONS >= 1
    assert settings.INTERVIEW_MAX_QUESTIONS >= settings.INTERVIEW_MIN_QUESTIONS


@patch("app.ai.interview_service._call_groq", return_value=MOCK_Q)
def test_ceiling_forces_completion(mock_groq, client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr(settings, "INTERVIEW_MAX_QUESTIONS", 3)
    monkeypatch.setattr(settings, "INTERVIEW_MIN_QUESTIONS", 1)

    _, candidate_id = _create_job_and_candidate(client, auth_headers)
    start = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    assert start.status_code == 201
    interview_id = start.json()["interview_id"]
    token = start.json()["access_token"]
    hdr = {**auth_headers, "X-Interview-Token": token}

    for _ in range(2):
        r = client.post(
            f"/interviews/{interview_id}/message", json={"content": "answer"}, headers=hdr
        )
        assert r.status_code == 200
        assert r.json()["is_complete"] is False

    r = client.post(f"/interviews/{interview_id}/message", json={"content": "answer"}, headers=hdr)
    assert r.status_code == 200
    data = r.json()
    assert data["is_complete"] is True
    assert "[INTERVIEW_COMPLETE]" not in data["message"]


@patch("app.ai.interview_service._call_groq")
def test_marker_completion_still_works(mock_groq, client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr(settings, "INTERVIEW_MAX_QUESTIONS", 8)
    monkeypatch.setattr(settings, "SCORING_MIN_AI_QUESTIONS", 0)

    _, candidate_id = _create_job_and_candidate(client, auth_headers)
    with patch("app.ai.interview_service._call_groq", return_value=MOCK_Q):
        start = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    interview_id = start.json()["interview_id"]
    token = start.json()["access_token"]
    hdr = {**auth_headers, "X-Interview-Token": token}

    mock_groq.side_effect = [MOCK_COMPLETE, MOCK_SCORING_JSON]
    r = client.post(f"/interviews/{interview_id}/message", json={"content": "answer"}, headers=hdr)
    assert r.status_code == 200
    data = r.json()
    assert data["is_complete"] is True
    assert "[INTERVIEW_COMPLETE]" not in data["message"]
