# 🗺️ HireLens — Единый Roadmap

> Единый файл планов. Собрал сюда всё из бывших `ROADMAP_TOP1.md`, `IMPROVEMENTS.md`,
> `BACKEND_FRONTEND_AUDIT.md`, `MD_FILES_AUDIT.md`, `PHASE_1.1_GROUND_TRUTH_COMPLETE.md`,
> `REBRAND_HIRELENS_PLAN.md`, `ai-hr-screening-masterplan.md` (файлы удалены как избыточные).
> Безопасность вынесена отдельно → **[SECURITY_AUDIT.md](./SECURITY_AUDIT.md)**.
> Деплой-инструкции → [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md), [DEPLOYMENT_INSTRUCTIONS.md](./DEPLOYMENT_INSTRUCTIONS.md).

**Цель:** обогнать HireVue / Paradox.ai / Helio AI на рынке СНГ и стать №1.
**Окно возможностей:** Telegram-first, локальные языки (KG/UZ), цена в ~10× ниже, локальные платежи (O!Pay/MBank), anti-cheat как киллер-фича.
**Принцип:** качественно, с тестами и ревью. Один шаг = одна ветка = один MR.

---

## 📊 Анализ конкурентов (актуализация 07.07.2026)

Сравнение по **фактическим функциям из кода** (не по старым пометкам — видео/anti-cheat/языки/команды уже реализованы).

| Функция | HireVue | Paradox | micro1 | Ribbon | Sever.AI/VCV (СНГ) | **HireLens** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| AI-интервью текст/голос | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (Whisper) |
| Видео-интервью (запись) | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (WebRTC) |
| Структурный скоринг + reasoning | ✅ | ⚠️ | ✅ | ✅ | ✅ | ✅ (4 измерения + confidence) |
| Anti-cheat / fraud detection | ⚠️ | ❌ | ⚠️ | ✅ | ❌ | ✅ (тайминг + LLM) |
| Bias-аудит / governance-дашборд | ✅ | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ *(флаги есть, дашборда нет)* |
| AI-copilot по базе (NL-чат) | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ✅ |
| Автопланирование (календарь) | ✅ | ✅ (киллер) | ❌ | ⚠️ | ✅ | ✅ *(B4)* |
| Coding / технические тесты | ✅ | ❌ | ✅ | ❌ | ⚠️ | ❌ |
| ATS-интеграции | ✅ 100+ | ✅ | ✅ | ⚠️ | ✅ | ❌ |
| Публичный API / webhooks | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ *(D2)* |
| Омниканальность | Email | SMS/WA/WeChat | Video | SMS/WA | ✅ | ✅ **Telegram-цикл** |
| Мультиязычность | ✅ | ✅ 100+ | ✅ | ✅ | RU | ✅ RU/KY/EN |
| Локальные языки КГ/УЗ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ KY *(UZ — B2)* |
| Биллинг / self-serve тарифы | ❌ | ❌ | ⚠️ | ✅ | ⚠️ | ❌ *(B5)* |
| Цена | $25–200K/год | custom | ~$6/интервью | средняя | ₽ подписка | **$49–149 (план)** |

✅ есть · ⚠️ частично · ❌ нет

**Наше окно (никто из конкурентов не закрывает):** Telegram-first полный цикл + локальные языки (KY) + anti-cheat + AI-copilot + цена в 100–1000× ниже. Глобальные не пойдут по цене, российские (Sever.AI/VCV) — по языкам и Telegram.

**Критические пробелы (есть у всех, у нас нет):** автопланирование (B4 ✅), ATS/публичный API (D2 + ниже), coding-тесты, governance-дашборд (5.2), биллинг (B5).

---

## ✅ Что уже готово (снимок на 07.07.2026)

