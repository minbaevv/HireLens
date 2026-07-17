"""Тесты голосовых интервью (Whisper STT)."""
import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_job_and_start_interview(client: TestClient, auth_headers: dict) -> tuple[int, dict]:
    """Создаёт вакансию, кандидата, запускает интервью.

    Returns (interview_id, headers c X-Interview-Token) — SEC-1."""
    job_resp = client.post(
        "/jobs",
        json={"title": "Python Dev", "description": "Backend", "requirements": "Python 3+"},
        headers=auth_headers,
    )
    assert job_resp.status_code == 201
    job = job_resp.json()

    apply_resp = client.post(
        f"/apply/{job['apply_token']}",
        data={"name": "Голос Тест", "email": "voice@example.com", "resume_text": "2 года Python"},
    )
    assert apply_resp.status_code == 201
    candidate_id = apply_resp.json()["id"]

    with patch("app.ai.interview_service._call_groq", return_value="Здравствуйте! Расскажите о себе."):
        start_resp = client.post(f"/interviews/{candidate_id}/start", headers=auth_headers)
    assert start_resp.status_code == 201
    interview_id = start_resp.json()["interview_id"]
    iv_headers = {"X-Interview-Token": start_resp.json()["access_token"]}

    return interview_id, iv_headers


FAKE_AUDIO = b"RIFF" + b"\x00" * 100  # минимальный fake WAV
MOCK_TRANSCRIPT = "У меня три года опыта в Python и FastAPI."
MOCK_AI_RESPONSE = "Отлично! Расскажите о вашем опыте с базами данных."


# ---------------------------------------------------------------------------
# Тесты transcribe_audio (unit)
# ---------------------------------------------------------------------------

def test_transcribe_audio_too_large():
    """Файл больше 25MB → ValueError."""
    from app.ai.interview_service import transcribe_audio
    big_audio = b"x" * (26 * 1024 * 1024)  # 26MB
    with pytest.raises(ValueError, match="слишком большой"):
        transcribe_audio(big_audio, content_type="audio/wav")


def test_transcribe_audio_unsupported_format():
    """Неподдерживаемый формат → ValueError."""
    from app.ai.interview_service import transcribe_audio
    with pytest.raises(ValueError, match="Неподдерживаемый формат"):
        transcribe_audio(b"data", content_type="video/mp4")


@patch("app.ai.interview_service._get_groq_client")
def test_transcribe_audio_success(mock_client):
    """Успешная транскрипция."""
    from app.ai.interview_service import transcribe_audio

    mock_transcription = MagicMock()
    mock_transcription.text = MOCK_TRANSCRIPT
    mock_client.return_value.audio.transcriptions.create.return_value = mock_transcription

    result = transcribe_audio(FAKE_AUDIO, filename="test.wav", content_type="audio/wav")
    assert result == MOCK_TRANSCRIPT


@patch("app.ai.interview_service._get_groq_client")
def test_transcribe_audio_empty_result(mock_client):
    """Пустая транскрипция → ValueError."""
    from app.ai.interview_service import transcribe_audio

    mock_transcription = MagicMock()
    mock_transcription.text = "   "  # пустой текст
    mock_client.return_value.audio.transcriptions.create.return_value = mock_transcription

    with pytest.raises(ValueError, match="не содержит речи"):
        transcribe_audio(FAKE_AUDIO, content_type="audio/wav")


# ---------------------------------------------------------------------------
# Тесты API эндпоинта /voice
# ---------------------------------------------------------------------------

