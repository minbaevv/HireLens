# 🚀 Production Deployment Guide

**Дата:** 04.07.2026  
**Версия:** v2.0 (готова к production)

---

## ✅ Pre-Deployment Checklist

### 1. Environment Variables (.env)

**Критично изменить перед деплоем:**

```bash
# === AI Provider (ОБЯЗАТЕЛЬНО) ===
AI_PROVIDER=claude  # ← ИЗМЕНИТЬ с "groq" на "claude" для прода
ANTHROPIC_API_KEY=sk-ant-api03-xxx  # ← ДОБАВИТЬ реальный ключ
CLAUDE_MODEL=claude-sonnet-4-6  # Оптимально для качества/цены

# Groq как fallback (опционально, но рекомендуется)
GROQ_API_KEY=gsk_xxx
GROQ_MODEL=llama-3.3-70b-versatile

# === Security (КРИТИЧНО) ===
JWT_SECRET=<СГЕНЕРИРОВАТЬ_32+_СИМВОЛОВ>  # ← НЕ использовать "change-me-in-production"
JWT_EXPIRE_MINUTES=60  # Access token: 1 час (не 7 дней как в dev)
JWT_REFRESH_EXPIRE_MINUTES=43200  # Refresh: 30 дней

# === Database ===
DATABASE_URL=postgresql://user:password@db-host:5432/ai_hr_db

# === Frontend/Backend URLs ===
FRONTEND_URL=https://yourdomain.com
BACKEND_URL=https://api.yourdomain.com

# === Email (SMTP) ===
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@yourdomain.com
SMTP_PASSWORD=<app_password>
SMTP_FROM=noreply@yourdomain.com

# === Telegram (опционально) ===
TELEGRAM_BOT_TOKEN=<bot_token>  # HR уведомления
TELEGRAM_HR_CHAT_ID=<chat_id>
TELEGRAM_CANDIDATE_BOT_TOKEN=<bot_token>  # Интервью в Telegram
TELEGRAM_WEBHOOK_URL=https://api.yourdomain.com/telegram/webhook

# === Observability (ОБЯЗАТЕЛЬНО для прода) ===
SENTRY_DSN=https://xxx@sentry.io/xxx  # Error tracking
ENVIRONMENT=production
LOG_LEVEL=INFO  # WARNING для менее шумных логов
```

---

## 🔒 2. Security Hardening

### JWT Secret Generation

