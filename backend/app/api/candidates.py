"""Candidate Flow: публичная подача заявки + HR-просмотр кандидатов."""
import html
import json
import logging
import re
import secrets
from pathlib import Path
from datetime import UTC, datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.orm import Session

from pydantic import BaseModel, Field

from fastapi.responses import HTMLResponse, Response, StreamingResponse

from app.api.deps import CurrentActor, get_current_company, require_write_access
from app.api.schemas import CandidateApply, CandidateListItem, CandidateOut, JobPublicOut, FinalDecisionRequest
from app.core.config import settings
from app.core.db import get_db
from app.core.audit import actor_fields, record_audit
from app.core.plans import enforce_candidate_quota
from app.models.models import Candidate, CandidateStatus, Company, Interview, Job, Message
from app.services.resume_parser import parse_resume
from app.services.telegram import notify_new_candidate

from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/apply", tags=["candidates"])
hr_router = APIRouter(prefix="/candidates", tags=["candidates"])

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".txt"}  # SEC-13: .doc/.docx убраны (небезопасный парсинг)

# Фото кандидата (pilot feedback: Dinara) — необязательное
PHOTO_DIR = Path("uploads/photos")
ALLOWED_PHOTO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB


def _valid_candidate_photo(ext: str, data: bytes) -> bool:
    if ext == ".png":
        return data[:8] == b"\x89PNG\r\n\x1a\n"
    if ext in (".jpg", ".jpeg"):
        return data[:3] == b"\xff\xd8\xff"
    if ext == ".webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False

# Порядок колонок Kanban
KANBAN_COLUMNS = [
    CandidateStatus.applied,
    CandidateStatus.interviewing,
    CandidateStatus.completed,
    CandidateStatus.invited,
    CandidateStatus.hired,
    CandidateStatus.rejected,
]

# Допустимые переходы между статусами (HR вручную)
ALLOWED_STAGE_TRANSITIONS: dict[CandidateStatus, set[CandidateStatus]] = {
    CandidateStatus.applied: {
        CandidateStatus.interviewing,
        CandidateStatus.rejected,
    },
    CandidateStatus.interviewing: {
        CandidateStatus.completed,
        CandidateStatus.rejected,
    },
    CandidateStatus.completed: {
        CandidateStatus.hired,
        CandidateStatus.rejected,
        CandidateStatus.interviewing,  # повторное интервью
        CandidateStatus.invited,       # приглашение на очное собеседование
    },
    CandidateStatus.invited: {
        CandidateStatus.hired,
        CandidateStatus.rejected,
        CandidateStatus.completed,     # вернуть в "оценены"
    },
    CandidateStatus.hired: {
        CandidateStatus.rejected,  # отмена оффера
    },
    CandidateStatus.rejected: {
        CandidateStatus.applied,   # возобновление
    },
}


class KanbanColumn(BaseModel):
    status: CandidateStatus
    label: str
    count: int
    candidates: List[CandidateListItem]


class KanbanBoard(BaseModel):
    columns: List[KanbanColumn]
    total: int


STATUS_LABELS: dict[CandidateStatus, str] = {
    CandidateStatus.applied: "📩 Новые",
    CandidateStatus.interviewing: "🎤 Интервью",
    CandidateStatus.completed: "✅ Оценены",
    CandidateStatus.invited: "📅 Приглашены",
    CandidateStatus.hired: "🎉 Наняты",
    CandidateStatus.rejected: "❌ Отказ",
}


class StageUpdateRequest(BaseModel):
    stage: CandidateStatus


class BulkStatusRequest(BaseModel):
    candidate_ids: List[int] = Field(min_length=1, max_length=500)
    status: CandidateStatus
    notify: bool = False


class BulkTagsRequest(BaseModel):
    candidate_ids: List[int] = Field(min_length=1, max_length=500)
    add: List[str] = Field(default_factory=list, max_length=30)
    remove: List[str] = Field(default_factory=list, max_length=30)


class BulkNotifyRequest(BaseModel):
    candidate_ids: List[int] = Field(min_length=1, max_length=500)


class BulkActionResponse(BaseModel):
    updated: int
    skipped: int
    total: int


# ---------------------------------------------------------------------------
# Публичные эндпоинты (без авторизации) — для кандидатов
# ---------------------------------------------------------------------------

@router.get("/{token}", response_model=JobPublicOut, summary="Получить информацию о вакансии")
def get_job_by_token(
    token: str,
    db: Session = Depends(get_db),
) -> JobPublicOut:
    """Публичная страница вакансии по уникальному токену."""
    job = db.query(Job).filter(Job.apply_token == token, Job.is_active == True).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена или уже закрыта",
        )
    company = job.company
    brand = {}
    if company is not None and getattr(company, "brand_enabled", False):
        brand = {
            "company_name": company.brand_name or None,
            "company_logo_url": company.brand_logo_url or None,
            "company_color": company.brand_color or None,
        }
    return JobPublicOut(
        title=job.title,
        description=job.description,
        requirements=job.requirements,
        language=job.language,
        **brand,
    )


