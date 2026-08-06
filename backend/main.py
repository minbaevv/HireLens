import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.auth import router as auth_router
from app.api.team import router as team_router
from app.api.jobs import router as jobs_router
from app.api.candidates import router as apply_router
from app.api.candidates import hr_router as candidates_router
from app.api.careers import router as careers_router
from app.api.interviews import router as interviews_router
from app.api.health import router as health_router
from app.api.analytics import router as analytics_router
from app.api.landing import router as landing_router
from app.api.seo import router as seo_router
from app.api.referral import router as referral_router
from app.api.billing import router as billing_router
from app.api.admin import router as admin_router
from app.api.telegram_webhook import router as telegram_router
from app.api.copilot import router as copilot_router
from app.api.prompts import router as prompts_router
from app.api.coding import router as coding_router
from app.api.coding import public_router as coding_public_router
from app.api.integrations import router as integrations_router
from app.api.google_calendar import router as google_calendar_router
from app.api.public_api import router as public_api_router
from app.api.branding import router as branding_router
from app.api.privacy import router as privacy_router
from app.core.config import settings
from app.core.limiter import limiter

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Sentry: включается только если задан SENTRY_DSN (на проде)
if settings.SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,  # 10% транзакций для performance-мониторинга
        send_default_pii=False,  # не отправляем персональные данные кандидатов
    )

app = FastAPI(
    title="HireLens API",
    description="SaaS платформа для автоматизированного скрининга кандидатов",
    version="1.0.0",
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS: в production разрешаем только реальный фронтенд-домен, в dev — localhost.
_cors_origins = [settings.FRONTEND_URL]
if settings.ENVIRONMENT != "production":
    _cors_origins += ["http://localhost:3000", "http://localhost", "http://localhost:5173"]
_cors_origins = [o for o in dict.fromkeys(_cors_origins) if o]
if settings.ENVIRONMENT == "production" and "localhost" in settings.FRONTEND_URL:
    logger.warning("FRONTEND_URL всё ещё localhost в production — задайте реальный домен в .env для корректного CORS.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Interview-Token", "X-API-Key"],
)


# SEC-12: security-заголовки на каждый ответ
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# SEC-17: глобальный обработчик неожиданных ошибок — не утекает stacktrace клиенту
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Необработанная ошибка на {request.method} {request.url.path}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(team_router)
app.include_router(jobs_router)
app.include_router(apply_router)
app.include_router(candidates_router)
app.include_router(careers_router)  # Публичная careers-страница компании (исправлен 404 на /api/careers/{id})
app.include_router(interviews_router)
app.include_router(analytics_router)
app.include_router(landing_router)
app.include_router(seo_router)
app.include_router(referral_router)
app.include_router(billing_router)
app.include_router(admin_router)
app.include_router(telegram_router)
app.include_router(copilot_router)
app.include_router(prompts_router)
app.include_router(coding_router)
app.include_router(coding_public_router)
app.include_router(integrations_router)  # D2 — управление API-ключами и webhooks (JWT)
app.include_router(google_calendar_router)  # B4 — Google Calendar: OAuth + автопланирование
app.include_router(public_api_router)  # D2 — публичный API /api/v1 (X-API-Key)
app.include_router(branding_router)  # Фаза 3 — White-label (брендирование)
app.include_router(privacy_router)  # Фаза 3 — Приватность / GDPR

# SEC-3: публичный StaticFiles-mount /videos удалён — записи интервью содержат
# персональные данные кандидатов. Видео раздаётся через защищённый эндпоинт
# GET /interviews/{id}/video/{filename} (требует HR-авторизацию, см. interviews.py).
videos_dir = Path("uploads/videos")
videos_dir.mkdir(parents=True, exist_ok=True)
