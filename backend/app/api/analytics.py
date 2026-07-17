"""Аналитика Dashboard."""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import Integer, case, func
from sqlalchemy.orm import Session

from app.api.deps import CurrentActor, get_current_company, require_admin
from app.api.schemas import AIAccuracyStats
from app.core.db import get_db
from app.models.audit_log import AuditLog
from app.models.models import Candidate, CandidateStatus, Company, Interview, InterviewStatus, Job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class StatusCount(BaseModel):
    status: str
    count: int


class TopJob(BaseModel):
    job_id: int
    title: str
    total_candidates: int
    avg_score: Optional[float]
    hired_count: int


class AnalyticsSummary(BaseModel):
    # Общее
    total_jobs: int
    active_jobs: int
    total_candidates: int
    total_interviews: int
    completed_interviews: int
    # Скоринг
    avg_score: Optional[float]
    hired_count: int
    rejected_count: int
    hire_rate: float  # % нанятых из завершивших интервью
    # Распределение по статусам
    by_status: List[StatusCount]
    # Топ вакансии
    top_jobs: List[TopJob]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Общая аналитика компании",
)
def get_summary(
    job_id: Optional[int] = Query(default=None, description="Фильтр по вакансии"),
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company),
) -> AnalyticsSummary:
    """Статистика по вакансиям, кандидатам, интервью и скорингу."""
    company_id = current_company.id

    # Вакансии
    jobs_q = db.query(Job).filter(Job.company_id == company_id)
    total_jobs = jobs_q.count()
    active_jobs = jobs_q.filter(Job.is_active == True).count()

    # Кандидаты
    cand_q = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Job.company_id == company_id)
    )
    if job_id:
        cand_q = cand_q.filter(Candidate.job_id == job_id)

    total_candidates = cand_q.count()
    hired_count = cand_q.filter(Candidate.status == CandidateStatus.hired).count()
    rejected_count = cand_q.filter(Candidate.status == CandidateStatus.rejected).count()

    avg_score_row = cand_q.filter(Candidate.score.isnot(None)).with_entities(
        func.avg(Candidate.score)
    ).scalar()
    avg_score = round(float(avg_score_row), 1) if avg_score_row else None

    # Интервью
    interview_q = (
        db.query(Interview)
        .join(Candidate, Interview.candidate_id == Candidate.id)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Job.company_id == company_id)
    )
    if job_id:
        interview_q = interview_q.filter(Candidate.job_id == job_id)

    total_interviews = interview_q.count()
    completed_interviews = interview_q.filter(
        Interview.status == InterviewStatus.completed
    ).count()

    # Hire rate = hired / completed_interviews * 100
    hire_rate = round(hired_count / completed_interviews * 100, 1) if completed_interviews > 0 else 0.0

    # Распределение по статусам
    status_rows = (
        db.query(Candidate.status, func.count(Candidate.id))
        .join(Job, Candidate.job_id == Job.id)
        .filter(Job.company_id == company_id)
        .group_by(Candidate.status)
        .all()
    )
    by_status = [StatusCount(status=s.value, count=c) for s, c in status_rows]

    # Топ-5 вакансий по количеству кандидатов
    top_jobs_rows = (
        db.query(
            Job.id,
            Job.title,
            func.count(Candidate.id).label("total"),
            func.avg(Candidate.score).label("avg_score"),
            func.sum(
                case(
                    (Candidate.status == CandidateStatus.hired, 1),
                    else_=0,
                )
            ).label("hired"),
        )
        .join(Candidate, Candidate.job_id == Job.id, isouter=True)
        .filter(Job.company_id == company_id)
        .group_by(Job.id, Job.title)
        .order_by(func.count(Candidate.id).desc())
        .limit(5)
        .all()
    )

    top_jobs = [
        TopJob(
            job_id=row.id,
            title=row.title,
            total_candidates=row.total or 0,
            avg_score=round(float(row.avg_score), 1) if row.avg_score else None,
            hired_count=int(row.hired or 0),
        )
        for row in top_jobs_rows
    ]

    return AnalyticsSummary(
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        total_candidates=total_candidates,
        total_interviews=total_interviews,
        completed_interviews=completed_interviews,
        avg_score=avg_score,
        hired_count=hired_count,
        rejected_count=rejected_count,
        hire_rate=hire_rate,
        by_status=by_status,
        top_jobs=top_jobs,
    )


