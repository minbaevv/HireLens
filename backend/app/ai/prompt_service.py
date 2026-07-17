"""Prompt Versioning (Roadmap 6.2).

Слой между статичными code-default промптами (app.ai.prompts) и версиями
в БД (таблица prompt_templates). Логика:

1. Если для (company_id, prompt_key) есть активные версии — берём их;
   при нескольких активных — A/B: случайный выбор по весу ab_weight.
2. Иначе (нет строк / база недоступна / ошибка) — fallback на code-default.

Это гарантирует полную обратную совместимость: без записей в БД поведение
идентично старому.
"""
import logging
import random
from string import Formatter
from typing import Optional

from sqlalchemy.orm import Session

from app.ai.prompts import (
    INTERVIEW_SYSTEM_PROMPT,
    PRE_SCREENING_PROMPT,
    SCORING_SYSTEM_PROMPT,
)
from app.models.prompt_template import PromptTemplate

logger = logging.getLogger(__name__)


class PromptKeyInfo:
    """Метаданные о редактируемом промпте."""

    def __init__(self, key: str, label: str, default: str, required: set[str]):
        self.key = key
        self.label = label
        self.default = default
        self.required = required


# Реестр редактируемых промптов. required — обязательные {placeholders}:
# если в кастомном тексте их нет или есть лишние — .format() упадёт,
# поэтому валидируем контент при создании версии.
PROMPT_KEYS: dict[str, PromptKeyInfo] = {
    "interview_system": PromptKeyInfo(
        "interview_system",
        "Системный промпт интервью",
        INTERVIEW_SYSTEM_PROMPT,
        {
            "data_handling_rule",
            "job_title",
            "job_requirements",
            "resume_text",
            "interview_language",
            "min_questions",
            "max_questions",
        },
    ),
    "scoring_system": PromptKeyInfo(
        "scoring_system",
        "Промпт скоринга",
        SCORING_SYSTEM_PROMPT,
        {
            "data_handling_rule",
            "job_title",
            "job_requirements",
            "transcript",
            "interview_language",
            "schema",
        },
    ),
    "prescreen": PromptKeyInfo(
        "prescreen",
        "Промпт скрининга резюме",
        PRE_SCREENING_PROMPT,
        {
            "data_handling_rule",
            "job_title",
            "job_requirements",
            "resume_text",
            "interview_language",
            "schema",
        },
    ),
}


def is_valid_key(key: str) -> bool:
    return key in PROMPT_KEYS


def default_content(key: str) -> str:
    return PROMPT_KEYS[key].default


def _placeholders(text: str) -> set[str]:
    """Имена всех {placeholders} в шаблоне (без позиционных/пустых)."""
    names: set[str] = set()
    for _, field_name, _, _ in Formatter().parse(text):
        if field_name:
            # берём только корень имени (name.attr / name[idx] -> name)
            root = field_name.replace("[", ".").split(".")[0]
            names.add(root)
    return names


def validate_content(key: str, content: str) -> tuple[bool, str]:
    """Проверяет, что кастомный промпт совместим с .format().

    Возвращает (ok, сообщение). Правила:
    - нет неизвестных {placeholders} (иначе KeyError при формате);
    - все обязательные placeholders присутствуют (иначе данные не попадут в промпт);
    - текст не пустой.
    """
    if not is_valid_key(key):
        return False, f"Неизвестный ключ промпта: {key}"
    if not content or not content.strip():
        return False, "Пустой текст промпта"
    try:
        found = _placeholders(content)
    except ValueError as e:
        return False, f"Некорректный шаблон (проверьте фигурные скобки): {e}"
    required = PROMPT_KEYS[key].required
    missing = required - found
    if missing:
        return False, "Отсутствуют обязательные подстановки: " + ", ".join(
            "{" + m + "}" for m in sorted(missing)
        )
    unknown = found - required
    if unknown:
        return False, "Недопустимые подстановки (будет ошибка формата): " + ", ".join(
            "{" + u + "}" for u in sorted(unknown)
        )
    return True, "ok"


