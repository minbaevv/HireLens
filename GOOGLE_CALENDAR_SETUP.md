# Настройка Google Calendar (B4 — автопланирование интервью)

Эта инструкция описывает, как получить `GOOGLE_OAUTH_CLIENT_ID` и `GOOGLE_OAUTH_CLIENT_SECRET`
и включить автопланирование интервью с созданием встреч в Google Meet.

Пока переменные не заданы, интеграция полностью отключена: в UI показывается
«Интеграция с Google не настроена», а эндпоинты `/integrations/google/*` неактивны.

---

## Шаг 1. Создать проект в Google Cloud Console

1. Откройте https://console.cloud.google.com/ и войдите под рабочим Google-аккаунтом.
2. Вверху нажмите на список проектов → **New Project**.
3. Название, например, `HireLens`. Создайте и переключитесь на него.

## Шаг 2. Включить Google Calendar API

1. Меню → **APIs & Services → Library**.
2. Найдите **Google Calendar API** → **Enable**.

## Шаг 3. Настроить OAuth consent screen

1. **APIs & Services → OAuth consent screen**.
2. User type: **External** → Create.
3. Заполните: App name (`HireLens`), User support email, Developer contact email.
4. **Scopes** — можно оставить пустым (запрашиваются в коде):
   - `https://www.googleapis.com/auth/calendar.events`
   - `https://www.googleapis.com/auth/calendar.readonly` (нужен для «Свободные слоты» / freeBusy)
   - `openid`, `email`, `profile`
5. **Test users** — добавьте свой Google-адрес (и адреса коллег, кто будет подключать календарь).
   Пока приложение в режиме Testing, входить могут только тестовые пользователи.

## Шаг 4. Создать OAuth Client ID

1. **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
2. Application type: **Web application**.
3. Name: `HireLens Web`.
4. **Authorized redirect URIs** — добавьте оба варианта, которые будете использовать:
   - `http://localhost:8000/integrations/google/callback` (локальная разработка)
   - `https://api.gethirelens.tech/integrations/google/callback` (продакшн — callback идёт на BACKEND, поддомен `api.`)
   > Важно: redirect URI должен **точно** совпадать со значением, которое использует backend
   > (`GOOGLE_OAUTH_REDIRECT_URI` или `{BACKEND_URL}/integrations/google/callback`).
5. Create → скопируйте **Client ID** и **Client Secret**.

## Шаг 5. Прописать переменные окружения

В `.env` (backend):

```env
BACKEND_URL=http://localhost:8000
GOOGLE_OAUTH_CLIENT_ID=<ваш client id>
GOOGLE_OAUTH_CLIENT_SECRET=<ваш client secret>
# Необязательно — по умолчанию = {BACKEND_URL}/integrations/google/callback
GOOGLE_OAUTH_REDIRECT_URI=
# Рабочие часы для подсказки свободных слотов
SCHEDULING_TIMEZONE=Europe/Moscow
SCHEDULING_WORK_START_HOUR=10
SCHEDULING_WORK_END_HOUR=19
SCHEDULING_SLOT_MINUTES=30
```

В продакшне выставьте `BACKEND_URL=https://gethirelens.tech` (или ваш backend-домен),
тогда redirect URI автоматически станет `https://api.gethirelens.tech/integrations/google/callback`.

## Шаг 6. Применить миграцию и перезапустить

```bash
cd backend
alembic upgrade head        # создаст таблицы google_credentials и scheduled_interviews
# перезапустите backend
```

## Шаг 7. Подключить в приложении

1. Войдите как **admin** компании → **Интеграции**.
2. В карточке **Google Календарь** нажмите **Подключить Google**.
3. Выберите аккаунт, подтвердите доступ → вернётесь обратно с сообщением «успешно подключён».
4. На карточке любого кандидата появится блок **Планирование интервью**:
   - выберите дату/время или нажмите **Свободные слоты**;
   - при отправке создаётся событие в Google Calendar со ссылкой Google Meet;
   - кандидат приглашается по email (если включена галочка);
   - встречу можно отменить — событие удалится из календаря.

---

## Частые проблемы

- **redirect_uri_mismatch** — URI в Google Cloud Console не совпадает с backend. Проверьте протокол
  (http/https), порт и путь `/integrations/google/callback`.
- **access_denied / это тестовое приложение** — добавьте свой email в **Test users** (Шаг 3.5),
  либо опубликуйте приложение (Publish App).
- **invalid_grant при обновлении токена** — переподключите Google в разделе «Интеграции»
  (refresh-токен мог быть отозван).
- **Нет ссылки Google Meet** — убедитесь, что Calendar API включён и аккаунт поддерживает Meet.

## Публикация приложения (по желанию)

Пока приложение в режиме **Testing**, подключаться могут только Test users, а refresh-токен
живёт до 7 дней. Для боевого использования: OAuth consent screen → **Publish App**
(для запрашиваемых scope верификация Google обычно не требуется, но возможен экран
«приложение не проверено» — это нормально для внутреннего использования).
