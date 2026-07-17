"""Единая точка вызова LLM: Claude (основной) + Groq (fallback).

Порядок провайдеров определяется settings.AI_PROVIDER:
- "claude" — сначала Claude, при недоступности — Groq
- "groq" (default, dev/тесты) — сначала Groq, при недоступности — Claude

Каждый провайдер вызывается с retry (exponential backoff, до 3 попыток).
"""

import logging
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2  # секунды, умножается на номер попытки
DEFAULT_MAX_TOKENS = 1024
REQUEST_TIMEOUT = 30


def _call_claude(messages: list, system: str, temperature: float, max_tokens: int) -> str:
    """Один вызов Anthropic Claude API (без retry — retry в call_llm)."""
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=REQUEST_TIMEOUT)
    # Claude требует минимум одно user-сообщение
    chat = messages or [{"role": "user", "content": "Начинаем."}]
    # Prompt caching (Roadmap P1): системный промпт одинаков для всех кандидатов
    # одной вакансии → cache_control экономит ~50% стоимости и ~30% latency.
    system_blocks = [
        {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
    ]
    response = client.messages.create(
        model=settings.CLAUDE_MODEL,
        system=system_blocks,
        messages=chat,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.content[0].text.strip()


def _call_groq(messages: list, system: str, temperature: float, max_tokens: int) -> str:
    """Один вызов Groq API (без retry — retry в call_llm)."""
    from groq import Groq

    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "system", "content": system}] + (messages or []),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=REQUEST_TIMEOUT,
    )
    return response.choices[0].message.content.strip()


def _providers_in_order() -> list[tuple]:
    """Список доступных провайдеров в порядке приоритета."""
    claude = ("claude", _call_claude) if settings.ANTHROPIC_API_KEY else None
    groq = ("groq", _call_groq) if settings.GROQ_API_KEY else None

    if settings.AI_PROVIDER == "claude":
        ordered = [claude, groq]
    else:
        ordered = [groq, claude]
    return [p for p in ordered if p is not None]


def call_llm(
    messages: list,
    system: str,
    temperature: float = 0.7,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> str:
    """Вызывает LLM с retry и автоматическим fallback на резервного провайдера.

    Args:
        messages: История чата [{"role": "user"|"assistant", "content": str}].
        system: Системный промпт.
        temperature: Температура генерации.
        max_tokens: Лимит токенов ответа.

    Returns:
        Текст ответа модели.

    Raises:
        RuntimeError: Если не настроен ни один провайдер или все недоступны.
    """
    providers = _providers_in_order()
    if not providers:
        raise RuntimeError(
            "Не настроен ни один AI-провайдер: задайте ANTHROPIC_API_KEY или GROQ_API_KEY"
        )

    last_error: Exception | None = None
    for name, fn in providers:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return fn(messages, system, temperature, max_tokens)
            except Exception as e:
                last_error = e
                logger.warning(f"{name} API ошибка (attempt {attempt}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
        logger.error(f"Провайдер {name} недоступен после {MAX_RETRIES} попыток, переключаюсь на резервный")

    raise RuntimeError(f"Все AI-провайдеры недоступны. Последняя ошибка: {last_error}")
