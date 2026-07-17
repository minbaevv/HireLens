"""Админ-API управления версиями промптов (Roadmap 6.2 — Prompt Versioning).

Позволяет владельцу/админу компании просматривать code-default, создавать
собственные версии промптов, активировать их и запускать A/B-тест — без деплоя.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai import prompt_service
from app.api.deps import CurrentActor, require_admin
from app.core.audit import actor_fields, record_audit
from app.core.db import get_db
from app.models.prompt_template import PromptTemplate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/prompts", tags=["prompts"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PromptKeyOut(BaseModel):
    key: str
    label: str
    default_content: str
    required_placeholders: list[str]
    active_versions: int


class PromptVersionOut(BaseModel):
    id: int
    prompt_key: str
    version: int
    name: Optional[str]
    content: str
    is_active: bool
    ab_weight: int
    created_by_email: Optional[str]

    @classmethod
    def of(cls, pt: PromptTemplate) -> "PromptVersionOut":
        return cls(
            id=pt.id,
            prompt_key=pt.prompt_key,
            version=pt.version,
            name=pt.name,
            content=pt.content,
            is_active=pt.is_active,
            ab_weight=pt.ab_weight,
            created_by_email=pt.created_by_email,
        )


class CreateVersionIn(BaseModel):
    content: str = Field(..., min_length=1)
    name: Optional[str] = Field(default=None, max_length=255)
    activate: bool = False


class AbWeightsIn(BaseModel):
    weights: dict[int, int] = Field(..., description="{version_id: вес>0} — минимум 2 версии")


class ValidateIn(BaseModel):
    content: str


class ValidateOut(BaseModel):
    ok: bool
    message: str


def _require_key(key: str) -> None:
    if not prompt_service.is_valid_key(key):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Неизвестный ключ промпта: {key}",
        )


# ---------------------------------------------------------------------------
# Endpoints (только admin/owner)
# ---------------------------------------------------------------------------

@router.get("/keys", response_model=list[PromptKeyOut], summary="Список редактируемых промптов")
def list_keys(
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> list[PromptKeyOut]:
    company_id = actor.company.id
    out: list[PromptKeyOut] = []
    for key, info in prompt_service.PROMPT_KEYS.items():
        active = (
            db.query(PromptTemplate)
            .filter(
                PromptTemplate.company_id == company_id,
                PromptTemplate.prompt_key == key,
                PromptTemplate.is_active.is_(True),
            )
            .count()
        )
        out.append(
            PromptKeyOut(
                key=key,
                label=info.label,
                default_content=info.default,
                required_placeholders=sorted(info.required),
                active_versions=active,
            )
        )
    return out


@router.get("/{key}", response_model=list[PromptVersionOut], summary="Версии промпта")
def list_versions(
    key: str,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> list[PromptVersionOut]:
    _require_key(key)
    versions = prompt_service.list_versions(db, actor.company.id, key)
    return [PromptVersionOut.of(pt) for pt in versions]


@router.post("/{key}/validate", response_model=ValidateOut, summary="Проверить текст промпта")
def validate(
    key: str,
    body: ValidateIn,
    actor: CurrentActor = Depends(require_admin),
) -> ValidateOut:
    _require_key(key)
    ok, message = prompt_service.validate_content(key, body.content)
    return ValidateOut(ok=ok, message=message)


@router.post(
    "/{key}",
    response_model=PromptVersionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую версию промпта",
)
def create_version(
    key: str,
    body: CreateVersionIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> PromptVersionOut:
    _require_key(key)
    try:
        pt = prompt_service.create_version(
            db,
            actor.company.id,
            key,
            content=body.content,
            name=body.name,
            activate=body.activate,
            created_by_email=actor.company.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    record_audit(
        db,
        company_id=actor.company.id,
        action="prompt.create_version",
        entity_type="prompt_template",
        entity_id=pt.id,
        detail={"key": key, "version": pt.version, "activated": body.activate},
        request=request,
        **actor_fields(actor),
    )
    return PromptVersionOut.of(pt)


@router.post(
    "/{key}/{version_id}/activate",
    response_model=PromptVersionOut,
    summary="Сделать версию единственной активной",
)
def activate_version(
    key: str,
    version_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> PromptVersionOut:
    _require_key(key)
    try:
        pt = prompt_service.activate_version(db, actor.company.id, key, version_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    record_audit(
        db,
        company_id=actor.company.id,
        action="prompt.activate",
        entity_type="prompt_template",
        entity_id=pt.id,
        detail={"key": key, "version": pt.version},
        request=request,
        **actor_fields(actor),
    )
    return PromptVersionOut.of(pt)


@router.post(
    "/{key}/ab",
    response_model=list[PromptVersionOut],
    summary="Запустить A/B-тест между версиями",
)
def set_ab(
    key: str,
    body: AbWeightsIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> list[PromptVersionOut]:
    _require_key(key)
    try:
        versions = prompt_service.set_ab_weights(db, actor.company.id, key, body.weights)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    record_audit(
        db,
        company_id=actor.company.id,
        action="prompt.ab_test",
        entity_type="prompt_template",
        detail={"key": key, "weights": body.weights},
        request=request,
        **actor_fields(actor),
    )
    return [PromptVersionOut.of(pt) for pt in versions]


@router.delete(
    "/{key}/{version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить версию промпта",
)
def delete_version(
    key: str,
    version_id: int,
    request: Request,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> None:
    _require_key(key)
    try:
        prompt_service.delete_version(db, actor.company.id, key, version_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    record_audit(
        db,
        company_id=actor.company.id,
        action="prompt.delete_version",
        entity_type="prompt_template",
        entity_id=version_id,
        detail={"key": key},
        request=request,
        **actor_fields(actor),
    )