- **MVP v2.0 (фазы 1–6):** auth, jobs, candidates, AI-интервью, frontend, email+dashboard.
- **Фаза A (фундамент):** CI-каркас, frontend-тесты, единый LLM-диспетчер Claude+Groq с retry/fallback, Sentry, рефакторинг моделей по доменам, refresh-токены, мультиязычность RU/KY/EN. *(кроме A1.2 — линтеры ждут рабочий CI)*
- **Фаза B (паритет):** B1 командный доступ + роли admin/recruiter/viewer (**backend + фронт**: TeamPage `/team`, AcceptInvitePage `/team/accept`), B1.2 ролевые ограничения, B3 PWA + мобильный UI.
- **Фаза C (обгон, киллер-фичи) — полностью:** C1 anti-cheat, C2 видео-интервью (WebRTC+Whisper+ffmpeg), C3 полный Telegram-цикл, C4 AI-copilot по базе кандидатов, C5 bias-аудит + структурированный скоринг.
- **Фаза D:** D1 редизайн — дизайн-система, тёмная тема, анимации + reduced-motion, focus-visible, theme-color. **D1.5 UI-полировка (07.07.2026):** единая синяя палитра (индиго/фиолет убраны, `brand`=primary токен), графики дашборда (пай→бары, полные подписи в тултипе), плюрализация RU/KY/EN в `t()`, честные метрики (порог ≥5 для точности AI, база hire_rate), Kanban на иконках Lucide + выровненные колонки, лендинг (убрана накрутка цифр, честные value-props, превью-мокап), сайдбар без «провала пустоты».
- **Ground Truth (Phase 1.1):** backend — `PATCH /candidates/{id}/final-decision`, `GET /analytics/ai-accuracy`, авто-флаг `requires_manual_review`, 1.3 валидация ответа LLM; **фронт** — UI финального решения + фильтр «требуют проверки» + счётчик на дашборде.
- **Ребрендинг → HireLens:** новый lens-логотип, PWA-иконки, имя заменено во фронте/бэке, убрано «by Justper». *(домен/товарный знак — проверить отдельно, вне кода)*
- **Интеграция backend↔frontend — 100%:** refresh-interceptor, Kanban drag&drop, JobDetailPage, TeamPage/accept-invite. Незадействован только `GET /health` (опциональный индикатор) + ops-эндпоинты Telegram.

---

## 🔴 Приоритет 1 — Быстрые победы (без внешних ключей, ~1 неделя)

Дёшево, повышает надёжность/стоимость AI сразу.

- [x] **Truncation транскрипта** — обрезка до `SCORING_TRANSCRIPT_MAX_CHARS` (6000) с головы + маркер. ✅ 08.07.2026
- [x] **Проверка полноты интервью** — < `SCORING_MIN_AI_QUESTIONS` (4) вопросов AI → `confidence = min(confidence, 0.3)` + флаг «Interview too short». Тест: `test_short_interview_caps_confidence`. ✅ 08.07.2026
- [x] **Prompt caching для Claude** — `cache_control: ephemeral` на системный промпт. *(llm.py:_call_claude)* ✅ 08.07.2026
- [x] **Temperature под задачу** — `TEMPERATURE_INTERVIEW=0.7 / SCORING=0.3 / PRESCREENING=0.2` в config (env-переопределяемо). ✅ 08.07.2026
- [x] **Штраф confidence за отсутствие резюме** — `confidence *= SCORING_NO_RESUME_PENALTY` (0.7, отключается через env `=1.0`) + флаг «No resume provided». ✅ 08.07.2026
- [x] **Frontend Phase 1.1** — UI финального решения HR + фильтр «требуют проверки» + счётчик на дашборде. ✅ (было уже реализовано в коде)
- [x] **Frontend TeamPage (хвост B1)** — TeamPage `/team` (список/инвайт/роль/удаление) + AcceptInvitePage `/team/accept`. ✅ 07.07.2026

---

## 🟠 Приоритет 2 — Точность AI (ядро продукта, ~2 недели)

