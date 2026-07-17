"""Health check эндпоинт с проверкой БД."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.db import get_db

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
def health_check(db: Session = Depends(get_db)):
    """Проверяет доступность сервиса и базы данных."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": "0.4.0",
        "database": db_status,
    }
