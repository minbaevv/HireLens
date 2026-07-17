# HireLens Public API (v1)

Публичный REST API для интеграции HireLens с внешними системами (CRM, ATS, внутренние дашборды).

Базовый URL: `https://<ваш-домен>/api/v1`

---

## Авторизация

Все запросы к `/api/v1/*` требуют API-ключ в заголовке `X-API-Key`.

```
X-API-Key: hl_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Ключи создаются в интерфейсе: **Кабинет → Интеграции → API-ключи**. Полный ключ показывается один раз при создании — сохраните его. В БД хранится только SHA-256 хеш.

Коды ошибок:
- `401` — ключ отсутствует, неверен или отозван.
- `402` — подписка компании истекла.
- `404` — ресурс не найден (или принадлежит другой компании).

---

## Эндпоинты

### `GET /api/v1/ping`
Проверка ключа.
```json
{ "ok": true, "company_id": 1, "company": "Acme Inc" }
```

### `GET /api/v1/jobs`
Список вакансий компании.

Параметры: `active` (bool, опц.), `limit` (1–200, по умолч. 50), `offset` (по умолч. 0).
```json
[
  {
    "id": 12, "title": "Backend Developer", "description": "...",
    "requirements": "Python, FastAPI", "language": "ru", "is_active": true,
    "apply_url": "https://.../apply/abc123", "created_at": "2026-07-14T10:00:00+00:00"
  }
]
```

### `GET /api/v1/jobs/{job_id}`
Одна вакансия по id.

### `GET /api/v1/candidates`
Список кандидатов.

Параметры: `job_id` (опц.), `status` (опц.), `limit`, `offset`.
```json
[
  {
    "id": 44, "job_id": 12, "name": "Иван П.", "email": "ivan@example.com",
    "status": "completed", "overall_score": 78.5, "recommendation": "hire",
    "created_at": "2026-07-14T11:00:00+00:00"
  }
]
```

### `GET /api/v1/candidates/{candidate_id}`
Один кандидат по id.

> Примечание: подробные внутренние поля (anti-cheat, bias reasoning, подробный разбор) не возвращаются через публичный API.

---

## Webhooks

Настраиваются в **Кабинет → Интеграции → Webhooks**. HireLens отправляет POST на ваш URL при наступлении события.

### Поддерживаемые события
- `interview.completed` — интервью завершено.
- `candidate.scored` — кандидат оценён.
- `candidate.created` — новый кандидат (отклик).

Подписка на `*` означает «все события».

### Формат тела
```json
{
  "id": "<uuid доставки>",
  "event": "candidate.scored",
  "created_at": "2026-07-14T11:05:00+00:00",
  "data": { "candidate_id": 44, "job_id": 12, "overall_score": 78.5, "recommendation": "hire" }
}
```

### Заголовки
- `X-HireLens-Event` — имя события.
- `X-HireLens-Delivery` — уникальный id доставки.
- `X-HireLens-Signature` — `sha256=<hex>`, HMAC-SHA256 от тела запроса на вашем secret.

### Проверка подписи (пример на Python)
```python
import hmac, hashlib

def verify(secret: str, body: bytes, signature: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### Доставка
- 2 попытки, таймаут `WEBHOOK_TIMEOUT_SECONDS` (по умолч. 10с).
- Успешной считается ответ с кодом 2xx.
- История доставок доступна в UI (кнопка «Тест» и журнал).

### SSRF-защита
Разрешены только `http`/`https` URL; в production — только `https`. Приватные/loopback/link-local адреса блокируются (отключается через `WEBHOOK_ALLOW_PRIVATE_URLS=true`, не рекомендуется).

---

## Управление (требует JWT admin)

Эти эндпоинты используются интерфейсом кабинета (авторизация — обычный Bearer-токен, роль admin):

- `GET/POST /integrations/api-keys`, `DELETE /integrations/api-keys/{id}`
- `GET/POST /integrations/webhooks`, `PATCH/DELETE /integrations/webhooks/{id}`
- `POST /integrations/webhooks/{id}/test` — тестовая доставка
- `GET /integrations/webhooks/{id}/deliveries` — лог доставок
- `GET /integrations/webhooks/events` — список поддерживаемых событий