@router.get("/{token}/og", include_in_schema=False)
def apply_job_og(token: str, db: Session = Depends(get_db)) -> HTMLResponse:
    """OG-мета для превью ссылки в мессенджерах/соцсетях (WhatsApp, Telegram и т.д.).

    Отдаёт название вакансии + компанию вместо общего заголовка. Краулеры nginx направляют сюда."""
    base = (settings.FRONTEND_URL or "").rstrip("/")
    page_url = f"{base}/apply/{token}"
    job = db.query(Job).filter(Job.apply_token == token, Job.is_active == True).first()
    site = "HireLens"
    image = ""
    if job is not None:
        company = job.company
        if company is not None and getattr(company, "brand_enabled", False):
            if company.brand_name:
                site = company.brand_name
            if company.brand_logo_url:
                logo = company.brand_logo_url
                image = logo if logo.startswith("http") else base + logo
        title = f"{job.title} — {site}"
        raw = " ".join((job.description or "").split())
        desc = (raw[:157] + "…") if len(raw) > 158 else (raw or f"Вакансия «{job.title}». Пройдите короткое AI-интервью.")
    else:
        title = "HireLens — AI-скрининг кандидатов"
        desc = "Пройдите короткое AI-интервью по вакансии."

    def e(s: str) -> str:
        return html.escape(s or "", quote=True)

    img_tag = f'<meta property="og:image" content="{e(image)}">' if image else ""
    doc = (
        '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        f"<title>{e(title)}</title>"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<meta name="description" content="{e(desc)}">'
        '<meta property="og:type" content="website">'
        f'<meta property="og:title" content="{e(title)}">'
        f'<meta property="og:description" content="{e(desc)}">'
        f'<meta property="og:url" content="{e(page_url)}">'
        f'<meta property="og:site_name" content="{e(site)}">'
        f"{img_tag}"
        '<meta name="twitter:card" content="summary_large_image">'
        f'<meta name="twitter:title" content="{e(title)}">'
        f'<meta name="twitter:description" content="{e(desc)}">'
        f'<meta http-equiv="refresh" content="0; url={e(page_url)}">'
        f'</head><body><p>Перенаправление… <a href="{e(page_url)}">{e(title)}</a></p></body></html>'
    )
    return HTMLResponse(content=doc)

def _normalize_phone(raw):
    """Приводит телефон к международному формату (KG по умолчанию: +996).

    В Кыргызстане часто пишут местный номер с ведущим 0 (0705121370),
    из-за чего ссылка wa.me не открывает контакт. Нормализуем в +996XXXXXXXXX.
    """
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    has_plus = s.startswith("+")
    digits = re.sub(r"\D", "", s)
    if not digits:
        return None
    if has_plus:
        return "+" + digits
    if digits.startswith("996"):
        return "+" + digits
    if digits.startswith("0"):
        return "+996" + digits.lstrip("0")
    if len(digits) == 9:
        return "+996" + digits
    return "+" + digits


