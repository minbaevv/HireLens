"""API эндпоинты для AI-интервью."""
import logging
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.ai.interview_service import send_message, start_interview, transcribe_audio
from app.api.deps import get_current_company
from app.core.db import get_db
from app.core.limiter import limiter
from app.models.models import (
    Candidate,
    Interview,
    InterviewStatus,
    Message,
    MessageRole,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/interviews", tags=["interviews"])


def _get_interview_by_token(
    interview_id: int, request: Request, db: Session
) -> Interview:
    """SEC-1: доступ кандидата к интервью только по access_token.

    Токен передаётся в заголовке X-Interview-Token (или ?token= для совместимости).
    Защищает от IDOR-перебора последовательных id (чтение чужих интервью, cost-DoS).
    """
    import secrets as _secrets

    token = request.headers.get("X-Interview-Token") or request.query_params.get("token") or ""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Интервью не найдено")
    if not token or not _secrets.compare_digest(token, interview.access_token or ""):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Неверный токен интервью")
    return interview


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class InterviewStartResponse(BaseModel):
    interview_id: int
    access_token: str  # SEC-1: кандидат использует его для всех запросов к интервью
    message: str
    is_complete: bool


class MessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    interview_id: int
    message: str
    is_complete: bool
    transcribed_text: Optional[str] = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: MessageRole
    content: str


class InterviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
    status: InterviewStatus
    messages: List[MessageOut] = []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{candidate_id}/start",
    response_model=InterviewStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Начать AI-интервью",
)
@limiter.limit("10/hour")
def start(
    request: Request,
    candidate_id: int,
    db: Session = Depends(get_db),
):
    """Запускает интервью. Доступен кандидату без авторизации."""
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кандидат не найден")
    try:
        result = start_interview(candidate_id, db)
        return InterviewStartResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Groq API ошибка: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI сервис недоступен")


@router.post(
    "/{interview_id}/message",
    response_model=MessageResponse,
    summary="Отправить ответ на вопрос AI",
)
def message(
    interview_id: int,
    body: MessageRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db),
):
    """Кандидат отвечает на вопрос. Требует X-Interview-Token (SEC-1)."""
    _get_interview_by_token(interview_id, request, db)
    try:
        result = send_message(interview_id, body.content, db, background_tasks)
        return MessageResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Groq API ошибка: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI сервис недоступен")