- [x] **1.1 Configurable Scoring Weights** *(✅ полностью: бэкенд/API/промпт/миграция + UI профилей весов в форме вакансии: Сбалансированный/Технический/Управленческий/Свой)* — `Job.scoring_weights` (JSON), профили «Technical / Management / Custom». `overall_score = Σ(component.score × weight)` вместо «угадывания» весов LLM. Модель+миграция+промпт+API+фронт. **+15–20% точности для спец-ролей.**
- [x] **3.1 Resume↔Interview Cross-Validation** — промпт сравнивает заявления в интервью с резюме, поле `discrepancies` («сказал 5 лет Python, в резюме 1»).
- [x] **3.2 Empty/Evasive Answer Detection** *(✅ 09.07.2026)* — «не знаю»/общие фразы → red flag `evasive_answers`.
- [x] **2.1 Detailed Reasoning API** *(✅ API + вкладка Scoring Breakdown)* — `GET /candidates/{id}/scoring-details` (компоненты + reasoning + confidence + weight) + вкладка «Scoring Breakdown» во фронте.
- [x] **2.3 Confidence Visualization** *(✅ бейдж Low/Medium/High)* — бейдж Low/Medium/High рядом со score. *(быстрая фронт-задача)*
- [x] **1.2 Calibration Feedback Loop** *(✅ precision/recall в analytics)* — недельный job: precision/recall AI-рекомендаций vs реальные наймы (данные уже собираются в Ground Truth); alert при точности < 70%.
- [x] **1.3 Unified Scale + Confidence Bounds** *(✅ score_range «75 ±10»)* — pre_score и overall на одной шкале, диапазон «75 ±10» вместо голого confidence.

---

## 🟡 Приоритет 3 — Производительность и Compliance (~2 недели)