@router.post(
    "/{token}",
    response_model=CandidateOut,
    status_code=status.HTTP_201_CREATED,
    summary="Подать заявку на вакансию",
)
@limiter.limit("5/minute")
def apply_to_job(
    request: Request,
    token: str,
    name: str = Form(..., min_length=1, max_length=255),
    email: str = Form(...),
    phone: Optional[str] = Form(default=None, max_length=32),
    resume_text: Optional[str] = Form(default=None),
    resume_file: Optional[UploadFile] = File(default=None),
    photo_file: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
) -> CandidateOut:
    """Кандидат подаёт заявку: имя, email и резюме (текст или файл PDF/TXT)."""
    job = db.query(Job).filter(Job.apply_token == token, Job.is_active == True).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена или уже закрыта",
        )

    # B5-lite: строгий месячный лимит кандидатов тарифа (free=5, starter=50, pro=300)
    enforce_candidate_quota(db, job.company)

    # Проверяем дубликат email для этой вакансии
    existing = db.query(Candidate).filter(
        Candidate.job_id == job.id,
        Candidate.email == email,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Вы уже подали заявку на эту вакансию",
        )

    # Получаем текст резюме
    final_resume_text: Optional[str] = resume_text

    if resume_file and resume_file.filename:
        # Проверяем расширение
        ext = "." + resume_file.filename.rsplit(".", 1)[-1].lower() if "." in resume_file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Неподдерживаемый формат файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        file_bytes = resume_file.file.read()

        # SEC-13: проверка сигнатуры файла (magic bytes)
        if ext == ".pdf" and not file_bytes.startswith(b"%PDF"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Файл не является корректным PDF",
            )
        if ext == ".txt" and b"\x00" in file_bytes[:8192]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Файл не является текстовым",
            )

        # Проверяем размер
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Файл слишком большой. Максимум 5 MB",
            )

        parsed = parse_resume(file_bytes, resume_file.filename)
        if parsed:
            final_resume_text = parsed
        elif not final_resume_text:
            logger.warning(f"Не удалось извлечь текст из файла {resume_file.filename}")

    # Фото кандидата (необязательно): валидируем до создания записи
    photo_bytes = None
    photo_ext = ""
    if photo_file and photo_file.filename:
        photo_ext = ("." + photo_file.filename.rsplit(".", 1)[-1].lower()) if "." in photo_file.filename else ""
        if photo_ext not in ALLOWED_PHOTO_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Фото: поддерживаются PNG, JPG или WEBP",
            )
        photo_bytes = photo_file.file.read()
        if len(photo_bytes) > MAX_PHOTO_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Фото слишком большое. Максимум 5 MB",
            )
        if not _valid_candidate_photo(photo_ext, photo_bytes):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Файл не является корректным изображением",
            )

    candidate = Candidate(
        job_id=job.id,
        name=name,
        email=email,
        phone=_normalize_phone(phone),
        resume_text=final_resume_text,
        status=CandidateStatus.applied,
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    logger.info(f"Новый кандидат #{candidate.id} на вакансию '{job.title}' (job_id={job.id})")

    # Сохраняем фото (после commit — нужен candidate.id)
    if photo_bytes is not None:
        try:
            PHOTO_DIR.mkdir(parents=True, exist_ok=True)
            pfname = f"{candidate.id}_{secrets.token_hex(8)}{photo_ext}"
            (PHOTO_DIR / pfname).write_bytes(photo_bytes)
            candidate.photo_url = f"/api/candidates/photo/{pfname}"
            db.commit()
            db.refresh(candidate)
        except Exception as e:
            logger.warning(f"Не удалось сохранить фото кандидата #{candidate.id}: {e}")

    # D2 — webhook candidate.created (best-effort, поток заявки не блокируем).
    try:
        from app.services import webhook_service

        webhook_service.dispatch_event(
            db,
            job.company.id,
            "candidate.created",
            {
                "candidate_id": candidate.id,
                "job_id": job.id,
                "name": candidate.name,
                "email": candidate.email,
                "status": candidate.status.value if candidate.status else None,
            },
        )
    except Exception as _wh_e:
        logger.warning("Не удалось отправить webhook candidate.created: %s", _wh_e)

    # Telegram уведомление HR о новом кандидате
    notify_new_candidate(
        candidate_name=name,
        candidate_email=email,
        job_title=job.title,
        company=job.company,
    )

    # Алерт владельцу сервиса при 80% и 100% месячной квоты компании.
    # Фоновый поток + best-effort: подачу заявки не задерживает и не ломает.
    try:
        from app.services.quota_alerts import check_candidate_quota_async

        check_candidate_quota_async(job.company_id)
    except Exception as _qa_e:
        logger.warning("Не удалось запустить квота-алерт: %s", _qa_e)

    # AI предварительный скрининг резюме в фоне
    if candidate.resume_text:
        from fastapi import BackgroundTasks
        from app.ai.interview_service import pre_screen_resume
        from app.core.db import SessionLocal

        def _run_pre_screen(candidate_id: int):
            _db = SessionLocal()
            try:
                from app.models.models import Candidate as CandidateModel
                c = _db.query(CandidateModel).filter(CandidateModel.id == candidate_id).first()
                if c:
                    pre_screen_resume(c, _db)
            except Exception as e:
                logger.warning(f"Pre-screen background error: {e}")
            finally:
                _db.close()

        import threading
        threading.Thread(target=_run_pre_screen, args=(candidate.id,), daemon=True).start()

    return CandidateOut.model_validate(candidate)


# ---------------------------------------------------------------------------
# HR эндпоинты (требуют авторизации)
# ---------------------------------------------------------------------------

class CandidateListResponse(BaseModel):
    items: List[CandidateListItem]
    total: int
    page: int
    page_size: int
    pages: int


@hr_router.get(
    "",
    response_model=CandidateListResponse,
    summary="Список кандидатов компании",
)
def list_candidates(
    job_id: Optional[int] = Query(default=None, description="Фильтр по вакансии"),
    status_filter: Optional[CandidateStatus] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None, description="Поиск по имени/email"),
    requires_review: Optional[bool] = Query(
        default=None,
        description="Только кандидаты, требующие ручной проверки HR",
    ),
    tag: Optional[str] = Query(default=None, description="Фильтр по тегу"),
    sort_by: str = Query(default="created_at", description="Сортировка: score | created_at"),
    order: str = Query(default="desc", description="asc | desc"),
    page: int = Query(default=1, ge=1, description="Номер страницы"),
    page_size: int = Query(default=20, ge=1, le=100, description="Количество на странице"),
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company),
) -> CandidateListResponse:
    """Список кандидатов с пагинацией, поиском и сортировкой."""
    import math
    query = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Job.company_id == current_company.id)
    )
    if job_id is not None:
        job = db.query(Job).filter(
            Job.id == job_id,
            Job.company_id == current_company.id,
        ).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вакансия не найдена")
        query = query.filter(Candidate.job_id == job_id)

    if status_filter is not None:
        query = query.filter(Candidate.status == status_filter)

    if requires_review is not None:
        query = query.filter(Candidate.requires_manual_review == requires_review)

    if tag:
        query = query.filter(Candidate.tags.ilike(f'%"{tag}"%'))

    if search:
        like = f"%{search.lower()}%"
        from sqlalchemy import func as sqlfunc
        query = query.filter(
            sqlfunc.lower(Candidate.name).like(like) |
            sqlfunc.lower(Candidate.email).like(like)
        )

    # Сортировка
    sort_col = Candidate.score if sort_by == "score" else Candidate.created_at
    if order == "asc":
        query = query.order_by(sort_col.asc().nullslast())
    else:
        query = query.order_by(sort_col.desc().nullslast())

    total = query.count()
    pages = max(1, math.ceil(total / page_size))
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return CandidateListResponse(
        items=[CandidateListItem.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@hr_router.get(
    "/export",
    summary="Экспорт кандидатов (CSV / Excel / PDF)",
)
def export_candidates(
    format: str = Query(default="csv", pattern="^(csv|xlsx|pdf)$", description="csv | xlsx | pdf"),
    job_id: Optional[int] = Query(default=None, description="Фильтр по вакансии"),
    status_filter: Optional[CandidateStatus] = Query(default=None, alias="status"),
    search: Optional[str] = Query(default=None, description="Поиск по имени/email"),
    tag: Optional[str] = Query(default=None, description="Фильтр по тегу"),
    requires_review: Optional[bool] = Query(default=None, description="Только требующие проверки"),
    ids: Optional[str] = Query(default=None, description="ID кандидатов через запятую (экспорт выбранных)"),
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company),
):
    """Экспортирует кандидатов компании в CSV/Excel/PDF с учётом фильтров или выбранных ID."""
    from app.services.export import (
        generate_candidates_csv,
        generate_candidates_list_pdf,
        generate_candidates_xlsx,
    )

    query = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Job.company_id == current_company.id)
    )

    if ids:
        id_list = [int(p.strip()) for p in ids.split(",") if p.strip().isdigit()]
        if not id_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Некорректный список ID",
            )
        query = query.filter(Candidate.id.in_(id_list[:1000]))
    else:
        if job_id:
            query = query.filter(Candidate.job_id == job_id)
        if status_filter:
            query = query.filter(Candidate.status == status_filter)
        if tag:
            query = query.filter(Candidate.tags.ilike(f'%"{tag}"%'))
        if requires_review is not None:
            query = query.filter(Candidate.requires_manual_review == requires_review)
        if search:
            like = f"%{search.lower()}%"
            from sqlalchemy import func as sqlfunc
            query = query.filter(
                sqlfunc.lower(Candidate.name).like(like)
                | sqlfunc.lower(Candidate.email).like(like)
            )

    candidates = query.order_by(Candidate.created_at.desc()).all()
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

    if format == "xlsx":
        try:
            content = generate_candidates_xlsx(candidates)
        except RuntimeError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="candidates_{ts}.xlsx"'},
        )

    if format == "pdf":
        try:
            content = generate_candidates_list_pdf(
                candidates, company_name=getattr(current_company, "name", None)
            )
        except RuntimeError as e:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="candidates_{ts}.pdf"'},
        )

    csv_bytes = generate_candidates_csv(candidates)
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f'attachment; filename="candidates_{ts}.csv"'},
    )


