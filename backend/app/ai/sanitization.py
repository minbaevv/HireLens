"""Защита LLM-слоя: SEC-8 (prompt injection) и SEC-15 (PII redaction).

Пользовательский текст (резюме, ответы кандидата) НИКОГДА не должен трактоваться
моделью как инструкция. Здесь — детектор попыток инъекции, обёртка данных в
делимитеры и маскирование персональных данных перед отправкой в лог/LLM.
"""
import re

# --- SEC-8: детектор prompt injection (RU/EN) ---
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(the\s+)?previous\s+instructions",
    r"disregard\s+(the\s+)?(above|previous|prior)",
    r"forget\s+(everything|all|previous|the\s+above)",
    r"you\s+are\s+now\s+",
    r"new\s+instructions?\s*:",
    r"system\s+prompt",
    r"act\s+as\s+(a|an)\s+",
    r"set\s+(the\s+)?(score|rating)\s+to\s+100",
    r"give\s+(me\s+)?(a\s+)?(score|rating)\s+of\s+100",
    r"игнорир\w*\s+(все\s+|всех\s+)?(предыдущие|прошлые)",
    r"забудь\s+(все|всё|предыдущие|инструкции)",
    r"ты\s+теперь\s+",
    r"нов\w*\s+инструкци\w*",
    r"поставь\s+(оценку\s+)?100",
    r"систем\w*\s+промпт",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

DATA_START = "<<<CANDIDATE_DATA_START>>>"
DATA_END = "<<<CANDIDATE_DATA_END>>>"

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\-\(\) ]{7,}\d)(?!\d)")


def detect_injection(text: str | None) -> bool:
    """True, если в тексте есть похожая на prompt-injection инструкция."""
    if not text:
        return False
    return bool(_INJECTION_RE.search(text))


def wrap_untrusted(text: str | None) -> str:
    """Оборачивает недоверенный пользовательский текст в делимитеры (SEC-8).

    Любые делимитеры внутри самого текста нейтрализуются, чтобы кандидат не мог
    подделать закрывающий маркер и «выйти» из блока данных.
    """
    safe = (text or "").replace(DATA_START, "[...]").replace(DATA_END, "[...]")
    return f"{DATA_START}\n{safe}\n{DATA_END}"


def redact_pii(text: str | None) -> str:
    """SEC-15: маскирует email и телефоны (для транскрипта скоринга и логов)."""
    if not text:
        return text or ""
    text = _EMAIL_RE.sub("[email]", text)
    text = _PHONE_RE.sub("[phone]", text)
    return text