@router.post(
    "/{interview_id}/video",
    response_model=MessageResponse,
    summary="Отправить видео-ответ (WebRTC + Whisper STT)",
)
async def video_message(
    interview_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    video: UploadFile = File(..., description="Видео файл (webm, mp4). Макс 100MB."),
    db: Session = Depends(get_db),
):
    """Принимает видео, извлекает аудио, транскрибирует через Whisper, отправляет как текстовый ответ. C2"""
    import os
    from datetime import datetime, UTC
    from pathlib import Path
    from app.services.video_processing import extract_audio_from_video, get_video_duration

    # Валидация размера (100MB)
    MAX_VIDEO_SIZE_MB = 100
    video_bytes = await video.read()
    size_mb = len(video_bytes) / (1024 * 1024)
    if size_mb > MAX_VIDEO_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Видео слишком большое: {size_mb:.1f}MB. Максимум {MAX_VIDEO_SIZE_MB}MB."
        )

    # Валидация формата
    content_type = video.content_type or ""
    allowed_types = {"video/webm", "video/mp4"}
    if content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Неподдерживаемый формат: {content_type}. Поддерживаются: webm, mp4."
        )

    # Проверка интервью + токена (SEC-1)
    interview = _get_interview_by_token(interview_id, request, db)

    # Сохранение видео
    upload_dir = Path("uploads/videos") / str(interview_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    ext = ".webm" if "webm" in content_type else ".mp4"
    video_filename = f"{timestamp}{ext}"
    video_path = upload_dir / video_filename

    with open(video_path, "wb") as f:
        f.write(video_bytes)

    logger.info(f"Видео сохранено: {video_path} ({size_mb:.2f}MB)")

    # Извлечение аудио и транскрипция
    job_language = None
    if interview.candidate and interview.candidate.job:
        job_language = interview.candidate.job.language

    try:
        audio_bytes = extract_audio_from_video(str(video_path))
        transcribed_text = transcribe_audio(
            audio_bytes, filename="audio.wav", content_type="audio/wav", language=job_language
        )
    except RuntimeError as e:
        logger.error(f"Ошибка обработки видео: {e}")
        # Удаляем видео при ошибке
        if video_path.exists():
            os.remove(video_path)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Не удалось обработать видео: {str(e)}"
        )

    # Получить длительность видео
    video_duration = get_video_duration(str(video_path))

    # Отправляем транскрипт в интервью
    try:
        result = send_message(interview_id, transcribed_text, db, background_tasks)

        # Обновляем последнее сообщение пользователя: добавляем video_url и video_duration
        last_user_message = (
            db.query(Message)
            .filter(Message.interview_id == interview_id, Message.role == MessageRole.user)
            .order_by(Message.id.desc())
            .first()
        )
        if last_user_message:
            # SEC-3: URL указывает на защищённый эндпоинт вместо публичной статики
            last_user_message.video_url = f"/interviews/{interview_id}/video/{video_filename}"
            last_user_message.video_duration = video_duration
            db.commit()

        return MessageResponse(
            interview_id=result["interview_id"],
            message=result["message"],
            is_complete=result["is_complete"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        logger.error(f"AI сервис ошибка: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI сервис недоступен")


@router.post(
    "/{interview_id}/voice",
    response_model=MessageResponse,
    summary="Отправить голосовой ответ (Whisper STT)",
)
async def voice_message(
    interview_id: int,
    background_tasks: BackgroundTasks,
    request: Request,
    audio: UploadFile = File(..., description="Аудио файл (mp3, wav, webm, ogg, flac, m4a). Макс 25MB."),
    db: Session = Depends(get_db),
):
    """Принимает аудио, транскрибирует через Whisper, отправляет как текстовый ответ.

    SEC-1 fix: раньше требовал HR-авторизацию (get_current_company), хотя эндпоинт
    используется кандидатом — голосовые ответы были сломаны. Теперь доступ по
    X-Interview-Token, как и остальные эндпоинты кандидата.
    """
    interview = _get_interview_by_token(interview_id, request, db)

    # Читаем аудио
    audio_bytes = await audio.read()
    content_type = audio.content_type or "audio/webm"
    filename = audio.filename or "audio.webm"

    job_language = None
    if interview.candidate and interview.candidate.job:
        job_language = interview.candidate.job.language

    try:
        transcribed_text = transcribe_audio(
            audio_bytes, filename=filename, content_type=content_type, language=job_language
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Whisper API ошибка: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Whisper сервис недоступен")

    # Передаём транскрипт в обычный send_message
    try:
        result = send_message(interview_id, transcribed_text, db, background_tasks)
        # Добавляем транскрипт в ответ для отображения в UI
        return MessageResponse(
            interview_id=result["interview_id"],
            message=result["message"],
            is_complete=result["is_complete"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        logger.error(f"Groq API ошибка: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI сервис недоступен")


@router.get(
    "/{interview_id}",
    response_model=InterviewOut,
    summary="Получить интервью с историей сообщений",
)
def get_interview(
    interview_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Returns interview with full message history. Требует X-Interview-Token (SEC-1)."""
    interview = _get_interview_by_token(interview_id, request, db)
    messages = (
        db.query(Message)
        .filter(Message.interview_id == interview_id)
        .order_by(Message.id)
        .all()
    )
    return InterviewOut(
        id=interview.id,
        candidate_id=interview.candidate_id,
        status=interview.status,
        messages=[MessageOut.model_validate(m) for m in messages],
    )


@router.get(
    "/{interview_id}/video/{filename}",
    summary="Скачать видео интервью (только HR своей компании)",
)
def get_interview_video(
    interview_id: int,
    filename: str,
    db: Session = Depends(get_db),
    current_company=Depends(get_current_company),
):
    """SEC-3: видео с персональными данными кандидатов раздаётся только
    авторизованному HR той компании, которой принадлежит вакансия
    (раньше — публичная статика /videos/... без auth)."""
    from pathlib import Path as _Path

    from fastapi.responses import FileResponse

    from app.models.models import Job

    interview = (
        db.query(Interview)
        .join(Candidate, Interview.candidate_id == Candidate.id)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Interview.id == interview_id, Job.company_id == current_company.id)
        .first()
    )
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Интервью не найдено")

    # Защита от path traversal: имя файла без разделителей пути
    safe_name = _Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Некорректное имя файла")

    video_path = _Path("uploads/videos") / str(interview_id) / safe_name
    if not video_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Видео не найдено")

    media_type = "video/webm" if safe_name.endswith(".webm") else "video/mp4"
    return FileResponse(video_path, media_type=media_type, filename=safe_name)