@hr_router.get(
    "/{candidate_id}/report.pdf",
    summary="PDF отчёт по кандидату",
)
def export_candidate_pdf(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company),
):
    """Генерирует PDF отчёт по кандидату с результатами интервью."""
    from app.services.export import generate_candidate_pdf

    candidate = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Candidate.id == candidate_id, Job.company_id == current_company.id)
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кандидат не найден")

    # История интервью
    interview = (
        db.query(Interview)
        .filter(Interview.candidate_id == candidate_id)
        .order_by(Interview.id.desc())
        .first()
    )
    messages = []
    if interview:
        messages = (
            db.query(Message)
            .filter(Message.interview_id == interview.id)
            .order_by(Message.id)
            .all()
        )

    # Комментарии HR по кандидату (выводятся в отчёте)
    from app.models.candidate_comment import CandidateComment

    comments = (
        db.query(CandidateComment)
        .filter(CandidateComment.candidate_id == candidate_id)
        .order_by(CandidateComment.created_at, CandidateComment.id)
        .all()
    )

    try:
        pdf_bytes = generate_candidate_pdf(
            candidate=candidate,
            job_title=candidate.job.title,
            messages=messages,
            comments=comments,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    # Имя файла должно быть ASCII (заголовок latin-1)
    safe_name = f"candidate_{candidate_id}"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'},
    )


