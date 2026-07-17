"""Публичный лендинг — информация о продукте без авторизации.

D3: контент лендинга локализован (RU/KY/EN) через query-параметр ?lang=.
tagline/description/features/pricing/cases отдаются на выбранном языке;
статистика берётся из БД. Дефолт и fallback — русский.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.models import Candidate, Company, Interview

router = APIRouter(tags=["landing"])

SUPPORTED_LANGS = ("ru", "ky", "en")
DEFAULT_LANG = "ru"
FEATURE_ICONS = ["🤖", "🎤", "📊", "📧", "📄", "📦"]


class PricingPlan(BaseModel):
    name: str
    price: str
    currency: str = "сом"
    period: str
    features: list[str]
    highlighted: bool = False


class UseCase(BaseModel):
    industry: str
    challenge: str
    solution: str
    outcome: str


class LandingStats(BaseModel):
    companies: int
    interviews_conducted: int
    candidates_processed: int
    avg_time_saved_hours: int


class LandingResponse(BaseModel):
    product_name: str
    lang: str
    tagline: str
    description: str
    market: str
    stats: LandingStats
    features: list[dict]
    pricing: list[PricingPlan]
    cases: list[UseCase]
    contact_email: str


def _features(items: list[tuple[str, str]]) -> list[dict]:
    return [
        {"icon": FEATURE_ICONS[i], "title": title, "description": desc}
        for i, (title, desc) in enumerate(items)
    ]


_CONTENT: dict = {
    "ru": {
        "tagline": "Нанимайте лучших в 10× быстрее",
        "description": (
            "SaaS-платформа для автоматизированного скрининга кандидатов. "
            "Компании публикуют вакансии, кандидаты проходят AI-интервью, "
            "HR получает ранжированный список с оценками без траты времени."
        ),
        "market": "Кыргызстан → СНГ",
        "features": _features([
            ("AI-интервью", "Кандидат проходит структурированное интервью с AI без участия HR"),
            ("Голосовые ответы", "Кандидат может отвечать голосом через Whisper STT"),
            ("AI-скоринг", "Каждый кандидат получает оценку 0–100 и рекомендацию hire/maybe/reject"),
            ("Уведомления", "HR получает Telegram + Email при каждом новом кандидате"),
            ("Экспорт отчётов", "Скачивайте CSV и PDF отчёты по кандидатам"),
            ("Kanban доска", "Визуально управляйте воронкой найма по колонкам"),
        ]),
        "pricing": [
            {"name": "Free", "price": "0", "period": "навсегда",
             "features": ["5 кандидатов/месяц", "1 вакансия", "AI-интервью", "Email уведомления"]},
            {"name": "Starter", "price": "4900", "period": "месяц", "highlighted": True,
             "features": ["50 кандидатов/месяц", "3 вакансии", "Голосовые интервью", "Telegram бот", "CSV экспорт"]},
            {"name": "Pro", "price": "12900", "period": "месяц",
             "features": ["300 кандидатов/месяц", "Далее 45 сом за кандидата", "Безлимит вакансий", "PDF отчёты", "Аналитика Dashboard", "Приоритетная поддержка"]},
        ],
        "cases": [
            {"industry": "IT / Разработка",
             "challenge": "Сотни откликов на вакансию, мало времени на живые интервью",
             "solution": "AI проводит первичное техническое интервью и anti-cheat проверку",
             "outcome": "HR смотрит только топ кандидатов"},
            {"industry": "Ритейл / Массовый наём",
             "challenge": "Высокий поток кандидатов на линейные позиции",
             "solution": "Кандидаты проходят интервью в Telegram на своём языке (KY/RU)",
             "outcome": "Скрининг идёт круглосуточно без рекрутера"},
            {"industry": "Аутсорсинг / Агентства",
             "challenge": "Нужно быстро оценивать кандидатов для разных клиентов",
             "solution": "Отдельные вакансии с настраиваемыми весами скоринга",
             "outcome": "Ранжированный short-list за минуты"},
        ],
    },
    "ky": {
        "tagline": "Эң мыктыларды 10× тез жалданыз",
        "description": (
            "Талапкерлерди автоматтык скринингден өткөрүүчү SaaS-платформа. "
            "Компаниялар вакансия жарыялайт, талапкерлер AI-интервьюден өтөт, "
            "HR баалары менен иреттелген тизмени убакыт кетирбей алат."
        ),
        "market": "Кыргызстан → КМШ",
        "features": _features([
            ("AI-интервью", "Талапкер HR катышпай AI менен түзүмдүү интервьюден өтөт"),
            ("Үндүк жооптор", "Талапкер Whisper STT аркылуу үн менен жооп бере алат"),
            ("AI-скоринг", "Ар бир талапкер 0–100 баа жана hire/maybe/reject сунушун алат"),
            ("Билдирүүлөр", "HR ар жаңы талапкерге Telegram + Email алат"),
            ("Отчетторду экспорттоо", "Талапкерлер боюнча CSV жана PDF отчетторун жүктөңүз"),
            ("Kanban такта", "Жалдоо воронкасын колонкалар менен башкарыңыз"),
        ]),
        "pricing": [
            {"name": "Free", "price": "0", "period": "туулабай",
             "features": ["айына 5 талапкер", "1 вакансия", "AI-интервью", "Email билдирүүлөр"]},
            {"name": "Starter", "price": "4900", "period": "ай", "highlighted": True,
             "features": ["айына 50 талапкер", "3 вакансия", "Үндүк интервью", "Telegram бот", "CSV экспорт"]},
            {"name": "Pro", "price": "12900", "period": "ай",
             "features": ["айына 300 талапкер", "андан ары талапкерге 45 сом", "чексиз вакансия", "PDF отчеттор", "Dashboard аналитика", "Приоритеттүү колдоо"]},
        ],
        "cases": [
            {"industry": "IT / Ийгилик",
             "challenge": "Вакансияга жүздөгөн арыз, жандуу интервьюгө убакыт аз",
             "solution": "AI баштапкы техникалык интервью жана anti-cheat текшерүүнү жүргүзөт",
             "outcome": "HR биртоп талапкерлерди гана көрөт"},
            {"industry": "Ритейл / Көпчүлүк жалдоо",
             "challenge": "Сызыктуу кызматтарга талапкерлердин көп агымы",
             "solution": "Талапкерлер Telegramде өз тилинде (KY/RU) интервьюден өтөт",
             "outcome": "Скрининг рекрутерсиз түнкө-күндү иштейт"},
            {"industry": "Аутсорсинг / Агенттиктер",
             "challenge": "Ар кылан клиенттер үчүн талапкерлерди тез баалоо керек",
             "solution": "Скоринг салмактары жөнгө салынуучу өбөлөк вакансиялар",
             "outcome": "Иреттелген short-list мүнөттөрдө"},
        ],
    },
    "en": {
        "tagline": "Hire the best 10× faster",
        "description": (
            "A SaaS platform for automated candidate screening. "
            "Companies post jobs, candidates take AI interviews, "
            "and HR gets a ranked, scored shortlist without spending hours."
        ),
        "market": "Kyrgyzstan → CIS",
        "features": _features([
            ("AI interviews", "Candidates take a structured interview with AI, no HR needed"),
            ("Voice answers", "Candidates can answer by voice via Whisper STT"),
            ("AI scoring", "Every candidate gets a 0–100 score and a hire/maybe/reject recommendation"),
            ("Notifications", "HR gets Telegram + Email on every new candidate"),
            ("Report export", "Download CSV and PDF reports on candidates"),
            ("Kanban board", "Visually manage your hiring funnel by columns"),
        ]),
        "pricing": [
            {"name": "Free", "price": "0", "period": "forever",
             "features": ["5 candidates/month", "1 job", "AI interviews", "Email notifications"]},
            {"name": "Starter", "price": "4900", "period": "month", "highlighted": True,
             "features": ["50 candidates/month", "3 jobs", "Voice interviews", "Telegram bot", "CSV export"]},
            {"name": "Pro", "price": "12900", "period": "month",
             "features": ["300 candidates/month", "Then 45 KGS per candidate", "Unlimited jobs", "PDF reports", "Analytics dashboard", "Priority support"]},
        ],
        "cases": [
            {"industry": "IT / Engineering",
             "challenge": "Hundreds of applicants per role, little time for live interviews",
             "solution": "AI runs the first technical interview and an anti-cheat check",
             "outcome": "HR only reviews the top candidates"},
            {"industry": "Retail / High-volume hiring",
             "challenge": "A large flow of candidates for frontline roles",
             "solution": "Candidates interview in Telegram in their own language (KY/RU)",
             "outcome": "Screening runs 24/7 without a recruiter"},
            {"industry": "Outsourcing / Agencies",
             "challenge": "Need to evaluate candidates fast across different clients",
             "solution": "Separate jobs with configurable scoring weights",
             "outcome": "A ranked short-list in minutes"},
        ],
    },
}


@router.get("/landing", response_model=LandingResponse, summary="Публичная информация о продукте")
def get_landing(
    lang: str = Query(default=DEFAULT_LANG, description="ru | ky | en"),
    db: Session = Depends(get_db),
) -> LandingResponse:
    """Возвращает локализованную публичную информацию для лендинга."""
    lang = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
    c = _CONTENT[lang]

    companies_count = db.query(func.count(Company.id)).scalar() or 0
    interviews_count = db.query(func.count(Interview.id)).scalar() or 0
    candidates_count = db.query(func.count(Candidate.id)).scalar() or 0

    return LandingResponse(
        product_name="HireLens",
        lang=lang,
        tagline=c["tagline"],
        description=c["description"],
        market=c["market"],
        stats=LandingStats(
            companies=companies_count,
            interviews_conducted=interviews_count,
            candidates_processed=candidates_count,
            avg_time_saved_hours=8,
        ),
        features=c["features"],
        pricing=[PricingPlan(**p) for p in c["pricing"]],
        cases=[UseCase(**u) for u in c["cases"]],
        contact_email="contact@gethirelens.tech",
    )
