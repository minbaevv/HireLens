"""Best-effort запись в журнал действий (GAP-2)."""
import json
import logging
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def _client_ip(request: Optional[Request]) -> Optional[str]:
    if request is None:
        return None
    try:
        if request.client and request.client.host:
            return request.client.host
    except Exception:
        pass
    return None


def actor_fields(actor) -> dict:
    try:
        if getattr(actor, "team_member", None) is not None:
            tm = actor.team_member
            return {"actor_type": "team_member", "actor_id": tm.id, "actor_email": tm.email}
        company = actor.company
        return {"actor_type": "company", "actor_id": company.id, "actor_email": company.email}
    except Exception:
        return {"actor_type": "unknown"}


def record_audit(
    db: Session,
    *,
    company_id: int,
    action: str,
    actor_type: str = "company",
    actor_id: Optional[int] = None,
    actor_email: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    detail: Optional[dict] = None,
    request: Optional[Request] = None,
) -> None:
    try:
        entry = AuditLog(
            company_id=company_id,
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            actor_email=actor_email,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
            ip_address=_client_ip(request),
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.warning("Не удалось записать audit log (%s): %s", action, e)
        try:
            db.rollback()
        except Exception:
            pass