@hr_router.get(
    "/kanban",
    response_model=KanbanBoard,
    summary="Kanban доска кандидатов",
)
def get_kanban_board(
    job_id: Optional[int] = Query(default=None, description="Фильтр по вакансии"),
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company),
) -> KanbanBoard:
    """Возвращает всех кандидатов сгруппированных по колонкам Kanban."""
    base_query = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Job.company_id == current_company.id)
    )

    if job_id is not None:
        job = db.query(Job).filter(
            Job.id == job_id,
            Job.company_id == current_company.id,
        ).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вакансия не найдена")
        base_query = base_query.filter(Candidate.job_id == job_id)

    all_candidates = base_query.order_by(Candidate.score.desc().nullslast(), Candidate.created_at.desc()).all()

    groups: dict[CandidateStatus, list[Candidate]] = {s: [] for s in KANBAN_COLUMNS}
    for c in all_candidates:
        if c.status in groups:
            groups[c.status].append(c)

    columns = [
        KanbanColumn(
            status=col_status,
            label=STATUS_LABELS[col_status],
            count=len(groups[col_status]),
            candidates=[CandidateListItem.model_validate(c) for c in groups[col_status]],
        )
        for col_status in KANBAN_COLUMNS
    ]

    return KanbanBoard(columns=columns, total=len(all_candidates))


# ---------------------------------------------------------------------------
# Массовые операции (bulk): статусы, теги, уведомления
# ---------------------------------------------------------------------------

MAX_TAG_LENGTH = 30


def _normalize_tags(raw: List[str]) -> List[str]:
    """Обрезает пробелы, отбрасывает пустые, дедуплицирует (без учёта регистра)."""
    result: List[str] = []
    seen: set[str] = set()
    for item in raw or []:
        tag = (item or "").strip()[:MAX_TAG_LENGTH].strip()
        if not tag:
            continue
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(tag)
    return result


def _load_tags(raw) -> List[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (ValueError, TypeError):
        return []


def _owned_candidates(db: Session, company_id: int, ids: List[int]) -> List[Candidate]:
    if not ids:
        return []
    return (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Job.company_id == company_id, Candidate.id.in_(ids))
        .all()
    )


def _send_status_emails_async(payloads: List[tuple]) -> None:
    """Фоновая отправка писем о статусе (name, email, job_title, language, status)."""
    if not payloads:
        return

    def _run():
        from app.services.email import notify_candidate_status
        for name, email, job_title, language, status_value in payloads:
            try:
                notify_candidate_status(
                    candidate_name=name,
                    candidate_email=email,
                    job_title=job_title,
                    new_status=status_value,
                    language=language,
                )
            except Exception as e:
                logger.warning(f"Массовое уведомление не отправлено ({email}): {e}")

    import threading
    threading.Thread(target=_run, daemon=True).start()


@hr_router.get("/tags", summary="Список уникальных тегов компании")
def list_company_tags(
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company),
) -> List[str]:
    """Уникальные теги всех кандидатов компании (отсортировано)."""
    rows = (
        db.query(Candidate.tags)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Job.company_id == current_company.id, Candidate.tags.isnot(None))
        .all()
    )
    seen: dict[str, str] = {}
    for (raw,) in rows:
        for tag in _load_tags(raw):
            seen.setdefault(tag.lower(), tag)
    return sorted(seen.values(), key=lambda x: x.lower())


@hr_router.post("/bulk/status", response_model=BulkActionResponse, summary="Массовая смена статуса")
def bulk_update_status(
    body: BulkStatusRequest,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_write_access),
) -> BulkActionResponse:
    """Массово меняет статус выбранных кандидатов (роль admin/recruiter)."""
    company = actor.company
    candidates = _owned_candidates(db, company.id, body.candidate_ids)
    updated = 0
    email_payloads: List[tuple] = []
    for c in candidates:
        if c.status == body.status:
            continue
        c.status = body.status
        updated += 1
        if body.notify:
            email_payloads.append(
                (c.name, c.email, c.job.title, getattr(c.job, "language", "ru"), body.status.value)
            )
    db.commit()
    if updated:
        record_audit(
            db,
            company_id=company.id,
            action="candidate.bulk_status_change",
            entity_type="candidate",
            detail={"new_status": body.status.value, "count": updated},
            **actor_fields(actor),
        )
    if body.notify:
        _send_status_emails_async(email_payloads)
    total = len(set(body.candidate_ids))
    return BulkActionResponse(updated=updated, skipped=total - updated, total=total)


