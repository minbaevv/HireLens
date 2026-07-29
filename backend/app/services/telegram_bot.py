"""Телеграм бот для кандидатов.

Флоу:
  /start <token>  — кандидат открывает ссылку вакансии
  Бот спрашивает имя → телефон → фото → email → резюме (необязательно)
  Затем начинается AI-интервью прямо в чате

Язык диалога берётся из Job.language (ru/ky/en) — так же, как и язык
AI-интервью и веб-формы заявки (см. A6.1/A6.2).
"""
import logging
from typing import Optional

import httpx

from app.core.config import settings
from app.services.i18n_texts import is_skip_word, t

logger = logging.getLogger(__name__)

TG_API = "https://api.telegram.org/bot{token}/{method}"

# Состояния диалога в памяти (в продакшне — Redis, здесь для MVP)
# Структура: { chat_id: { "state": str, "data": dict } }
_sessions: dict = {}

STATE_IDLE        = "idle"
STATE_WAIT_NAME   = "wait_name"
STATE_WAIT_PHONE  = "wait_phone"
STATE_WAIT_PHOTO  = "wait_photo"
STATE_WAIT_EMAIL  = "wait_email"
STATE_WAIT_RESUME = "wait_resume"
STATE_INTERVIEW   = "interview"

# Фото кандидата из Telegram (pilot feedback: Dinara)
MAX_TG_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB


def _api(method: str, token: str = None, **kwargs) -> dict:
    """POST запрос к Telegram Bot API."""
    token = token or settings.TELEGRAM_CANDIDATE_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN
    if not token:
        return {}
    try:
        url = TG_API.format(token=token, method=method)
        resp = httpx.post(url, json=kwargs, timeout=10)
        return resp.json()
    except Exception as e:
        logger.warning(f"TG API error [{method}]: {e}")
        return {}


def send_message(chat_id: int, text: str, reply_markup=None, token: str = None) -> None:
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    _api("sendMessage", token=token, **payload)


def set_webhook(url: str, token: str = None) -> bool:
    """Register webhook URL with Telegram (SEC-2: с secret_token, если задан)."""
    kwargs = {"url": url}
    if settings.TELEGRAM_WEBHOOK_SECRET:
        kwargs["secret_token"] = settings.TELEGRAM_WEBHOOK_SECRET
    result = _api("setWebhook", token=token, **kwargs)
    ok = result.get("ok", False)
    logger.info(f"Webhook set to {url}: {ok}")
    return ok


def _get_session(chat_id: int) -> dict:
    if chat_id not in _sessions:
        _sessions[chat_id] = {"state": STATE_IDLE, "data": {}}
    return _sessions[chat_id]


def _reset_session(chat_id: int) -> None:
    _sessions[chat_id] = {"state": STATE_IDLE, "data": {}}


def _lang(session: dict) -> str:
    """Язык текущего диалога (по умолчанию — русский)."""
    return session["data"].get("language", "ru")


