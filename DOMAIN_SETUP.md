# 🚀 Настройка домена gethirelens.tech — чеклист «в день покупки»

Этот файл — пошаговый план на тот день, когда ты купишь домен. Идёшь сверху вниз,
ничего не пропуская. Технические детали деплоя (nginx, certbot, docker) подробно
расписаны в `PRODUCTION_DEPLOYMENT.md` — здесь общий порядок + всё про почту.

---

## 0. Купить домен

- Регистратор: **Porkbun** → домен **gethirelens.tech**.
- После покупки зайди в раздел управления DNS (Porkbun → Details → DNS Records).
- Заранее приготовь **IP сервера Contabo** (понадобится в шаге 2). Обозначим его `<CONTABO_IP>`.

---

## 1. Пойми: почта — это ДВЕ разные вещи

| Что | Зачем | Чем решаем |
|-----|-------|-----------|
| **Ящик `hello@gethirelens.tech`** | принимать письма от людей (контакт с лендинга) | пересылка (Cloudflare) или почтовый хостинг (Zoho/Yandex) |
| **Отправка писем приложением** (SMTP) | коды подтверждения, уведомления кандидатам/HR | Mailtrap (`live.smtp.mailtrap.io`) |

Это не одно и то же — настраиваются отдельно (шаги 3 и 4).

---

## 2. DNS-записи (в панели Porkbun)

### 2.1. Для сайта и API (обязательно для деплоя)

| Тип | Хост | Значение |
|-----|------|----------|
| A | `@` (корень) | `<CONTABO_IP>` |
| A | `www` | `<CONTABO_IP>` |
| A | `api` | `<CONTABO_IP>` |

> После добавления подожди распространения DNS (обычно 5–30 мин, иногда до нескольких часов).
> Поэтому DNS настраивай **первым делом с утра**.

### 2.2. Для почты — см. шаг 3 (записи зависят от выбранного провайдера).

---

## 3. Ящик hello@gethirelens.tech

Выбери ОДИН вариант.

### Вариант A — Пересылка через Cloudflare (бесплатно, рекомендую для старта) ✅

1. Заведи аккаунт на **Cloudflare**, добавь домен `gethirelens.tech`.
2. Cloudflare даст 2 NS-сервера → пропиши их в Porkbun как nameservers домена.
   (После этого DNS-записями из шага 2.1 управляешь уже в Cloudflare.)
3. Cloudflare → **Email → Email Routing** → включить.
4. Создай адрес `hello@gethirelens.tech` → **Destination** = твой личный Gmail
   (`saigonsaigonovich@gmail.com`).
5. Cloudflare сам добавит нужные **MX + SPF (TXT)** записи — подтверди.
6. (Опционально) чтобы **отвечать «от имени» hello@**: Gmail → Настройки →
   «Аккаунты и импорт» → «Отправлять письма как» → добавь адрес.

### Вариант B — Полноценный ящик Zoho / Yandex 360 (бесплатно)

1. Зарегистрируй домен в Zoho Mail или Yandex 360 для бизнеса.
2. Подтверди владение доменом (TXT-запись, которую даст провайдер).
3. Добавь их **MX + SPF + DKIM** записи в DNS.
4. Заходишь в почту через веб-интерфейс/приложение провайдера.

---

## 4. Почта приложения (SMTP, транзакционные письма)

1. В Mailtrap переключись с sandbox на **Sending Domains** → добавь `gethirelens.tech`.
2. Добавь в DNS выданные Mailtrap **SPF + DKIM (+ DMARC)** записи.
3. В прод-`.env`:
   ```
   SMTP_HOST=live.smtp.mailtrap.io
   SMTP_PORT=587
   SMTP_USER=<из Mailtrap>
   SMTP_PASSWORD=<из Mailtrap>
   SMTP_FROM=noreply@gethirelens.tech
   ```

> SPF/DKIM обязательны — без них письма приложения будут падать в спам.

---

## 5. Деплой на Contabo (детали — в PRODUCTION_DEPLOYMENT.md)

1. Залить проект на сервер, заполнить прод-`.env` (см. шаг 6).
2. `docker compose build && docker compose up -d`
3. Прогнать миграции: `docker compose exec backend alembic upgrade head`
   (автоматически НЕ запускается).
4. HTTPS: применить боевой nginx с `:443` + Let's Encrypt (certbot) —
   отдельные server-блоки для `gethirelens.tech` и `api.gethirelens.tech`.
5. Закрыть порт БД: убрать проброс `5432:5432` из `docker-compose.yml`.

---

## 6. Прод-`.env`: секреты и переменные

### Сгенерировать
```
JWT_SECRET           = openssl rand -hex 32
TELEGRAM_WEBHOOK_SECRET = openssl rand -hex 16
POSTGRES_PASSWORD    = openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 32
```

### Обязательно задать / ротировать (старые ключи утекли — сменить!)
- `GROQ_API_KEY` (реальный ключ вместо плейсхолдера)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CANDIDATE_BOT_TOKEN`
- `TELEGRAM_CANDIDATE_BOT_USERNAME` (@username бота кандидата, БЕЗ `@`)
- `SUPERADMIN_EMAILS=alex.ferguson.love@gmail.com`
- `FRONTEND_URL=https://gethirelens.tech`
- `BACKEND_URL=https://api.gethirelens.tech`
- `TELEGRAM_WEBHOOK_URL=https://api.gethirelens.tech/telegram/webhook`

---

## 7. Telegram webhooks (после старта backend)

1. `GET https://api.gethirelens.tech/telegram/set-webhook` (HR-бот)
2. `GET https://api.gethirelens.tech/telegram/set-candidate-webhook` (бот кандидата)
3. Проверь: в карточке вакансии появится ссылка «Открыть в Telegram»
   (работает, если задан `TELEGRAM_CANDIDATE_BOT_USERNAME`).

---

## 8. Google OAuth

1. В Google Cloud Console проверь Authorized redirect URI:
   `https://api.gethirelens.tech/integrations/google/callback`
2. В приложении: Integrations → **Disconnect → Connect** заново
   (чтобы выдался scope `calendar.readonly` — иначе не работают «Свободные слоты»).

---

## 9. Смоук-тест (проверка после деплоя)

- [ ] `https://gethirelens.tech` открывается по HTTPS (замок в браузере)
- [ ] `https://api.gethirelens.tech/health` отвечает `ok`
- [ ] Регистрация компании + приходит код на email (SMTP работает)
- [ ] Письмо на `hello@gethirelens.tech` доходит тебе в Gmail
- [ ] Кандидат открывает телеграм-ссылку → проходит интервью → HR получает уведомление
- [ ] Google-календарь подключается, показываются свободные слоты

---

### Итоговый порядок в день покупки

```
1. Купить домен (Porkbun)
2. DNS: A-записи @/www/api → Contabo IP   (сразу, чтобы успело распространиться)
3. Почта: Cloudflare Email Routing → hello@ падает в Gmail
4. SMTP: Mailtrap sending domain + SPF/DKIM
5. Deploy: docker up → миграции → HTTPS (certbot)
6. .env: секреты, ротация ключей
7. Telegram: set-webhook x2
8. Google OAuth: reconnect
9. Смоук-тест по чеклисту
```