@hr_router.post("/bulk/tags", response_model=BulkActionResponse, summary="Массовые теги")
def bulk_update_tags(
    body: BulkTagsRequest,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_write_access),
) -> BulkActionResponse:
    """Массово добавляет/удаляет теги (роль admin/recruiter)."""
    to_add = _normalize_tags(body.add)
    to_remove = {t.strip().lower() for t in (body.remove or []) if t and t.strip()}
    if not to_add and not to_remove:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Укажите теги для добавления или удаления",
        )
    company = actor.company
    candidates = _owned_candidates(db, company.id, body.candidate_ids)
    updated = 0
    for c in candidates:
        current = _load_tags(c.tags)
        new_tags = [t for t in current if t.lower() not in to_remove]
        existing_lower = {t.lower() for t in new_tags}
        for tag in to_add:
            if tag.lower() not in existing_lower:
                new_tags.append(tag)
                existing_lower.add(tag.lower())
        if new_tags != current:
            c.tags = json.dumps(new_tags, ensure_ascii=False) if new_tags else None
            updated += 1
    db.commit()
    if updated:
        record_audit(
            db,
            company_id=company.id,
            action="candidate.bulk_tags",
            entity_type="candidate",
            detail={"add": to_add, "remove": sorted(to_remove), "count": updated},
            **actor_fields(actor),
        )
    total = len(set(body.candidate_ids))
    return BulkActionResponse(updated=updated, skipped=total - updated, total=total)


@hr_router.post("/bulk/notify", response_model=BulkActionResponse, summary="Массовое email-уведомление")
def bulk_notify(
    body: BulkNotifyRequest,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_write_access),
) -> BulkActionResponse:
    """Отправляет каждому выбранному кандидату письмо о его текущем статусе (роль admin/recruiter)."""
    company = actor.company
    candidates = _owned_candidates(db, company.id, body.candidate_ids)
    payloads: List[tuple] = [
        (c.name, c.email, c.job.title, getattr(c.job, "language", "ru"), c.status.value)
        for c in candidates
    ]
    _send_status_emails_async(payloads)
    if payloads:
        record_audit(
            db,
            company_id=company.id,
            action="candidate.bulk_notify",
            entity_type="candidate",
            detail={"count": len(payloads)},
            **actor_fields(actor),
        )
    total = len(set(body.candidate_ids))
    return BulkActionResponse(updated=len(payloads), skipped=total - len(payloads), total=total)


@hr_router.get(
    "/{candidate_id}",
    response_model=CandidateOut,
    summary="Детали кандидата",
)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company),
) -> CandidateOut:
    """Полная информация о кандидате включая резюме."""
    candidate = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(
            Candidate.id == candidate_id,
            Job.company_id == current_company.id,
        )
        .first()
    )
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кандидат не найден",
        )
    return CandidateOut.model_validate(candidate)


@hr_router.post(
    "/{candidate_id}/rescore",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Перескорить кандидата (повторный AI-скоринг)",
)
def rescore_candidate(
    candidate_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_write_access),
):
    """Повторно запускает AI-скоринг по завершённому интервью кандидата.

    Нужно, если предыдущий скоринг завершился сбоем (кандидат помечен для
    ручной проверки). Скоринг выполняется в фоне; результат через 10-30 секунд.
    """
    candidate = db.query(Candidate).join(Job).filter(
        Candidate.id == candidate_id,
        Job.company_id == actor.company.id,
    ).first()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кандидат не найден")

    interview = (
        db.query(Interview)
        .filter(Interview.candidate_id == candidate_id)
        .order_by(Interview.id.desc())
        .first()
    )
    if not interview:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У кандидата нет интервью для скоринга",
        )

    from app.ai.interview_service import _run_scoring_task

    background_tasks.add_task(_run_scoring_task, interview.id)
    logger.info(
        f"Rescore: candidate #{candidate_id}, interview #{interview.id} - manual"
    )
    record_audit(
        db,
        company_id=actor.company.id,
        action="candidate.rescore",
        entity_type="candidate",
        entity_id=candidate.id,
        detail={"interview_id": interview.id},
        **actor_fields(actor),
    )
    return {"status": "scoring_started", "interview_id": interview.id}