@patch("app.ai.interview_service._call_groq", return_value=MOCK_AI_RESPONSE)
@patch("app.api.interviews.transcribe_audio", return_value=MOCK_TRANSCRIPT)
def test_voice_message_success(mock_transcribe, mock_groq, client: TestClient, auth_headers: dict):
    """Голосовой ответ → транскрипция → AI ответ."""
    interview_id, iv_headers = create_job_and_start_interview(client, auth_headers)

    resp = client.post(
        f"/interviews/{interview_id}/voice",
        files={"audio": ("test.wav", io.BytesIO(FAKE_AUDIO), "audio/wav")},
        headers=iv_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == MOCK_AI_RESPONSE
    assert data["is_complete"] is False
    mock_transcribe.assert_called_once()


@patch("app.api.interviews.transcribe_audio", side_effect=ValueError("Неподдерживаемый формат: video/mp4"))
def test_voice_message_invalid_format(mock_transcribe, client: TestClient, auth_headers: dict):
    """Неверный формат аудио → 422."""
    interview_id, iv_headers = create_job_and_start_interview(client, auth_headers)

    resp = client.post(
        f"/interviews/{interview_id}/voice",
        files={"audio": ("test.mp4", io.BytesIO(b"data"), "video/mp4")},
        headers=iv_headers,
    )
    assert resp.status_code == 422


@patch("app.api.interviews.transcribe_audio", return_value=MOCK_TRANSCRIPT)
def test_voice_message_interview_not_found(mock_transcribe, client: TestClient, auth_headers: dict):
    """Несуществующее интервью → 404."""
    resp = client.post(
        "/interviews/99999/voice",
        files={"audio": ("test.wav", io.BytesIO(FAKE_AUDIO), "audio/wav")},
        headers=auth_headers,
    )
    assert resp.status_code == 404


@patch("app.api.interviews.transcribe_audio", side_effect=RuntimeError("Whisper недоступен"))
def test_voice_message_whisper_unavailable(mock_transcribe, client: TestClient, auth_headers: dict):
    """Whisper API недоступен → 503."""
    interview_id, iv_headers = create_job_and_start_interview(client, auth_headers)

    resp = client.post(
        f"/interviews/{interview_id}/voice",
        files={"audio": ("test.wav", io.BytesIO(FAKE_AUDIO), "audio/wav")},
        headers=iv_headers,
    )
    assert resp.status_code == 503


@patch("app.ai.interview_service._call_groq")
@patch("app.api.interviews.transcribe_audio", return_value=MOCK_TRANSCRIPT)
def test_voice_message_completes_interview(mock_transcribe, mock_groq, client: TestClient, auth_headers: dict):
    """Голосовой ответ может завершить интервью."""
    interview_id, iv_headers = create_job_and_start_interview(client, auth_headers)

    mock_groq.side_effect = [
        "Спасибо! [INTERVIEW_COMPLETE]",
        '{"score": 90, "summary": "Отлично", "strengths": ["Python"], "weaknesses": [], "recommendation": "hire", "reasoning": "Опытный"}',
    ]

    resp = client.post(
        f"/interviews/{interview_id}/voice",
        files={"audio": ("test.wav", io.BytesIO(FAKE_AUDIO), "audio/wav")},
        headers=iv_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_complete"] is True


# ---------------------------------------------------------------------------
# Тесты языка транскрипции Whisper по языку вакансии (A6.3)
# ---------------------------------------------------------------------------

@patch("app.ai.interview_service._get_groq_client")
def test_transcribe_audio_passes_language_for_supported_languages(mock_client):
    """Для ru/en язык передаётся в Whisper API явно."""
    from app.ai.interview_service import transcribe_audio

    mock_transcription = MagicMock()
    mock_transcription.text = MOCK_TRANSCRIPT
    mock_client.return_value.audio.transcriptions.create.return_value = mock_transcription

    transcribe_audio(FAKE_AUDIO, filename="test.wav", content_type="audio/wav", language="en")

    _, kwargs = mock_client.return_value.audio.transcriptions.create.call_args
    assert kwargs["language"] == "en"


@patch("app.ai.interview_service._get_groq_client")
def test_transcribe_audio_kyrgyz_uses_auto_detect(mock_client):
    """Для 'ky' явный код языка не передаётся (Whisper не поддерживает кыргызский)."""
    from app.ai.interview_service import transcribe_audio

    mock_transcription = MagicMock()
    mock_transcription.text = MOCK_TRANSCRIPT
    mock_client.return_value.audio.transcriptions.create.return_value = mock_transcription

    transcribe_audio(FAKE_AUDIO, filename="test.wav", content_type="audio/wav", language="ky")

    _, kwargs = mock_client.return_value.audio.transcriptions.create.call_args
    assert "language" not in kwargs
