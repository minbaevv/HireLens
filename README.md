
# 🔭 HireLens

SaaS-платформа для автоматизированного скрининга кандидатов: компании публикуют вакансии, кандидаты проходят AI-интервью, HR получает ранжированный список с оценками.

**Рынок:** Кыргызстан → СНГ

---

## 🛠 Стек

| Слой | Технологии |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| База данных | PostgreSQL |
| AI | Claude API (Sonnet 4) + Groq API (fallback) + Whisper STT |
| Видео обработка | ffmpeg (audio extraction) |
| Frontend | React, Vite, Tailwind CSS |
| Аутентификация | JWT (python-jose, passlib/bcrypt) |
| Парсинг резюме | pdfplumber |
| Rate Limiting | slowapi |
| Уведомления | Telegram Bot + Email (SMTP) |
| Инфраструктура | Docker, docker-compose, nginx, GitHub Actions CI/CD |

---

## 📊 Статус проекта

| Шаг | Описание | Статус |
|---|---|---|
| 1 | Docker + CI/CD | ✅ Готово |
| 2 | Rate Limiting + безопасность | ✅ Готово |
| 3 | Background Tasks (асинхронный скоринг) | ✅ Готово |
| 4 | Telegram бот для HR | ✅ Готово |
| 5 | Голосовые интервью (Whisper STT) | ✅ Готово |
| 6 | Kanban доска кандидатов | ✅ Готово |
| 7 | Аналитика Dashboard | ✅ Готово |
| 8 | Email уведомления | ✅ Готово |
| 9 | Экспорт PDF/Excel | ✅ Готово |
| 10 | Публичный лендинг + SEO | ✅ Готово |

> ⚠️ Базовый MVP (шаги 1-10) завершён. **Текущий план развития:** [ROADMAP.md](./ROADMAP.md) — путь к топ-1 продукту в СНГ.

---

## 🚀 Запуск локально

### Через Docker (рекомендуется)

```bash
cp .env.docker.example .env
# Заполни GROQ_API_KEY и JWT_SECRET
docker-compose up --build
```

- API: `http://localhost:8000`
- Frontend: `http://localhost`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### Нативно (backend)

**Требования:**
- Python 3.12+
- **ffmpeg** (для видео-интервью C2)
  - Linux: `sudo apt-get install ffmpeg`
  - macOS: `brew install ffmpeg`
  - Windows: [скачать ffmpeg](https://ffmpeg.org/download.html) и добавить в PATH

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

### Нативно (frontend)

```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 Тесты

```bash
cd backend
pytest -v
```

Всего: **80 тестов** (6 auth + 8 jobs + 9 candidates + 8 interviews + 9 voice + 12 kanban + 6 analytics + 7 email + 1 health)

---

## 📁 Структура проекта

```
ai-hr-screening/
├── backend/
│   ├── app/
│   │   ├── ai/           # interview_service.py, prompts.py
│   │   ├── api/          # auth.py, jobs.py, candidates.py, interviews.py, analytics.py, health.py
│   │   ├── core/         # config.py, db.py, security.py, limiter.py
│   │   ├── models/       # models.py
│   │   └── services/     # resume_parser.py, telegram.py, email.py
│   ├── alembic/
│   ├── tests/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   └── src/
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── nginx.conf
├── .github/workflows/ci.yml
├── ROADMAP.md              # единый план развития
├── SECURITY_AUDIT.md       # аудит безопасности
├── PRODUCTION_DEPLOYMENT.md
└── README.md
```

---

## 🔑 Основные API эндпоинты

```
POST   /auth/register              — регистрация компании
POST   /auth/login                 — логин, получение JWT
GET    /auth/me                    — текущая компания
GET    /health                     — health check + статус БД

POST   /jobs                       — создать вакансию
GET    /jobs                       — список вакансий
GET    /jobs/{id}                  — одна вакансия
PATCH  /jobs/{id}                  — обновить вакансию
DELETE /jobs/{id}                  — удалить вакансию

GET    /apply/{token}              — публичная страница вакансии
POST   /apply/{token}              — подать заявку (резюме PDF/TXT)

GET    /candidates                 — список кандидатов
GET    /candidates/kanban          — Kanban доска по колонкам
GET    /candidates/{id}            — детали кандидата
PATCH  /candidates/{id}/status     — обновить статус
PATCH  /candidates/{id}/stage      — Kanban: переместить между колонкам

POST   /interviews/{id}/start      — начать AI-интервью
POST   /interviews/{id}/message    — ответить на вопрос AI
POST   /interviews/{id}/voice      — голосовой ответ (Whisper STT)
GET    /interviews/{id}            — история сообщений

GET    /analytics/summary          — аналитика: вакансии, кандидаты, hire_rate, top_jobs
GET    /candidates/export          — экспорт CSV
GET    /candidates/{id}/report.pdf — PDF отчёт кандидата
GET    /landing                    — публичная информация о продукте
```