@hr_router.get(
    "/{candidate_id}/scoring-details",
    summary="Детализация скоринга (Priority 2)",
)
def get_scoring_details(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company),
):
    """Под-оценки, reasoning, расхождения резюме/интервью и evasive answers."""
    candidate = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Candidate.id == candidate_id, Job.company_id == current_company.id)
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кандидат не найден")

    def _loads(val, default):
        if not val:
            return default
        try:
            return json.loads(val)
        except (ValueError, TypeError):
            return default

    cross = _loads(candidate.cross_validation, {"discrepancies": [], "evasive_answers": []})
    attr_data = _loads(candidate.answer_attribution, {"questions": [], "attribution": {}})
    _qmap = {q.get("n"): q for q in attr_data.get("questions", []) if isinstance(q, dict)}

    def _resolve(dim):
        refs = []
        for n in attr_data.get("attribution", {}).get(dim, []) or []:
            q = _qmap.get(n)
            if q:
                refs.append({"n": n, "message_id": q.get("message_id"), "question": q.get("question")})
        return refs

    return {
        "candidate_id": candidate.id,
        "overall_score": candidate.score,
        "confidence": candidate.confidence,
        "recommendation": candidate.recommendation,
        "requires_manual_review": candidate.requires_manual_review,
        "dimensions": {
            "technical": candidate.technical_score,
            "soft_skills": candidate.soft_skills_score,
            "experience": candidate.experience_score,
            "motivation": candidate.motivation_score,
        },
        "reasoning": _loads(candidate.scoring_reasoning, {}),
        "discrepancies": cross.get("discrepancies", []),
        "evasive_answers": cross.get("evasive_answers", []),
        "bias_flags": _loads(candidate.bias_flags, []),
        "attribution": {
            "technical_skills": _resolve("technical_skills"),
            "soft_skills": _resolve("soft_skills"),
            "experience": _resolve("experience"),
            "motivation": _resolve("motivation"),
        },
        "questions": attr_data.get("questions", []),
    }


@hr_router.get(
    "/{candidate_id}/transcript",
    summary="Транскрипт интервью кандидата",
)
def get_candidate_transcript(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_company: Company = Depends(get_current_company),
):
    """Диалог последнего интервью (роль ai/user + текст) — HR видит ответы в карточке без PDF."""
    candidate = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(Candidate.id == candidate_id, Job.company_id == current_company.id)
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кандидат не найден")

    interview = (
        db.query(Interview)
        .filter(Interview.candidate_id == candidate_id)
        .order_by(Interview.id.desc())
        .first()
    )
    messages = []
    if interview:
        messages = (
            db.query(Message)
            .filter(Message.interview_id == interview.id)
            .order_by(Message.id)
            .all()
        )

    return {
        "candidate_id": candidate.id,
        "interview_id": interview.id if interview else None,
        "messages": [
            {
                "id": m.id,
                "role": m.role.value,
                "content": m.content,
                "video_url": m.video_url,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


@hr_router.get("/photo/{filename}", summary="Фото кандидата")
def get_candidate_photo(filename: str, exp: Optional[int] = None, sig: Optional[str] = None):
    """SEC-3: фото кандидата — персональные данные, раздаётся только
    по подписанной ссылке с ограниченным сроком жизни (24 часа).
    Подпись выдаёт API авторизованному HR вместе с карточкой кандидата."""
    from fastapi.responses import FileResponse

    from app.core.security import verify_file_token

    safe = Path(filename).name
    if safe != filename:
        raise HTTPException(status_code=400, detail="Некорректное имя файла")
    if not verify_file_token(safe, exp, sig):
        raise HTTPException(status_code=403, detail="Ссылка на фото недействительна или устарела")
    path = PHOTO_DIR / safe
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Фото не найдено")
    return FileResponse(path)


class InviteRequest(BaseModel):
    date: str = Field(min_length=1, max_length=40)
    time: str = Field(default="", max_length=40)
    location: str = Field(min_length=1, max_length=300)
    note: str = Field(default="", max_length=1000)


@hr_router.post(
    "/{candidate_id}/invite",
    response_model=CandidateOut,
    summary="Пригласить кандидата на очное собеседование",
)
def invite_candidate(
    candidate_id: int,
    body: InviteRequest,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_write_access),
) -> CandidateOut:
    """Отправляет кандидату письмо-приглашение на очное собеседование
    и переводит его в статус 'invited' (требует роль admin/recruiter)."""
    current_company = actor.company
    candidate = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(
            Candidate.id == candidate_id,
            Job.company_id == current_company.id,
        )
        .first()
    )
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кандидат не найден",
        )

    candidate.status = CandidateStatus.invited
    db.commit()
    db.refresh(candidate)
    logger.info(f"Кандидат #{candidate_id} приглашён на очное собеседование")
    record_audit(
        db,
        company_id=current_company.id,
        action="candidate.invited",
        entity_type="candidate",
        entity_id=candidate.id,
        detail={"date": body.date, "time": body.time, "location": body.location},
        **actor_fields(actor),
    )

    try:
        from app.services.email import notify_interview_invitation
        notify_interview_invitation(
            candidate_name=candidate.name,
            candidate_email=candidate.email,
            job_title=candidate.job.title,
            date=body.date,
            time=body.time,
            location=body.location,
            note=body.note,
            company_name=(getattr(current_company, "brand_name", None) or getattr(current_company, "name", "")),
            language=getattr(candidate.job, "language", "ru"),
        )
    except Exception as e:
        logger.warning(f"Email приглашение кандидату не отправлено: {e}")

    return CandidateOut.model_validate(candidate)


