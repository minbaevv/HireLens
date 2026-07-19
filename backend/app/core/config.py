import os
from pathlib import Path
from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parents[2]
_root_dir = _backend_dir.parent

if (_backend_dir / ".env").exists():
    load_dotenv(_backend_dir / ".env")
elif (_root_dir / ".env").exists():
    load_dotenv(_root_dir / ".env")
else:
    load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://localhost:5432/ai_hr_db")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))
    # Refresh-токен: 30 дней по умолчанию
    JWT_REFRESH_EXPIRE_MINUTES: int = int(os.getenv("JWT_REFRESH_EXPIRE_MINUTES", "43200"))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    # AI провайдер: "groq" (сейчас основной, бесплатный тир) или "claude" (Haiku 4.5, качество). Второй — автоматический fallback
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "groq")
    # Основная модель Claude: Haiku 4.5 — лучший баланс цена/качество для скрининга
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
    # Температуры под задачу (Roadmap Приоритет 1):
    # интервью — креативнее, скоринг/прескрининг — детерминированнее
    TEMPERATURE_INTERVIEW: float = float(os.getenv("TEMPERATURE_INTERVIEW", "0.7"))
    TEMPERATURE_SCORING: float = float(os.getenv("TEMPERATURE_SCORING", "0.3"))
    TEMPERATURE_PRESCREENING: float = float(os.getenv("TEMPERATURE_PRESCREENING", "0.2"))
    # Лимит символов транскрипта для скоринга (защита от context overflow)
    SCORING_TRANSCRIPT_MAX_CHARS: int = int(os.getenv("SCORING_TRANSCRIPT_MAX_CHARS", "6000"))
    # Минимум вопросов AI для достоверного скоринга
    SCORING_MIN_AI_QUESTIONS: int = int(os.getenv("SCORING_MIN_AI_QUESTIONS", "4"))
    # Scoring response token limit (large Cyrillic JSON; 1024 truncated -> broken JSON)
    SCORING_MAX_TOKENS: int = int(os.getenv("SCORING_MAX_TOKENS", "3000"))
    # Множитель confidence, если у кандидата нет резюме (1.0 = штраф отключён)
    SCORING_NO_RESUME_PENALTY: float = float(os.getenv("SCORING_NO_RESUME_PENALTY", "0.7"))
    # SEC-14: максимум интервью на одного кандидата (защита от cost-DoS)
    MAX_INTERVIEWS_PER_CANDIDATE: int = int(os.getenv("MAX_INTERVIEWS_PER_CANDIDATE", "3"))
    # Adaptive interview flow: границы адаптивной длины интервью.
    # min — мягкий пол (на уровне промпта + штраф confidence в скоринге);
    # max — жёсткий потолок (детерминированно завершаем интервью, анти cost-DoS/runaway).
    INTERVIEW_MIN_QUESTIONS: int = int(os.getenv("INTERVIEW_MIN_QUESTIONS", "5"))
    INTERVIEW_MAX_QUESTIONS: int = int(os.getenv("INTERVIEW_MAX_QUESTIONS", "8"))
    # Telegram бот для HR уведомлений (старый)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_BOT_USERNAME: str = os.getenv("TELEGRAM_BOT_USERNAME", "")  # без @, для deep-link кнопки
    TELEGRAM_HR_CHAT_ID: str = os.getenv("TELEGRAM_HR_CHAT_ID", "")
    # Telegram бот для кандидатов (новый)
    TELEGRAM_CANDIDATE_BOT_TOKEN: str = os.getenv("TELEGRAM_CANDIDATE_BOT_TOKEN", "")
    TELEGRAM_CANDIDATE_BOT_USERNAME: str = os.getenv("TELEGRAM_CANDIDATE_BOT_USERNAME", "")  # без @, для deep-link кандидата
    # Webhook URL для бота кандидатов
    TELEGRAM_WEBHOOK_URL: str = os.getenv("TELEGRAM_WEBHOOK_URL", "")
    # SEC-2: секрет для проверки подлинности вебхука Telegram
    TELEGRAM_WEBHOOK_SECRET: str = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
    # Email (SMTP)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "noreply@ai-hr-screening.com")
    # Observability
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    # Ручное управление подпиской (пока без платёжного шлюза): email'ы суперадминов через запятую
    SUPERADMIN_EMAILS: str = os.getenv("SUPERADMIN_EMAILS", "")
    # Пробный период: новым компаниям при подтверждении email выдаётся тариф
    # TRIAL_PLAN на TRIAL_DAYS дней. По истечении проба заканчивается и доступ
    # к платным функциям блокируется, пока суперадмин не активирует оплату.
    TRIAL_DAYS: int = int(os.getenv("TRIAL_DAYS", "3"))
    TRIAL_PLAN: str = os.getenv("TRIAL_PLAN", "starter")
    # D2 — Webhooks: таймаут доставки и разрешение приватных URL.
    # SSRF-защита: приватные/локальные адреса блокируются в production;
    # в dev разрешены (чтобы тестить на localhost). WEBHOOK_ALLOW_PRIVATE_URLS=true
    # явно разрешает приватные URL даже в production (не рекомендуется).
    WEBHOOK_TIMEOUT_SECONDS: int = int(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "10"))
    WEBHOOK_ALLOW_PRIVATE_URLS: bool = os.getenv("WEBHOOK_ALLOW_PRIVATE_URLS", "false").lower() == "true"
    # B4 — Google Calendar (автопланирование интервью). Интеграция включается,
    # только если заданы GOOGLE_OAUTH_CLIENT_ID и GOOGLE_OAUTH_CLIENT_SECRET.
    GOOGLE_OAUTH_CLIENT_ID: str = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    GOOGLE_OAUTH_CLIENT_SECRET: str = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
    # Redirect URI по умолчанию = {BACKEND_URL}/integrations/google/callback.
    # Должен ТОЧНО совпадать с значением в Google Cloud Console.
    GOOGLE_OAUTH_REDIRECT_URI: str = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "")
    GOOGLE_HTTP_TIMEOUT_SECONDS: int = int(os.getenv("GOOGLE_HTTP_TIMEOUT_SECONDS", "15"))
    # Планировщик: таймзона и рабочие часы по умолчанию для подбора слотов.
    SCHEDULING_TIMEZONE: str = os.getenv("SCHEDULING_TIMEZONE", "Asia/Bishkek")
    SCHEDULING_WORK_START_HOUR: int = int(os.getenv("SCHEDULING_WORK_START_HOUR", "10"))
    SCHEDULING_WORK_END_HOUR: int = int(os.getenv("SCHEDULING_WORK_END_HOUR", "19"))
    SCHEDULING_SLOT_MINUTES: int = int(os.getenv("SCHEDULING_SLOT_MINUTES", "30"))
    # C1.1 — при anti-cheat score ≥ порога авто-рекомендация "hire" понижается
    # до "maybe" и кандидат помечается на очную проверку. Шкала 0..100.
    ANTI_CHEAT_DOWNGRADE_THRESHOLD: float = float(os.getenv("ANTI_CHEAT_DOWNGRADE_THRESHOLD", "85"))

    @property
    def superadmin_emails(self) -> set[str]:
        return {e.strip().lower() for e in self.SUPERADMIN_EMAILS.split(",") if e.strip()}

    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.GOOGLE_OAUTH_CLIENT_ID and self.GOOGLE_OAUTH_CLIENT_SECRET)

    @property
    def google_oauth_redirect_uri(self) -> str:
        return self.GOOGLE_OAUTH_REDIRECT_URI or (
            self.BACKEND_URL.rstrip("/") + "/integrations/google/callback"
        )


settings = Settings()

# ─── SEC-4: fail-fast на небезопасной конфигурации в production ───
_WEAK_JWT_SECRETS = {
    "", "change-me-in-production", "secret", "changeme",
    "GENERATE_NEW_ONE_openssl_rand_hex_32",
}
if settings.ENVIRONMENT == "production":
    _errors = []
    if settings.JWT_SECRET in _WEAK_JWT_SECRETS or len(settings.JWT_SECRET) < 32:
        _errors.append(
            "JWT_SECRET не задан или слишком слабый. Сгенерируй: openssl rand -hex 32"
        )
    if settings.TELEGRAM_WEBHOOK_URL and not settings.TELEGRAM_WEBHOOK_SECRET:
        _errors.append(
            "TELEGRAM_WEBHOOK_URL задан без TELEGRAM_WEBHOOK_SECRET (SEC-2). "
            "Сгенерируй: openssl rand -hex 16"
        )
    if _errors:
        raise RuntimeError(
            "Небезопасная конфигурация production:\n- " + "\n- ".join(_errors)
        )
