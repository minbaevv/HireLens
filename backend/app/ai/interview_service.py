"""Сервис AI-интервью на базе Groq API."""
import asyncio
import json
import logging
import time
from typing import Optional

from sqlalchemy.orm import Session

from app.ai import prompt_service
from app.ai.prompts import (
    DATA_HANDLING_RULE,
    INTERVIEW_SYSTEM_PROMPT,
    NO_RESUME_PLACEHOLDER,
    SCORING_JSON_SCHEMA,
    SCORING_SYSTEM_PROMPT,
    language_name,
)
from app.ai.sanitization import detect_injection, redact_pii, wrap_untrusted
from app.core.config import settings
from app.models.models import (
    Candidate,
    CandidateStatus,
    Interview,
    InterviewStatus,
    Message,
    MessageRole,
)

logger = logging.getLogger(__name__)

INTERVIEW_COMPLETE_MARKER = "[INTERVIEW_COMPLETE]"

# Поддерживаемые форматы аудио для Whisper
ALLOWED_AUDIO_TYPES = {
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/wave",
    "audio/x-wav", "audio/webm", "audio/ogg", "audio/flac",
    "audio/mp4", "audio/m4a", "video/webm",
}
MAX_AUDIO_SIZE_MB = 25
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Сопоставление языка вакансии (Job.language) с кодом языка Whisper.
# ⚠️ Groq/OpenAI Whisper официально не поддерживает кыргызский как отдельный
# язык транскрипции. Для "ky" код намеренно не передаём — Whisper сам
# определит язык (auto-detect), что честнее принудительного неверного кода.
WHISPER_LANGUAGE_MAP = {"ru": "ru", "en": "en"}


def _resolve_whisper_language(language: Optional[str]) -> Optional[str]:
    """Возвращает код языка для Whisper API или None (авто-определение)."""
    return WHISPER_LANGUAGE_MAP.get(language)


def _get_groq_client():
    """Lazy-инициализация Groq клиента."""
    try:
        from groq import Groq
        return Groq(api_key=settings.GROQ_API_KEY)
    except ImportError:
        raise RuntimeError("Библиотека groq не установлена. Запусти: pip install groq")