@hr_router.patch(
    "/{candidate_id}/status",
    response_model=CandidateOut,
    summary="Обновить статус кандидата",
)
def update_candidate_status(
    candidate_id: int,
    new_status: CandidateStatus,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_write_access),
) -> CandidateOut:
    """HR меняет статус кандидата: hired / rejected / interviewing и т.д. (требует роль admin/recruiter)."""
    current_company = actor.company
    candidate = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(
            Candidate.id == candidate_id,
            Job.company_id == current_company.id,
        )
        .first()
    )
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кандидат не найден",
        )
    candidate.status = new_status
    db.commit()
    db.refresh(candidate)
    logger.info(f"Статус кандидата #{candidate_id} изменён на {new_status}")
    record_audit(
        db,
        company_id=current_company.id,
        action="candidate.status_change",
        entity_type="candidate",
        entity_id=candidate.id,
        detail={"new_status": new_status.value},
        **actor_fields(actor),
    )

    if new_status in (CandidateStatus.hired, CandidateStatus.rejected):
        try:
            from app.services.email import notify_candidate_status
            notify_candidate_status(
                candidate_name=candidate.name,
                candidate_email=candidate.email,
                job_title=candidate.job.title,
                new_status=new_status.value,
                language=getattr(candidate.job, "language", "ru"),
            )
        except Exception as e:
            logger.warning(f"Email уведомление кандидату не отправлено: {e}")

    return CandidateOut.model_validate(candidate)


@hr_router.patch(
    "/{candidate_id}/stage",
    response_model=CandidateOut,
    summary="Переместить кандидата на Kanban доске",
)
def move_candidate_stage(
    candidate_id: int,
    body: StageUpdateRequest,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_write_access),
) -> CandidateOut:
    """Перемещает кандидата между колонками Kanban (требует роль admin/recruiter)."""
    current_company = actor.company
    candidate = (
        db.query(Candidate)
        .join(Job, Candidate.job_id == Job.id)
        .filter(
            Candidate.id == candidate_id,
            Job.company_id == current_company.id,
        )
        .first()
    )
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кандидат не найден",
        )

    new_stage = body.stage
    current_stage = candidate.status

    # Переход в тот же статус — нормально
    if new_stage == current_stage:
        return CandidateOut.model_validate(candidate)

    allowed = ALLOWED_STAGE_TRANSITIONS.get(current_stage, set())
    if new_stage not in allowed:
        allowed_labels = [s.value for s in allowed]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Недопустимый переход: {current_stage.value} → {new_stage.value}. "
                f"Доступные: {allowed_labels}"
            ),
        )

    candidate.status = new_stage
    db.commit()
    db.refresh(candidate)
    logger.info(f"Kanban: кандидат #{candidate_id} перемещён {current_stage.value} → {new_stage.value}")
    return CandidateOut.model_validate(candidate)


# ---------------------------------------------------------------------------
# Ground Truth Tracking (Phase 10/10 - 1.1)
# ---------------------------------------------------------------------------

@hr_router.patch("/{candidate_id}/final-decision", response_model=CandidateOut)
def set_final_decision(
    candidate_id: int,
    body: FinalDecisionRequest,
    db: Session = Depends(get_db),
    actor: CurrentActor = Depends(require_write_access),
):
    """HR отмечает финальное решение по кандидату и оценивает точность AI рекомендации.

    Используется для измерения реальной AI accuracy через ground truth.
    """
    candidate = db.query(Candidate).join(Job).filter(
        Candidate.id == candidate_id,
        Job.company_id == actor.company.id,
    ).first()
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кандидат не найден")

    candidate.actual_hire_decision = body.actual_hire_decision
    candidate.ai_feedback = body.ai_feedback
    candidate.hr_notes = body.hr_notes

    # Автоматически снять флаг manual review, если HR принял решение
    if candidate.requires_manual_review:
        candidate.requires_manual_review = False

    db.commit()
    db.refresh(candidate)
    logger.info(
        f"Final decision: candidate #{candidate_id} → {body.actual_hire_decision}, "
        f"AI feedback: {body.ai_feedback}"
    )
    record_audit(
        db,
        company_id=actor.company.id,
        action="candidate.final_decision",
        entity_type="candidate",
        entity_id=candidate.id,
        detail={"actual_hire_decision": body.actual_hire_decision, "ai_feedback": body.ai_feedback},
        **actor_fields(actor),
    )
    return CandidateOut.model_validate(candidate)
