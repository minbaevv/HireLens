#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HireLens: защита от опечаток в email + тихий режим автозакрытия интервью.

Правит файлы на месте, ничего не затирая целиком. Можно запускать повторно:
уже применённые правки пропускаются.

Запуск:  python3 scripts/hirelens_patch_email_quiet.py [корень проекта]
"""
import os
import subprocess
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/root/HireLens"
changed = []


def variants(text):
    out = [text.encode("utf-8")]
    crlf = text.replace("\n", "\r\n").encode("utf-8")
    if crlf != out[0]:
        out.append(crlf)
    return out


def contains(raw, text):
    return any(v in raw for v in variants(text))


def edit(rel, old, new, marker):
    """Замена одного уникального фрагмента с проверкой по маркеру."""
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        sys.exit("НЕТ ФАЙЛА: %s" % path)
    raw = open(path, "rb").read()
    if contains(raw, marker):
        print("  = уже есть: %s (%s)" % (rel, marker[:40]))
        return
    olds, news = variants(old), variants(new)
    for ob, nb in zip(olds, news):
        if raw.count(ob) == 1:
            open(path, "wb").write(raw.replace(ob, nb))
            print("  + правка: %s (%s)" % (rel, marker[:40]))
            if rel not in changed:
                changed.append(rel)
            return
    for ob in olds:
        if raw.count(ob) > 1:
            sys.exit("ЯКОРЬ НЕ УНИКАЛЕН в %s: %r" % (rel, old[:80]))
    sys.exit("ЯКОРЬ НЕ НАЙДЕН в %s: %r" % (rel, old[:80]))


print("Корень проекта:", ROOT)

# ---------------------------------------------------------------------------
# 1. Новый модуль проверки email
# ---------------------------------------------------------------------------
EMAIL_CHECK = '''# -*- coding: utf-8 -*-
"""Проверка email кандидата: формат и подсказка при опечатке в домене.

Кандидаты вводят почту вручную и ошибаются (gmaid.com вместо gmail.com).
Письмо на несуществующий адрес отбивается: кандидат не получает приглашение,
а доля жёстких отказов портит репутацию домена-отправителя: при ~5% провайдер
начинает ограничивать всю отправку, включая письма HR.
"""
import re
from difflib import SequenceMatcher
from typing import Optional

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}$")

# Частые почтовые домены КГ/СНГ — эталон для поиска опечаток.
KNOWN_DOMAINS = (
    "gmail.com",
    "mail.ru",
    "yandex.ru",
    "yandex.com",
    "ya.ru",
    "icloud.com",
    "outlook.com",
    "hotmail.com",
    "yahoo.com",
    "bk.ru",
    "inbox.ru",
    "list.ru",
    "rambler.ru",
    "proton.me",
    "protonmail.com",
    "live.com",
    "mail.kg",
)


def normalize_email(raw) -> str:
    """Приводит адрес к единому виду: без пробелов, скобок и в нижнем регистре."""
    return str(raw or "").strip().strip("<>").strip().lower()


def is_valid_email(raw) -> bool:
    """Формальная проверка адреса (без обращения к сети)."""
    email = normalize_email(raw)
    if not email or len(email) > 254 or ".." in email:
        return False
    if not EMAIL_RE.match(email):
        return False
    domain = email.rsplit("@", 1)[1]
    if domain.startswith("-") or domain.endswith("-") or domain.startswith("."):
        return False
    return True


def suggest_email(raw) -> Optional[str]:
    """Возвращает исправленный адрес, если домен похож на известный с опечаткой."""
    email = normalize_email(raw)
    if "@" not in email:
        return None
    local, domain = email.rsplit("@", 1)
    if not local or not domain or domain in KNOWN_DOMAINS:
        return None
    best, best_ratio = None, 0.0
    for known in KNOWN_DOMAINS:
        ratio = SequenceMatcher(None, domain, known).ratio()
        if ratio > best_ratio:
            best, best_ratio = known, ratio
    if best and best_ratio >= 0.82:
        return local + "@" + best
    return None
'''

ec_path = os.path.join(ROOT, "backend/app/services/email_check.py")
old_ec = open(ec_path, "rb").read() if os.path.exists(ec_path) else b""
new_ec = EMAIL_CHECK.encode("utf-8")
if old_ec != new_ec:
    open(ec_path, "wb").write(new_ec)
    changed.append("backend/app/services/email_check.py")
    print("  + файл: backend/app/services/email_check.py")
else:
    print("  = уже есть: backend/app/services/email_check.py")

# ---------------------------------------------------------------------------
# 2. Telegram-бот: проверка и подсказка при опечатке
# ---------------------------------------------------------------------------
TG = "backend/app/services/telegram_bot.py"

edit(
    TG,
    """def _handle_email(chat_id: int, text: str, session: dict) -> None:
    import re
    lang = _lang(session)
    if not re.match(r"[^@]+@[^@]+\\.[^@]+", text):
        send_message(chat_id, t("invalid_email", lang))
        return
    session["data"]["email"] = text
    session["state"] = STATE_WAIT_RESUME
    send_message(chat_id, t("ask_resume", lang))