def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    content_type: str = "audio/webm",
    language: Optional[str] = None,
) -> str:
    """Транскрибирует аудио через Groq Whisper API.

    Args:
        audio_bytes: Байты аудио файла.
        filename: Имя файла (влияет на определение формата).
        content_type: MIME-тип аудио.
        language: Язык вакансии (ru/ky/en, см. Job.language) — подсказка Whisper
            для правильного распознавания. Для "ky" явный код не передаётся,
            см. WHISPER_LANGUAGE_MAP.

    Returns:
        Транскрибированный текст.

    Raises:
        ValueError: Если формат не поддерживается или файл слишком большой.
        RuntimeError: Если Whisper API недоступен.
    """
    # Валидация размера
    size_mb = len(audio_bytes) / (1024 * 1024)
    if size_mb > MAX_AUDIO_SIZE_MB:
        raise ValueError(f"Файл слишком большой: {size_mb:.1f}MB. Максимум {MAX_AUDIO_SIZE_MB}MB.")

    # Валидация типа
    if content_type not in ALLOWED_AUDIO_TYPES:
        raise ValueError(
            f"Неподдерживаемый формат: {content_type}. "
            f"Поддерживаются: mp3, wav, webm, ogg, flac, m4a."
        )

    client = _get_groq_client()
    whisper_language = _resolve_whisper_language(language)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            import io
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = filename

            create_kwargs = dict(
                file=(filename, audio_bytes, content_type),
                model="whisper-large-v3",
                response_format="text",
            )
            if whisper_language:
                create_kwargs["language"] = whisper_language

            transcription = client.audio.transcriptions.create(**create_kwargs)
            text = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()
            if not text:
                raise ValueError("Аудио не содержит речи или слишком тихое.")
            logger.info(f"Whisper транскрипция: '{text[:80]}...' ({size_mb:.2f}MB)")
            return text
        except ValueError:
            raise
        except Exception as e:
            logger.warning(f"Whisper API ошибка (attempt {attempt}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
            else:
                raise RuntimeError(f"Ошибка Whisper API после {MAX_RETRIES} попыток: {e}")


def _call_groq(messages: list, system: str, temperature: float = 0.7) -> str:
    """Вызов LLM через единый диспетчер (Claude — основной, Groq — fallback).

    Имя функции сохранено для обратной совместимости с тестами и mock-патчами.
    Retry и выбор провайдера — внутри app.ai.llm.call_llm (settings.AI_PROVIDER).
    """
    from app.ai.llm import call_llm

    return call_llm(messages, system, temperature=temperature)


def _build_chat_messages(db_messages: list[Message]) -> list[dict]:
    """Преобразует сообщения из БД в формат Groq."""
    result = []
    for msg in db_messages:
        role = "assistant" if msg.role == MessageRole.ai else "user"
        result.append({"role": role, "content": msg.content})
    return result


def _parse_scoring_weights(job) -> dict | None:
    """Priority 2: нормализованные веса критериев из Job.scoring_weights или None."""
    raw = getattr(job, "scoring_weights", None)
    if not raw:
        return None
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    weights = {}
    for k in ("technical", "soft", "experience", "motivation"):
        v = data.get(k)
        if isinstance(v, (int, float)) and v > 0:
            weights[k] = float(v)
    return weights or None


def _normalize_red_flags(raw) -> list:
    """Red flags: {category, detail} или строки → читаемые строки.

    Пустые и «нет значимых красных флагов»-заглушки отсеиваются (см. red_flags.py),
    категория приводится к читаемой метке («Пробел в навыках: ...»).
    """
    from app.ai.red_flags import format_red_flag, is_noise_detail

    result = []
    for rf in raw or []:
        if isinstance(rf, dict):
            cat = rf.get("category", "other")
            det = rf.get("detail", "") or rf.get("reason", "")
            if is_noise_detail(det):
                continue
            result.append(format_red_flag(cat, det))
        elif rf:
            s = str(rf).strip()
            if s and not is_noise_detail(s):
                result.append(s)
    return result


def _build_system_prompt(candidate: Candidate, db: "Session" = None) -> str:
    """Cтроит системный промпт для интервью.

    Roadmap 6.2 — текст промпта берётся из активной версии компании (prompt_templates),
    с fallback на code-default при отсутствии записей.
    """
    job = candidate.job
    resume = candidate.resume_text or NO_RESUME_PLACEHOLDER
    template = prompt_service.resolve_prompt(db, getattr(job, "company_id", None), "interview_system")
    return template.format(
        data_handling_rule=DATA_HANDLING_RULE,
        job_title=job.title,
        job_requirements=job.requirements,
        resume_text=wrap_untrusted(resume),
        interview_language=language_name(getattr(job, "language", None)),
        min_questions=settings.INTERVIEW_MIN_QUESTIONS,
        max_questions=settings.INTERVIEW_MAX_QUESTIONS,
    )


def pre_screen_resume(candidate: "Candidate", db: "Session") -> None:
    """AI скрининг резюме сразу после подачи заявки."""
    from app.ai.prompts import PRE_SCREENING_PROMPT, PRESCREEN_JSON_SCHEMA
    import re

    if not candidate.resume_text:
        logger.info(f"Candidate #{candidate.id}: no resume, skipping pre-screen")
        return

    job = candidate.job
    _prescreen_tpl = prompt_service.resolve_prompt(db, getattr(job, "company_id", None), "prescreen")
    prompt = _prescreen_tpl.format(
        data_handling_rule=DATA_HANDLING_RULE,
        job_title=job.title,
        job_requirements=job.requirements,
        resume_text=wrap_untrusted(candidate.resume_text[:3000]),  # лимит токенов + SEC-8
        interview_language=language_name(getattr(job, "language", None)),
        schema=PRESCREEN_JSON_SCHEMA,
    )

    try:
        raw = _call_groq([], prompt, temperature=settings.TEMPERATURE_PRESCREENING)
        # Извлекаем JSON
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            raw = match.group(0)
        result = json.loads(raw)
        candidate.pre_score = float(result.get("pre_score", 0))
        db.commit()
        logger.info(
            f"Pre-screen candidate #{candidate.id}: pre_score={candidate.pre_score}, "
            f"verdict={result.get('verdict')}"
        )
    except Exception as e:
        logger.warning(f"Pre-screen failed for candidate #{candidate.id}: {e}")


def start_interview(candidate_id: int, db: Session) -> dict:
    """Начинает интервью: создаёт Interview, получает первый вопрос от AI.

    Returns:
        {"interview_id": int, "message": str, "is_complete": False}
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise ValueError(f"Кандидат #{candidate_id} не найден")

    # SEC-14: лимит интервью на кандидата (защита от cost-DoS)
    total_interviews = db.query(Interview).filter(
        Interview.candidate_id == candidate_id
    ).count()
    if total_interviews >= settings.MAX_INTERVIEWS_PER_CANDIDATE:
        raise ValueError("Достигнут лимит интервью для этого кандидата")

    # Проверяем нет ли активного интервью
    existing = db.query(Interview).filter(
        Interview.candidate_id == candidate_id,
        Interview.status == InterviewStatus.in_progress,
    ).first()
    if existing:
        raise ValueError("Интервью уже запущен")

    # Создаём запись интервью
    from datetime import datetime, UTC
    interview = Interview(
        candidate_id=candidate_id,
        status=InterviewStatus.in_progress,
        started_at=datetime.now(UTC),
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    # Получаем первый вопрос от AI
    system = _build_system_prompt(candidate, db)
    ai_text = _call_groq([], system, temperature=settings.TEMPERATURE_INTERVIEW)

    # Сохраняем первое сообщение AI
    msg = Message(interview_id=interview.id, role=MessageRole.ai, content=ai_text)
    db.add(msg)

    # Обновляем статус кандидата
    candidate.status = CandidateStatus.interviewing
    db.commit()

    logger.info(f"Интервью #{interview.id} запущен для кандидата #{candidate_id}")
    return {
        "interview_id": interview.id,
        "access_token": interview.access_token,  # SEC-1
        "message": ai_text,
        "is_complete": False,
    }


def send_message(
    interview_id: int,
    user_text: str,
    db: Session,
    background_tasks=None,
) -> dict:
    """Отправляет ответ кандидата и получает следующий вопрос AI.

    Returns:
        {"interview_id": int, "message": str, "is_complete": bool}
    """
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise ValueError(f"Интервью #{interview_id} не найдено")
    if interview.status != InterviewStatus.in_progress:
        raise ValueError("Интервью уже завершено")

    # Сохраняем ответ пользователя
    user_msg = Message(interview_id=interview_id, role=MessageRole.user, content=user_text)
    db.add(user_msg)
    db.commit()

    # Собираем всю историю для контекста
    all_messages = (
        db.query(Message)
        .filter(Message.interview_id == interview_id)
        .order_by(Message.id)
        .all()
    )
    candidate = interview.candidate
    system = _build_system_prompt(candidate, db)
    chat_history = _build_chat_messages(all_messages)

    ai_text = _call_groq(chat_history, system, temperature=settings.TEMPERATURE_INTERVIEW)

    # Adaptive flow: сколько вопросов AI уже задал (и кандидат ответил) до этого хода
    prior_ai_questions = sum(1 for m in all_messages if m.role == MessageRole.ai)

    is_complete = INTERVIEW_COMPLETE_MARKER in ai_text
    clean_text = ai_text.replace(INTERVIEW_COMPLETE_MARKER, "").strip()

    # Adaptive ceiling: жёсткий потолок длины интервью (анти cost-DoS / runaway).
    # Минимум (floor) задаётся на уровне промпта + штраф confidence в скоринге,
    # чтобы не ломать короткие сценарии; потолок же гарантируем детерминированно.
    if not is_complete and prior_ai_questions >= settings.INTERVIEW_MAX_QUESTIONS:
        is_complete = True
        clean_text = (
            "Спасибо за развёрнутые ответы! На этом наше интервью завершено — "
            "рекрутёр свяжется с вами по результатам."
        )
        logger.info(
            f"Интервью #{interview_id}: достигнут потолок "
            f"{settings.INTERVIEW_MAX_QUESTIONS} вопросов — завершаем (adaptive ceiling)"
        )

    ai_msg = Message(interview_id=interview_id, role=MessageRole.ai, content=clean_text)
    db.add(ai_msg)

    if is_complete:
        from datetime import datetime, UTC
        interview.status = InterviewStatus.completed
        interview.finished_at = datetime.now(UTC)
        db.commit()

        # Скоринг асинхронно — не блокируем HTTP ответ
        if background_tasks is not None:
            background_tasks.add_task(_run_scoring_task, interview.id)
            logger.info(f"Интервью #{interview_id} завершено, скоринг запущен в фоне")
        else:
            # Fallback для тестов — синхронно
            _run_scoring(interview, db)
            logger.info(f"Интервью #{interview_id} завершено, скоринг запущен синхронно")
    else:
        db.commit()

    return {"interview_id": interview_id, "message": clean_text, "is_complete": is_complete}


def _run_scoring_task(interview_id: int) -> None:
    """Background task: создаёт новую сессию БД и запускает скоринг."""
    from app.core.db import SessionLocal
    db = SessionLocal()
    try:
        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        if interview:
            _run_scoring(interview, db)
    except Exception as e:
        logger.error(f"Background scoring error для интервью #{interview_id}: {e}")
        # Страховка: если скоринг упал ДО своего внутреннего except (напр. ошибка
        # БД/промпта), кандидат не должен висеть в статусе «interviewing» навечно —
        # переводим в completed + флаг ручной проверки HR.
        try:
            db.rollback()
            _iv = db.query(Interview).filter(Interview.id == interview_id).first()
            _cand = _iv.candidate if _iv else None
            if _cand is not None and _cand.status != CandidateStatus.completed:
                _cand.status = CandidateStatus.completed
                _cand.requires_manual_review = True
                db.commit()
                logger.warning(
                    f"Скоринг интервью #{interview_id} упал — кандидат #{_cand.id} "
                    f"помечен completed + requires_manual_review"
                )
        except Exception as _rescue_err:
            logger.error(f"Не удалось снять кандидата с «interviewing»: {_rescue_err}")
            db.rollback()
    finally:
        db.close()


def _anticheat_llm(messages: list, system: str, temperature: float = 0.1) -> str:
    """Отдельный LLM-seam для anti-cheat (Roadmap 4.1 — Async Parallel Scoring).

    Выделен из scoring-вызова _call_groq, чтобы scoring и anti-cheat могли
    выполняться ПАРАЛЛЕЛЬНО и не делили один и тот же mock в тестах.
    """
    from app.ai.llm import call_llm

    return call_llm(messages, system, temperature=temperature)


def _run_parallel(tasks: dict) -> dict:
    """Выполняет несколько блокирующих вызовов параллельно в тредах.

    Roadmap 4.1: scoring + anti-cheat (и уведомления) идут не последовательно,
    а через asyncio.gather + asyncio.to_thread, что сокращает общий latency
    завершения интервью (~8–10 сек → ~3–4 сек).

    Args:
        tasks: {имя: callable без аргументов}. Каждый callable запускается в своём треде.

    Returns:
        {имя: результат | Exception}. Исключения не пробрасываются, а возвращаются
        как значение (return_exceptions=True) — вызывающий сам решает, что критично.
    """
    if not tasks:
        return {}
    names = list(tasks.keys())

    async def _gather():
        results = await asyncio.gather(
            *[asyncio.to_thread(tasks[n]) for n in names],
            return_exceptions=True,
        )
        return dict(zip(names, results))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # Обычный путь: активного event loop нет (фоновый поток FastAPI / тесты).
        return asyncio.run(_gather())
    # Мы уже внутри event loop — выполняем в отдельном потоке с собственным loop.
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(_gather())).result()


def _run_scoring(interview: Interview, db: Session) -> None:
    """Автоматический скоринг после завершения интервью."""
    candidate = interview.candidate
    job = candidate.job

    # Строим транскрипт
    messages = (
        db.query(Message)
        .filter(Message.interview_id == interview.id)
        .order_by(Message.id)
        .all()
    )
    # Priority 2.2 — Answer Attribution: нумеруем вопросы AI ([Q1]..) и ответы
    # кандидата ([A1]..), строим карту Q# -> Message.id для обратного резолва.
    transcript_lines = []
    question_map = []
    q_no = 0
    a_no = 0
    for msg in messages:
        if msg.role == MessageRole.ai:
            q_no += 1
            transcript_lines.append(f"[Q{q_no}] AI: {msg.content}")
            question_map.append({
                "n": q_no,
                "message_id": msg.id,
                "question": (msg.content or "")[:200],
            })
        else:
            a_no += 1
            transcript_lines.append(f"[A{a_no}] Кандидат: {msg.content}")
    transcript = "\n".join(transcript_lines)

    # Truncation (Roadmap P1): длинные интервью → context overflow и лишние токены.
    # Обрезаем с головы — финальные ответы важнее для скоринга.
    max_chars = settings.SCORING_TRANSCRIPT_MAX_CHARS
    if len(transcript) > max_chars:
        transcript = "[...начало интервью обрезано...]\n" + transcript[-max_chars:]
        logger.info(
            f"Транскрипт интервью #{interview.id} обрезан до {max_chars} символов для скоринга"
        )

    # Полнота интервью (Roadmap P1): скоринг по 1–2 ответам недостоверен
    ai_question_count = sum(1 for m in messages if m.role == MessageRole.ai)

    _scoring_tpl = prompt_service.resolve_prompt(db, getattr(job, "company_id", None), "scoring_system")
    scoring_prompt = _scoring_tpl.format(
        data_handling_rule=DATA_HANDLING_RULE,
        job_title=job.title,
        job_requirements=job.requirements,
        transcript=wrap_untrusted(redact_pii(transcript)),  # SEC-8 + SEC-15
        interview_language=language_name(getattr(job, "language", None)),
        schema=SCORING_JSON_SCHEMA,
    )

    try:
        # Roadmap 4.1 — Async Parallel Scoring: тяжёлый LLM-скоринг и anti-cheat
        # (тоже LLM-вызов) больше не идут друг за другом, а стартуют одновременно
        # (asyncio.gather + asyncio.to_thread). Итог: ~8–10 сек → ~3–4 сек.
        def _do_scoring():
            return _call_groq([], scoring_prompt, temperature=settings.TEMPERATURE_SCORING)

        def _do_anticheat():
            from app.ai.anticheat_service import analyze_interview
            return analyze_interview(messages, llm_fn=_anticheat_llm)

        _parallel = _run_parallel({"scoring": _do_scoring, "anticheat": _do_anticheat})
        _scoring_result = _parallel.get("scoring")
        _anti_result = _parallel.get("anticheat")
        if isinstance(_scoring_result, BaseException):
            # Скоринг — критичный путь → в общий except (ручная проверка HR).
            raise _scoring_result

        raw = _scoring_result
        # Извлекаем JSON если модель добавила markdown
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())

        # 1.3 — Scoring Validation: не сохраняем галлюцинации LLM.
        # При невалидном ответе бросаем ValueError → кандидат уходит на ручную проверку.
        overall = result.get("overall_score")
        if not isinstance(overall, (int, float)) or not (0 <= overall <= 100):
            raise ValueError(f"Невалидный overall_score от LLM: {overall!r}")
        if not str(result.get("summary", "")).strip():
            raise ValueError("Пустой summary от LLM")
        if result.get("recommendation") not in ("hire", "maybe", "reject"):
            raise ValueError(f"Невалидный recommendation от LLM: {result.get('recommendation')!r}")

        # C5.1 — Structured Scoring
        candidate.summary = result.get("summary", "")
        candidate.recommendation = result.get("recommendation", "maybe")

        # Сохранить детализацию
        candidate.technical_score = result.get("technical_skills", {}).get("score", 0)
        candidate.soft_skills_score = result.get("soft_skills", {}).get("score", 0)
        candidate.experience_score = result.get("experience", {}).get("score", 0)
        candidate.motivation_score = result.get("motivation", {}).get("score", 0)

        # Priority 2 — overall как взвешенная сумма критериев (если вакансия задаёт веса),
        # иначе доверяем overall_score от LLM.
        _weights = _parse_scoring_weights(job)
        if _weights:
            _dims = {
                "technical": candidate.technical_score or 0,
                "soft": candidate.soft_skills_score or 0,
                "experience": candidate.experience_score or 0,
                "motivation": candidate.motivation_score or 0,
            }
            _wsum = sum(_weights.values())
            candidate.score = round(sum(_dims[k] * _weights[k] for k in _weights) / _wsum, 1) if _wsum else float(overall)
            logger.info(f"Взвешенный overall #{candidate.id}: {candidate.score} (веса {_weights})")
        else:
            candidate.score = float(result.get("overall_score", 0))

        # Средняя confidence
        confidences = [
            result.get("technical_skills", {}).get("confidence", 0.0),
            result.get("soft_skills", {}).get("confidence", 0.0),
            result.get("experience", {}).get("confidence", 0.0),
            result.get("motivation", {}).get("confidence", 0.0),
        ]
        candidate.confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Штрафы confidence (Roadmap P1)
        penalty_flags: list[str] = []
        # 1) Интервью слишком короткое — скоринг по 1–2 ответам недостоверен
        if ai_question_count < settings.SCORING_MIN_AI_QUESTIONS:
            candidate.confidence = min(candidate.confidence, 0.3)
            penalty_flags.append(
                f"Interview too short: only {ai_question_count} AI questions "
                f"(min {settings.SCORING_MIN_AI_QUESTIONS})"
            )
        # 2) Нет резюме — не с чем сверять заявления кандидата
        if not candidate.resume_text and settings.SCORING_NO_RESUME_PENALTY < 1.0:
            candidate.confidence *= settings.SCORING_NO_RESUME_PENALTY
            penalty_flags.append("No resume provided")
        # SEC-8: попытка prompt-injection в резюме/ответах → принудительная ручная проверка
        _candidate_inputs = [candidate.resume_text or ""] + [
            m.content for m in messages if m.role == MessageRole.user
        ]
        if any(detect_injection(t) for t in _candidate_inputs):
            candidate.confidence = min(candidate.confidence, 0.3)
            penalty_flags.append(
                "Possible prompt-injection in candidate input (SEC-8) — manual review required"
            )

        # Reasoning для каждого компонента (JSON)
        candidate.scoring_reasoning = json.dumps({
            "technical_skills": result.get("technical_skills", {}).get("reasoning", ""),
            "soft_skills": result.get("soft_skills", {}).get("reasoning", ""),
            "experience": result.get("experience", {}).get("reasoning", ""),
            "motivation": result.get("motivation", {}).get("reasoning", ""),
        }, ensure_ascii=False)

        # Ground Truth Tracking (Phase 10/10 - 1.1): Флаг ручной проверки
        # Низкая confidence или экстремальные scores (0/100) требуют проверки HR
        if candidate.confidence < 0.7 or candidate.score in [0, 100]:
            candidate.requires_manual_review = True
            logger.warning(
                f"Candidate #{candidate.id} requires manual review: "
                f"confidence={candidate.confidence:.2f}, score={candidate.score}"
            )

        # Priority 2 — cross-validation (расхождения резюме/интервью) + evasive answers
        candidate.cross_validation = json.dumps({
            "discrepancies": result.get("discrepancies", []) or [],
            "evasive_answers": result.get("evasive_answers", []) or [],
        }, ensure_ascii=False)

        # Priority 2.2 — Answer Attribution: какие вопросы легли в основу оценок
        _valid_qn = {q["n"] for q in question_map}
        _raw_attr = result.get("attribution", {}) or {}
        _attr = {}
        for _dim in ("technical_skills", "soft_skills", "experience", "motivation"):
            _vals = _raw_attr.get(_dim, []) if isinstance(_raw_attr, dict) else []
            if not isinstance(_vals, list):
                _vals = []
            _attr[_dim] = sorted({
                int(v) for v in _vals
                if isinstance(v, (int, float)) and int(v) in _valid_qn
            })
        candidate.answer_attribution = json.dumps({
            "questions": question_map,
            "attribution": _attr,
        }, ensure_ascii=False)

        # C5.2 — Bias Detection + Priority 3: категоризированные red flags
        red_flags = _normalize_red_flags(result.get("red_flags", []))
        bias_detected = result.get("bias_detected", False)
        bias_flags = []
        if bias_detected:
            bias_flags.append("AI detected potential bias in reasoning")
        if red_flags:
            bias_flags.extend(red_flags)
        if penalty_flags:
            bias_flags.extend(penalty_flags)
        candidate.bias_flags = json.dumps(bias_flags, ensure_ascii=False) if bias_flags else None

        candidate.status = CandidateStatus.completed
        db.commit()
        logger.info(
            f"Скоринг кандидата #{candidate.id}: score={candidate.score}, "
            f"tech={candidate.technical_score}, soft={candidate.soft_skills_score}, "
            f"exp={candidate.experience_score}, mot={candidate.motivation_score}, "
            f"confidence={candidate.confidence:.2f}, rec={candidate.recommendation}"
        )

        # Anti-cheat (C1) уже посчитан ПАРАЛЛЕЛЬНО со скорингом (Roadmap 4.1) —
        # здесь только сохраняем результат.
        try:
            if isinstance(_anti_result, BaseException):
                raise _anti_result
            if _anti_result is None:
                raise RuntimeError("anti-cheat не выполнен")
            candidate.anti_cheat_score = _anti_result["score"]
            candidate.anti_cheat_flags = json.dumps(_anti_result["flags"], ensure_ascii=False)
            # C1.1 — Anti-cheat ↔ рекомендация: при высоком риске списывания не
            # доверяем автоматическому "hire". Балл кандидата НЕ трогаем (он отражает
            # качество ответов), но рекомендацию понижаем и требуем очную проверку.
            _ac_score = candidate.anti_cheat_score or 0
            if _ac_score >= settings.ANTI_CHEAT_DOWNGRADE_THRESHOLD:
                candidate.requires_manual_review = True
                if candidate.recommendation == "hire":
                    candidate.recommendation = "maybe"
                    logger.warning(
                        f"Candidate #{candidate.id}: рекомендация понижена hire→maybe "
                        f"(anti-cheat={_ac_score:.0f} ≥ {settings.ANTI_CHEAT_DOWNGRADE_THRESHOLD:.0f})"
                    )
                _ac_note = (
                    f"⚠️ Высокий риск списывания ({_ac_score:.0f}/100) — "
                    f"проверить очно перед решением о найме"
                )
                try:
                    _bf = json.loads(candidate.bias_flags) if candidate.bias_flags else []
                except Exception:
                    _bf = []
                if _ac_note not in _bf:
                    _bf.append(_ac_note)
                candidate.bias_flags = json.dumps(_bf, ensure_ascii=False)
            db.commit()
            logger.info(f"Anti-cheat кандидата #{candidate.id}: score={_anti_result['score']}")
        except Exception as ac_err:
            logger.warning(f"Anti-cheat анализ не выполнен: {ac_err}")

        # Roadmap 4.1 — уведомления HR (Telegram + email) отправляем ПАРАЛЛЕЛЬНО.
        # Простые значения извлекаем в главном треде (после commit ORM-атрибуты
        # перечитываются здесь же), а сами уведомления открывают свои сессии БД.
        _overall = float(overall)
        # C1.1 — берём итоговую рекомендацию с учётом возможного понижения по anti-cheat.
        _rec = candidate.recommendation or "maybe"
        _summary = result.get("summary", "")
        _cand_name = candidate.name
        _cand_email = candidate.email
        _cand_id = candidate.id
        _job_title = job.title
        _company_id = job.company_id

        def _notify_telegram():
            try:
                from app.services.telegram import notify_interview_complete
                from app.core.config import settings as cfg
                from app.core.db import SessionLocal as SL
                from app.models.models import Company as CompanyModel
                _dbt = SL()
                try:
                    _co = _dbt.query(CompanyModel).filter(CompanyModel.id == _company_id).first()
                    notify_interview_complete(
                        candidate_name=_cand_name,
                        job_title=_job_title,
                        score=_overall,
                        recommendation=_rec,
                        summary=_summary,
                        frontend_url=cfg.FRONTEND_URL,
                        candidate_id=_cand_id,
                        company=_co,
                    )
                finally:
                    _dbt.close()
            except Exception as tg_err:
                logger.warning(f"Telegram уведомление не отправлено: {tg_err}")

        def _notify_email():
            try:
                from app.services.email import notify_interview_result
                from app.core.db import SessionLocal as SL
                from app.models.models import Company as CompanyModel
                _dbe = SL()
                try:
                    _co = _dbe.query(CompanyModel).filter(CompanyModel.id == _company_id).first()
                    if _co:
                        notify_interview_result(
                            candidate_name=_cand_name,
                            candidate_email=_cand_email,
                            job_title=_job_title,
                            score=_overall,
                            recommendation=_rec,
                            summary=_summary,
                            hr_email=_co.email,
                            candidate_id=_cand_id,
                        )
                finally:
                    _dbe.close()
            except Exception as email_err:
                logger.warning(f"Email уведомление не отправлено: {email_err}")

        _run_parallel({"telegram": _notify_telegram, "email": _notify_email})

        # D2 — webhooks: уведомляем внешние интеграции (best-effort, не блокируем).
        # Ленивый импорт — чтобы избежать циклических зависимостей.
        try:
            from app.services import webhook_service

            _scored_payload = {
                "candidate_id": _cand_id,
                "job_id": job.id,
                "name": _cand_name,
                "email": _cand_email,
                "overall_score": candidate.score,
                "recommendation": candidate.recommendation,
                "confidence": candidate.confidence,
                "requires_manual_review": bool(candidate.requires_manual_review),
            }
            webhook_service.dispatch_event(db, _company_id, "candidate.scored", _scored_payload)
            webhook_service.dispatch_event(
                db,
                _company_id,
                "interview.completed",
                {
                    "interview_id": interview.id,
                    "candidate_id": _cand_id,
                    "job_id": job.id,
                    "status": "completed",
                },
            )
        except Exception as wh_err:
            logger.warning(f"Webhook dispatch не выполнен: {wh_err}")

    except Exception as e:
        logger.error(f"Ошибка скоринга: {e}")
        # 1.3 — при любой ошибке скоринга (невалидный/непарсируемый ответ LLM)
        # не доверяем автоматике: помечаем кандидата на ручную проверку HR.
        candidate.requires_manual_review = True
        candidate.status = CandidateStatus.completed
        db.commit()