def handle_update(update: dict, db) -> None:
    """Обрабатывает входящее обновление от Telegram."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id: int = message["chat"]["id"]
    text: str = message.get("text", "").strip()

    # Голосовое сообщение (C3.1)
    voice = message.get("voice")
    if voice:
        _handle_voice_message(chat_id, voice, message, db)
        return

    session = _get_session(chat_id)
    state = session["state"]

    # --- /start <token> ---
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        token = parts[1].strip() if len(parts) > 1 else ""
        _handle_start(chat_id, token, session, db)
        return

    # --- /cancel ---
    if text == "/cancel":
        lang = _lang(session)
        _reset_session(chat_id)
        send_message(chat_id, t("cancelled", lang))
        return

    # Номер телефона кнопкой «Отправить мой номер»
    contact = message.get("contact")
    if contact:
        if state == STATE_WAIT_PHONE:
            _handle_phone(chat_id, contact.get("phone_number", ""), session)
        return

    # Фото кандидата
    photos = message.get("photo")
    if photos:
        if state == STATE_WAIT_PHOTO:
            _handle_photo(chat_id, photos, session, db)
        else:
            send_message(chat_id, t("photo_not_expected", _lang(session)))
        return

    # --- Диалог по состоянию ---
    if state == STATE_WAIT_NAME:
        _handle_name(chat_id, text, session)
    elif state == STATE_WAIT_PHONE:
        _handle_phone(chat_id, text, session)
    elif state == STATE_WAIT_PHOTO:
        _handle_photo_text(chat_id, text, session)
    elif state == STATE_WAIT_EMAIL:
        _handle_email(chat_id, text, session)
    elif state == STATE_WAIT_RESUME:
        _handle_resume(chat_id, text, session, db)
    elif state == STATE_INTERVIEW:
        _handle_interview_message(chat_id, text, session, db)
    else:
        send_message(chat_id, t("greeting_default", _lang(session)))


def _handle_start(chat_id: int, token: str, session: dict, db) -> None:
    """Handles /start with job token."""
    from app.models.models import Job

    if not token:
        send_message(chat_id, t("no_token", _lang(session)))
        return

    # Сначала пробуем токен вакансии (кандидат), затем код привязки компании.
    job = db.query(Job).filter(Job.apply_token == token, Job.is_active == True).first()
    if job is not None:
        lang = getattr(job, "language", None) or "ru"
        session["state"] = STATE_WAIT_NAME
        session["data"] = {"job_id": job.id, "job_title": job.title, "token": token, "language": lang}
        send_message(chat_id, t("ask_name", lang, job_title=job.title))
        return

    from app.models.models import Company
    company = db.query(Company).filter(Company.telegram_link_code == token).first()
    if company is not None:
        company.telegram_chat_id = str(chat_id)
        company.telegram_link_code = None  # одноразовый код
        db.commit()
        send_message(chat_id, f"✅ Уведомления HireLens привязаны к компании «{company.name}».", token=settings.TELEGRAM_BOT_TOKEN)
        return

    send_message(chat_id, t("job_not_found", _lang(session)))


def _handle_name(chat_id: int, text: str, session: dict) -> None:
    lang = _lang(session)
    if len(text) < 2:
        send_message(chat_id, t("name_too_short", lang))
        return
    session["data"]["name"] = text
    session["state"] = STATE_WAIT_PHONE
    send_message(
        chat_id,
        t("ask_phone", lang, name=text),
        reply_markup={
            "keyboard": [[{"text": t("btn_send_phone", lang), "request_contact": True}]],
            "resize_keyboard": True,
            "one_time_keyboard": True,
        },
    )


def _normalize_phone(raw):
    """Приводит телефон к формату +996XXXXXXXXX (как в веб-анкете)."""
    import re
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    has_plus = s.startswith("+")
    digits = re.sub(r"\D", "", s)
    if not digits:
        return None
    if has_plus:
        return "+" + digits
    if digits.startswith("996"):
        return "+" + digits
    if digits.startswith("0"):
        return "+996" + digits.lstrip("0")
    if len(digits) == 9:
        return "+996" + digits
    return "+" + digits


def _handle_phone(chat_id: int, raw: str, session: dict) -> None:
    """Шаг «телефон»: кнопка контакта или ручной ввод."""
    lang = _lang(session)
    phone = _normalize_phone(raw)
    if not phone or len(phone) < 10:
        send_message(chat_id, t("invalid_phone", lang))
        return
    session["data"]["phone"] = phone
    session["state"] = STATE_WAIT_PHOTO
    send_message(
        chat_id,
        t("ask_photo", lang),
        reply_markup={
            "keyboard": [[{"text": t("btn_skip", lang)}]],
            "resize_keyboard": True,
            "one_time_keyboard": True,
        },
    )


def _goto_email(chat_id: int, session: dict) -> None:
    lang = _lang(session)
    session["state"] = STATE_WAIT_EMAIL
    send_message(
        chat_id,
        t("ask_email", lang, name=session["data"].get("name", "")),
        reply_markup={"remove_keyboard": True},
    )


def _handle_photo_text(chat_id: int, text: str, session: dict) -> None:
    """Шаг «фото»: текст вместо картинки — только «пропустить»."""
    lang = _lang(session)
    if is_skip_word(text, lang):
        _goto_email(chat_id, session)
        return
    send_message(chat_id, t("ask_photo_again", lang))


def _handle_photo(chat_id: int, photos: list, session: dict, db) -> None:
    """Скачивает самый крупный размер фото и кладёт в сессию."""
    lang = _lang(session)
    data = None
    try:
        file_id = photos[-1]["file_id"]
        data = _download_telegram_file(file_id)
    except Exception as e:
        logger.warning(f"Photo download error: {e}")
    if not data or data[:3] != b"\xff\xd8\xff" or len(data) > MAX_TG_PHOTO_SIZE:
        send_message(chat_id, t("photo_error", lang))
        return
    session["data"]["photo_bytes"] = data
    send_message(chat_id, t("photo_saved", lang))
    _goto_email(chat_id, session)


def _handle_email(chat_id: int, text: str, session: dict) -> None:
    import re
    lang = _lang(session)
    if not re.match(r"[^@]+@[^@]+\.[^@]+", text):
        send_message(chat_id, t("invalid_email", lang))
        return
    session["data"]["email"] = text
    session["state"] = STATE_WAIT_RESUME
    send_message(chat_id, t("ask_resume", lang))


def _handle_resume(chat_id: int, text: str, session: dict, db) -> None:
    lang = _lang(session)
    resume = None if is_skip_word(text, lang) else text
    session["data"]["resume_text"] = resume
    _create_candidate_and_start_interview(chat_id, session, db)


def _create_candidate_and_start_interview(chat_id: int, session: dict, db) -> None:
    """Creates candidate in DB and starts AI interview."""
    from app.models.models import Candidate, CandidateStatus, Job
    from app.ai.interview_service import start_interview, pre_screen_resume
    from app.services.telegram import notify_new_candidate

    data = session["data"]
    lang = data.get("language", "ru")
    job_id = data["job_id"]
    name = data["name"]
    email = data["email"]
    resume_text = data.get("resume_text")

    # Проверяем дубликат
    existing = db.query(Candidate).filter(
        Candidate.job_id == job_id,
        Candidate.email == email,
    ).first()
    if existing:
        send_message(chat_id, t("duplicate_application", lang))
        _reset_session(chat_id)
        return

    job = db.query(Job).filter(Job.id == job_id).first()

    candidate = Candidate(
        job_id=job_id,
        name=name,
        email=email,
        phone=data.get("phone"),
        resume_text=resume_text,
        status=CandidateStatus.applied,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    # Фото из Telegram — сохраняем туда же, куда его кладёт веб-анкета
    photo_bytes = data.get("photo_bytes")
    if photo_bytes:
        try:
            import secrets
            from pathlib import Path
            photo_dir = Path("uploads/photos")
            photo_dir.mkdir(parents=True, exist_ok=True)
            pfname = f"{candidate.id}_{secrets.token_hex(8)}.jpg"
            (photo_dir / pfname).write_bytes(photo_bytes)
            candidate.photo_url = f"/api/candidates/photo/{pfname}"
            db.commit()
            db.refresh(candidate)
        except Exception as e:
            logger.warning(f"Фото из Telegram не сохранено (#{candidate.id}): {e}")

    # Пре-скрининг резюме
    if resume_text:
        try:
            pre_screen_resume(candidate, db)
        except Exception as e:
            logger.warning(f"Pre-screen error: {e}")

    # Telegram уведомление HR (всегда на русском — для HR)
    notify_new_candidate(
        candidate_name=name,
        candidate_email=email,
        job_title=job.title if job else data["job_title"],
        company=job.company if job else None,
    )

    send_message(chat_id, t("application_accepted", lang))

    # Запускаем интервью
    try:
        result = start_interview(candidate.id, db)
        session["state"] = STATE_INTERVIEW
        session["data"]["interview_id"] = result["interview_id"]
        session["data"]["candidate_id"] = candidate.id
        send_message(chat_id, result["message"])
    except Exception as e:
        logger.error(f"Start interview error: {e}")
        send_message(chat_id, t("interview_start_error", lang))
        _reset_session(chat_id)


def _handle_interview_message(chat_id: int, text: str, session: dict, db) -> None:
    """Sends candidate reply to AI and returns next question."""
    from app.ai.interview_service import send_message as ai_send

    lang = _lang(session)
    interview_id = session["data"].get("interview_id")
    if not interview_id:
        _reset_session(chat_id)
        return

    try:
        result = ai_send(interview_id, text, db)
        send_message(chat_id, result["message"])

        if result["is_complete"]:
            send_message(chat_id, t("interview_complete", lang))
            _reset_session(chat_id)
    except Exception as e:
        logger.error(f"Interview message error: {e}")
        send_message(chat_id, t("interview_message_error", lang))


def _handle_voice_message(chat_id: int, voice: dict, message: dict, db) -> None:
    """Обрабатывает голосовое сообщение (C3.1)."""
    session = _get_session(chat_id)
    state = session["state"]
    lang = _lang(session)

    # Голос работает только во время интервью
    if state != STATE_INTERVIEW:
        send_message(chat_id, t("voice_only_in_interview", lang))
        return

    interview_id = session["data"].get("interview_id")
    if not interview_id:
        _reset_session(chat_id)
        return

    try:
        # 1. Получить file_id
        file_id = voice["file_id"]

        # 2. Скачать audio через Telegram API
        audio_bytes = _download_telegram_file(file_id)
        if not audio_bytes:
            send_message(chat_id, t("voice_download_error", lang))
            return

        # 3. Транскрибировать через Whisper
        from app.ai.interview_service import transcribe_audio
        from app.models.models import Candidate, Interview

        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        job_language = None
        if interview and interview.candidate and interview.candidate.job:
            job_language = interview.candidate.job.language

        transcribed_text = transcribe_audio(
            audio_bytes,
            filename="voice.ogg",
            content_type="audio/ogg",
            language=job_language
        )

        # 4. Отправить транскрипт как текстовый ответ
        from app.ai.interview_service import send_message as ai_send
        result = ai_send(interview_id, transcribed_text, db)

        # Показать транскрипт кандидату
        send_message(chat_id, f"🎤 <i>{transcribed_text}</i>")
        send_message(chat_id, result["message"])

        if result["is_complete"]:
            send_message(chat_id, t("interview_complete", lang))
            _reset_session(chat_id)

    except Exception as e:
        logger.error(f"Voice message error: {e}")
        send_message(chat_id, t("voice_processing_error", lang))


def _download_telegram_file(file_id: str) -> Optional[bytes]:
    """Скачивает файл из Telegram."""
    try:
        # 1. Получить file_path
        result = _api("getFile", file_id=file_id)
        if not result.get("ok"):
            return None

        file_path = result["result"]["file_path"]

        # 2. Скачать файл
        token = settings.TELEGRAM_CANDIDATE_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN
        download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"

        resp = httpx.get(download_url, timeout=30)
        if resp.status_code != 200:
            return None

        return resp.content

    except Exception as e:
        logger.error(f"Telegram file download error: {e}")
        return None