```bash
# Сгенерировать криптографически безопасный secret (32+ символов)
openssl rand -base64 48
# Или Python
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

⚠️ **ВАЖНО:** Не коммитить `.env` в git! Добавлен в `.gitignore`.

### HTTPS Only

Убедиться, что:
- Backend доступен только через HTTPS (nginx/Caddy с SSL)
- Frontend redirect с HTTP → HTTPS
- CORS настроен только на production домен

### Rate Limiting

По умолчанию включен (slowapi):
- `/apply/{token}`: 5 заявок/мин с одного IP
- `/auth/login`: 20 попыток/мин
- `/auth/register`: 10 регистраций/час

Для production можно ужесточить в `app/api/*.py` (декораторы `@limiter.limit`).

---

## 🗄️ 3. Database Setup

### Production PostgreSQL

```bash
# Создать БД и пользователя
createdb ai_hr_db
psql ai_hr_db

CREATE USER ai_hr_user WITH PASSWORD '<strong_password>';
GRANT ALL PRIVILEGES ON DATABASE ai_hr_db TO ai_hr_user;
```

### Миграции

```bash
cd backend

# Проверить текущее состояние
alembic current

# Применить все миграции
alembic upgrade head

# Проверить, что все таблицы созданы
psql $DATABASE_URL -c "\dt"
# Ожидаем: companies, jobs, candidates, interviews, messages, team_members
```

### Backup Strategy

**Рекомендация:** Автоматический daily backup через cron:

```bash
# /etc/cron.daily/backup-ai-hr-db.sh
#!/bin/bash
pg_dump ai_hr_db | gzip > /backups/ai_hr_db_$(date +\%Y\%m\%d).sql.gz
# Удалить бекапы старше 30 дней
find /backups -name "ai_hr_db_*.sql.gz" -mtime +30 -delete
```

---

## 🐳 4. Docker Deployment

### Build Images

```bash
# Backend
docker build -f Dockerfile.backend -t ai-hr-backend:v2.0 .

# Frontend
docker build -f Dockerfile.frontend -t ai-hr-frontend:v2.0 .
```

### Docker Compose (Production)

Использовать `docker-compose.yml` (не dev версию):

```bash
# Поднять всё (backend + frontend + postgres)
docker-compose up -d

# Проверить логи
docker-compose logs -f backend

# Проверить health
curl https://api.yourdomain.com/health
# Ожидаем: {"status": "healthy", "database": "connected", ...}
```

### Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/ai-hr-screening

# Backend API
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Frontend
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    root /var/www/ai-hr-frontend/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 📊 5. Monitoring & Observability

### Sentry (Error Tracking)

1. Создать проект на sentry.io
2. Добавить `SENTRY_DSN` в `.env`
3. Ошибки автоматически логируются (уже интегрировано в `main.py`)

### Health Check

```bash
# Периодически проверять (cron каждые 5 минут)
curl -f https://api.yourdomain.com/health || alert_admin
```

### Database Monitoring

```sql
-- Топ медленных запросов
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
```

### Metrics (TODO — будет в Phase "10/10")

Пока метрики только в логах. Для production рекомендуется добавить:
- Prometheus + Grafana
- Метрики: interviews/hour, AI latency, error rate, DB connections

---

## 🧪 6. Pre-Launch Testing

### Smoke Tests

```bash
cd backend

# Проверить, что все тесты проходят на production окружении
pytest -v

# Load test (опционально, требует установки locust)
locust -f tests/load_test.py --host https://api.yourdomain.com
```

### Manual QA Checklist

- [ ] Регистрация компании
- [ ] Создание вакансии
- [ ] Публичная ссылка `/apply/{token}` открывается
- [ ] Подача заявки кандидатом
- [ ] Pre-screening резюме работает (pre_score проставлен)
- [ ] Запуск AI-интервью
- [ ] Voice/video интервью (если используется)
- [ ] Скоринг после завершения (score, recommendation)
- [ ] Email уведомления приходят
- [ ] Telegram уведомления (если настроено)
- [ ] Командный доступ: invite → accept → проверка прав
- [ ] PWA: установка на телефон работает
- [ ] Kanban доска отображается
- [ ] Analytics dashboard показывает метрики
- [ ] Экспорт CSV/PDF работает

---

## 🚀 7. Launch!

### Soft Launch (Pilot Clients)

1. **1-3 компании в Бишкеке**
   - Дать бесплатный доступ на 30 дней
   - Собрать feedback по UX
   - Проверить AI accuracy на реальных данных

2. **Мониторинг первой недели:**
   - Sentry: нет критических ошибок?
   - Логи: LLM latency < 5 сек?
   - База: размер БД растёт нормально?
   - Email: SMTP не в спаме?

3. **Сбор Ground Truth:**
   - Попросить HR отмечать: "AI был прав" / "AI ошибся"
   - Цель: измерить AI accuracy (ожидаем 70-80% на старте)

### Public Launch

После 2-4 недель пилота:
- Публичный лендинг (есть в `/landing`)
- SEO: hh.kg, LinkedIn, Telegram группы IT Кыргызстан
- Ценообразование: Free (5 кандидатов) → Starter ($49) → Pro ($149)

---

## 📞 8. Support & Maintenance

### Backup Restore

```bash
# Восстановить из бекапа
gunzip < /backups/ai_hr_db_20260704.sql.gz | psql ai_hr_db
```

### Database Migration

```bash
# Новая миграция (после изменения models)
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Rollback Strategy

```bash
# Откатить на предыдущую версию
docker-compose down
docker-compose up -d --force-recreate

# Откатить миграцию БД
alembic downgrade -1
```

### Log Rotation

```bash
# /etc/logrotate.d/ai-hr-screening
/var/log/ai-hr-screening/*.log {
    daily
    missingok
    rotate 30
    compress
    notifempty
    create 0644 www-data www-data
}
```

---

## ⚡ Performance Optimization (Post-Launch)

После первых клиентов, если нужно:

1. **DB Indexes** (если запросы медленные):
   ```sql
   CREATE INDEX idx_candidates_job_score ON candidates(job_id, score DESC);
   CREATE INDEX idx_interviews_candidate_status ON interviews(candidate_id, status);
   ```

2. **Redis Cache** (если много read-запросов):
   - Кэшировать `/analytics/summary`
   - TTL 5 минут

3. **Celery Workers** (если scoring тормозит):
   - Вынести LLM вызовы в отдельные worker процессы
   - Redis Queue

4. **CDN для фронтенда** (если международные клиенты):
   - Cloudflare или Vercel

---

## 🎯 Success Metrics (First Month)

- **Technical:**
  - ✅ Uptime > 99.5%
  - ✅ API latency p95 < 3s
  - ✅ Zero critical bugs in Sentry
  - ✅ AI accuracy > 70% (измерить через ground truth)

- **Business:**
  - 🎯 3-5 pilot clients
  - 🎯 50+ кандидатов прошли интервью
  - 🎯 1+ компания перешла на платный план

---

## 📚 Useful Commands

```bash
# Health check
curl https://api.yourdomain.com/health | jq

# Database connections
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;"

# Docker logs (last 100 lines)
docker-compose logs --tail=100 backend

# Restart backend
docker-compose restart backend

# Check AI provider in use
grep AI_PROVIDER backend/.env
```

---

**Готово к деплою! 🚀**

Следующий шаг: Phase "Make Everything 10/10" (AI quality improvements).
