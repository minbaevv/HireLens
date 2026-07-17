"""Тесты anti-cheat анализа (C1)."""
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from app.ai.anticheat_service import analyze_interview
from app.models.models import Message, MessageRole


def _msg(role: MessageRole, content: str, created_at: datetime) -> Message:
    m = Message(role=role, content=content)
    m.created_at = created_at
    return m


def test_flags_instant_long_answer():
    """Длинный ответ за 1 секунду — подозрительно."""
    base = datetime.now(UTC)
    messages = [
        _msg(MessageRole.ai, "Расскажите о своём опыте работы с базами данных.", base),
        _msg(
            MessageRole.user,
            "У меня большой опыт работы с PostgreSQL и MySQL включая оптимизацию запросов.",
            base + timedelta(seconds=1),
        ),
    ]
    llm_fn = MagicMock(return_value='{"ai_likelihood": 0, "reasoning": ""}')
    result = analyze_interview(messages, llm_fn=llm_fn)
    assert result["score"] > 0
    assert any("быстрее" in f for f in result["flags"])


def test_no_flags_for_normal_timing():
    """Ответ через 20 секунд на короткий вопрос — норма."""
    base = datetime.now(UTC)
    messages = [
        _msg(MessageRole.ai, "Расскажите о себе.", base),
        _msg(MessageRole.user, "Меня зовут Иван, я бэкенд-разработчик.", base + timedelta(seconds=20)),
    ]
    llm_fn = MagicMock(return_value='{"ai_likelihood": 5, "reasoning": ""}')
    result = analyze_interview(messages, llm_fn=llm_fn)
    assert result["score"] < 10


def test_ai_generated_text_flagged():
    """Высокий ai_likelihood от LLM — попадает в флаги и score."""
    base = datetime.now(UTC)
    messages = [
        _msg(MessageRole.ai, "Расскажите о себе.", base),
        _msg(MessageRole.user, "Я обладаю обширным опытом...", base + timedelta(seconds=30)),
    ]
    llm_fn = MagicMock(
        return_value='{"ai_likelihood": 85, "reasoning": "Слишком гладкий и обезличенный текст"}'
    )
    result = analyze_interview(messages, llm_fn=llm_fn)
    assert result["score"] >= 40
    assert any("AI-детектор" in f for f in result["flags"])


def test_llm_failure_does_not_crash():
    """Ошибка LLM (например, StopIteration от исчерпанного side_effect в других тестах) — не крашит."""
    base = datetime.now(UTC)
    messages = [
        _msg(MessageRole.ai, "Вопрос", base),
        _msg(MessageRole.user, "Ответ", base + timedelta(seconds=10)),
    ]
    llm_fn = MagicMock(side_effect=RuntimeError("no provider"))
    result = analyze_interview(messages, llm_fn=llm_fn)
    assert result["score"] == 0.0
    assert result["flags"] == []


def test_empty_messages():
    """Пустой транскрипт — никаких ошибок, score 0."""
    result = analyze_interview([], llm_fn=MagicMock())
    assert result["score"] == 0.0
    assert result["flags"] == []


def test_paste_signal_flagged():
    """[C1.2] Длинный ответ почти мгновенно — сигнал вставки из буфера."""
    base = datetime.now(UTC)
    long_answer = " ".join(f"навык{i}" for i in range(30))
    messages = [
        _msg(MessageRole.ai, "Опишите ваш опыт подробно.", base),
        _msg(MessageRole.user, long_answer, base + timedelta(seconds=1)),
    ]
    llm_fn = MagicMock(return_value='{"ai_likelihood": 0, "reasoning": ""}')
    result = analyze_interview(messages, llm_fn=llm_fn)
    assert result["risk_level"] == "high"
    assert any("вставк" in f for f in result["flags"])


def test_markdown_formatting_flagged():
    """[C1.2] markdown/списочное форматирование в чат-ответе — признак вставки."""
    base = datetime.now(UTC)
    md_answer = "Мой опыт:\n- проектирование API\n- оптимизация баз данных\n- настройка CI/CD пайплайнов"
    messages = [
        _msg(MessageRole.ai, "Расскажите о своём опыте.", base),
        _msg(MessageRole.user, md_answer, base + timedelta(seconds=40)),
    ]
    llm_fn = MagicMock(return_value='{"ai_likelihood": 0, "reasoning": ""}')
    result = analyze_interview(messages, llm_fn=llm_fn)
    assert any("markdown" in f for f in result["flags"])


def test_similar_answers_flagged():
    """[C1.2] Почти дословно совпадающие ответы — шаблон/дубликат."""
    base = datetime.now(UTC)
    dup = "Я решаю задачи системно анализирую требования проектирую решение и довожу его до продакшена стабильно"
    messages = [
        _msg(MessageRole.ai, "Первый вопрос?", base),
        _msg(MessageRole.user, dup, base + timedelta(seconds=40)),
        _msg(MessageRole.ai, "Второй вопрос?", base + timedelta(seconds=60)),
        _msg(MessageRole.user, dup, base + timedelta(seconds=120)),
    ]
    llm_fn = MagicMock(return_value='{"ai_likelihood": 0, "reasoning": ""}')
    result = analyze_interview(messages, llm_fn=llm_fn)
    assert any("совпадают" in f for f in result["flags"])
    assert result["risk_level"] in ("medium", "high")


def test_result_has_risk_level_and_signals():
    """[C1.2] Результат содержит risk_level и разбивку сигналов."""
    base = datetime.now(UTC)
    messages = [
        _msg(MessageRole.ai, "Расскажите о себе.", base),
        _msg(MessageRole.user, "Меня зовут Иван, я бэкенд-разработчик.", base + timedelta(seconds=20)),
    ]
    result = analyze_interview(
        messages, llm_fn=MagicMock(return_value='{"ai_likelihood": 5, "reasoning": ""}')
    )
    assert result["risk_level"] == "low"
    assert set(result["signals"]) == {"timing", "ai_text", "paste", "duplication"}
    assert result["flags"] == []