# ---------------------------------------------------------------------------
# Ground Truth Tracking Analytics (Phase 10/10 - 1.1)
# ---------------------------------------------------------------------------

@router.get(
    "/ai-accuracy",
    response_model=AIAccuracyStats,
    summary="Статистика точности AI рекомендаций",
)
def get_ai_accuracy(
    job_id: Optional[int] = Query(default=None, description="Фильтр по вакансии"),
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company),
) -> AIAccuracyStats:
    """Измеряет реальную точность AI через ground truth.

    Показывает процент правильных AI рекомендаций (hire/maybe/reject)
    на основе финальных решений HR (actual_hire_decision + ai_feedback).
    """
    company_id = current_company.id

    # Кандидаты с feedback от HR
    query = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(
            Job.company_id == company_id,
            Candidate.ai_feedback.isnot(None),  # Только с оценкой HR
        )
    )
    if job_id:
        query = query.filter(Candidate.job_id == job_id)

    candidates = query.all()
    total_with_feedback = len(candidates)

    if total_with_feedback == 0:
        return AIAccuracyStats(
            total_with_feedback=0,
            correct_predictions=0,
            incorrect_predictions=0,
            partial_predictions=0,
            accuracy_rate=0.0,
            breakdown_by_recommendation={},
        )

    # Подсчёт по категориям
    correct = sum(1 for c in candidates if c.ai_feedback == "correct")
    incorrect = sum(1 for c in candidates if c.ai_feedback == "incorrect")
    partial = sum(1 for c in candidates if c.ai_feedback == "partial")

    accuracy_rate = round((correct / total_with_feedback) * 100, 1) if total_with_feedback > 0 else 0.0

    # Breakdown по AI рекомендациям (hire/maybe/reject)
    breakdown = {}
    for rec in ["hire", "maybe", "reject"]:
        rec_candidates = [c for c in candidates if c.recommendation == rec]
        if rec_candidates:
            breakdown[rec] = {
                "total": len(rec_candidates),
                "correct": sum(1 for c in rec_candidates if c.ai_feedback == "correct"),
                "incorrect": sum(1 for c in rec_candidates if c.ai_feedback == "incorrect"),
                "partial": sum(1 for c in rec_candidates if c.ai_feedback == "partial"),
                "accuracy": round(
                    (sum(1 for c in rec_candidates if c.ai_feedback == "correct") / len(rec_candidates)) * 100, 1
                ),
            }

    logger.info(
        f"AI accuracy для company #{company_id}: {accuracy_rate}% "
        f"({correct}/{total_with_feedback} correct)"
    )

    return AIAccuracyStats(
        total_with_feedback=total_with_feedback,
        correct_predictions=correct,
        incorrect_predictions=incorrect,
        partial_predictions=partial,
        accuracy_rate=accuracy_rate,
        breakdown_by_recommendation=breakdown,
    )


# ---------------------------------------------------------------------------
# Priority 3: Bias / red-flags report
# ---------------------------------------------------------------------------

class BiasReportItem(BaseModel):
    candidate_id: int
    name: str
    job_title: str
    flags: List[str]


class BiasReport(BaseModel):
    total_candidates_scored: int
    flagged_count: int
    flagged_rate: float
    manual_review_count: int
    items: List[BiasReportItem]


@router.get(
    "/bias-report",
    response_model=BiasReport,
    summary="Отчёт по bias / red flags (Priority 3)",
)
def get_bias_report(
    job_id: Optional[int] = Query(default=None, description="Фильтр по вакансии"),
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company),
) -> BiasReport:
    """Агрегирует кандидатов с bias/red-flags для аудита справедливости скоринга."""
    import json as _json
    from app.ai.red_flags import clean_flag_string
    q = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Job.company_id == current_company.id)
    )
    if job_id:
        q = q.filter(Candidate.job_id == job_id)
    scored = q.filter(Candidate.score.isnot(None)).all()
    items: List[BiasReportItem] = []
    manual_review = 0
    for c in scored:
        if c.requires_manual_review:
            manual_review += 1
        if c.bias_flags:
            try:
                raw_flags = _json.loads(c.bias_flags)
            except (ValueError, TypeError):
                raw_flags = []
            # Очищаем: отсеиваем «нет флагов»-шум и приводим к читаемому виду
            # (работает и для старых записей с legacy-форматом '[category] detail').
            cleaned = [cf for f in raw_flags if (cf := clean_flag_string(str(f)))]
            if cleaned:
                items.append(BiasReportItem(
                    candidate_id=c.id,
                    name=c.name,
                    job_title=c.job.title if c.job else "?",
                    flags=cleaned,
                ))
    total = len(scored)
    flagged = len(items)
    return BiasReport(
        total_candidates_scored=total,
        flagged_count=flagged,
        flagged_rate=round(flagged / total * 100, 1) if total else 0.0,
        manual_review_count=manual_review,
        items=items,
    )


