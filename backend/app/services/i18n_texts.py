"""Локализация текстов для уведомлений кандидатам (email + Telegram-бот).

Язык уведомления берётся из Job.language (ru | ky | en, см. backend/app/models/job.py).
HR-уведомления (Telegram HR, email HR) язык не меняют — остаются на русском.
"""
from __future__ import annotations

SUPPORTED_LANGUAGES = ("ru", "ky", "en")
DEFAULT_LANGUAGE = "ru"


def normalize_language(code: str | None) -> str:
    """Возвращает поддерживаемый код языка, fallback — русский."""
    return code if code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


# ---------------------------------------------------------------------------
# Email кандидату: изменение статуса заявки
# ---------------------------------------------------------------------------

CANDIDATE_STATUS_EMAIL: dict[str, dict[str, dict[str, str]]] = {
    "hired": {
        "ru": {
            "title": "🎉 Поздравляем!",
            "color": "#10B981",
            "message": (
                "Мы рады сообщить, что вы прошли отбор! "
                "Наша команда свяжется с вами в ближайшее время."
            ),
        },
        "ky": {
            "title": "🎉 Куттуктайбыз!",
            "color": "#10B981",
            "message": (
                "Сиз тандоодон өткөнүңүздү билдиргенге кубанычтабыз! "
                "Биздин команда жакында сиз менен байланышат."
            ),
        },
        "en": {
            "title": "🎉 Congratulations!",
            "color": "#10B981",
            "message": (
                "We are happy to let you know that you have been selected! "
                "Our team will contact you shortly."
            ),
        },
    },
    "rejected": {
        "ru": {
            "title": "О результате вашей заявки",
            "color": "#EF4444",
            "message": (
                "Спасибо за интерес к нашей компании. К сожалению, на этот раз "
                "мы остановились на другом кандидате. Удачи!"
            ),
        },
        "ky": {
            "title": "Арызыңыздын жыйынтыгы жөнүндө",
            "color": "#EF4444",
            "message": (
                "Компаниябызга кызыгууңуз үчүн рахмат. Тилекке каршы, бул жолу "
                "биз башка талапкерди тандадык. Ийгилик каалайбыз!"
            ),
        },
        "en": {
            "title": "About your application result",
            "color": "#EF4444",
            "message": (
                "Thank you for your interest in our company. Unfortunately, "
                "we have chosen another candidate this time. Good luck!"
            ),
        },
    },
}

EMAIL_GREETING = {"ru": "Уважаемый(-ая)", "ky": "Урматтуу", "en": "Dear"}
EMAIL_JOB_LABEL = {"ru": "Вакансия", "ky": "Вакансия", "en": "Position"}


# ---------------------------------------------------------------------------
# Telegram-бот: диалог с кандидатом
# ---------------------------------------------------------------------------

