"""Алерт ВЛАДЕЛЬЦУ сервиса о расходе месячной квоты кандидатов.

Зачем: 27.07.2026 у клиента (company #16) лимит стартера в 50 кандидатов
закончился за четыре дня. Заявки молча отклонялись, клиент причины не знал,
владелец узнал случайно. Баннер на дашборде предупреждает КЛИЕНТА,
этот модуль — ВЛАДЕЛЬЦА, чтобы можно было связаться и поднять тариф заранее.

Письмо уходит на SUPERADMIN_EMAILS не чаще одного раза на порог в календарный
месяц: 80% («скоро упрётся») и 100% («заявки уже блокируются»).
Дедупликация — по журналу audit_logs, поэтому новая таблица и миграция
не нужны. Отправка best-effort: любая ошибка только логируется и никогда
не ломает подачу заявки кандидатом.
"""
import logging
import threading

from app.core.audit import record_audit
from app.core.config import settings
from app.core.db import SessionLocal
# _month_start переиспользуем намеренно: границы месяца обязаны совпадать
# с enforcement, иначе алерт и блокировка разойдутся на стыке месяцев.
from app.core.plans import _month_start, candidates_this_month, effective_plan, limits_for
from app.models.audit_log import AuditLog
from app.models.company import Company
# Переиспользуем настроенный SMTP-транспорт, чтобы не дублировать конфиг.
from app.services.email import _send_email

logger = logging.getLogger(__name__)

# Порог предупреждения совпадает с порогом баннера на дашборде (80%).
WARN_RATIO = 0.8

ACTION_WARN = "quota.alert.warn"
ACTION_FULL = "quota.alert.full"


def _already_sent(db, company_id: int, action: str) -> bool:
    """Уже отправляли такой алерт этой компании в текущем месяце?"""
    return (
        db.query(AuditLog)
        .filter(
            AuditLog.company_id == company_id,
            AuditLog.action == action,
            AuditLog.created_at >= _month_start(),
        )
        .first()
        is not None
    )


def _build_html(company: Company, plan: str, used: int, limit: int, is_full: bool) -> str:
    if is_full:
        headline = "Лимит кандидатов исчерпан — заявки блокируются"
        color = "#DC2626"
        lead = (
            "Новые отклики на вакансии этой компании больше не принимаются. "
            "Кандидаты видят сообщение о временной приостановке приёма заявок."
        )
    else:
        headline = "Клиент приближается к лимиту кандидатов"
        color = "#D97706"
        lead = "Стоит связаться с клиентом и предложить повышение тарифа заранее."

    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {color};">{headline}</h2>
        <p>{lead}</p>
        <table style="border-collapse: collapse; width: 100%;">
            <tr><td style="padding: 8px; color: #6B7280;">Компания:</td>
                <td style="padding: 8px;"><strong>{company.name}</strong> (id {company.id})</td></tr>
            <tr><td style="padding: 8px; color: #6B7280;">Email:</td>
                <td style="padding: 8px;">{company.email}</td></tr>
            <tr><td style="padding: 8px; color: #6B7280;">Тариф:</td>
                <td style="padding: 8px;">{plan}</td></tr>
            <tr><td style="padding: 8px; color: #6B7280;">Кандидатов за месяц:</td>
                <td style="padding: 8px;"><strong>{used} из {limit}</strong></td></tr>
        </table>
        <p style="margin-top: 20px;">
            <a href="{settings.FRONTEND_URL}/admin"
               style="background: {color}; color: white; padding: 10px 20px;
                      text-decoration: none; border-radius: 6px;">
                Открыть админку
            </a>
        </p>
        <p style="color: #9CA3AF; font-size: 12px; margin-top: 30px;">
            HireLens · счётчик обнулится 1-го числа следующего месяца
        </p>
    </div>
    """


def check_candidate_quota(company_id: int) -> None:
    """Проверяет расход квоты компании и при необходимости шлёт алерт владельцу.

    Открывает собственную сессию: вызывается из фонового потока, где сессия
    запроса уже может быть закрыта.
    """
    recipients = sorted(settings.superadmin_emails)
    if not recipients:
        return

    db = SessionLocal()
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if company is None:
            return

        limit = limits_for(company)["max_candidates_per_month"]
        if not limit:  # безлимитный тариф — предупреждать не о чем
            return

        used = candidates_this_month(db, company.id)
        if used >= limit:
            action, is_full = ACTION_FULL, True
        elif used >= limit * WARN_RATIO:
            action, is_full = ACTION_WARN, False
        else:
            return

        if _already_sent(db, company.id, action):
            return

        plan = effective_plan(company)
        subject = (
            f"HireLens: у «{company.name}» исчерпан лимит кандидатов ({used}/{limit})"
            if is_full
            else f"HireLens: «{company.name}» близка к лимиту кандидатов ({used}/{limit})"
        )
        html = _build_html(company, plan, used, limit, is_full)

        sent_any = False
        for to in recipients:
            if _send_email(to, subject, html):
                sent_any = True

        # Метку ставим и при неудачной отправке тоже — иначе при сломанном SMTP
        # каждая новая заявка будет пытаться слать письмо заново.
        record_audit(
            db,
            company_id=company.id,
            action=action,
            actor_type="system",
            detail={"used": used, "limit": limit, "plan": plan, "sent": sent_any},
        )
        logger.info(
            "Квота-алерт (%s) для компании #%s: %s/%s, отправлено=%s",
            action, company.id, used, limit, sent_any,
        )
    except Exception as e:
        logger.warning("Не удалось проверить квоту компании #%s: %s", company_id, e)
    finally:
        db.close()


def check_candidate_quota_async(company_id: int) -> None:
    """Фоновый запуск: SMTP медленный, подачу заявки задерживать нельзя."""
    try:
        threading.Thread(
            target=check_candidate_quota, args=(company_id,), daemon=True
        ).start()
    except Exception as e:
        logger.warning("Не удалось запустить проверку квоты (#%s): %s", company_id, e)