""",
    """def _handle_email(chat_id: int, text: str, session: dict) -> None:
    from app.services.email_check import is_valid_email, normalize_email, suggest_email

    lang = _lang(session)
    raw = (text or "").strip()

    # Кандидат подтвердил предложенное исправление домена
    pending = session["data"].get("email_suggest")
    if pending and raw.lower() in ("да", "дa", "ооба", "иба", "yes", "y", "ok", "ок"):
        raw = pending

    if not is_valid_email(raw):
        send_message(chat_id, t("invalid_email", lang))
        return

    email = normalize_email(raw)
    fix = suggest_email(email)
    # Подсказываем один раз: если кандидат повторил тот же адрес — принимаем
    if fix and session["data"].get("email_typo_shown") != email:
        session["data"]["email_suggest"] = fix
        session["data"]["email_typo_shown"] = email
        send_message(chat_id, t("email_typo", lang, suggested=fix))
        return

    session["data"].pop("email_suggest", None)
    session["data"].pop("email_typo_shown", None)
    session["data"]["email"] = email
    session["state"] = STATE_WAIT_RESUME
    send_message(chat_id, t("ask_resume", lang))
""",
    "from app.services.email_check import",
)

# ---------------------------------------------------------------------------
# 3. Текст подсказки на трёх языках
# ---------------------------------------------------------------------------
I18N = "backend/app/services/i18n_texts.py"

edit(
    I18N,
    """    "ask_resume": {
""",
    """    "email_typo": {
        "ru": "Похоже, в адресе опечатка. Вы имели в виду <b>{suggested}</b>?\\nНапишите <b>да</b> — или пришлите правильный email.",
        "ky": "Даректе ката болушу мүмкүн. Сиз <b>{suggested}</b> деп жазгыңыз келдиби?\\n<b>ооба</b> деп жазыңыз — же туура email жөнөтүңүз.",
        "en": "That address looks like a typo. Did you mean <b>{suggested}</b>?\\nReply <b>yes</b> — or send the correct email.",
    },
    "ask_resume": {
""",
    '"email_typo": {',
)

# ---------------------------------------------------------------------------
# 4. Веб-анкета: отбрасываем явно битые адреса
# ---------------------------------------------------------------------------
CAND = "backend/app/api/candidates.py"

edit(
    CAND,
    """    # Проверяем дубликат email для этой вакансии
""",
    """    # Защита от битых адресов: письмо на несуществующий ящик отбивается
    # и портит репутацию домена-отправителя
    from app.services.email_check import is_valid_email, normalize_email

    if not is_valid_email(email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Проверьте адрес электронной почты — на него придёт приглашение",
        )
    email = normalize_email(email)

    # Проверяем дубликат email для этой вакансии
""",
    "from app.services.email_check import is_valid_email, normalize_email",
)

# ---------------------------------------------------------------------------
# 5. Веб-анкета: подсказка прямо под полем
# ---------------------------------------------------------------------------
APPLY = "frontend/src/pages/ApplyPage.jsx"

edit(
    APPLY,
    """export default function ApplyPage() {
""",
    """// Частые почтовые домены — для подсказки при опечатке (gmaid.com → gmail.com).
const KNOWN_EMAIL_DOMAINS = ['gmail.com', 'mail.ru', 'yandex.ru', 'yandex.com', 'ya.ru', 'icloud.com',
  'outlook.com', 'hotmail.com', 'yahoo.com', 'bk.ru', 'inbox.ru', 'list.ru', 'rambler.ru',
  'proton.me', 'protonmail.com', 'live.com', 'mail.kg']

function editDistance(a, b) {
  let prev = Array.from({ length: b.length + 1 }, (_, j) => j)
  for (let i = 1; i <= a.length; i++) {
    const cur = [i]
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1))
    }
    prev = cur
  }
  return prev[b.length]
}