TG_TEXTS: dict[str, dict[str, str]] = {
    "greeting_default": {
        "ru": "Привет! Чтобы подать заявку на вакансию, открой ссылку из объявления.",
        "ky": "Салам! Вакансияга арыз берүү үчүн жарыядагы шилтемени ач.",
        "en": "Hi! To apply for a job, open the link from the job posting.",
    },
    "cancelled": {
        "ru": "❌ Отменено. Напиши /start чтобы начать заново.",
        "ky": "❌ Жокко чыгарылды. Кайра баштоо үчүн /start деп жаз.",
        "en": "❌ Cancelled. Type /start to begin again.",
    },
    "no_token": {
        "ru": "Для подачи заявки открой ссылку из объявления о вакансии.",
        "ky": "Арыз берүү үчүн вакансия жарыясындагы шилтемени ач.",
        "en": "To apply, please open the link from the job posting.",
    },
    "job_not_found": {
        "ru": "❌ Вакансия не найдена или уже закрыта.",
        "ky": "❌ Вакансия табылган жок же жабылган.",
        "en": "❌ Job not found or already closed.",
    },
    "ask_name": {
        "ru": "Добро пожаловать! 👋\n\nВы подаёте заявку на вакансию: <b>{job_title}</b>\n\nПожалуйста, напишите ваше <b>имя и фамилию</b>:",
        "ky": "Кош келиңиз! 👋\n\nСиз төмөнкү вакансияга арыз берип жатасыз: <b>{job_title}</b>\n\nСураныч, <b>атыңызды жана фамилияңызды</b> жазыңыз:",
        "en": "Welcome! 👋\n\nYou are applying for: <b>{job_title}</b>\n\nPlease enter your <b>full name</b>:",
    },
    "name_too_short": {
        "ru": "Пожалуйста, введите полное имя.",
        "ky": "Сураныч, толук атыңызды жазыңыз.",
        "en": "Please enter your full name.",
    },
    "ask_email": {
        "ru": "Отлично, <b>{name}</b>! Теперь введите ваш <b>email</b>:",
        "ky": "Мыкты, <b>{name}</b>! Эми <b>email</b> дарегиңизди жазыңыз:",
        "en": "Great, <b>{name}</b>! Now please enter your <b>email</b>:",
    },
    "invalid_email": {
        "ru": "Неправильный email. Попробуйте ещё раз:",
        "ky": "Email туура эмес. Кайра аракет кылыңыз:",
        "en": "Invalid email. Please try again:",
    },
    "ask_phone": {
        "ru": "Приятно, <b>{name}</b>! Теперь оставьте <b>номер телефона</b> — по нему с вами свяжутся.\nНажмите кнопку ниже или напишите номер вручную:",
        "ky": "Жакшы, <b>{name}</b>! Эми <b>телефон номериңизди</b> калтырыңыз — ал аркылуу сиз менен байланышат.\nТөмөндөгү батырманы басыңыз же номерди колуңуз менен жазыңыз:",
        "en": "Nice to meet you, <b>{name}</b>! Now please share your <b>phone number</b> — we will use it to contact you.\nTap the button below or type your number:",
    },
    "btn_send_phone": {
        "ru": "📱 Отправить номер",
        "ky": "📱 Номерди жөнөтүү",
        "en": "📱 Share my number",
    },
    "invalid_phone": {
        "ru": "Номер не похож на телефон. Напишите в виде 0705121370 или +996705121370:",
        "ky": "Номер туура емес. 0705121370 же +996705121370 түрүндө жазыңыз:",
        "en": "That does not look like a phone number. Use 0705121370 or +996705121370:",
    },
    "ask_photo": {
        "ru": "Спасибо! Теперь пришлите своё <b>фото</b> картинкой — желательно реальное и недавнее, где видно лицо.\nЕсли не хотите — нажмите «Пропустить».",
        "ky": "Рахмат! Эми <b>сүрөтүңүздү</b> жөнөтүңүз — жүзүңүз анык көрүнгөн, жаңы сүрөт болсо жакшы.\nКаалабасаңыз «Өткөрүп жиберүү» батырмасын басыңыз.",
        "en": "Thank you! Now please send your <b>photo</b> as an image — ideally a recent one where your face is visible.\nIf you prefer not to, tap «Skip».",
    },
    "btn_skip": {
        "ru": "Пропустить",
        "ky": "Өткөрүп жиберүү",
        "en": "Skip",
    },
    "ask_photo_again": {
        "ru": "Отправьте фото картинкой или нажмите «Пропустить».",
        "ky": "Сүрөттү сүрөт түрүндө жөнөтүңүз же «Өткөрүп жиберүү» батырмасын басыңыз.",
        "en": "Please send the photo as an image, or tap «Skip».",
    },
    "photo_saved": {
        "ru": "Фото получено, спасибо!",
        "ky": "Сүрөт алынды, рахмат!",
        "en": "Photo received, thank you!",
    },
    "photo_error": {
        "ru": "Не удалось принять фото. Попробуйте ещё раз или нажмите «Пропустить».",
        "ky": "Сүрөттү алуу мүмкүн болгон жок. Кайра аракет кылыңыз же «Өткөрүп жиберүү» басыңыз.",
        "en": "Could not accept the photo. Please try again or tap «Skip».",
    },
    "photo_not_expected": {
        "ru": "Сейчас фото не требуется — ответьте, пожалуйста, текстом.",
        "ky": "Азыр сүрөт керек емес — сураныч, текст менен жооп бериңиз.",
        "en": "A photo is not needed right now — please reply with text.",
    },
    "ask_resume": {
        "ru": "Хорошо! Теперь отправьте краткое <b>резюме</b> текстом — опыт, навыки, достижения.\nИли напишите <b>пропустить</b> чтобы пройти без резюме.",
        "ky": "Жакшы! Эми кыскача <b>резюмеңизди</b> текст түрүндө жөнөтүңүз — тажрыйба, көндүмдөр, жетишкендиктер.\nЖе резюмесиз өтүү үчүн <b>өткөрүп жиберүү</b> деп жазыңыз.",
        "en": "Great! Now send a short <b>resume</b> as text — experience, skills, achievements.\nOr type <b>skip</b> to continue without a resume.",
    },
    "duplicate_application": {
        "ru": "⚠️ Вы уже подавали заявку на эту вакансию.",
        "ky": "⚠️ Сиз бул вакансияга мурда эле арыз бергенсиз.",
        "en": "⚠️ You have already applied for this job.",
    },
    "application_accepted": {
        "ru": "✅ Заявка принята! Переходим к собеседованию.\nОтвечайте спокойно и подробно — так мы лучше вас узнаем. Удачи! 🚀",
        "ky": "✅ Арыз кабыл алынды! Эми аңгемеге өтөбүз.\nСуроолорго жоош жана кеңири жооп бериңиз — биз сизди жакшыраак тааныйбыз. Ийгилик! 🚀",
        "en": "✅ Application accepted! Let's move on to the interview.\nTake your time and answer in detail — it helps us get to know you. Good luck! 🚀",
    },
    "interview_start_error": {
        "ru": "Произошла ошибка при запуске интервью. Попробуйте позже.",
        "ky": "Интервьюну баштоодо ката кетти. Кийинчерээк аракет кылыңыз.",
        "en": "An error occurred while starting the interview. Please try again later.",
    },
    "interview_message_error": {
        "ru": "Произошла ошибка. Попробуйте ещё раз.",
        "ky": "Ката кетти. Кайра аракет кылыңыз.",
        "en": "An error occurred. Please try again.",
    },
    "interview_complete": {
        "ru": "✅ <b>Интервью завершено!</b>\n\nСпасибо за ваше время. Мы обработаем результаты и свяжемся с вами в ближайшее время. 🙏",
        "ky": "✅ <b>Интервью аяктады!</b>\n\nУбактыңыз үчүн рахмат. Биз жыйынтыктарды иштетип, жакында сиз менен байланышабыз. 🙏",
        "en": "✅ <b>Interview completed!</b>\n\nThank you for your time. We will process the results and contact you shortly. 🙏",
    },
    "voice_only_in_interview": {
        "ru": "Голосовые сообщения можно отправлять только во время интервью.",
        "ky": "Үн билдирүүлөрдү интервью учурунда гана жөнөтсө болот.",
        "en": "Voice messages can only be sent during the interview.",
    },
    "voice_download_error": {
        "ru": "Не удалось скачать голосовое сообщение. Попробуйте ещё раз.",
        "ky": "Үн билдирүүсүн жүктөп алуу мүмкүн болгон жок. Кайра аракет кылыңыз.",
        "en": "Failed to download voice message. Please try again.",
    },
    "voice_processing_error": {
        "ru": "Ошибка при обработке голосового сообщения. Попробуйте отправить текстом.",
        "ky": "Үн билдирүүсүн иштетүүдө ката кетти. Текст түрүндө жөнөтүп көрүңүз.",
        "en": "Error processing voice message. Please try sending as text.",
    },
}

TG_SKIP_WORDS: dict[str, tuple[str, ...]] = {
    "ru": ("пропустить", "skip", "-"),
    "ky": ("өткөрүп жиберүү", "skip", "-"),
    "en": ("skip", "-"),
}


def t(key: str, language: str | None = None, **kwargs: str) -> str:
    """Возвращает локализованный текст Telegram-бота по ключу.

    Fallback-порядок: запрошенный язык → русский → пустая строка.
    """
    lang = normalize_language(language)
    entry = TG_TEXTS.get(key, {})
    template = entry.get(lang) or entry.get(DEFAULT_LANGUAGE, "")
    return template.format(**kwargs) if kwargs else template


def is_skip_word(text: str, language: str | None = None) -> bool:
    """Проверяет, означает ли текст «пропустить резюме» на языке кандидата."""
    lang = normalize_language(language)
    words = set(w.lower() for w in TG_SKIP_WORDS.get(lang, TG_SKIP_WORDS[DEFAULT_LANGUAGE]))
    words.update(("skip", "-"))  # универсальный fallback вне зависимости от языка
    return text.strip().lower() in words