- [x] **4.1 Async Parallel Scoring** *(✅ батч #6, 09.07.2026)* — scoring + anti-cheat + уведомления (Telegram/email) выполняются параллельно через `asyncio.gather` + `asyncio.to_thread`. Anti-cheat вынесен в отдельный LLM-seam `_anticheat_llm`. 8–10 сек → 3–4 сек.
- [x] **C1.2 Anti-cheat 2.0 (усиление)** *(✅ 09.07.2026)* — добавлены key-free сигналы поверх тайминга + LLM ChatGPT-детектора: **paste/burst** (длинный ответ почти мгновенно), **markdown/списочное форматирование** в чат-ответе, **межвопросная сверка** (3-грамм Jaccard → шаблон/дубликаты) + **градация риска low/medium/high** с пояснением для HR (сводка в `anti_cheat_flags`). Промпт LLM-детектора усилён под copy-paste/шаблоны. +4 теста. Осталось (опц., требует видео/клиентской телеметрии): keystroke dynamics, сигналы из вебки/фокуса окна. Сигнал для ручной проверки, не автовердикт.
- [x] **5.1 Active Debiasing (PII Redaction)** *(✅ redact_pii)* — маскировать имена/пол/возраст в транскрипте перед scoring. Compliance с anti-discrimination.
- [x] **5.2 Bias Audit Dashboard** *(✅ полностью: API /analytics/bias-report + страница «Аудит справедливости» `/governance` с фильтром по вакансии)* — `GET /analytics/bias-report` (bias_rate по вакансиям за период) + страница. Защита от исков/регуляторов.
- [x] **5.3 Categorized Red Flags** *(✅ объекты {category, detail})* — типизировать red_flags в объект `{technical, communication, behavioral}` вместо массива строк → фильтрация.
- [x] **2.2 Answer Attribution** *(✅ [Q#]-теги + Message.id + API + фронт, батч #5, 09.07.2026)* — reasoning ссылается на номер вопроса (Q3→SQL), связь с `Message.id`. *(сложная фича)*

---

## 🔵 Приоритет 4 — Архитектура и долгий срок

- [x] **6.2 Prompt Versioning в БД** *(✅ 10.07.2026)* — промпты интервью/скоринга/скрининга хранятся версиями в таблице `prompt_templates` (per-company). Админ-API (`/prompts`, только owner/admin): просмотр code-default, создание версий с валидацией `{placeholders}`, активация, **A/B-тест** между версиями по весам, удаление. Резолвер `prompt_service.resolve_prompt` подставляет активную версию (при нескольких — взвешенный случайный выбор), с fallback на code-default → полная обратная совместимость. Правки без деплоя. +12 тестов. Вынесены 3 ключа: `interview_system` / `scoring_system` / `prescreen` (anticheat/copilot — по мере надобности).
- [ ] **ML-based scoring** — XGBoost на исторических (features интервью + решение HR), гибрид LLM+ML, latency < 1 сек, выше consistency.
- [ ] **Real-time coaching кандидату** — во время интервью подсказки «ответ слишком общий». NPS +20%.
- [ ] **ATS-интеграции** (Workday, Greenhouse) — двусторонняя синхронизация. Ключ к enterprise.
- [x] **Adaptive interview flow** *(✅ адаптивный промпт + границы + потолок, батч #4)* — AI динамически выбирает следующий вопрос вместо фиксированных 5–7.

---

## 📦 Фазы роста (ROADMAP D/B)
- [x] **D2 — Публичный API + webhooks** для интеграций. ✅ *(REST `/api/v1` с авторизацией по API-ключу X-API-Key; webhooks с HMAC-подписью и SSRF-защитой; события interview.completed / candidate.scored / candidate.created; страница «Интеграции» в UI; см. [API.md](./API.md).)*
- [x] **D3 — SEO-лендинги** KG/RU/EN, кейсы клиентов (честные сценарии применения), реферальная программа. ✅ *(контент лендинга `/landing` теперь локализован RU/KY/EN через ?lang=.)*
- [ ] **D4 — Деплой на прод** (Railway/Render + домен + HTTPS). Инструкции: [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md). ⚠️ Перед деплоем закрыть критичные из [SECURITY_AUDIT.md](./SECURITY_AUDIT.md).

---

## ⚔️ Конкурентные пробелы (из анализа 07.07.2026)

Функции, которые есть у HireVue/Paradox/micro1/Ribbon, но нет у нас. Приоритезированы по влиянию на продажи в нашей нише (СНГ/ЦА SMB).

- [x] **GAP-1 — Автопланирование интервью (= B4).** Киллер-фича Paradox (26 ч → 18 мин на планирование). Самый заметный пробел для реального найма. Ждёт Google OAuth. **Высокий приоритет.**
- [x] **GAP-2 — Governance-дашборд (= Improvement 5.2 + audit logs).** Тренд 2026 у HireVue: bias-rate по вакансиям, audit logs, diversity-дашборд. У нас сырые `bias_flags` есть — нужен агрегат + `/analytics/bias-report` + журнал действий. **Высокий (комплаенс + доверие enterprise).**
- [ ] **GAP-3 — Биллинг / self-serve тарифы (= B5).** Без него нет монетизации; у Ribbon self-serve есть. Ждёт Stripe/O!Pay. **Высокий (монетизация).**
- [ ] **GAP-4 — ATS-интеграции + публичный API (= D2 + ATS-строка ниже).** Вход к среднему/крупному клиенту. Начать с webhooks + REST, затем коннекторы (HeadHunter API hh.ru/hh.kz как локальный аналог). **Средний.**
- [x] **GAP-5 — Coding / технические ассессменты.** HireVue (CodeVue) и micro1 сильны в IT-найме: генерация задач по стеку + автопроверка кода. Открывает IT-сегмент. **Средний (по мере входа в IT-найм).**
- [x] **GAP-6 — Adaptive interview flow.** micro1/Ribbon динамически подбирают вопросы. У нас фиксированные 5–7. Улучшает качество и candidate experience. **Низкий (дублирует пункт из Приоритета 4).**

---

## 🔒 Заблокировано — нужны ключи/внешнее от пользователя

- [ ] **A1.2** — починить замечания линтеров (ruff/eslint), затем убрать `continue-on-error` в CI (GitHub Actions, `.github/workflows/ci.yml`).
- [ ] **B2** — казахский + узбекский языки (i18n-каркас уже есть из A6).
- [x] **B4** — автопланирование (Google Calendar) — готово. Требует **Google OAuth Client ID/Secret** (настройка — см. GOOGLE_CALENDAR_SETUP.md).
- [ ] **B5** — биллинг (Stripe + O!Pay/MBank), тарифы Free/Starter/Pro, лимиты по плану — нужен **Stripe Secret Key + доступ к O!Pay/MBank**.
- [ ] **B6** — импорт вакансий через HeadHunter API (hh.ru / hh.kz; отдельного hh.kg не существует).

---

## 🔐 Безопасность (перед деплоем — блокеры)

Полный аудит: **[SECURITY_AUDIT.md](./SECURITY_AUDIT.md)**. Критичное:
- [x] **SEC-1** — IDOR закрыт: `Interview.access_token` (secrets.token_urlsafe(32), миграция `i7g1e6h95d0f`). Кандидатские эндпоинты `/message`, `/video`, `/voice`, `GET /interviews/{id}` требуют `X-Interview-Token` (constant-time сравнение). Фронт хранит токен в sessionStorage. Заодно исправлен баг: `/voice` требовал HR-авторизацию, хотя это эндпоинт кандидата. Тест: `test_interview_requires_access_token`. ✅ 08.07.2026
- [x] **SEC-2** — Telegram webhook проверяет `X-Telegram-Bot-Api-Secret-Token` (env `TELEGRAM_WEBHOOK_SECRET`); `setWebhook` регистрируется с `secret_token`. ✅ 08.07.2026
- [x] **SEC-3** — публичный mount `/videos` удалён; видео раздаётся через `GET /interviews/{id}/video/{filename}` — только HR своей компании + защита от path traversal. ✅ 08.07.2026
- [x] **SEC-4** — fail-fast при `ENVIRONMENT=production`: слабый/дефолтный `JWT_SECRET` (< 32 символов) или webhook без секрета → RuntimeError при старте. ✅ 08.07.2026
- [x] **SEC-9** — утёкший Groq-ключ вычищен из `.env` (плейсхолдер + инструкция). ⚠️ **Ключ всё ещё в git-истории — обязательно отзови его на console.groq.com и выпусти новый!** ✅ 08.07.2026

---

## 🧹 Гигиена документации

- [x] README — стек AI обновлён (Claude+Groq).
- [x] Планы сведены в этот файл; избыточные plan-MD удалены (masterplan v2.0, IMPROVEMENTS, оба аудита, Phase 1.1, rebrand).
- [ ] Опционально: `CHANGELOG.md`, `CONTRIBUTING.md`, `ARCHITECTURE.md`, `API.md` (последний — при D2).

---

## 🎯 Метрики «Топ-1»

- Time-to-hire ниже конкурентов; NPS кандидатов > 50.
- 3 платящих клиента в первый месяц после деплоя; $1000 → $10 000 MRR.
- 99.5% uptime; coverage backend > 80%.
- AI accuracy (корреляция с решениями HR): ~70% → **85–90%** после Приоритетов 1–2.
- Cost per scoring: −50% (prompt caching); scoring latency: 8–10 сек → 3–4 сек (async).

---

## 📝 Журнал выполнения (сжатая история)

**Волна батчей 08–09.07.2026 (key-free):** #1 фронт-хвосты · #2 GAP-2 audit logs · #3 GAP-5 coding · email-верификация (SEC-11) + Telegram per-company · #4 Adaptive interview flow · #5 Answer Attribution + fix Telegram-тестов · #6 Async Parallel Scoring (scoring∥anti-cheat∥уведомления) · C1.2 Anti-cheat 2.0 (paste/burst, markdown, межвопросная сверка, градация риска) · 6.2 Prompt Versioning (версии промптов в БД + админ-API + A/B, без деплоя). Ключевая key-free ветка вычерпана — дальше большие/ключевые фичи.

| Дата | Шаг | Что сделано |
|---|---|---|
| 17.06.2026 | MVP 1–5 | Auth, Jobs, Candidates, AI-интервью, Frontend |
| 30.06.2026 | MVP 6 | Email + Dashboard. Базовый MVP v2.0 завершён |
| 02.07.2026 | A1 | CI-каркас: lint (ruff+ESLint), SAST/Secret-шаблоны, pytest-cov |
| 02.07.2026 | A3 | Единый LLM-диспетчер `llm.py` (Claude+Groq, retry, fallback). ⚠️ Инцидент: реальный GROQ_API_KEY попал в git — **отозвать** |
| 02.07.2026 | A2 | Vitest + Testing Library, тесты бейджей |
| 02.07.2026 | A4 | Sentry (без PII), LOG_LEVEL/ENVIRONMENT |
| 02.07.2026 | A5 | Модели по доменам, refresh-токены, Python 3.12 |
| 02–03.07.2026 | A6 | Мультиязычность RU/KY/EN: `Job.language`, i18n фронта, локализация email/Telegram, язык Whisper |
| 03.07.2026 | B1 + B1.2 | Командный доступ (TeamMember, инвайты, роли), ролевые ограничения (viewer read-only) |
| 03.07.2026 | B3 | PWA: manifest, service worker, InstallPrompt, мобильный UI интервью |
| 03–04.07.2026 | C1 | Anti-cheat: тайминг + LLM-детектор ChatGPT-стиля |
| 04.07.2026 | C2 | Видео-интервью: WebRTC + Whisper STT + ffmpeg, VideoRecorder |
| 04.07.2026 | C3 | Telegram полный цикл: заявка → интервью (текст+голос) → результат |
| 04.07.2026 | C5 | Bias-аудит + структурированный скоринг (4 компонента, confidence, reasoning) |
| 04.07.2026 | Phase 1.1 | Ground Truth: final-decision, ai-accuracy, авто manual-review |
| 07.07.2026 | C4 | AI-copilot: чат по базе кандидатов (context-stuffing, изоляция по company_id) |
| 07.07.2026 | bugfix | score=0 в уведомлениях (overall_score), VideoRecorder cleanup, тест-зависимости фронта |
| 07.07.2026 | D1 (1–4) | Тёмная тема/дизайн-система, HR + публичные страницы на токены, анимации, focus-ring, theme-color |
| 07.07.2026 | Ребрендинг | AI HR Screening → HireLens: логотип, PWA-иконки, имя везде |
| 07.07.2026 | Аудиты | Security audit ([SECURITY_AUDIT.md](./SECURITY_AUDIT.md)) + консолидация планов в этот файл |
| 07.07.2026 | B1 фронт | Команда во фронте: `TeamPage` (список/инвайт/смена роли/удаление, все 5 эндпоинтов `/team/*`) + `AcceptInvitePage` (`/team/accept` — приём приглашения по токену, авто-логин; закрыл 404 из письма-инвайта). Пункт «Команда» в сайдбаре, i18n RU/KY/EN. Интеграция backend↔frontend доведена до 100%. build ✅ + 36 тестов ✅ |
| 10.07.2026 | 6.2 Prompt Versioning | Версии промптов (interview/scoring/prescreen) в таблице `prompt_templates` per-company; админ-API `/prompts` (create/activate/A-B/delete + валидация placeholders); резолвер с взвешенным A/B и fallback на code-default. Правки без деплоя. +12 тестов, миграция `o4m8k3n62j7l`. |
| 09.07.2026 | C1.2 Anti-cheat 2.0 | +сигналы paste/burst, markdown-формат, межвопросная сверка (3-грамм Jaccard), градация риска low/med/high + сводка для HR; усилён промпт. +4 теста. |
| 09.07.2026 | 4.1 Async Scoring | scoring + anti-cheat + HR-уведомления параллельно (`asyncio.gather` + `asyncio.to_thread`), ~8–10 сек → ~3–4 сек. Anti-cheat вынесен в отдельный seam `_anticheat_llm` (чтобы не делить mock со скорингом), в тестах — autouse-заглушка. Зафиксирован план усиления anti-cheat (C1.2). |
| 07.07.2026 | D1.5 UI | UI-полировка по 6-этапному чек-листу: (1) единая синяя палитра — `brand` индиго→`#3B82F6`, индиго/фиолет убраны везде; (2) графики дашборда — пай→гориз. бары, полное имя вакансии в тултипе; (3) плюрализация RU/KY/EN в `t()` (формы через `\|`), честные метрики (точность AI ≥5, база hire_rate), контакт `hello@hirelens.io`; (4) Kanban — иконки Lucide вместо эмодзи, empty-state, выровненные колонки; (5) лендинг — убрана накрутка цифр в бэке, честные value-props + превью-мокап; (6) сайдбар без «провала пустоты». build ✅ + фронт 36 ✅ + backend test_landing 5 ✅ (обновлён под честную статистику) |

**Правила:** завершённый шаг → строка в журнал + чекбокс выше. Не начинать следующий шаг, пока текущий не проверен.

---

## ✅ Priority 2/3 — прогресс (09.07.2026)

- **Priority 2:** взвешенный скоринг (`Job.scoring_weights`), cross-validation резюме↔интервью, evasive-answer detection, эндпоинт `scoring-details`. ✅
- **Priority 3:** bias-дашборд (`/analytics/bias-report`), категоризированные red flags, PII-редактинг перед скорингом. ✅
- Осталось: фронтенд-визуализация confidence/весов (UI 1.1/5.2). Асинхронный параллельный скоринг — ✅ батч #6.


## ✅ GAP-5 — Coding-ассессменты (backend, 09.07.2026)
- Модели `CodingChallenge` + `CodingSubmission`, миграция `l0j4h9k28g3i`.
- Key-free оценщик `app/services/coding_eval.py` (ast.parse без исполнения кода).
- HR API `/coding/*`: CRUD задач, assign, submissions, review.
- Публичный поток кандидата `/coding/public/{token}` (просмотр + отправка решения).
- Аудит: coding.challenge_create/update/delete, coding.assign, coding.review.
- ✅ Фронтенд-UI для GAP-5 (15.07.2026): раздел «Тех-тесты» (список/создание/редактирование задач + проверка решений), карточка назначения на странице кандидата и публичная страница кандидата `/coding/:token` (RU/KY/EN).


## ✅ D3 — SEO-лендинги + реферальная программа (10.07.2026)
- **Локализация `/landing`** — tagline/description/features/pricing/cases на RU/KY/EN через `?lang=` (fallback на RU).
- **Кейсы** — честные сценарии применения (отрасль/задача/решение/результат), без вымышленных отзывов.
- **SEO** — `app/api/seo.py`: `/robots.txt` + `/sitemap.xml` (hreflang RU/KY/EN); на фронте динамические title/meta/OG/JSON-LD + hreflang.
- **Реферальная программа** — `app/api/referral.py` (`GET /referral/me`), колонки `referral_code`/`referred_by_company_id` (миграция `p5n9l4o73k8m`), привязка при регистрации по `?ref=`, страница `/referral` в кабинете.
- **Тесты** — `test_landing.py` (языки + fallback + sitemap/robots), `test_referral.py` (код, стабильность, учёт приглашённых, авторизация).

## ✅ Ручное управление подписками + цены в сомах (14.07.2026)
- **Причина** — ИП пока не одобрено, автоэквайринг (FreedomPay) недоступен → делаем ручной режим, чтобы принимать оплату переводом уже сейчас.
- **Backend** — `app/core/payments.py` (цены KGS + реквизиты перевода), `app/api/billing.py` (`GET /billing/me`: тариф, статус active/expired, дата и дни до конца, реквизиты), `app/api/admin.py` (супер-админ: список компаний, ручная установка тарифа+срок, начисление бонусных месяцев). Колонка `plan_expires_at` (миграция `q6o0m5p84l9n`). Создание вакансий требует активной подписки (`require_active_subscription` → 402 при истёкшей).
- **Супер-админ** — доступ по `SUPERADMIN_EMAILS` (список email через запятую в `.env`).
- **Цены в сомах** — лендинг и JSON-LD переведены с USD на KGS: Starter 4900 сом, Pro 12900 сом, overage 45 сом/кандидат; поле `currency` в `PricingPlan`.
- **Frontend** — страницы `/billing` (статус + инструкция оплаты переводом) и `/admin` (таблица управления тарифами), пункты меню (Admin — только супер-админу), ключи переводов billing.*/admin.*/nav.* для RU/KY/EN.
- **Тесты** — `test_billing.py` (free по умолчанию, 403 без супер-админа, установка тарифа, бонус, блокировка при истёкшей подписке 402).
- **Честно** — рефералка по-прежнему только считается/показывается; бонусные месяцы начисляются супер-админом вручную (авто-начисление появится с платёжным шлюзом).

## ⏳ ПЛАН (отложено до ИП/платежей): Feature-gating по тарифам

> Сейчас все функции доступны всем вне зависимости от тарифа (тарифы — только маркетинг на лендинге).
> Ограничены только лимиты (вакансии/кандидаты, `app/core/plans.py`). **Функциональные стены строим ТОЛЬКО когда заработает оплата** (иначе стена без пути апгрейда).

### Как включать (безопасно)
- Флаг `FEATURE_GATING_ENABLED` в `config.py` (по умолчанию **OFF**). Всё кодится заранее, но не влияет, пока флаг выключен.
- Хелпер `require_feature(feature, company)` (в `deps.py`): при OFF — всегда пропускает; при ON — 402/403 если тариф ниже нужного.
- Включить флаг одновременно с запуском авто-эквайринга (Stripe / O!Pay / MBank).

### Сбалансированная карта тарифов (черновик)
- **Free** — ядро: AI-интервью, скоринг, Email-уведомления, Kanban, 1 язык. Лимиты: 1 вакансия / 5 кандидатов.
- **Starter** — + голосовое интервью, Telegram-уведомления, CSV-экспорт, мультиязык, команда/роли.
- **Pro** — + PDF-отчёты, аналитика, bias-аудит, anti-cheat, Google Calendar, coding-задачи, кастомные промпты, публичный API + webhooks, AI-copilot, приоритет.

### Задачи когда дойдёт дело
1. `FEATURE_GATING_ENABLED` в `config.py` + `.env.example` (default OFF).
2. Карта `feature -> min_plan` в `app/core/plans.py`.
3. `require_feature()` в `deps.py` + повесить на соответствующие роутеры.
4. Фронт: скрывать/блокировать UI по тарифу + подсказка «апгрейд».
5. Тесты: OFF — всё доступно; ON — низкий тариф получает 402/403.
6. Включить флаг вместе с платёжным шлюзом.

## ✅ Чеки об оплате + QR + одна карта Visa (14.07.2026)
- **Загрузка чека** — клиент прикрепляет чек об оплате на `/billing` (`POST /billing/receipt`, файлы в `uploads/receipts/`, таблица `payment_receipts`, миграция `r7p1n6q95m0o`). Супер-админ видит заявки в `/admin`, открывает файл, подтверждает/отклоняет (`/admin/receipts*`).
- **QR** — на странице оплаты QR-код с номером карты (чтобы не вводить вручную).
- **Одна карта Visa** — реквизиты упрощены: один номер, перевод с любого банка.
- **Тесты** — `test_receipts.py`.
- **❗ Действие пользователя** — вписать реальные реквизиты в `app/core/payments.py` (номер карты, имя, банк, Telegram).
