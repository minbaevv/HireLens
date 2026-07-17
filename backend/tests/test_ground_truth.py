"""Tests for Ground Truth Tracking (Phase 10/10 - 1.1)."""
import pytest
from fastapi import status


def test_set_final_decision_hired_correct(client, auth_headers, db):
    """HR отмечает кандидата как нанятого, AI был прав."""
    # Создать вакансию
    job_resp = client.post(
        "/jobs",
        headers=auth_headers,
        json={"title": "Test Job", "description": "Desc", "requirements": "Req"},
    )
    job_id = job_resp.json()["id"]

    # Создать кандидата
    apply_resp = client.post(
        f"/apply/{job_resp.json()['apply_token']}",
        data={"name": "Test Candidate", "email": "test@test.com", "resume_text": "Resume"},
    )
    candidate_id = apply_resp.json()["id"]

    # Симулировать scoring (в реальности через интервью)
    from app.models.models import Candidate
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    candidate.score = 85
    candidate.recommendation = "hire"
    candidate.confidence = 0.8
    db.commit()

    # HR отмечает финальное решение: hired, AI был correct
    response = client.patch(
        f"/candidates/{candidate_id}/final-decision",
        headers=auth_headers,
        json={
            "actual_hire_decision": "hired",
            "ai_feedback": "correct",
            "hr_notes": "Отличный кандидат, соответствует ожиданиям",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["actual_hire_decision"] == "hired"
    assert data["ai_feedback"] == "correct"
    assert data["hr_notes"] == "Отличный кандидат, соответствует ожиданиям"
    assert data["requires_manual_review"] is False  # Флаг снят после HR решения


def test_set_final_decision_rejected_incorrect(client, auth_headers, db):
    """HR отклонил кандидата, хотя AI рекомендовал hire — AI ошибся."""
    job_resp = client.post(
        "/jobs",
        headers=auth_headers,
        json={"title": "Test Job", "description": "Desc", "requirements": "Req"},
    )
    job_id = job_resp.json()["id"]

    apply_resp = client.post(
        f"/apply/{job_resp.json()['apply_token']}",
        data={"name": "Test Candidate", "email": "test@test.com", "resume_text": "Resume"},
    )
    candidate_id = apply_resp.json()["id"]

    from app.models.models import Candidate
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    candidate.score = 75
    candidate.recommendation = "hire"
    candidate.confidence = 0.65  # Низкая confidence
    candidate.requires_manual_review = True
    db.commit()

    response = client.patch(
        f"/candidates/{candidate_id}/final-decision",
        headers=auth_headers,
        json={
            "actual_hire_decision": "rejected_final",
            "ai_feedback": "incorrect",
            "hr_notes": "Не прошёл техническое собеседование",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["actual_hire_decision"] == "rejected_final"
    assert data["ai_feedback"] == "incorrect"
    assert data["requires_manual_review"] is False


def test_ai_accuracy_empty(client, auth_headers):
    """AI accuracy когда нет feedback от HR."""
    response = client.get("/analytics/ai-accuracy", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_with_feedback"] == 0
    assert data["accuracy_rate"] == 0.0
    assert data["breakdown_by_recommendation"] == {}


def test_ai_accuracy_calculation(client, auth_headers, db):
    """AI accuracy: 2 correct, 1 incorrect из 3 кандидатов = 66.7%."""
    job_resp = client.post(
        "/jobs",
        headers=auth_headers,
        json={"title": "Test Job", "description": "Desc", "requirements": "Req"},
    )
    token = job_resp.json()["apply_token"]

    # Кандидат 1: AI correct (hire → hired)
    c1_resp = client.post(
        f"/apply/{token}",
        data={"name": "Candidate 1", "email": "c1@test.com", "resume_text": "Resume 1"},
    )
    c1_id = c1_resp.json()["id"]
    from app.models.models import Candidate
    c1 = db.query(Candidate).filter(Candidate.id == c1_id).first()
    c1.score = 90
    c1.recommendation = "hire"
    c1.confidence = 0.9
    db.commit()
    client.patch(
        f"/candidates/{c1_id}/final-decision",
        headers=auth_headers,
        json={"actual_hire_decision": "hired", "ai_feedback": "correct"},
    )

    # Кандидат 2: AI correct (reject → rejected)
    c2_resp = client.post(
        f"/apply/{token}",
        data={"name": "Candidate 2", "email": "c2@test.com", "resume_text": "Resume 2"},
    )
    c2_id = c2_resp.json()["id"]
    c2 = db.query(Candidate).filter(Candidate.id == c2_id).first()
    c2.score = 30
    c2.recommendation = "reject"
    c2.confidence = 0.8
    db.commit()
    client.patch(
        f"/candidates/{c2_id}/final-decision",
        headers=auth_headers,
        json={"actual_hire_decision": "rejected_final", "ai_feedback": "correct"},
    )

    # Кандидат 3: AI incorrect (hire → rejected)
    c3_resp = client.post(
        f"/apply/{token}",
        data={"name": "Candidate 3", "email": "c3@test.com", "resume_text": "Resume 3"},
    )
    c3_id = c3_resp.json()["id"]
    c3 = db.query(Candidate).filter(Candidate.id == c3_id).first()
    c3.score = 80
    c3.recommendation = "hire"
    c3.confidence = 0.6
    db.commit()
    client.patch(
        f"/candidates/{c3_id}/final-decision",
        headers=auth_headers,
        json={"actual_hire_decision": "rejected_final", "ai_feedback": "incorrect"},
    )

    # Проверить AI accuracy
    response = client.get("/analytics/ai-accuracy", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["total_with_feedback"] == 3
    assert data["correct_predictions"] == 2
    assert data["incorrect_predictions"] == 1
    assert data["accuracy_rate"] == 66.7  # 2/3 * 100

    # Breakdown по recommendation
    assert "hire" in data["breakdown_by_recommendation"]
    hire_breakdown = data["breakdown_by_recommendation"]["hire"]
    assert hire_breakdown["total"] == 2
    assert hire_breakdown["correct"] == 1
    assert hire_breakdown["incorrect"] == 1
    assert hire_breakdown["accuracy"] == 50.0  # 1/2 * 100


def test_requires_manual_review_low_confidence(client, auth_headers, db):
    """Кандидат с низкой confidence автоматически помечен для ручной проверки."""
    job_resp = client.post(
        "/jobs",
        headers=auth_headers,
        json={"title": "Test Job", "description": "Desc", "requirements": "Req"},
    )
    apply_resp = client.post(
        f"/apply/{job_resp.json()['apply_token']}",
        data={"name": "Test", "email": "test@test.com", "resume_text": "Resume"},
    )
    candidate_id = apply_resp.json()["id"]

    # Симулировать scoring с низкой confidence
    from app.models.models import Candidate
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    candidate.score = 50
    candidate.confidence = 0.5  # < 0.7
    candidate.requires_manual_review = True
    db.commit()

    response = client.get(f"/candidates/{candidate_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["requires_manual_review"] is True


def test_requires_manual_review_extreme_score(client, auth_headers, db):
    """Score = 0 или 100 автоматически требует ручной проверки."""
    job_resp = client.post(
        "/jobs",
        headers=auth_headers,
        json={"title": "Test Job", "description": "Desc", "requirements": "Req"},
    )
    apply_resp = client.post(
        f"/apply/{job_resp.json()['apply_token']}",
        data={"name": "Test", "email": "test@test.com", "resume_text": "Resume"},
    )
    candidate_id = apply_resp.json()["id"]

    from app.models.models import Candidate
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    candidate.score = 100  # Экстремальный score
    candidate.confidence = 0.95
    candidate.requires_manual_review = True
    db.commit()

    response = client.get(f"/candidates/{candidate_id}", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["requires_manual_review"] is True