function suggestEmail(value) {
  const v = String(value || '').trim().toLowerCase()
  const at = v.lastIndexOf('@')
  if (at < 1 || at === v.length - 1) return ''
  const local = v.slice(0, at)
  const domain = v.slice(at + 1)
  if (!domain.includes('.') || domain.length < 5 || KNOWN_EMAIL_DOMAINS.includes(domain)) return ''
  for (const known of KNOWN_EMAIL_DOMAINS) {
    if (Math.abs(domain.length - known.length) <= 2 && editDistance(domain, known) <= 2) {
      return local + '@' + known
    }
  }
  return ''
}

export default function ApplyPage() {
""",
    "function suggestEmail(value) {",
)

edit(
    APPLY,
    """              <input type="email" className="input" placeholder="ivan@example.com"
                value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} required />
""",
    """              <input type="email" className="input" placeholder="ivan@example.com"
                value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} required />
              {suggestEmail(form.email) && (
                <button type="button"
                  onClick={() => setForm(f => ({ ...f, email: suggestEmail(f.email) || f.email }))}
                  className="mt-1 text-xs text-brand-600 hover:underline text-left">
                  Возможно, вы имели в виду {suggestEmail(form.email)}? Нажмите, чтобы исправить
                </button>
              )}
""",
    "suggestEmail(form.email) && (",
)

# ---------------------------------------------------------------------------
# 6. Тихий режим: по автозакрытым интервью HR не уведомляем
# ---------------------------------------------------------------------------
IS = "backend/app/ai/interview_service.py"

edit(
    IS,
    "def _run_scoring_task(interview_id: int) -> None:",
    "def _run_scoring_task(interview_id: int, notify: bool = True) -> None:",
    "def _run_scoring_task(interview_id: int, notify: bool = True)",
)

edit(
    IS,
    """        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        if interview:
            _run_scoring(interview, db)
""",
    """        interview = db.query(Interview).filter(Interview.id == interview_id).first()
        if interview:
            _run_scoring(interview, db, notify=notify)
""",
    "_run_scoring(interview, db, notify=notify)",
)

edit(
    IS,
    "def _finalize_interview(interview, db, closing_text: str, background_tasks=None) -> dict:",
    "def _finalize_interview(interview, db, closing_text: str, background_tasks=None, notify: bool = True) -> dict:",
    "background_tasks=None, notify: bool = True) -> dict:",
)

edit(
    IS,
    """    if background_tasks is not None:
        background_tasks.add_task(_run_scoring_task, interview.id)
    else:
        _run_scoring(interview, db)
""",
    """    if background_tasks is not None:
        background_tasks.add_task(_run_scoring_task, interview.id, notify)
    else:
        _run_scoring(interview, db, notify=notify)