def resolve_prompt(db: Optional[Session], company_id: Optional[int], key: str) -> str:
    """Возвращает текст промпта для компании с fallback на code-default.

    Никогда не бросает: любая ошибка БД — это fallback на статичный промпт.
    """
    default = PROMPT_KEYS[key].default if key in PROMPT_KEYS else ""
    if not key in PROMPT_KEYS:
        raise KeyError(f"Неизвестный ключ промпта: {key}")
    if db is None or company_id is None:
        return default
    try:
        active = (
            db.query(PromptTemplate)
            .filter(
                PromptTemplate.company_id == company_id,
                PromptTemplate.prompt_key == key,
                PromptTemplate.is_active.is_(True),
            )
            .all()
        )
    except Exception as e:  # таблицы нет / БД недоступна
        logger.warning("resolve_prompt(%s) fallback на default: %s", key, e)
        return default

    if not active:
        return default
    if len(active) == 1:
        return active[0].content or default

    # A/B: взвешенный случайный выбор
    weights = [max(1, int(pt.ab_weight or 1)) for pt in active]
    chosen = random.choices(active, weights=weights, k=1)[0]
    return chosen.content or default


# --- CRUD-хелперы для админ-API ---

def list_versions(db: Session, company_id: int, key: str) -> list[PromptTemplate]:
    return (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.company_id == company_id,
            PromptTemplate.prompt_key == key,
        )
        .order_by(PromptTemplate.version.desc())
        .all()
    )


def _next_version(db: Session, company_id: int, key: str) -> int:
    last = (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.company_id == company_id,
            PromptTemplate.prompt_key == key,
        )
        .order_by(PromptTemplate.version.desc())
        .first()
    )
    return (last.version + 1) if last else 1


def create_version(
    db: Session,
    company_id: int,
    key: str,
    content: str,
    name: Optional[str] = None,
    activate: bool = False,
    created_by_email: Optional[str] = None,
) -> PromptTemplate:
    """Создаёт новую версию. При activate=True делает её единственной активной."""
    ok, msg = validate_content(key, content)
    if not ok:
        raise ValueError(msg)
    version = _next_version(db, company_id, key)
    pt = PromptTemplate(
        company_id=company_id,
        prompt_key=key,
        version=version,
        name=name,
        content=content,
        is_active=False,
        ab_weight=1,
        created_by_email=created_by_email,
    )
    db.add(pt)
    db.commit()
    db.refresh(pt)
    if activate:
        activate_version(db, company_id, key, pt.id)
        db.refresh(pt)
    return pt


def activate_version(db: Session, company_id: int, key: str, version_id: int) -> PromptTemplate:
    """Делает версию единственной активной (выключает остальные, сбрасывает A/B)."""
    target = _get_owned(db, company_id, key, version_id)
    for pt in list_versions(db, company_id, key):
        pt.is_active = pt.id == version_id
        pt.ab_weight = 1
    db.commit()
    db.refresh(target)
    return target


def set_ab_weights(db: Session, company_id: int, key: str, weights: dict[int, int]) -> list[PromptTemplate]:
    """A/B: делает активными указанные версии с весами, остальные — неактивны.

    weights: {version_id: weight>0}. Нужно е2 версий, иначе это обычная активация.
    """
    valid = {vid: int(w) for vid, w in weights.items() if int(w) > 0}
    if not valid:
        raise ValueError("Нужен хотя бы один положительный вес")
    owned = {pt.id: pt for pt in list_versions(db, company_id, key)}
    for vid in valid:
        if vid not in owned:
            raise ValueError(f"Версия #{vid} не найдена для ключа {key}")
    for pt in owned.values():
        if pt.id in valid:
            pt.is_active = True
            pt.ab_weight = valid[pt.id]
        else:
            pt.is_active = False
            pt.ab_weight = 1
    db.commit()
    return list_versions(db, company_id, key)


def delete_version(db: Session, company_id: int, key: str, version_id: int) -> None:
    target = _get_owned(db, company_id, key, version_id)
    db.delete(target)
    db.commit()


def _get_owned(db: Session, company_id: int, key: str, version_id: int) -> PromptTemplate:
    pt = (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.id == version_id,
            PromptTemplate.company_id == company_id,
            PromptTemplate.prompt_key == key,
        )
        .first()
    )
    if pt is None:
        raise ValueError(f"Версия #{version_id} не найдена")
    return pt
