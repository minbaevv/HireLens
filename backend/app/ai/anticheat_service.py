"""Anti-cheat анализ AI-интервью (C1 + C1.2 — Anti-cheat 2.0).

Сигналы (все key-free, без внешних сервисов):
1. Скорость ответа относительно его длины (эвристика по Message.created_at).
2. Оценка LLM, насколько ответы похожи на ChatGPT-стиль / copy-paste.
3. [C1.2] Paste/burst: длинный ответ почти мгновенно + markdown/списочное форматирование (типично для вставки).
4. [C1.2] Межвопросная сверка: почти дословно совпадающие ответы (шаблон/дубликаты).

К результату добавлена градация риска (low/medium/high) с пояснением для HR.

⚠️ Честно: это сигнал для ручной проверки HR, а не автоматический вердикт. Любой сигнал
может ошибаться (быстрый наборщик, грамотная речь, повтор терминов — не обязательно читер).
"""
import json
import logging
import re
from typing import Callable, Optional

from app.models.models import Message, MessageRole

logger = logging.getLogger(__name__)

# --- Тайминг (сигнал 1) ---
# Сколько секунд "на слово" ожидаем от живого человека при наборе с обдумыванием.
# 0.15 — намеренно мягкий порог, чтобы не давать ложных срабатываний на быстро печатающих.
MIN_SECONDS_PER_WORD = 0.15
MIN_WORDS_TO_FLAG = 8

# --- Paste/burst (сигнал 3, C1.2) ---
# Длинный ответ, появившийся почти мгновенно, — очень вероятно вставка из буфера.
# Строгий высокоточный порог (отдельно от градуированного тайминга).
PASTE_MIN_WORDS = 25
PASTE_MAX_SECONDS = 3.0

# --- Межвопросная сверка (сигнал 4, C1.2) ---
DUP_SIMILARITY_THRESHOLD = 0.6  # доля общих 3-грамм между двумя ответами
DUP_MIN_WORDS = 12  # сравниваем только содержательные ответы

# --- Веса сигналов ---
# Базовый скор (timing + LLM) сохранён как был (обратная совместимость),
# новые сигналы добавляются сверху (с ограничением 100).
TIMING_WEIGHT = 0.4
AI_TEXT_WEIGHT = 0.6
PASTE_WEIGHT = 0.5
DUP_WEIGHT = 0.4

# --- Градация риска ---
RISK_LOW_MAX = 25.0   # < 25 → low
RISK_MEDIUM_MAX = 60.0  # 25..60 → medium, >= 60 → high

LlmFn = Callable[..., str]

# markdown/списочные артефакты, типичные для вставки из ChatGPT/документа
_FORMAT_PATTERNS = [
    re.compile(r"^\s*[-*\u2022]\s+", re.MULTILINE),   # маркированный список
    re.compile(r"^\s*\d+[.)]\s+", re.MULTILINE),        # нумерованный список
    re.compile(r"\*\*[^*]+\*\*"),                        # **жирный**
    re.compile(r"^#{1,6}\s+", re.MULTILINE),             # заголовки
]


def _default_llm_fn(messages: list, system: str, temperature: float = 0.1) -> str:
    from app.ai.llm import call_llm
    return call_llm(messages, system, temperature=temperature)


def _answer_pairs(messages: list[Message]):
    """Генератор пар (ответ_кандидата, delta_сек) — delta от предыдущего AI-вопроса.

    delta = None, если тайминг недоступен.
    """
    prev_ai: Optional[Message] = None
    for msg in messages:
        if msg.role == MessageRole.ai:
            prev_ai = msg
            continue
        if msg.role == MessageRole.user:
            delta = None
            if prev_ai is not None and prev_ai.created_at and msg.created_at:
                delta = (msg.created_at - prev_ai.created_at).total_seconds()
            yield msg, delta
            prev_ai = None


def _analyze_response_timing(messages: list[Message]) -> tuple[list[str], float]:
    """Ищет ответы, набранные подозрительно быстро для их длины."""
    flags: list[str] = []
    total_pairs = 0
    suspicious = 0

    for msg, delta in _answer_pairs(messages):
        if delta is None:
            continue
        total_pairs += 1
        word_count = len(msg.content.split())
        if word_count >= MIN_WORDS_TO_FLAG and 0 <= delta < word_count * MIN_SECONDS_PER_WORD:
            suspicious += 1
            flags.append(
                f"Ответ из {word_count} слов дан за {delta:.1f} сек — быстрее обычной скорости печати"
            )

    score = round((suspicious / total_pairs) * 100, 1) if total_pairs else 0.0
    return flags, score


def _has_format_artifacts(text: str) -> bool:
    """markdown/списочное форматирование внутри чат-ответа — признак вставки."""
    return any(p.search(text) for p in _FORMAT_PATTERNS)


def _analyze_paste_signals(messages: list[Message]) -> tuple[list[str], float]:
    """[C1.2] Paste/burst: длинный ответ почти мгновенно или с markdown-разметкой."""
    flags: list[str] = []
    total = 0
    suspicious = 0

    for idx, (msg, delta) in enumerate(_answer_pairs(messages), start=1):
        total += 1
        word_count = len(msg.content.split())
        flagged = False

        if (
            delta is not None
            and word_count >= PASTE_MIN_WORDS
            and 0 <= delta < PASTE_MAX_SECONDS
        ):
            flags.append(
                f"Ответ #{idx}: {word_count} слов за {delta:.1f} сек — похоже на вставку из буфера"
            )
            flagged = True

        if word_count >= MIN_WORDS_TO_FLAG and _has_format_artifacts(msg.content):
            flags.append(
                f"Ответ #{idx}: markdown/списочное форматирование в чат-ответе — типично для вставки"
            )
            flagged = True

        if flagged:
            suspicious += 1

    score = round((suspicious / total) * 100, 1) if total else 0.0
    return flags, score


