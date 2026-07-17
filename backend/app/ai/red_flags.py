"""Нормализация и очистка red flags (Priority 3).

Модель иногда возвращает «пустой» флаг-заглушку вида
{"category": "other", "detail": "Нет значимых красных флагов"} — это НЕ флаг.
Здесь единая логика: отсеиваем шум и приводим категорию к читаемой метке,
чтобы в интерфейсе не было сырых тегов вроде [skill_gap] / [other].
"""
from typing import Optional

# Читаемые метки категорий (RU — дашборд HR)
RED_FLAG_LABELS = {
    "integrity": "Честность",
    "skill_gap": "Пробел в навыках",
    "communication": "Коммуникация",
    "experience_mismatch": "Несоответствие опыта",
    "other": "Прочее",
}

# Маркеры «нет флагов» (ru/en) — если деталь по сути об этом, флаг игнорируем.
# Формулировки специфичные (про «красные флаги/значимое»), чтобы НЕ зацепить
# реальные флаги вроде «нет опыта с CRM».
_NOISE_MARKERS = (
    "нет значим", "значимых красных", "нет красных флаг", "красных флагов нет",
    "отсутствуют красн", "отсутствуют значим", "не выявлено красн", "не выявлено значим",
    "не обнаружено красн", "нет серьёзных", "нет серьезных", "нет замечан", "без красных флаг",
    "no significant", "no red flag", "no major", "none identified", "no concerns",
    "not applicable",
)
_NOISE_EXACT = {"", "-", "\u2014", "n/a", "na", "none", "нет", "нету", "жок"}


def is_noise_detail(detail: str) -> bool:
    """True, если текст по сути означает «флагов нет» (шум)."""
    d = (detail or "").strip().lower()
    if d in _NOISE_EXACT:
        return True
    return any(m in d for m in _NOISE_MARKERS)


def format_red_flag(category: str, detail: str) -> str:
    """«Пробел в навыках: отсутствие знаний о CRM» вместо «[skill_gap] ...»."""
    label = RED_FLAG_LABELS.get((category or "other").strip().lower(), RED_FLAG_LABELS["other"])
    detail = (detail or "").strip()
    return f"{label}: {detail}" if detail else label


def clean_flag_string(flag: str) -> Optional[str]:
    """Очистка УЖЕ сохранённой строки-флага (legacy формат '[category] detail').

    Возвращает читаемую строку или None, если это шум. Не-red-flag строки
    (anti-cheat / penalty) остаются как есть.
    """
    s = (flag or "").strip()
    if not s:
        return None
    category = None
    detail = s
    if s.startswith("[") and "]" in s:
        idx = s.index("]")
        category = s[1:idx].strip()
        detail = s[idx + 1:].strip()
    if category and category.lower() in RED_FLAG_LABELS:
        if is_noise_detail(detail):
            return None
        return format_red_flag(category, detail)
    # не red-flag формат (anti-cheat / penalty) — отсеиваем только явный шум
    if is_noise_detail(s):
        return None
    return s
