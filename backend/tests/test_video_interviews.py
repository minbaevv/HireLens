"""Тесты для видео-интервью (C2)."""
import io
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.candidate import Candidate, CandidateStatus
from app.models.interview import Interview, InterviewStatus, Message, MessageRole
from app.models.job import Job
from app.services.video_processing import extract_audio_from_video, get_video_duration


@pytest.fixture
def mock_video_file():
    """Создаёт mock видеофайл (5MB)."""
    video_bytes = b"MOCK_VIDEO_DATA" * (5 * 1024 * 1024 // 15)  # ~5MB
    return io.BytesIO(video_bytes)


def test_video_upload_success(client, db: Session, auth_headers):
    """POST /interviews/{id}/video — успешная загрузка видео."""
    # Создать вакансию, кандидата, интервью
    from app.models.company import Company
    company = db.query(Company).filter(Company.email == "jobs@test.com").first()
    job = Job(company_id=company.id, title="Backend Dev", description="Test job", requirements="Python", language="ru")
    db.add(job)
    db.commit()

    candidate = Candidate(job_id=job.id, name="Test", email="test@c.com", status=CandidateStatus.applied)
    db.add(candidate)
    db.commit()

    interview = Interview(candidate_id=candidate.id, status=InterviewStatus.in_progress)
    db.add(interview)
    db.commit()

    # Mock ffmpeg, Whisper, LLM. send_message НЕ мокаем — она создаёт user-сообщение,
    # к которому эндпоинт затем прикрепляет video_url/duration; мокаем только LLM внутри неё.
    with patch("app.services.video_processing.extract_audio_from_video") as mock_extract, \
         patch("app.services.video_processing.get_video_duration") as mock_duration, \
         patch("app.api.interviews.transcribe_audio") as mock_whisper, \
         patch("app.ai.interview_service._call_groq") as mock_llm:

        # Mock извлечения аудио и длительности
        mock_extract.return_value = b"FAKE_AUDIO_WAV_DATA"
        mock_duration.return_value = 10.5

        mock_whisper.return_value = "У меня 3 года опыта в Python"
        mock_llm.return_value = "Отлично! Расскажите о проектах."

        # Создать mock видеофайл
        video_data = b"FAKE_VIDEO_WEBM_DATA" * 1000
        files = {"video": ("test.webm", io.BytesIO(video_data), "video/webm")}

        response = client.post(f"/interviews/{interview.id}/video", files=files, headers={"X-Interview-Token": interview.access_token})

    assert response.status_code == 200
    data = response.json()
    assert data["interview_id"] == interview.id
    assert "Отлично" in data["message"]
    assert data["is_complete"] is False

    # Проверить что видео сохранено и video_url записан
    user_msg = db.query(Message).filter(
        Message.interview_id == interview.id,
        Message.role == MessageRole.user
    ).first()
    assert user_msg is not None
    assert user_msg.video_url is not None
    assert user_msg.video_url.startswith(f"/interviews/{interview.id}/video/")
    assert user_msg.video_duration == 10.5

    # Проверить что файл создан
    video_path = Path("uploads") / "videos" / str(interview.id)
    assert video_path.exists()
    files_in_dir = list(video_path.glob("*.webm"))
    assert len(files_in_dir) > 0

    # Очистка
    for f in files_in_dir:
        os.remove(f)


def test_video_upload_too_large(client, db: Session, auth_headers):
    """POST /interviews/{id}/video — файл > 100MB."""
    from app.models.company import Company
    company = db.query(Company).filter(Company.email == "jobs@test.com").first()
    job = Job(company_id=company.id, title="Backend Dev", description="Test", requirements="Python")
    db.add(job)
    db.commit()

    candidate = Candidate(job_id=job.id, name="Test", email="test@c.com")
    db.add(candidate)
    db.commit()

    interview = Interview(candidate_id=candidate.id, status=InterviewStatus.in_progress)
    db.add(interview)
    db.commit()

    # Создать файл > 100MB (101MB)
    large_video = b"X" * (101 * 1024 * 1024)
    files = {"video": ("large.webm", io.BytesIO(large_video), "video/webm")}

    response = client.post(f"/interviews/{interview.id}/video", files=files, headers={"X-Interview-Token": interview.access_token})

    assert response.status_code == 413
    assert "слишком большое" in response.json()["detail"]


def test_video_upload_invalid_format(client, db: Session, auth_headers):
    """POST /interviews/{id}/video — неподдерживаемый формат."""
    from app.models.company import Company
    company = db.query(Company).filter(Company.email == "jobs@test.com").first()
    job = Job(company_id=company.id, title="Backend Dev", description="Test", requirements="Python")
    db.add(job)
    db.commit()

    candidate = Candidate(job_id=job.id, name="Test", email="test@c.com")
    db.add(candidate)
    db.commit()

    interview = Interview(candidate_id=candidate.id, status=InterviewStatus.in_progress)
    db.add(interview)
    db.commit()

    # Неверный MIME type
    video_data = b"FAKE_AVI_DATA"
    files = {"video": ("test.avi", io.BytesIO(video_data), "video/x-msvideo")}

    response = client.post(f"/interviews/{interview.id}/video", files=files, headers={"X-Interview-Token": interview.access_token})

    assert response.status_code == 422
    assert "Неподдерживаемый формат" in response.json()["detail"]


def test_video_upload_interview_not_found(client):
    """POST /interviews/{id}/video — интервью не существует."""
    video_data = b"DATA"
    files = {"video": ("test.webm", io.BytesIO(video_data), "video/webm")}

    response = client.post("/interviews/99999/video", files=files)

    assert response.status_code == 404
    assert "не найдено" in response.json()["detail"]


def test_video_upload_ffmpeg_not_available(client, db: Session, auth_headers):
    """POST /interviews/{id}/video — ffmpeg недоступен."""
    from app.models.company import Company
    company = db.query(Company).filter(Company.email == "jobs@test.com").first()
    job = Job(company_id=company.id, title="Backend Dev", description="Test", requirements="Python")
    db.add(job)
    db.commit()

    candidate = Candidate(job_id=job.id, name="Test", email="test@c.com")
    db.add(candidate)
    db.commit()

    interview = Interview(candidate_id=candidate.id, status=InterviewStatus.in_progress)
    db.add(interview)
    db.commit()

    with patch("app.services.video_processing.subprocess.run") as mock_subprocess:
        # ffmpeg -version не найден
        mock_subprocess.side_effect = FileNotFoundError("ffmpeg")

        video_data = b"DATA" * 1000
        files = {"video": ("test.webm", io.BytesIO(video_data), "video/webm")}

        response = client.post(f"/interviews/{interview.id}/video", files=files, headers={"X-Interview-Token": interview.access_token})

    assert response.status_code == 503
    assert "обработать видео" in response.json()["detail"]


def test_extract_audio_from_video_ffmpeg_missing():
    """extract_audio_from_video — ffmpeg не установлен."""
    with patch("app.services.video_processing.subprocess.run") as mock_subprocess:
        mock_subprocess.side_effect = FileNotFoundError("ffmpeg")

        with pytest.raises(RuntimeError, match="ffmpeg не установлен"):
            extract_audio_from_video("/fake/path.webm")


def test_get_video_duration_success():
    """get_video_duration — успешное определение длительности."""
    with patch("app.services.video_processing.subprocess.run") as mock_subprocess:
        mock_subprocess.return_value = MagicMock(stdout="45.6\n", returncode=0)

        duration = get_video_duration("/fake/video.mp4")

    assert duration == 45.6


def test_get_video_duration_error():
    """get_video_duration — ошибка ffprobe → возвращает 0.0."""
    with patch("app.services.video_processing.subprocess.run") as mock_subprocess:
        mock_subprocess.side_effect = FileNotFoundError("ffprobe")

        duration = get_video_duration("/fake/video.mp4")

    assert duration == 0.0