def _shingles(text: str, n: int = 3) -> set:
    """Множество n-грамм из слов (нормализация: lower + только буквы/цифры)."""
    words = re.findall(r"\w+", text.lower())
    if len(words) < n:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _analyze_answer_similarity(messages: list[Message]) -> tuple[list[str], float]:
    """[C1.2] Почти дословно совпадающие ответы (шаблон/дубликаты)."""
    substantial = [
        (idx, m.content)
        for idx, m in enumerate(
            (m for m in messages if m.role == MessageRole.user), start=1
        )
        if len(m.content.split()) >= DUP_MIN_WORDS
    ]
    if len(substantial) < 2:
        return [], 0.0

    shingle_sets = [(idx, _shingles(text)) for idx, text in substantial]
    flags: list[str] = []
    max_sim = 0.0
    for i in range(len(shingle_sets)):
        for j in range(i + 1, len(shingle_sets)):
            sim = _jaccard(shingle_sets[i][1], shingle_sets[j][1])
            if sim > max_sim:
                max_sim = sim
            if sim >= DUP_SIMILARITY_THRESHOLD:
                flags.append(
                    f"Ответы #{shingle_sets[i][0]} и #{shingle_sets[j][0]} почти дословно совпадают "
                    f"({sim * 100:.0f}%) — возможен шаблон/копия"
                )

    score = round(max_sim * 100, 1) if flags else 0.0
    return flags, score


def _analyze_ai_generated_text(messages: list[Message], llm_fn: LlmFn) -> tuple[list[str], float]:
    """Просит LLM оценить, насколько ответы кандидата похожи на ChatGPT-стиль."""
    from app.ai.prompts import ANTICHEAT_PROMPT, ANTICHEAT_JSON_SCHEMA, DATA_HANDLING_RULE
    from app.ai.sanitization import wrap_untrusted

    candidate_lines = [m.content for m in messages if m.role == MessageRole.user]
    if not candidate_lines:
        return [], 0.0

    transcript = "\n".join(f"- {line}" for line in candidate_lines)
    prompt = ANTICHEAT_PROMPT.format(
        data_handling_rule=DATA_HANDLING_RULE,
        transcript=wrap_untrusted(transcript[:6000]),
        schema=ANTICHEAT_JSON_SCHEMA,
    )

    try:
        raw = llm_fn([], prompt, temperature=0.1)
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)
        result = json.loads(raw)
        likelihood = float(result.get("ai_likelihood", 0))
        reasoning = (result.get("reasoning") or "").strip()
        flags = [f"AI-детектор: {reasoning}"] if likelihood >= 40 and reasoning else []
        return flags, likelihood
    except Exception as e:
        logger.warning(f"Anti-cheat AI-детектор недоступен: {e}")
        return [], 0.0


def _risk_level(score: float) -> str:
    if score < RISK_LOW_MAX:
        return "low"
    if score < RISK_MEDIUM_MAX:
        return "medium"
    return "high"


_RISK_LABEL = {
    "low": "\U0001F7E2 Риск списывания: низкий",
    "medium": "\U0001F7E1 Риск списывания: средний — рекомендуется ручная проверка",
    "high": "\U0001F534 Риск списывания: высокий — обязательна ручная проверка",
}


def analyze_interview(messages: list[Message], llm_fn: Optional[LlmFn] = None) -> dict:
    """Возвращает {"score", "flags", "risk_level", "signals"}. Чем выше score — тем подозрительнее.

    Базовый скор (timing*0.4 + ai*0.6) сохранён для обратной совместимости; новые
    сигналы (paste/burst и межвопросная сверка) добавляются сверху с ограничением 100.

    Args:
        messages: Все сообщения интервью по порядку.
        llm_fn: Функция вызова LLM вида fn(messages, system, temperature) -> str.
    """
    llm_fn = llm_fn or _default_llm_fn
    timing_flags, timing_score = _analyze_response_timing(messages)
    ai_flags, ai_score = _analyze_ai_generated_text(messages, llm_fn)
    paste_flags, paste_score = _analyze_paste_signals(messages)
    dup_flags, dup_score = _analyze_answer_similarity(messages)

    base = timing_score * TIMING_WEIGHT + ai_score * AI_TEXT_WEIGHT
    extra = paste_score * PASTE_WEIGHT + dup_score * DUP_WEIGHT
    combined = round(min(100.0, base + extra), 1)

    detail_flags = timing_flags + ai_flags + paste_flags + dup_flags
    risk = _risk_level(combined)

    # Сводка риска для HR — только когда есть что показать (есть флаги или риск ≥ medium).
    flags = detail_flags
    if detail_flags or risk != "low":
        flags = [f"{_RISK_LABEL[risk]} (score {combined:.0f})"] + detail_flags

    return {
        "score": combined,
        "flags": flags,
        "risk_level": risk,
        "signals": {
            "timing": timing_score,
            "ai_text": ai_score,
            "paste": paste_score,
            "duplication": dup_score,
        },
    }