""",
    "background_tasks.add_task(_run_scoring_task, interview.id, notify)",
)

edit(
    IS,
    "def finish_interview(interview_id: int, db: Session, background_tasks=None) -> dict:",
    "def finish_interview(interview_id: int, db: Session, background_tasks=None, notify: bool = True) -> dict:",
    "def finish_interview(interview_id: int, db: Session, background_tasks=None, notify: bool = True)",
)

edit(
    IS,
    """        return {"interview_id": interview_id, "message": "", "is_complete": True}
    return _finalize_interview(interview, db, INTERVIEW_TIMEOUT_MESSAGE, background_tasks)
""",
    """        return {"interview_id": interview_id, "message": "", "is_complete": True}
    return _finalize_interview(
        interview, db, INTERVIEW_TIMEOUT_MESSAGE, background_tasks, notify=notify
    )
""",
    "INTERVIEW_TIMEOUT_MESSAGE, background_tasks, notify=notify",
)

edit(
    IS,
    "def _run_scoring(interview: Interview, db: Session) -> None:",
    "def _run_scoring(interview: Interview, db: Session, notify: bool = True) -> None:",
    "def _run_scoring(interview: Interview, db: Session, notify: bool = True)",
)

edit(
    IS,
    """        _run_parallel({"telegram": _notify_telegram, "email": _notify_email})
""",
    """        if notify:
            _run_parallel({"telegram": _notify_telegram, "email": _notify_email})
        else:
            logger.info(
                "Тихий режим: уведомления HR по кандидату #%s пропущены", _cand_id
            )
""",
    "Тихий режим: уведомления HR",
)

CLOSE = "backend/app/scripts/close_abandoned_interviews.py"

edit(
    CLOSE,
    "                finish_interview(interview_id, db)\n",
    "                finish_interview(interview_id, db, notify=False)\n",
    "finish_interview(interview_id, db, notify=False)",
)

# ---------------------------------------------------------------------------
# Проверки
# ---------------------------------------------------------------------------
print("\nПроверка синтаксиса:")
py_files = [
    "backend/app/services/email_check.py",
    TG,
    I18N,
    CAND,
    IS,
    CLOSE,
]
for rel in py_files:
    path = os.path.join(ROOT, rel)
    res = subprocess.run([sys.executable, "-m", "py_compile", path], capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr[:1500])
        sys.exit("ОШИБКА СИНТАКСИСА: " + rel)
    print("  ok", rel)

sys.path.insert(0, os.path.join(ROOT, "backend"))
import importlib.util

spec = importlib.util.spec_from_file_location(
    "email_check", os.path.join(ROOT, "backend/app/services/email_check.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

cases_valid = ["kuke@gmail.com", " Kuke@Gmail.com ", "a.b+c@mail.ru", "hr@asmanpark.kg"]
cases_bad = ["привет", "kuke@gmail", "kuke@@gmail.com", "kuke gmail.com", "@gmail.com", ""]
cases_typo = {
    "minbaeis@gmaid.com": "minbaeis@gmail.com",
    "test@gmial.com": "test@gmail.com",
    "test@mail.ry": "test@mail.ru",
    "test@yandx.ru": "test@yandex.ru",
}
print("\nСамопроверка email:")
for value in cases_valid:
    assert mod.is_valid_email(value), "должен быть валидным: %r" % value
    assert mod.suggest_email(value) is None, "ложная подсказка: %r" % value
for value in cases_bad:
    assert not mod.is_valid_email(value), "должен быть отклонён: %r" % value
for value, want in cases_typo.items():
    got = mod.suggest_email(value)
    assert got == want, "подсказка %r: ожидалось %r, получено %r" % (value, want, got)
print("  все проверки пройдены (%d случаев)" % (len(cases_valid) + len(cases_bad) + len(cases_typo)))

print("\nИзменённые файлы: %d" % len(changed))
for rel in changed:
    print("  ", rel)
print("\nALL_OK")