# ---------------------------------------------------------------------------
# 1.2 Calibration Feedback Loop: precision/recall AI vs реальные наймы
# ---------------------------------------------------------------------------

class CalibrationReport(BaseModel):
    total_with_decision: int
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    precision: float
    recall: float
    f1: float
    accuracy: float
    alert: bool          # True если точность < 70% (на выборке >= 5)
    alert_message: Optional[str] = None


@router.get(
    "/calibration",
    response_model=CalibrationReport,
    summary="1.2 Калибровка: precision/recall AI vs реальные наймы",
)
def get_calibration(
    job_id: Optional[int] = Query(default=None, description="Фильтр по вакансии"),
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company),
) -> CalibrationReport:
    """Считает precision/recall/F1 AI-рекомендаций относительно реальных наймов.

    positive prediction = recommendation == "hire";
    positive actual     = actual_hire_decision == "hired".
    Алерт, если accuracy < 70% на выборке >= 5 решений.
    """
    company_id = current_company.id
    query = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(
            Job.company_id == company_id,
            Candidate.actual_hire_decision.in_(["hired", "rejected_final"]),
        )
    )
    if job_id:
        query = query.filter(Candidate.job_id == job_id)
    rows = query.all()

    tp = fp = fn = tn = 0
    for c in rows:
        pred_hire = (c.recommendation == "hire")
        actual_hire = (c.actual_hire_decision == "hired")
        if pred_hire and actual_hire:
            tp += 1
        elif pred_hire and not actual_hire:
            fp += 1
        elif not pred_hire and actual_hire:
            fn += 1
        else:
            tn += 1

    total = len(rows)
    precision = round(tp / (tp + fp) * 100, 1) if (tp + fp) else 0.0
    recall = round(tp / (tp + fn) * 100, 1) if (tp + fn) else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 1) if (precision + recall) else 0.0
    accuracy = round((tp + tn) / total * 100, 1) if total else 0.0

    alert = total >= 5 and accuracy < 70.0
    alert_message = (
        f"Точность AI {accuracy}% ниже порога 70% на {total} решениях — пересмотрите веса/промпты."
        if alert else None
    )

    logger.info(f"Calibration company #{company_id}: acc={accuracy}% P={precision}% R={recall}% (n={total})")
    return CalibrationReport(
        total_with_decision=total,
        true_positive=tp, false_positive=fp, false_negative=fn, true_negative=tn,
        precision=precision, recall=recall, f1=f1, accuracy=accuracy,
        alert=alert, alert_message=alert_message,
    )



# ---------------------------------------------------------------------------
# GAP-2 — Audit logs / governance
# ---------------------------------------------------------------------------

class AuditLogOut(BaseModel):
    id: int
    action: str
    actor_type: str
    actor_id: Optional[int]
    actor_email: Optional[str]
    entity_type: Optional[str]
    entity_id: Optional[int]
    detail: Optional[str]
    ip_address: Optional[str]
    created_at: Optional[str]


@router.get(
    "/audit-logs",
    response_model=List[AuditLogOut],
    summary="GAP-2: журнал действий (governance)",
)
def get_audit_logs(
    action: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_admin),
) -> List[AuditLogOut]:
    """Только admin. Последние действия по компании."""
    q = db.query(AuditLog).filter(AuditLog.company_id == actor.company.id)
    if action:
        q = q.filter(AuditLog.action == action)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    rows = (
        q.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        AuditLogOut(
            id=r.id,
            action=r.action,
            actor_type=r.actor_type,
            actor_id=r.actor_id,
            actor_email=r.actor_email,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            detail=r.detail,
            ip_address=r.ip_address,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]
