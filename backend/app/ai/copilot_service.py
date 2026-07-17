"""AI-copilot для HR (C4): чат по базе кандидатов на естественном языке.

HR пишет запрос («топ-5 на бэкенд с FastAPI», «кто прошёл интервью без anti-cheat
флагов»), сервис собирает компактный контекст кандидатов ЭТОЙ компании, отдаёт его
LLM вместе с вопросом и возвращает текстовый ответ + id упомянутых кандидатов
(чтобы фронт сделал кликабельные ссылки).

Подход — context-stuffing с лимитом: кандидаты уже отскорены и с summary, поэтому
в контекст идёт компактная таблица, а не сырые резюме. Это даёт семантику
(«кто знает FastAPI») из коробки. При большой базе список усечён до самых
свежих/высокооценённых — усечение честно проговаривается в ответе.
"""
import logging
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.prompts import (
    COPILOT_NO_TRUNCATION_NOTE,
    COPILOT_REFS_MARKER,
    COPILOT_SYSTEM_PROMPT,
    COPILOT_TRUNCATION_NOTE,
)
from app.models.models import Candidate, Job

logger = logging.getLogger(__name__)

# Потолок кандидатов в контексте LLM. Кандидаты компактны (одна строка каждый),
# поэтому лимит щедрый; при превышении усекаем по score/дате и сообщаем об этом.
MAX_CANDIDATES_IN_CONTEXT = 150
# Ограничение сниппета резюме, чтобы не раздувать контекст.
RESUME_SNIPPET_CHARS = 300
# Лимит истории диалога (пар «вопрос-ответ»), которую передаём в LLM.
MAX_HISTORY_MESSAGES = 6


def _call_copilot_llm(messages: list, system: str, temperature: float = 0.3) -> str:
    """Вызов LLM через единый диспетчер (Claude основной, Groq fallback).

    Отдельная обёртка — чтобы в тестах мокать именно copilot, не задевая
    interview_service._call_groq.
    """
    from app.ai.llm import call_llm

    return call_llm(messages, system, temperature=temperature)


def _fmt_score(value) -> str:
    return "—" if value is None else str(int(value)) if float(value).is_integer() else f"{value:.1f}"


def _candidate_line(c: Candidate) -> str:
    """Одна компактная строка кандидата для контекста LLM."""
    job_title = c.job.title if c.job else "?"
    parts = [
        f"#{c.id}",
        f"name={c.name}",
        f"job={job_title}",
        f"status={c.status.value}",
        f"score={_fmt_score(c.score)}",
    ]
    if c.recommendation:
        parts.append(f"rec={c.recommendation}")
    # Под-оценки только если есть
    sub = []
    if c.technical_score is not None:
        sub.append(f"tech={c.technical_score}")
    if c.soft_skills_score is not None:
        sub.append(f"soft={c.soft_skills_score}")
    if c.experience_score is not None:
        sub.append(f"exp={c.experience_score}")
    if c.motivation_score is not None:
        sub.append(f"mot={c.motivation_score}")
    if sub:
        parts.append("(" + " ".join(sub) + ")")
    if c.anti_cheat_score is not None and c.anti_cheat_score >= 40:
        parts.append(f"anti_cheat={_fmt_score(c.anti_cheat_score)}")
    if c.bias_flags:
        parts.append("bias_flagged")

    line = " | ".join(parts)

    summary = (c.summary or "").strip()
    if summary:
        line += f"\n  summary: {summary}"
    resume = (c.resume_text or "").strip()
    if resume:
        snippet = resume[:RESUME_SNIPPET_CHARS].replace("\n", " ")
        line += f"\n  resume: {snippet}"
    return line


def _load_candidates(company_id: int, db: Session) -> tuple[list[Candidate], bool]:
    """Кандидаты компании, отсортированные по score/дате, с флагом усечения."""
    query = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Job.company_id == company_id)
        .order_by(Candidate.score.desc().nullslast(), Candidate.created_at.desc())
    )
    total = query.count()
    candidates = query.limit(MAX_CANDIDATES_IN_CONTEXT).all()
    truncated = total > MAX_CANDIDATES_IN_CONTEXT
    return candidates, truncated


def _build_context_block(candidates: list[Candidate]) -> str:
    return "\n".join(_candidate_line(c) for c in candidates)


def _parse_response(raw: str) -> tuple[str, list[int]]:
    """Отделяет текст ответа от машинного маркера с id упомянутых кандидатов."""
    idx = raw.rfind(COPILOT_REFS_MARKER)
    if idx == -1:
        return raw.strip(), []
    answer = raw[:idx].strip()
    refs_part = raw[idx + len(COPILOT_REFS_MARKER):].strip()
    ids: list[int] = []
    for token in re.split(r"[,\s]+", refs_part):
        token = token.strip().lstrip("#")
        if token.isdigit():
            ids.append(int(token))
    # dedup, сохраняя порядок
    seen: set[int] = set()
    unique = [i for i in ids if not (i in seen or seen.add(i))]
    return answer, unique


def _build_chat_messages(history: Optional[list[dict]], user_message: str) -> list[dict]:
    """История диалога + текущий вопрос в формате чата LLM."""
    messages: list[dict] = []
    if history:
        for item in history[-MAX_HISTORY_MESSAGES:]:
            role = item.get("role")
            content = (item.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages


def ask_copilot(
    company_id: int,
    user_message: str,
    db: Session,
    history: Optional[list[dict]] = None,
) -> dict:
    """Отвечает на запрос HR по базе кандидатов компании.

    Returns:
        {"answer": str, "referenced_candidate_ids": list[int], "candidates_analyzed": int}
    """
    candidates, truncated = _load_candidates(company_id, db)

    # Пустая база — не тратим LLM-вызов.
    if not candidates:
        return {
            "answer": "",
            "referenced_candidate_ids": [],
            "candidates_analyzed": 0,
        }

    system = COPILOT_SYSTEM_PROMPT.format(
        candidates_block=_build_context_block(candidates),
        truncation_note=COPILOT_TRUNCATION_NOTE if truncated else COPILOT_NO_TRUNCATION_NOTE,
        marker=COPILOT_REFS_MARKER,
    )
    chat_messages = _build_chat_messages(history, user_message)

    raw = _call_copilot_llm(chat_messages, system, temperature=0.3)
    answer, ref_ids = _parse_response(raw)

    # Оставляем только id, реально принадлежащие загруженному контексту компании —
    # защита от галлюцинации несуществующего/чужого кандидата.
    valid_ids = {c.id for c in candidates}
    referenced = [i for i in ref_ids if i in valid_ids]

    logger.info(
        f"Copilot company #{company_id}: analyzed={len(candidates)} "
        f"truncated={truncated} referenced={len(referenced)}"
    )
    return {
        "answer": answer,
        "referenced_candidate_ids": referenced,
        "candidates_analyzed": len(candidates),
    }
