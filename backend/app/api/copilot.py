"""AI-copilot для HR (C4): чат по базе кандидатов на естественном языке."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.ai.copilot_service import ask_copilot
from app.api.deps import get_current_company
from app.api.schemas import CopilotReferencedCandidate, CopilotRequest, CopilotResponse
from app.core.db import get_db
from app.core.limiter import limiter
from app.models.models import Candidate, Company, Job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/copilot", tags=["copilot"])

# Ответ при пустой базе — без вызова LLM.
EMPTY_DB_ANSWER = (
    "Пока нет ни одного кандидата, о котором можно рассказать. "
    "Опубликуйте вакансию и получите первые заявки — тогда я помогу их анализировать."
)


@router.post(
    "/chat",
    response_model=CopilotResponse,
    summary="Спросить AI-copilot о кандидатах",
)
@limiter.limit("20/minute")
def chat(
    request: Request,
    body: CopilotRequest,
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company),
) -> CopilotResponse:
    """HR задаёт вопрос на естественном языке — copilot отвечает по базе кандидатов
    ЭТОЙ компании (напр. «топ-5 на бэкенд с FastAPI»)."""
    history = [m.model_dump() for m in body.history] if body.history else None

    try:
        result = ask_copilot(
            company_id=current_company.id,
            user_message=body.message,
            db=db,
            history=history,
        )
    except RuntimeError as e:
        logger.error(f"Copilot LLM ошибка: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI сервис недоступен",
        )

    if result["candidates_analyzed"] == 0:
        return CopilotResponse(answer=EMPTY_DB_ANSWER, referenced_candidates=[], candidates_analyzed=0)

    # Подтягиваем имена/скор для упомянутых кандидатов (кликабельные чипы во фронте)
    referenced: list[CopilotReferencedCandidate] = []
    ref_ids = result["referenced_candidate_ids"]
    if ref_ids:
        rows = (
            db.query(Candidate)
            .join(Job, Candidate.job_id == Job.id)
            .filter(Candidate.id.in_(ref_ids), Job.company_id == current_company.id)
            .all()
        )
        by_id = {c.id: c for c in rows}
        # Сохраняем порядок, в котором их упомянул copilot
        for cid in ref_ids:
            c = by_id.get(cid)
            if c:
                referenced.append(
                    CopilotReferencedCandidate(
                        id=c.id, name=c.name, score=c.score, recommendation=c.recommendation
                    )
                )

    return CopilotResponse(
        answer=result["answer"],
        referenced_candidates=referenced,
        candidates_analyzed=result["candidates_analyzed"],
    )
